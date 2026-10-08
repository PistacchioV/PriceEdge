"""Datasets do ANBIMA Data — puxados pela porta que cada um tem, e salvos localmente.

A página ``data.anbima.com.br/datasets`` lista os datasets da ANBIMA, mas a grade
de cada um vem de ``data-api.prd.anbima.com.br/web-bff``, que responde ``401 —
token cannot be blank`` sem o token de sessão que a própria página gera, com
reCAPTCHA. Reproduzir esse token seria contornar a proteção deles; não é o
caminho. Cada dataset entra por uma de três portas legítimas:

``DIARIO``      A ANBIMA publica o dataset como arquivo de texto aberto, um por
                data (títulos públicos, debêntures). Consulta-se por data.

``CMS``         O dataset público inteiro é um ``.xlsx`` publicado no CMS do
                ANBIMA Data (``data-strapi.prd.anbima.com.br``), cuja API de
                conteúdo é aberta. É uma fotografia, não uma série: a data é a
                da publicação, e ela pode ter meses.

``IMPORTACAO``  Sem arquivo aberto. A pessoa baixa o arquivo no ANBIMA Data, no
                próprio navegador — passando pelo que a página pedir, como
                usuária —, e solta aqui. É a mesma ideia da importação do Term
                SOFR: quem tem acesso traz o arquivo.

**O CMS também guarda os restritos.** As versões restritas dos Fundos 175 estão
lá com endereço acessível. Isso é configuração, não permissão: o dado é para
associados, e por isso a porta ``CMS`` só existe para dataset **público**. Um
associado que baixe o restrito no ANBIMA Data, logado, importa o arquivo dele.

**Tudo o que entra é salvo localmente**, em ``dados/anbima/<slug>/``, um
arquivo por data, no formato original. É o que faz o histórico passar da janela
curta que a ANBIMA mantém aberta. A pasta é ignorada pelo git — o repositório é
público, e dado de terceiro (às vezes restrito) não sai da máquina de quem o
baixou.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from . import planilha, rede
from .calendario import para_data
from .erros import ErroDeFonte

PAGINA_DATASETS = "https://data.anbima.com.br/datasets"
CMS = "https://data-strapi.prd.anbima.com.br"
PASTA = Path(__file__).resolve().parent / "dados" / "anbima"

DIARIO = "diario"
CMS_PUBLICO = "cms"
IMPORTACAO = "importacao"

PUBLICO = "publico"
RESTRITO = "restrito"

EXTENSOES_ACEITAS = (".xlsx", ".csv", ".tsv", ".txt")
# o que a pessoa pode soltar: o ANBIMA Data entrega ".xls" que por dentro é .xlsx
EXTENSOES_DE_ENTRADA = EXTENSOES_ACEITAS + (".xls",)
_COLUNAS_DE_DATA = ("data de referencia", "data referencia")


class ErroDataset(ErroDeFonte):
    """O dataset não veio — data sem publicação, arquivo ilegível ou falha de rede."""


@dataclass(frozen=True)
class Dataset:
    slug: str                        # o do endereço no ANBIMA Data
    nome: str
    grupo: str
    descricao: str
    acesso: str = PUBLICO
    fonte: str = IMPORTACAO
    arquivo: Optional[str] = None    # DIARIO: molde da URL por data
    slug_cms: Optional[str] = None   # CMS: o slug no CMS, quando difere

    @property
    def disponivel(self) -> bool:
        """Puxado sem a pessoa trazer o arquivo."""
        return self.fonte in (DIARIO, CMS_PUBLICO)

    @property
    def endereco(self) -> str:
        return f"{PAGINA_DATASETS}/{self.slug}/detalhes"


CATALOGO: List[Dataset] = [
    Dataset("titulos-publicos-precificacao-anbima", "Títulos Públicos - Precificação ANBIMA",
            "Mercado Secundário",
            "Taxas indicativas, PU e intervalos de LTN, NTN-F, NTN-B, NTN-C e LFT.",
            fonte=DIARIO,
            arquivo="https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{data:%y%m%d}.txt"),
    Dataset("data-debentures-precificacao-anbima", "Debêntures - Precificação ANBIMA",
            "Mercado Secundário",
            "Taxas de compra, venda e indicativa, PU, % do PU par, duration e NTN-B de "
            "referência das debêntures.",
            fonte=DIARIO,
            arquivo="https://www.anbima.com.br/informacoes/merc-sec-debentures/arqs/"
                    "db{data:%y%m%d}.txt"),
    Dataset("fundos-175-caracteristicas-publico", "Fundos 175 - Características (público)",
            "Fundos de Investimento", "Cadastro da base de Fundos 175.", fonte=CMS_PUBLICO),
    Dataset("fundos-175-dados-periodicos-publico", "Fundos 175 - Dados periódicos (público)",
            "Fundos de Investimento", "Dados periódicos dos Fundos 175.", fonte=CMS_PUBLICO),
    Dataset("cris-cras-precificacao-anbima", "CRIs e CRAs - Precificação ANBIMA",
            "Mercado Secundário", "Taxas indicativas de CRIs e CRAs."),
    Dataset("data-titulos-publicos-dados-negociacao-publico",
            "Títulos públicos - Dados de negociação (público)", "Mercado Secundário",
            "Pré e pós-trade consolidados de títulos públicos federais."),
    Dataset("previas-do-reune", "Títulos Privados - Negociações (Prévias do REUNE)",
            "Mercado Secundário", "Negociações de debêntures, CRIs, CRAs e CFFs por ticker."),
    Dataset("ofertas-publicas-boletim-consolidado", "Ofertas públicas - Boletim consolidado",
            "Mercado Primário", "Estatísticas de operações de mercado de capitais."),
    Dataset("data-carteira-teorica-ihfa-publico", "Carteira Teórica - IHFA (público)",
            "Índices", "Composição teórica do IHFA nos dois últimos trimestres."),
    Dataset("data-composicao-carteira-diaria-ihfa-publico",
            "Composição da Carteira Diária - IHFA (público)", "Índices",
            "Composição diária do IHFA nos últimos cinco dias úteis."),
    Dataset("data-resumo-indice-ihfa-publico", "Resumo do IHFA (público)", "Índices",
            "Histórico de resultados diários do IHFA."),
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


def dataset(slug: str) -> Dataset:
    achado = POR_SLUG.get(slug or "")
    if achado is None:
        raise ErroDataset("dataset desconhecido: {slug}", slug=slug)
    return achado


# ---------------------------------------------------------------- leitura

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
    while cabecalho and not cabecalho[-1]:           # o "@" final não é coluna
        cabecalho.pop()
        linhas = [l[:len(cabecalho)] for l in linhas]
    return cabecalho, linhas


def ler_arquivo(nome: str, dados: bytes) -> tuple:
    """``(colunas, linhas)`` de qualquer formato que entra aqui."""
    if nome.lower().endswith(".txt") and planilha.formato(dados) == planilha.TEXTO:
        return ler(dados.decode("latin-1"))
    try:
        linhas = planilha.ler(nome, dados)
    except planilha.ErroPlanilha as exc:
        raise ErroDataset.de(exc) from exc
    linhas = [l for l in linhas if any((c or "").strip() for c in l)]
    if not linhas:
        return [], []
    largura = max(len(l) for l in linhas)
    cabecalho = [(c or "").strip() for c in linhas[0]] + [""] * (largura - len(linhas[0]))
    corpo = [[(c or "").strip() for c in l] + [""] * (largura - len(l)) for l in linhas[1:]]
    return cabecalho, corpo


# coluna de data: o nome diz. "Data Referencia", "Data Base/Emissao", "Data
# Vencimento", "Repac./ Venc.", "Data de Início de Atividade"…
_NOME_DE_DATA = re.compile(r"\bdata\b|venc|repac", re.IGNORECASE)
_AAAAMMDD = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")


def _data_br(valor: str) -> str:
    """``20261007`` / ``2026-10-07`` → ``07/10/2026``. O que não é data volta igual."""
    texto = (valor or "").strip()
    achado = _AAAAMMDD.match(texto) or _ISO.match(texto)
    if not achado:
        # o .xlsx guarda data como número de série (45418 = 07/05/2024); só
        # vale aqui porque a coluna já é de data — noutra seria um número
        if re.fullmatch(r"\d{5}(?:\.0+)?", texto):
            dia = planilha.como_data(texto)
            return dia.strftime("%d/%m/%Y") if dia else valor
        return valor
    ano, mes, dia = (int(x) for x in achado.groups())
    if not 1900 <= ano <= 2200:
        return valor
    try:
        return date(ano, mes, dia).strftime("%d/%m/%Y")
    except ValueError:
        return valor                       # 20261399 não é data: fica como veio


def datas_em_formato_br(colunas: List[str], linhas: List[List[str]]) -> List[List[str]]:
    """Datas em dd/mm/aaaa nas colunas de data — na tela e no CSV.

    O boletim de títulos públicos escreve ``20261007``; o cadastro de fundos,
    ``2023-01-24``. Os dois viram o formato da mesa. A regra só age em coluna
    cujo **nome** é de data e em valor que **é** uma data válida: um número de
    oito dígitos noutra coluna fica como está.
    """
    alvos = [i for i, c in enumerate(colunas) if _NOME_DE_DATA.search(c or "")]
    if not alvos:
        return linhas
    saida = []
    for linha in linhas:
        nova = list(linha)
        for i in alvos:
            if i < len(nova):
                nova[i] = _data_br(nova[i])
        saida.append(nova)
    return saida


# -------------------------------------------------------- base local ---

def _pasta(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug or ""):        # o slug vira caminho
        raise ErroDataset("dataset desconhecido: {slug}", slug=slug)
    return PASTA / slug


@dataclass
class Salvo:
    dataset: Dataset
    referencia: date
    arquivo: Path
    origem: str                      # DIARIO / CMS / IMPORTACAO
    nome_original: str
    salvo_em: str
    tamanho: int


def salvar(slug: str, referencia, nome_original: str, dados: bytes, origem: str) -> Salvo:
    """Grava o arquivo como veio, mais uma ficha de onde ele veio.

    Formato original e não convertido: é a cópia fiel do que a ANBIMA
    publicou, e o leitor daqui pode melhorar sem ser preciso baixar de novo.
    Mesma data, mesmo dataset: a nova substitui a antiga.
    """
    ds = dataset(slug)
    dia = para_data(referencia)
    extensao = Path(nome_original).suffix.lower()
    if extensao not in EXTENSOES_DE_ENTRADA:
        raise ErroDataset("{arquivo}: use .xlsx, .csv, .tsv ou o .txt da ANBIMA — o .xls "
                          "antigo precisa ser salvo de novo como .xlsx.",
                          arquivo=nome_original)
    # gravado com a extensão do que o arquivo É: o ".xls" do ANBIMA Data é .xlsx
    if planilha.formato(dados) == planilha.XLSX:
        extensao = ".xlsx"
    pasta = _pasta(ds.slug)
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob(f"{dia.isoformat()}.*"):
        antigo.unlink()
    destino = pasta / f"{dia.isoformat()}{extensao}"
    destino.write_bytes(dados)
    ficha = {"origem": origem, "nome_original": nome_original,
             "salvo_em": datetime.now().isoformat(timespec="seconds")}
    (pasta / f"{dia.isoformat()}.ficha.json").write_text(
        json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
    return Salvo(ds, dia, destino, origem, nome_original, ficha["salvo_em"], len(dados))


def salvos(slug: str) -> List[Salvo]:
    """O que está guardado de um dataset, do mais recente ao mais antigo."""
    ds = dataset(slug)
    pasta = _pasta(ds.slug)
    if not pasta.exists():
        return []
    saida = []
    for arquivo in pasta.iterdir():
        if arquivo.name.endswith(".ficha.json") or arquivo.suffix.lower() not in EXTENSOES_ACEITAS:
            continue
        try:
            dia = date.fromisoformat(arquivo.stem)
        except ValueError:
            continue
        ficha_arq = pasta / f"{arquivo.stem}.ficha.json"
        ficha = json.loads(ficha_arq.read_text(encoding="utf-8")) if ficha_arq.exists() else {}
        saida.append(Salvo(ds, dia, arquivo, ficha.get("origem", ""),
                           ficha.get("nome_original", arquivo.name),
                           ficha.get("salvo_em", ""), arquivo.stat().st_size))
    return sorted(saida, key=lambda s: s.referencia, reverse=True)


def abrir(slug: str, referencia) -> Tabela:
    """A tabela de uma data já salva — sem rede."""
    dia = para_data(referencia)
    for s in salvos(slug):
        if s.referencia == dia:
            colunas, linhas = ler_arquivo(s.arquivo.name, s.arquivo.read_bytes())
            return Tabela(s.dataset, dia, colunas, datas_em_formato_br(colunas, linhas))
    raise ErroDataset("não há {nome} salvo para {data}", nome=dataset(slug).nome,
                      data=f"{dia:%d/%m/%Y}")


# ------------------------------------------------------------- portas ---

def _obter(url: str, nome: str, dia: Optional[date] = None, timeout: int = 60) -> bytes:
    try:
        return rede.obter(url, timeout=timeout)
    except rede.ErroRede as exc:
        if getattr(exc, "status", None) == 404 and dia is not None:
            raise ErroDataset(
                "a ANBIMA não publicou {nome} para {data}. Ou não foi dia útil, ou a "
                "data é antiga demais — ela mantém só algumas semanas de arquivos.",
                nome=nome, data=f"{dia:%d/%m/%Y}") from exc
        raise ErroDataset("não foi possível obter {nome}: {motivo}",
                          nome=nome, motivo=str(exc)) from exc


def baixar(slug: str, referencia, timeout: int = 40) -> Tabela:
    """Porta DIARIO: baixa a data, salva localmente e devolve a tabela."""
    ds = dataset(slug)
    if ds.fonte != DIARIO:
        raise ErroDataset("{nome} não tem arquivo aberto por data na ANBIMA — ele só se "
                          "consulta no ANBIMA Data.", nome=ds.nome)
    dia = para_data(referencia)
    bruto = _obter(ds.arquivo.format(data=dia), ds.nome, dia, timeout)
    colunas, linhas = ler(bruto.decode("latin-1"))
    if not linhas:
        raise ErroDataset("{nome} de {data} veio sem linhas", nome=ds.nome,
                          data=f"{dia:%d/%m/%Y}")
    salvar(ds.slug, dia, f"{ds.slug}_{dia:%y%m%d}.txt", bruto, DIARIO)
    return Tabela(ds, dia, colunas, datas_em_formato_br(colunas, linhas))


def versao_publicada(slug: str) -> dict:
    """O arquivo que o CMS tem para um dataset público: ``{url, nome, data}``."""
    ds = dataset(slug)
    if ds.fonte != CMS_PUBLICO or ds.acesso != PUBLICO:
        raise ErroDataset("{nome} não tem arquivo público publicado no ANBIMA Data.",
                          nome=ds.nome)
    alvo = quote(ds.slug_cms or ds.slug)
    url = (f"{CMS}/api/datasets?filters%5Bslug%5D%5B%24eq%5D={alvo}"
           "&populate%5Battachment%5D%5Bpopulate%5D=*")
    try:
        resposta = rede.obter_json(url, timeout=40)
    except rede.ErroRede as exc:
        raise ErroDataset("não foi possível obter {nome}: {motivo}",
                          nome=ds.nome, motivo=str(exc)) from exc
    for item in resposta.get("data") or []:
        atributos = item.get("attributes") or {}
        if atributos.get("isRestricted"):
            continue                              # nunca: ver o cabeçalho do módulo
        anexo = atributos.get("attachment") or {}
        midia = (anexo.get("file") or {}).get("data") or []
        # o CMS devolve um objeto ou uma lista, conforme o campo aceite um ou vários
        for registro in (midia if isinstance(midia, list) else [midia]):
            arquivo = (registro or {}).get("attributes") or {}
            if arquivo.get("url", "").lower().endswith(EXTENSOES_ACEITAS):
                # a mais recente das duas: em Características a data de exibição
                # ficou em 18/12/2024 enquanto o arquivo trocado é de 29/12/2025
                datas = [d[:10] for d in (anexo.get("display_date"),
                                          atributos.get("updatedAt")) if d]
                return {"url": CMS + arquivo["url"], "nome": arquivo.get("name") or "",
                        "data": para_data(max(datas)) if datas else date.today()}
    raise ErroDataset("o ANBIMA Data não tem arquivo publicado para {nome}", nome=ds.nome)


def baixar_publicado(slug: str) -> Salvo:
    """Porta CMS: baixa a versão publicada e salva com a data dela."""
    versao = versao_publicada(slug)
    ds = dataset(slug)
    bruto = _obter(versao["url"], ds.nome, timeout=120)
    return salvar(ds.slug, versao["data"], versao["nome"] or Path(versao["url"]).name,
                  bruto, CMS_PUBLICO)


def _coluna_de_data(colunas: List[str]) -> Optional[int]:
    import unicodedata
    for i, c in enumerate(colunas):
        sem_acento = "".join(ch for ch in unicodedata.normalize("NFKD", c or "")
                             if not unicodedata.combining(ch))
        if " ".join(sem_acento.lower().split()) in _COLUNAS_DE_DATA:
            return i
    return None


def _csv_de(colunas: List[str], linhas: List[List[str]]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(colunas)
    escritor.writerows(linhas)
    return saida.getvalue().encode("utf-8")


def importar(slug: str, referencia, nome: str, dados: bytes) -> List[Salvo]:
    """Porta IMPORTACAO: o arquivo que a pessoa baixou no ANBIMA Data.

    O arquivo do ANBIMA Data traz **vários dias** de uma vez — o de CRIs e CRAs
    vem com os cinco últimos dias úteis, ~350 papéis cada, numa coluna "Data de
    referência". Salvá-lo inteiro sob a data do formulário punha quatro dias
    com a data errada. Havendo essa coluna, cada dia vira um salvo próprio, e a
    data do formulário só vale para arquivo sem ela. O original fica guardado
    inteiro, uma vez, em ``originais/``.

    Lê antes de salvar: um arquivo que não abre não pode virar "salvo" e
    falhar só na hora de alguém consultar.
    """
    colunas, linhas = ler_arquivo(nome, dados)
    if not linhas:
        raise ErroDataset("{arquivo} não tem linhas de dados", arquivo=nome)

    indice = _coluna_de_data(colunas)
    if indice is None:
        if referencia is None:
            raise ErroDataset("{arquivo} não tem coluna de data de referência: informe a "
                              "data a que ele se refere", arquivo=nome)
        return [salvar(slug, referencia, nome, dados, IMPORTACAO)]

    por_dia = {}
    for linha in linhas:
        dia = planilha.como_data(linha[indice] if indice < len(linha) else "")
        if dia is not None:
            por_dia.setdefault(dia, []).append(linha)
    if not por_dia:
        raise ErroDataset("a coluna de data de {arquivo} não tem nenhuma data legível",
                          arquivo=nome)

    originais = _pasta(dataset(slug).slug) / "originais"
    originais.mkdir(parents=True, exist_ok=True)
    (originais / f"{datetime.now():%Y%m%d-%H%M%S}_{Path(nome).name}").write_bytes(dados)
    return [salvar(slug, dia, f"{Path(nome).stem}_{dia:%Y%m%d}.csv",
                   _csv_de(colunas, grupo), IMPORTACAO)
            for dia, grupo in sorted(por_dia.items())]


def para_csv(tabela: Tabela) -> str:
    """CSV com ``;`` — o separador que o Excel em português abre sem perguntar."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(tabela.colunas)
    escritor.writerows(tabela.linhas)
    return saida.getvalue()
