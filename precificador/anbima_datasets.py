"""Datasets do ANBIMA Data — os que têm arquivo aberto, puxados por data.

A página ``data.anbima.com.br/datasets`` lista uns 25 datasets. Ela **não** é
uma fonte que se possa ler por fora: a grade de cada dataset vem de
``data-api.prd.anbima.com.br/web-bff``, que responde ``401 — token cannot be
blank`` a quem não traz o token de sessão que a própria página gera — e o
``env-config`` dela carrega uma chave de reCAPTCHA. Reproduzir esse token seria
contornar a proteção deles; não é o caminho.

O caminho é o mesmo do boletim de títulos públicos (``anbima.py``): a ANBIMA
publica parte desses dados como **arquivo de texto por data**, aberto, com os
mesmos números do dataset. Para cada dataset do catálogo, este módulo diz se há
arquivo aberto e, havendo, sabe baixá-lo e lê-lo.

Os arquivos têm o mesmo formato — latin-1, separados por ``@``, uma linha de
cabeçalho — e por isso um leitor só serve a todos. Os valores ficam como a
ANBIMA os publica (``0,8587``, ``N/D``, ``--``): é um visualizador de dataset,
e a tela mostra o que a fonte disse, não uma interpretação dele.

Quem precisar dos restritos tem a rota oficial: a API ANBIMA Feed
(``developers.anbima.com.br``), com credencial de associado. Ela não entra
aqui sem a credencial, e a credencial não entra digitada em lugar nenhum.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from . import rede
from .calendario import para_data
from .erros import ErroDeFonte

PAGINA_DATASETS = "https://data.anbima.com.br/datasets"

PUBLICO = "publico"
RESTRITO = "restrito"


class ErroDataset(ErroDeFonte):
    """O arquivo do dataset não veio — data sem publicação, ou falha de rede."""


@dataclass(frozen=True)
class Dataset:
    slug: str                        # o mesmo do endereço no ANBIMA Data
    nome: str
    grupo: str
    descricao: str
    acesso: str = PUBLICO
    arquivo: Optional[str] = None    # molde da URL por data; None = sem arquivo aberto
    busca: int = 0                   # coluna pela qual a tela filtra primeiro

    @property
    def disponivel(self) -> bool:
        return self.arquivo is not None

    @property
    def endereco(self) -> str:
        return f"{PAGINA_DATASETS}/{self.slug}/detalhes"


# O catálogo do ANBIMA Data, na ordem da página. Os dois com ``arquivo`` são os
# que a ANBIMA publica abertos por data; o resto aponta para a página dela.
CATALOGO: List[Dataset] = [
    Dataset("titulos-publicos-precificacao-anbima", "Títulos Públicos - Precificação ANBIMA",
            "Mercado Secundário",
            "Taxas indicativas, PU e intervalos de LTN, NTN-F, NTN-B, NTN-C e LFT.",
            arquivo="https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{data:%y%m%d}.txt",
            busca=0),
    Dataset("data-debentures-precificacao-anbima", "Debêntures - Precificação ANBIMA",
            "Mercado Secundário",
            "Taxas de compra, venda e indicativa, PU, % do PU par, duration e NTN-B de "
            "referência das debêntures.",
            arquivo="https://www.anbima.com.br/informacoes/merc-sec-debentures/arqs/"
                    "db{data:%y%m%d}.txt",
            busca=1),
    Dataset("cris-cras-precificacao-anbima", "CRIs e CRAs - Precificação ANBIMA",
            "Mercado Secundário", "Taxas indicativas de CRIs e CRAs."),
    Dataset("data-titulos-publicos-dados-negociacao-publico",
            "Títulos públicos - Dados de negociação (público)", "Mercado Secundário",
            "Pré e pós-trade consolidados de títulos públicos federais."),
    Dataset("previas-do-reune", "Títulos Privados - Negociações (Prévias do REUNE)",
            "Mercado Secundário", "Negociações de debêntures, CRIs, CRAs e CFFs por ticker."),
    Dataset("ofertas-publicas-boletim-consolidado", "Ofertas públicas - Boletim consolidado",
            "Mercado Primário", "Estatísticas de operações de mercado de capitais."),
    Dataset("fundos-175-caracteristicas-publico", "Fundos 175 - Características (público)",
            "Fundos de Investimento", "Cadastro da base de Fundos 175."),
    Dataset("fundos-175-dados-periodicos-publico", "Fundos 175 - Dados periódicos (público)",
            "Fundos de Investimento", "Dados periódicos dos Fundos 175."),
    Dataset("data-carteira-teorica-ihfa-publico", "Carteira Teórica - IHFA (público)",
            "Índices", "Composição teórica do IHFA nos dois últimos trimestres."),
    Dataset("titulos-privados-caracteristicas", "Títulos Privados - Características (restrito)",
            "Mercado Secundário", "Cadastro de debêntures, CRIs e CRAs.", acesso=RESTRITO),
    Dataset("titulos-privados-agenda-de-eventos", "Títulos Privados - Agenda de Eventos (restrito)",
            "Mercado Secundário", "Eventos de debêntures, CRIs e CRAs.", acesso=RESTRITO),
    Dataset("ofertas-publicas-series", "Ofertas públicas - Séries (restrito)",
            "Mercado Primário", "Características das séries emitidas.", acesso=RESTRITO),
    Dataset("data-titulos-publicos-dados-negociacao-restrito",
            "Títulos públicos - Dados de negociação (restrito)", "Mercado Secundário",
            "Pré e pós-trade de títulos públicos, detalhado.", acesso=RESTRITO),
    Dataset("data-titulos-publicos-dados-negociacao-selic-restrito",
            "Títulos públicos - Dados de negociação SELIC (restrito)", "Mercado Secundário",
            "Operações registradas no SELIC.", acesso=RESTRITO),
]

POR_SLUG = {d.slug: d for d in CATALOGO}
DISPONIVEIS = [d for d in CATALOGO if d.disponivel]


@dataclass
class Tabela:
    dataset: Dataset
    referencia: date
    colunas: List[str]
    linhas: List[List[str]] = field(default_factory=list)


def ler(conteudo: str) -> tuple:
    """``(colunas, linhas)`` de um arquivo ``@`` da ANBIMA.

    O cabeçalho é a primeira linha com o maior número de campos — antes dele
    vem o nome da associação e uma linha em branco. Linha com outro número de
    campos (rodapé, título de seção) fica de fora.
    """
    partidas = [l.split("@") for l in conteudo.splitlines() if "@" in l]
    if not partidas:
        return [], []
    largura = max(len(p) for p in partidas)
    candidatas = [p for p in partidas if len(p) == largura]
    cabecalho = [" ".join(c.split()) for c in candidatas[0]]
    linhas = [[c.strip() for c in p] for p in candidatas[1:] if any(c.strip() for c in p)]
    # coluna vazia no fim do cabeçalho (o "@" final) não é coluna
    while cabecalho and not cabecalho[-1]:
        cabecalho.pop()
        linhas = [l[:len(cabecalho)] for l in linhas]
    return cabecalho, linhas


def baixar(slug: str, referencia, timeout: int = 40) -> Tabela:
    dataset = POR_SLUG.get(slug)
    if dataset is None:
        raise ErroDataset("dataset desconhecido: {slug}", slug=slug)
    if not dataset.disponivel:
        raise ErroDataset("{nome} não tem arquivo aberto na ANBIMA — ele só se consulta "
                          "no ANBIMA Data.", nome=dataset.nome)
    dia = para_data(referencia)
    try:
        bruto = rede.obter(dataset.arquivo.format(data=dia), timeout=timeout)
    except rede.ErroRede as exc:
        if getattr(exc, "status", None) == 404:
            raise ErroDataset(
                "a ANBIMA não publicou {nome} para {data}. Ou não foi dia útil, ou a "
                "data é antiga demais — ela mantém só algumas semanas de arquivos.",
                nome=dataset.nome, data=f"{dia:%d/%m/%Y}") from exc
        raise ErroDataset("não foi possível obter {nome}: {motivo}",
                          nome=dataset.nome, motivo=str(exc)) from exc
    colunas, linhas = ler(bruto.decode("latin-1"))
    if not linhas:
        raise ErroDataset("{nome} de {data} veio sem linhas", nome=dataset.nome,
                          data=f"{dia:%d/%m/%Y}")
    return Tabela(dataset=dataset, referencia=dia, colunas=colunas, linhas=linhas)


def para_csv(tabela: Tabela) -> str:
    """CSV com ``;`` — o separador que o Excel em português abre sem perguntar."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(tabela.colunas)
    escritor.writerows(tabela.linhas)
    return saida.getvalue()
