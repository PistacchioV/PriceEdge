"""Câmbio — PTAX do Banco Central e futuros de dólar implícitos.

Duas coisas que a tela de NDF pedia digitadas e que dá para buscar:

**Spot.** A PTAX vem do Banco Central, pela série 1 do SGS (dólar comercial
venda) ou pelo Olinda, que devolve compra e venda separadas. A PTAX é a média
do dia, não a cotação D+2 de mesa — serve de ponto de partida, e a tela deixa
sobrescrever.

**Futuros de dólar.** A B3 não expõe os ajustes do pregão numa API pública: o
proxy de derivativos responde 404 e a página de ajustes é HTML renderizado por
JavaScript. O que ela publica é a curva **PTX — dólar a termo**, que é a
referência oficial dela para o dólar futuro. O contrato DOL vence no primeiro
dia útil do mês, então o preço de cada vencimento sai da curva interpolada
naquela data, multiplicado por 1.000 (a cotação do DOL é em milésimos).

O número que sai daqui é o dólar a termo da própria B3, não o ajuste negociado
— eles andam juntos, mas não são a mesma coisa, e a tela diz isso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from . import rede
from .calendario import (Calendario, calendario_anbima, para_data,
                         soma_meses)

SGS_DOLAR_VENDA = 1
API_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
API_OLINDA = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
              "CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data}'&$format=json")
API_MOEDA = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
             "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
             "dataFinalCotacao=@dataFinalCotacao)?@moeda='{moeda}'"
             "&@dataInicial='{inicio}'&@dataFinalCotacao='{fim}'&$format=json")

# Moedas que o Banco Central boletina, com o código dele. A paridade que vem
# junto é sempre contra o dólar — direta (EUR/USD, GBP/USD) nas moedas cotadas
# "por unidade", e invertida (USD/JPY) nas cotadas "por dólar". Ler a paridade
# sem saber de que lado ela está é como a taxa de iene vira 156 em vez de 0,0064.
PARIDADE_INVERTIDA = {"JPY", "CHF", "CAD", "SEK", "NOK", "DKK"}

CABECALHO = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


class ErroCambio(RuntimeError):
    """Falha ao obter cotação de câmbio."""


@dataclass(frozen=True)
class Ptax:
    data: date
    compra: Optional[float]
    venda: float
    moeda: str = "USD"
    paridade_compra: Optional[float] = None
    paridade_venda: Optional[float] = None

    @property
    def media(self) -> float:
        return (self.compra + self.venda) / 2.0 if self.compra else self.venda

    @property
    def contra_dolar(self) -> Optional[float]:
        """A paridade sempre no sentido *moeda por dólar não*: unidades de USD.

        O boletim inverte o lado em algumas moedas; aqui elas voltam todas para
        o mesmo sentido, que é o que a tela de EUR/USD espera.
        """
        if self.paridade_venda is None:
            return None
        if self.moeda in PARIDADE_INVERTIDA:
            return 1.0 / self.paridade_venda if self.paridade_venda else None
        return self.paridade_venda


def _buscar(url: str, timeout: int = 25):
    try:
        return rede.obter_json(url, timeout=timeout)
    except rede.ErroRede as exc:
        raise ErroCambio(f"não foi possível obter a cotação: {exc}") from exc


def ptax(referencia=None, tolerancia: int = 10) -> Ptax:
    """PTAX de fechamento da data (ou a última publicada antes dela).

    Fim de semana, feriado e o dia corrente antes das 13h não têm PTAX — daí a
    janela para trás em vez de um erro seco.
    """
    fim = para_data(referencia) if referencia else date.today()
    inicio = fim.toordinal() - tolerancia
    inicio = date.fromordinal(inicio)

    dados = _buscar(f"{API_SGS.format(serie=SGS_DOLAR_VENDA)}?formato=json"
                    f"&dataInicial={inicio:%d/%m/%Y}&dataFinal={fim:%d/%m/%Y}")
    linhas = [linha for linha in dados if linha.get("valor")]
    if not linhas:
        raise ErroCambio(
            f"o Banco Central não publicou PTAX entre {inicio:%d/%m/%Y} e "
            f"{fim:%d/%m/%Y}. A cotação sai por volta das 13h do dia útil.")
    ultima = linhas[-1]
    return Ptax(para_data(ultima["data"]), None, float(ultima["valor"]))


def ptax_moeda(codigo: str, referencia=None, tolerancia: int = 10) -> Ptax:
    """Boletim de fechamento de qualquer moeda que o BCB publica, não só o dólar.

    O mesmo endpoint serve euro, iene, libra e as demais — o que muda é o código.
    Vem sempre o par contra o real (``cotacao``) e a paridade contra o dólar
    (``paridade``), e é a janela para trás que resolve fim de semana e feriado.
    """
    codigo = (codigo or "USD").upper()
    fim = para_data(referencia) if referencia else date.today()
    inicio = date.fromordinal(fim.toordinal() - tolerancia)

    dados = _buscar(API_MOEDA.format(moeda=codigo, inicio=f"{inicio:%m-%d-%Y}",
                                     fim=f"{fim:%m-%d-%Y}"))
    linhas = [x for x in dados.get("value") or []
              if x.get("tipoBoletim") == "Fechamento" and x.get("cotacaoVenda")]
    if not linhas:
        raise ErroCambio(
            f"o Banco Central não publicou boletim de {codigo} entre "
            f"{inicio:%d/%m/%Y} e {fim:%d/%m/%Y}. O fechamento sai por volta "
            "das 13h do dia útil.")

    linha = linhas[-1]
    return Ptax(
        data=para_data(linha["dataHoraCotacao"][:10]),
        compra=float(linha["cotacaoCompra"]), venda=float(linha["cotacaoVenda"]),
        moeda=codigo,
        paridade_compra=float(linha["paridadeCompra"]) if linha.get("paridadeCompra") else None,
        paridade_venda=float(linha["paridadeVenda"]) if linha.get("paridadeVenda") else None,
    )


def ptax_detalhada(referencia=None) -> Ptax:
    """PTAX com compra e venda separadas, pelo Olinda. Cai no SGS se falhar."""
    d = para_data(referencia) if referencia else date.today()
    try:
        dados = _buscar(API_OLINDA.format(data=f"{d:%m-%d-%Y}"))
        linhas = dados.get("value") or []
        if linhas:
            linha = linhas[-1]
            return Ptax(d, float(linha["cotacaoCompra"]), float(linha["cotacaoVenda"]))
    except ErroCambio:
        pass
    return ptax(d)


# ------------------------------------------------------- futuros de dólar --

@dataclass(frozen=True)
class FuturoDolar:
    vencimento: date
    dias_corridos: int
    dias_uteis: int
    preco: float          # em pontos de DOL (5.125,00 = R$ 5,125 por dólar)

    @property
    def taxa(self) -> float:
        """O mesmo preço em reais por dólar."""
        return self.preco / 1000.0


def vencimentos_dol(data_base, quantidade: int = 2,
                    calendario: Optional[Calendario] = None) -> List[date]:
    """Vencimentos do futuro de dólar: primeiro dia útil de cada mês à frente."""
    cal = calendario or calendario_anbima()
    base = para_data(data_base)
    datas, mes = [], 0
    while len(datas) < quantidade:
        mes += 1
        primeiro = soma_meses(date(base.year, base.month, 1), mes)
        vencimento = cal.ajusta(primeiro)          # primeiro dia útil do mês
        if vencimento > base:
            datas.append(vencimento)
    return datas


def futuros_dol(data_base, curva_ptx, quantidade: int = 2,
                calendario: Optional[Calendario] = None) -> List[FuturoDolar]:
    """Preço dos próximos vencimentos do DOL, lidos da curva PTX da B3.

    ``curva_ptx`` é a curva "Dólar a Termo (Real x dólar)" — uma curva de preço,
    não de taxa. O valor sai interpolado na data de vencimento e vai para
    pontos de DOL multiplicando por 1.000.
    """
    cal = calendario or calendario_anbima()
    base = para_data(data_base)
    saida = []
    for vencimento in vencimentos_dol(base, quantidade, cal):
        dc = (vencimento - base).days
        du = cal.dias_uteis(base, vencimento)
        saida.append(FuturoDolar(vencimento, dc, du,
                                 curva_ptx.taxa_para(dc, du) * 1000.0))
    return saida
