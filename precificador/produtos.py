"""Produtos prontos — cada um corresponde a uma das planilhas de aula.

Aqui mora só a montagem: quais pernas o swap tem, qual curva desconta cada
uma e qual é a variável que o "Atingir Meta" procura.  A matemática está em
``instrumentos`` e ``curvas``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Sequence

from .calendario import (FOLLOWING, Calendario, calendario_anbima, para_data,
                         soma_meses)
from .curvas import Curva, CurvaTermSOFR
from .instrumentos import (BULLET, PERCENTUAL, SPREAD, Periodo, Swap,
                           agenda_periodica, perna_cdi, perna_ipca_capitalizado,
                           perna_pre_usd, perna_prefixada_exp252,
                           perna_term_sofr, pesos_amortizacao, taxa_par)


@dataclass
class ParametrosSwap:
    inicio: date
    vencimento: date
    nocional: float
    meses_periodo: int = 6
    amortizacao: str = BULLET
    pesos: Optional[Sequence[float]] = None
    fee: float = 0.0
    convencao_dia_util: str = FOLLOWING
    sem_fluxo: bool = False

    def __post_init__(self):
        self.inicio = para_data(self.inicio)
        self.vencimento = para_data(self.vencimento)
        if self.vencimento <= self.inicio:
            raise ValueError("o vencimento tem que ser posterior ao início")

    def agenda(self, calendario: Optional[Calendario] = None) -> List[Periodo]:
        return agenda_periodica(self.inicio, self.vencimento, self.meses_periodo,
                                calendario, convencao=self.convencao_dia_util,
                                sem_fluxo=self.sem_fluxo)


def _pesos(params: ParametrosSwap, n: int) -> List[float]:
    return pesos_amortizacao(n, params.amortizacao, params.pesos)


# ------------------------------------------------- 1. Pré BRL x CDI ± spread

def swap_pre_x_cdi(params: ParametrosSwap, taxa_pre: float, valor_cdi: float,
                   curva_di: Curva, calendario: Optional[Calendario] = None,
                   modo_cdi: str = SPREAD) -> Swap:
    """Ativo em pré BRL, passivo em CDI. Uma curva só: DI futuro.

    ``modo_cdi`` escolhe como a ponta CDI é remunerada — ``spread``
    (CDI ± spread, multiplicativo) ou ``percentual`` (110% do CDI, sobre a
    taxa diária).
    """
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))
    ativa = perna_prefixada_exp252(params.nocional, taxa_pre, periodos,
                                   curva_di, pesos, nome="Pré BRL")
    passiva = perna_cdi(params.nocional, periodos, curva_di, pesos,
                        modo=modo_cdi, valor=valor_cdi)
    rotulo = "% do CDI" if modo_cdi == PERCENTUAL else "CDI ± spread"
    return Swap(f"Pré BRL × {rotulo}", ativa, passiva, "BRL", params.fee)


def spread_par_cdi(params: ParametrosSwap, taxa_pre: float, curva_di: Curva,
                   calendario: Optional[Calendario] = None) -> float:
    """Spread sobre o CDI que zera o MtM contra a taxa pré dada."""
    return taxa_par(lambda s: swap_pre_x_cdi(params, taxa_pre, s, curva_di, calendario),
                    chute=0.02)


def percentual_par_cdi(params: ParametrosSwap, taxa_pre: float, curva_di: Curva,
                       calendario: Optional[Calendario] = None) -> float:
    """Percentual do CDI que zera o MtM (1,10 = 110% do CDI)."""
    return taxa_par(
        lambda p: swap_pre_x_cdi(params, taxa_pre, p, curva_di, calendario,
                                 modo_cdi=PERCENTUAL),
        chute=1.0)


def pre_par_cdi(params: ParametrosSwap, valor_cdi: float, curva_di: Curva,
                calendario: Optional[Calendario] = None,
                modo_cdi: str = SPREAD) -> float:
    """Caminho inverso: taxa pré equivalente a um CDI ± spread ou % do CDI."""
    return taxa_par(
        lambda p: swap_pre_x_cdi(params, p, valor_cdi, curva_di, calendario, modo_cdi),
        chute=0.15)


# ------------------------------------------------ 2. Pré USD x Pré BRL (XCS)

def swap_pre_usd_x_pre_brl(params: ParametrosSwap, taxa_usd: float, taxa_brl: float,
                           curva_di: Curva, curva_cupom: Curva, spot: float,
                           calendario: Optional[Calendario] = None) -> Swap:
    """Cross-currency: ativo em pré USD + variação cambial, passivo em pré BRL.

    Duas curvas, e cada fluxo desconta pela sua: o lado em dólar pelo cupom
    cambial (linear 360), o lado em reais pelo DI (exponencial 252).  O
    nocional em dólar é ``nocional / spot``.
    """
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))
    nocional_usd = params.nocional / spot
    ativa = perna_pre_usd(nocional_usd, taxa_usd, periodos, curva_cupom, pesos,
                          fx=spot, nome="Pré USD + var. cambial")
    passiva = perna_prefixada_exp252(params.nocional, taxa_brl, periodos,
                                     curva_di, pesos, nome="Pré BRL")
    return Swap("Pré USD × Pré BRL", ativa, passiva, "BRL", params.fee)


def pre_brl_par(params: ParametrosSwap, taxa_usd: float, curva_di: Curva,
                curva_cupom: Curva, spot: float,
                calendario: Optional[Calendario] = None) -> float:
    return taxa_par(
        lambda t: swap_pre_usd_x_pre_brl(params, taxa_usd, t, curva_di,
                                         curva_cupom, spot, calendario),
        chute=0.14)


def pre_usd_par(params: ParametrosSwap, taxa_brl: float, curva_di: Curva,
                curva_cupom: Curva, spot: float,
                calendario: Optional[Calendario] = None) -> float:
    return taxa_par(
        lambda t: swap_pre_usd_x_pre_brl(params, t, taxa_brl, curva_di,
                                         curva_cupom, spot, calendario),
        chute=0.05)


# ------------------------------------- 3. IPCA capitalizado x CDI ± spread --

def swap_ipca_x_cdi(params: ParametrosSwap, taxa_real: float, valor_cdi: float,
                    curva_di: Curva, curva_ipca: Curva,
                    calendario: Optional[Calendario] = None,
                    modo_cdi: str = SPREAD) -> Swap:
    """Ativo IPCA+ capitalizado, passivo CDI ± spread (vanilla).

    A inflação implícita sai de (1+DI)/(1+DIxIPCA)-1, com as duas curvas
    tiradas do mesmo arquivo da B3 e interpoladas do mesmo jeito.
    """
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))
    ativa = perna_ipca_capitalizado(params.nocional, taxa_real, periodos,
                                    curva_di, curva_ipca, pesos, nome="IPCA+ capitalizado")
    passiva = perna_cdi(params.nocional, periodos, curva_di, pesos,
                        modo=modo_cdi, valor=valor_cdi)
    rotulo = "% do CDI" if modo_cdi == PERCENTUAL else "CDI ± spread"
    return Swap(f"IPCA capitalizado × {rotulo}", ativa, passiva, "BRL", params.fee)


def spread_par_ipca(params: ParametrosSwap, taxa_real: float, curva_di: Curva,
                    curva_ipca: Curva, calendario: Optional[Calendario] = None) -> float:
    return taxa_par(lambda s: swap_ipca_x_cdi(params, taxa_real, s, curva_di,
                                              curva_ipca, calendario), chute=0.02)


def percentual_par_ipca(params: ParametrosSwap, taxa_real: float, curva_di: Curva,
                        curva_ipca: Curva,
                        calendario: Optional[Calendario] = None) -> float:
    """Percentual do CDI que zera o MtM contra a ponta IPCA+."""
    return taxa_par(
        lambda p: swap_ipca_x_cdi(params, taxa_real, p, curva_di, curva_ipca,
                                  calendario, modo_cdi=PERCENTUAL),
        chute=1.0)


# --------------------------------------------- 4. Pré USD x Term SOFR ± spread

def swap_pre_usd_x_term_sofr(params: ParametrosSwap, taxa_usd: float, spread: float,
                             curva_sofr: CurvaTermSOFR,
                             calendario: Optional[Calendario] = None) -> Swap:
    """Ativo pré USD, passivo Term SOFR ± spread. Tudo em dólar, linear 360."""
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))
    nocional = params.nocional
    ativa = _perna_pre_usd_sofr(nocional, taxa_usd, periodos, curva_sofr, pesos,
                                params.inicio)
    passiva = perna_term_sofr(nocional, spread, periodos, curva_sofr, pesos,
                              params.inicio)
    return Swap("Pré USD × Term SOFR ± spread", ativa, passiva, "USD", params.fee)


def _perna_pre_usd_sofr(nocional, taxa, periodos, curva_sofr, pesos, inicio):
    """Pré em dólar descontado pela própria curva SOFR (não pelo cupom cambial)."""
    from .instrumentos import Fluxo, ResultadoPerna
    fluxos, saldo = [], nocional
    for periodo, peso in zip(periodos, pesos):
        amortizacao = nocional * peso
        taxa_periodo = periodo.dc_periodo * taxa / 360.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        df = curva_sofr.fator_desconto_entre(inicio, periodo.data_pagamento)
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, df,
                            amortizacao * df, juros * df))
        saldo -= amortizacao
    return ResultadoPerna("Pré USD", "USD", fluxos)


def spread_par_sofr(params: ParametrosSwap, taxa_usd: float,
                    curva_sofr: CurvaTermSOFR,
                    calendario: Optional[Calendario] = None) -> float:
    return taxa_par(lambda s: swap_pre_usd_x_term_sofr(params, taxa_usd, s,
                                                       curva_sofr, calendario),
                    chute=0.005)


# ------------------------------------------------------------- IPCA: VNA ----

@dataclass
class NumeroIndice:
    """NI pro-rata da NTN-B / debênture IPCA+ (aba "Cálculo NI Pro-Rata")."""
    ni_anterior: float
    projecao_mensal: float
    data_referencia: date

    def __post_init__(self):
        self.data_referencia = para_data(self.data_referencia)

    @property
    def data_base(self) -> date:
        d = self.data_referencia
        if d.day < 16:
            anterior = soma_meses(date(d.year, d.month, 15), -1)
            return anterior
        return date(d.year, d.month, 15)

    @property
    def proxima_base(self) -> date:
        return soma_meses(self.data_base, 1)

    @property
    def ni_cheio(self) -> float:
        return self.ni_anterior * (1.0 + self.projecao_mensal)

    def ni_pro_rata(self, calendario: Optional[Calendario] = None) -> float:
        cal = calendario or calendario_anbima()
        dup = cal.dias_uteis(self.data_base, self.data_referencia)
        dut = cal.dias_uteis(self.data_base, self.proxima_base)
        if dut == 0:
            return self.ni_anterior
        return self.ni_anterior * (self.ni_cheio / self.ni_anterior) ** (dup / dut)

    def vna(self, vne: float, ni_partida: float,
            calendario: Optional[Calendario] = None) -> float:
        return vne * (self.ni_pro_rata(calendario) / ni_partida)


# ----------------------------------------- 5. Pré USD x CDI ± spread (XCS) --

def swap_pre_usd_x_cdi(params: ParametrosSwap, taxa_usd: float, valor_cdi: float,
                       curva_di: Curva, curva_cupom: Curva, spot: float,
                       calendario: Optional[Calendario] = None,
                       modo_cdi: str = SPREAD) -> Swap:
    """Cross-currency com a ponta em reais flutuante.

    É o *Pré USD × Pré BRL* com a perna passiva trocada por CDI ± spread: o
    cliente que tem dívida em dólar troca para CDI mais um spread em vez de
    uma taxa pré.  Continuam sendo duas curvas de desconto distintas — cupom
    cambial no fluxo em dólar, DI no fluxo em reais — e o spread continua
    entrando de forma multiplicativa sobre o CDI.
    """
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))
    nocional_usd = params.nocional / spot
    ativa = perna_pre_usd(nocional_usd, taxa_usd, periodos, curva_cupom, pesos,
                          fx=spot, nome="Pré USD + var. cambial")
    passiva = perna_cdi(params.nocional, periodos, curva_di, pesos,
                        modo=modo_cdi, valor=valor_cdi)
    rotulo = "% do CDI" if modo_cdi == PERCENTUAL else "CDI ± spread"
    return Swap(f"Pré USD × {rotulo}", ativa, passiva, "BRL", params.fee)


def spread_par_usd_cdi(params: ParametrosSwap, taxa_usd: float, curva_di: Curva,
                       curva_cupom: Curva, spot: float,
                       calendario: Optional[Calendario] = None) -> float:
    """Spread sobre o CDI que zera o MtM contra a ponta pré em dólar."""
    return taxa_par(
        lambda s: swap_pre_usd_x_cdi(params, taxa_usd, s, curva_di,
                                     curva_cupom, spot, calendario),
        chute=0.02)


def percentual_par_usd_cdi(params: ParametrosSwap, taxa_usd: float, curva_di: Curva,
                           curva_cupom: Curva, spot: float,
                           calendario: Optional[Calendario] = None) -> float:
    """Percentual do CDI que zera o MtM contra a ponta pré em dólar."""
    return taxa_par(
        lambda p: swap_pre_usd_x_cdi(params, taxa_usd, p, curva_di, curva_cupom,
                                     spot, calendario, modo_cdi=PERCENTUAL),
        chute=1.0)


def pre_usd_par_cdi(params: ParametrosSwap, valor_cdi: float, curva_di: Curva,
                    curva_cupom: Curva, spot: float,
                    calendario: Optional[Calendario] = None,
                    modo_cdi: str = SPREAD) -> float:
    """Caminho inverso: taxa pré em dólar equivalente à ponta CDI."""
    return taxa_par(
        lambda t: swap_pre_usd_x_cdi(params, t, valor_cdi, curva_di,
                                     curva_cupom, spot, calendario, modo_cdi),
        chute=0.05)


# --------------------------------------------------------------------- NDF --

DIARIA = "diaria"
SEMANAL = "semanal"
MENSAL = "mensal"
TRIMESTRAL = "trimestral"
SEMESTRAL = "semestral"
ANUAL = "anual"

PROGRESSOES = {
    DIARIA: ("Diária", 0),
    SEMANAL: ("Semanal", 0),
    MENSAL: ("Mensal", 1),
    TRIMESTRAL: ("Trimestral", 3),
    SEMESTRAL: ("Semestral", 6),
    ANUAL: ("Anual", 12),
}


@dataclass
class PontoNDF:
    """Uma data da curva a termo da moeda."""
    data: date
    dias_corridos: int
    dias_uteis: int
    cupom: float          # juro da moeda estrangeira, linear 360
    di: float             # DI, exponencial 252
    carry: float          # (1+DI)/(1+cupom) − 1
    ndf: float            # preço a termo
    pontos: float         # (NDF − spot) × fator da moeda

    def para_dict(self) -> dict:
        return {
            "data": self.data.isoformat(),
            "dc": self.dias_corridos, "du": self.dias_uteis,
            "cupom": self.cupom, "di": self.di, "carry": self.carry,
            "ndf": self.ndf, "pontos": self.pontos,
        }


MODO_CUPOM = "cupom"        # DI no numerador, cupom publicado no denominador
MODO_IMPLICITO = "implicito"  # cupom sai da curva de preço a termo da B3
MODO_PRECO = "preco"        # o termo é lido direto de uma curva de preço (cross)
MODO_MANUAL = "manual"      # DI no numerador, juro estrangeiro digitado


@dataclass(frozen=True)
class MoedaNDF:
    """Uma moeda que o NDF sabe precificar, com a fonte de curva que ela usa.

    O que separa uma moeda da outra aqui não é a fórmula — é **de onde sai o
    juro da moeda estrangeira**, e é isso que ``modo`` diz:

    ``cupom``      a B3 publica a curva de cupom daquela moeda (dólar e euro).
    ``implicito``  a B3 só publica o preço a termo; o cupom sai invertendo a
                   paridade contra o DI.
    ``preco``      é um cross entre duas curvas de preço, sem DI no meio.
    ``manual``     não há fonte pública: o juro entra digitado.

    A B3 publica todas essas curvas na mesma grade de vértices, então o que
    muda de uma moeda para outra não é o prazo — é a taxa em cada vértice e a
    convenção que a desconta.
    """
    codigo: str
    nome: str
    par: str
    modo: str
    curvas_cupom: tuple = ()          # códigos B3, em ordem de preferência
    curva_preco: Optional[str] = None
    casas: int = 4
    fator_pontos: float = 10000.0
    spot_padrao: float = 5.10
    nota: Optional[str] = None

    @property
    def curva_cupom(self) -> Optional[str]:
        return self.curvas_cupom[0] if self.curvas_cupom else None

    @property
    def pede_taxa_digitada(self) -> bool:
        return self.modo == MODO_MANUAL


MOEDAS_NDF = [
    MoedaNDF("USD", "Dólar", "USD/BRL", MODO_CUPOM,
             ("DOC", "DOL", "DCO"), "PTX", 4, 10000.0, 5.10),
    MoedaNDF("EUR", "Euro", "EUR/BRL", MODO_CUPOM,
             ("EUC",), "EUR", 4, 10000.0, 5.95),
    MoedaNDF("JPY", "Iene", "JPY/BRL", MODO_IMPLICITO,
             (), "JPY", 6, 1000000.0, 0.0345,
             nota="A B3 publica o iene a termo com duas casas decimais — a curva "
                  "inteira sai em R$ 0,03 por iene. O cupom implícito que vem "
                  "dela é indicativo, não preço; para fechar contrato, digite a "
                  "taxa em iene no modo de moeda livre."),
    MoedaNDF("EURUSD", "Euro contra dólar", "EUR/USD", MODO_PRECO,
             (), "EURUSD", 4, 10000.0, 1.16,
             nota="Cross derivado das duas curvas de preço da B3: euro a termo "
                  "dividido por dólar a termo. Não passa pelo DI — as duas "
                  "pontas já estão em reais e o real cancela."),
    MoedaNDF("LIVRE", "Outra moeda", "XXX/BRL", MODO_MANUAL,
             (), None, 4, 10000.0, 1.00,
             nota="Libra, franco, peso, dólar canadense: a B3 não publica cupom "
                  "para nenhuma delas. O DI entra da curva e o juro da moeda "
                  "estrangeira entra digitado, linear em 360 dias."),
]

MOEDA_NDF_POR_CODIGO = {m.codigo: m for m in MOEDAS_NDF}
MOEDA_NDF_PADRAO = MOEDAS_NDF[0]


def moeda_ndf(codigo: Optional[str]) -> MoedaNDF:
    return MOEDA_NDF_POR_CODIGO.get((codigo or "").upper(), MOEDA_NDF_PADRAO)


def cupom_implicito(spot: float, preco_termo: float, di: float,
                    dias_corridos: int, dias_uteis: int) -> float:
    """Inverte a paridade coberta para achar o cupom que a curva de preço embute.

        termo = spot · (1+DI)^(DU/252) / (1 + cupom · DC/360)
        cupom = [spot · (1+DI)^(DU/252) / termo − 1] · 360/DC

    É o caminho para moedas que a B3 cota a termo mas para as quais não publica
    curva de juro: o preço está lá, e o cupom sai por diferença contra o DI.
    """
    if dias_corridos <= 0 or preco_termo <= 0:
        return 0.0
    razao = spot * (1.0 + di) ** (dias_uteis / 252.0) / preco_termo
    return (razao - 1.0) * 360.0 / dias_corridos


def ndf_forward(spot: float, di: float, cupom: float,
                dias_corridos: int, dias_uteis: int) -> float:
    """Dólar a termo pela paridade coberta de juros.

        NDF = spot · (1 + DI)^(DU/252) / (1 + cupom · DC/360)

    Repare nas duas convenções convivendo na mesma fórmula: a perna em reais
    capitaliza exponencial em dias úteis, a perna em dólar desconta linear em
    dias corridos.  Não é descuido — é como cada taxa é cotada.
    """
    return (spot * (1.0 + di) ** (dias_uteis / 252.0)
            / (1.0 + cupom * dias_corridos / 360.0))


def escada_datas(data_base, progressao: str = MENSAL, quantidade: int = 12,
                 calendario: Optional[Calendario] = None) -> List[date]:
    """Escada de vencimentos a partir da data-base.

    Reproduz a coluna "Rolling" da planilha:

    * diária  — dia útil seguinte, um a um;
    * semanal — cinco dias úteis à frente;
    * demais  — **último dia útil** do mês de vencimento, avançando 1, 3, 6 ou
      12 meses de cada vez.

    Nas progressões por mês a escada abre no **mês corrente**, não no seguinte:
    o primeiro preço que a mesa quer ver é o do fim do mês em que ela está. Se a
    data-base já passou desse dia — é a própria virada do mês —, ele sai e a
    escada começa no mês seguinte, sem perder um degrau da contagem.
    """
    cal = calendario or calendario_anbima()
    base = para_data(data_base)
    datas: List[date] = []

    if progressao == DIARIA:
        d = base
        for _ in range(quantidade):
            d = cal.workday(d, 1)
            datas.append(d)
        return datas

    if progressao == SEMANAL:
        d = base
        for _ in range(quantidade):
            d = cal.workday(d, 5)
            datas.append(d)
        return datas

    meses = PROGRESSOES.get(progressao, PROGRESSOES[MENSAL])[1]
    i = 0
    while len(datas) < quantidade:
        d = _ultimo_dia_util_do_mes(soma_meses(base, meses * i), cal)
        if d > base:
            datas.append(d)
        i += 1
    return datas


def _ultimo_dia_util_do_mes(referencia: date, cal: Calendario) -> date:
    """``WORKDAY(EOMONTH(d;0)+1; -1)`` — o último dia útil daquele mês."""
    d = para_data(referencia)
    primeiro_do_proximo = soma_meses(date(d.year, d.month, 1), 1)
    return cal.ajusta(primeiro_do_proximo - timedelta(days=1), seguinte=False)


def curva_ndf(data_base, spot: float, curva_di: Optional[Curva],
              curva_cupom: Optional[Curva], datas: Sequence,
              calendario: Optional[Calendario] = None,
              curva_preco: Optional[Curva] = None,
              moeda: Optional[MoedaNDF] = None,
              taxa_estrangeira: float = 0.0) -> List[PontoNDF]:
    """Monta a curva a termo da moeda para uma lista de vencimentos.

    O caminho muda com o ``modo`` da moeda — cupom publicado, cupom implícito na
    curva de preço, cross entre duas curvas de preço, ou juro digitado —, mas o
    que sai é sempre a mesma linha: cupom, DI, carry, termo e pontos.
    """
    m = moeda or MOEDA_NDF_PADRAO
    cal = calendario or calendario_anbima()
    base = para_data(data_base)

    if m.modo == MODO_PRECO and curva_preco is None:
        raise ValueError(f"{m.par} precisa da curva de preço a termo")
    if m.modo == MODO_IMPLICITO and curva_preco is None:
        raise ValueError(f"{m.par} precisa da curva de preço para implicar o cupom")
    if m.modo == MODO_CUPOM and curva_cupom is None:
        raise ValueError(f"{m.par} precisa da curva de cupom")
    if m.modo != MODO_PRECO and curva_di is None:
        raise ValueError("a curva de DI é obrigatória fora do modo de cross")

    pontos: List[PontoNDF] = []
    for bruta in datas:
        d = para_data(bruta)
        dc = (d - base).days
        du = cal.dias_uteis(base, d)
        if dc <= 0:
            continue

        if m.modo == MODO_PRECO:
            # cross entre curvas de preço: o real cancela, o DI não entra
            ndf = curva_preco.taxa_para(dc, du)
            di = 0.0
            cupom = (spot / ndf - 1.0) * 360.0 / dc if ndf > 0 else 0.0
        else:
            di = curva_di.taxa_para(dc, du)
            if m.modo == MODO_CUPOM:
                cupom = curva_cupom.taxa_para(dc, du)
            elif m.modo == MODO_IMPLICITO:
                cupom = cupom_implicito(spot, curva_preco.taxa_para(dc, du),
                                        di, dc, du)
            else:
                cupom = taxa_estrangeira
            ndf = ndf_forward(spot, di, cupom, dc, du)

        pontos.append(PontoNDF(
            data=d, dias_corridos=dc, dias_uteis=du,
            cupom=cupom, di=di, carry=(1.0 + di) / (1.0 + cupom) - 1.0,
            ndf=ndf, pontos=(ndf - spot) * m.fator_pontos,
        ))
    return pontos


def casado(primeiro_futuro: float, spot: float) -> float:
    """Casado em pips: 1º futuro de dólar menos o spot (DOL cota × 1.000)."""
    return primeiro_futuro - spot * 1000.0


def rolagem(primeiro_futuro: float, segundo_futuro: float) -> float:
    """Rolagem em pips: diferença do 2º para o 1º futuro (× 10)."""
    return (segundo_futuro - primeiro_futuro) * 10.0
