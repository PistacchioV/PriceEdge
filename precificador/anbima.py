"""Taxas do mercado secundário de títulos públicos — o boletim diário da ANBIMA.

É a mesma tabela da página *Taxas de Títulos Públicos* da ANBIMA
(``anbima.com.br/pt_br/informar/taxas-de-titulos-publicos.htm``), a que se
consulta digitando a data e clicando em "Consultar". Ela não é lida dali: a
ANBIMA publica o mesmo boletim como arquivo de texto, um por data,

    https://www.anbima.com.br/informacoes/merc-sec/arqs/msAAMMDD.txt

com os mesmos números — LTN 01/04/2027 em 07/10/2026 é 13,1120 · 13,0721 ·
13,0910 · 944,021979 nos dois. Ler o arquivo em vez do HTML do formulário é o
que deixa a tela de pé quando a ANBIMA mexer no layout da página: o formato do
arquivo é contrato com quem baixa, o desenho da tabela não é.

O arquivo vem em latin-1, separado por ``@``, com vírgula decimal:

    Titulo@Data Referencia@Codigo SELIC@Data Base/Emissao@Data Vencimento@
    Tx. Compra@Tx. Venda@Tx. Indicativas@PU@Desvio padrao@
    Interv. Ind. Inf. (D0)@Interv. Ind. Sup. (D0)@
    Interv. Ind. Inf. (D+1)@Interv. Ind. Sup. (D+1)@Criterio

As taxas chegam em percentual (``6,8078``) e saem daqui em **decimal**
(``0,068078``), como em todo o pacote.

A janela é curta: a ANBIMA mantém algumas semanas de arquivos (em outubro de
2026, de meados de setembro em diante). Data sem arquivo — fim de semana,
feriado, ou antiga demais — volta 404, e o erro diz isso em vez de "falha".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from . import rede
from .calendario import para_data
from .erros import ErroDeFonte

URL = "https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{data:%y%m%d}.txt"
PAGINA = "https://www.anbima.com.br/pt_br/informar/taxas-de-titulos-publicos.htm"

LTN = "LTN"
NTN_F = "NTN-F"
NTN_B = "NTN-B"
NTN_C = "NTN-C"
LFT = "LFT"

# a ordem da página da ANBIMA, e o que cada papel é
TIPOS = [
    (LTN, "LTN — prefixado, sem cupom"),
    (NTN_F, "NTN-F — prefixado, cupom de 10% a.a."),
    (NTN_B, "NTN-B — IPCA + juro real, cupom de 6% a.a."),
    (NTN_C, "NTN-C — IGP-M + juro real"),
    (LFT, "LFT — pós-fixado na Selic"),
]


class ErroANBIMA(ErroDeFonte):
    """O boletim não veio — data sem publicação, ou falha de rede."""


@dataclass(frozen=True)
class Titulo:
    """Uma linha do boletim. Taxas em decimal; ``None`` quando a ANBIMA não publica."""
    tipo: str
    referencia: date
    codigo_selic: str
    data_base: Optional[date]
    vencimento: date
    taxa_compra: Optional[float]
    taxa_venda: Optional[float]
    taxa_indicativa: Optional[float]
    pu: Optional[float]
    desvio_padrao: Optional[float]
    intervalo_min_d0: Optional[float]
    intervalo_max_d0: Optional[float]
    intervalo_min_d1: Optional[float]
    intervalo_max_d1: Optional[float]
    criterio: str = ""


def _numero(texto: str) -> Optional[float]:
    texto = (texto or "").strip()
    if not texto or texto == "--":
        return None
    try:
        return float(texto.replace(".", "").replace(",", ".")) if "," in texto \
            else float(texto)
    except ValueError:
        return None


def _taxa(texto: str) -> Optional[float]:
    valor = _numero(texto)
    return None if valor is None else valor / 100.0


def _data(texto: str) -> Optional[date]:
    texto = (texto or "").strip()
    try:
        return datetime.strptime(texto, "%Y%m%d").date()
    except ValueError:
        return None


def ler(conteudo: str) -> List[Titulo]:
    """As linhas do boletim, já tipadas. Cabeçalho e linhas estranhas ficam de fora."""
    titulos: List[Titulo] = []
    for linha in conteudo.splitlines():
        campos = linha.split("@")
        if len(campos) < 14 or campos[0].strip() == "Titulo":
            continue
        referencia, vencimento = _data(campos[1]), _data(campos[4])
        if referencia is None or vencimento is None:
            continue
        titulos.append(Titulo(
            tipo=campos[0].strip(), referencia=referencia,
            codigo_selic=campos[2].strip(), data_base=_data(campos[3]),
            vencimento=vencimento,
            taxa_compra=_taxa(campos[5]), taxa_venda=_taxa(campos[6]),
            taxa_indicativa=_taxa(campos[7]), pu=_numero(campos[8]),
            desvio_padrao=_numero(campos[9]),
            intervalo_min_d0=_taxa(campos[10]), intervalo_max_d0=_taxa(campos[11]),
            intervalo_min_d1=_taxa(campos[12]), intervalo_max_d1=_taxa(campos[13]),
            criterio=campos[14].strip() if len(campos) > 14 else ""))
    titulos.sort(key=lambda t: (t.tipo, t.vencimento))
    return titulos


def baixar(referencia, timeout: int = 30) -> List[Titulo]:
    """O boletim da data. 404 vira erro que diz por que costuma faltar."""
    dia = para_data(referencia)
    try:
        bruto = rede.obter(URL.format(data=dia), timeout=timeout)
    except rede.ErroRede as exc:
        if getattr(exc, "status", None) == 404:
            raise ErroANBIMA(
                "a ANBIMA não tem boletim de títulos públicos para {data}. Ou não "
                "foi dia útil, ou a data é antiga demais — ela mantém só algumas "
                "semanas de arquivos.", data=f"{dia:%d/%m/%Y}") from exc
        raise ErroANBIMA("não foi possível obter o boletim da ANBIMA: {motivo}",
                         motivo=str(exc)) from exc
    titulos = ler(bruto.decode("latin-1"))
    if not titulos:
        raise ErroANBIMA("o boletim da ANBIMA de {data} veio sem títulos",
                         data=f"{dia:%d/%m/%Y}")
    return titulos


def por_tipo(titulos: List[Titulo]) -> Dict[str, List[Titulo]]:
    """Agrupados na ordem da página da ANBIMA; tipo novo vai para o fim."""
    grupos: Dict[str, List[Titulo]] = {codigo: [] for codigo, _ in TIPOS}
    for t in titulos:
        grupos.setdefault(t.tipo, []).append(t)
    return {k: v for k, v in grupos.items() if v}
