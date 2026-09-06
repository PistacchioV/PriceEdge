"""Contagem de dias (day count) e regime de capitalização.

Duas escolhas independentes que a tela costuma tratar como uma só, e não são:

**A contagem** define a fração de ano τ entre duas datas. **O regime** define o
que se faz com ela — ``(1+i)^τ`` (composto) ou ``1 + i·τ`` (simples). Um pré
brasileiro é DU/252 composto; um cupom cambial é ACT/360 simples; um bond em
dólar é 30/360 composto. Trocar uma sem trocar a outra dá um número que parece
certo e não é.

As convenções aqui são as da ISDA, com a DU/252 da B3 no topo por ser o padrão
do mercado local:

    DU/252     dias úteis do calendário escolhido, sobre 252
    ACT/360    dias corridos sobre 360 — cupom cambial, SOFR, LIBOR
    ACT/365    dias corridos sobre 365 — mercado de libra, e a base "fixed"
    30/360     bond basis (ISDA 2006 4.16(f)): todo mês tem 30 dias
    30E/360    eurobond — a variante que também trunca o dia final em 30
    ACT/ACT    ISDA: cada trecho de ano dividido pelo tamanho real daquele ano

A diferença não é acadêmica. Em 181 dias corridos que contêm 125 dias úteis,
τ vai de 0,4960 (DU/252) a 0,5028 (ACT/360) — 68 pontos-base de fração de ano,
que a 14% a.a. valem quase R$ 9.500 num notional de 100 milhões.
"""

from __future__ import annotations

from calendar import isleap
from datetime import date
from typing import Optional

from .calendario import Calendario, calendario_anbima, para_data

DU_252 = "du_252"
ACT_360 = "act_360"
ACT_365 = "act_365"
T30_360 = "30_360"
T30E_360 = "30e_360"
ACT_ACT = "act_act"

CONVENCOES = [
    (DU_252, "DU/252 — dias úteis", "Padrão do mercado brasileiro: DI, pré em real, IPCA e TR."),
    (ACT_360, "ACT/360 — dias corridos", "Cupom cambial, SOFR e a maior parte do mercado em dólar."),
    (ACT_365, "ACT/365 — dias corridos", "Mercado de libra esterlina e a base fixa de ACT/365."),
    (T30_360, "30/360 — bond basis", "Todo mês vale 30 dias e todo ano 360; padrão de bond corporativo."),
    (T30E_360, "30E/360 — eurobond", "Como a 30/360, mas o dia final também é truncado em 30."),
    (ACT_ACT, "ACT/ACT — ISDA", "Cada trecho de ano dividido pelo tamanho real daquele ano."),
]
CONVENCAO_POR_CODIGO = {codigo: (nome, texto) for codigo, nome, texto in CONVENCOES}

# convenções que precisam de calendário: só a de dias úteis
COM_CALENDARIO = {DU_252}

COMPOSTO = "composto"
SIMPLES = "simples"

REGIMES = [
    (COMPOSTO, "Composto — (1 + i) ^ τ"),
    (SIMPLES, "Simples — 1 + i · τ"),
]

# o par que o mercado usa por padrão em cada contagem
REGIME_PADRAO = {DU_252: COMPOSTO, ACT_360: SIMPLES, ACT_365: SIMPLES,
                 T30_360: COMPOSTO, T30E_360: COMPOSTO, ACT_ACT: COMPOSTO}


def _dias_30_360(d0: date, d1: date, europeu: bool) -> int:
    """Dias entre as datas na régua de 30 dias por mês.

    Na 30/360 (bond basis) o dia final só cai para 30 se o inicial já tiver
    caído; na 30E/360 ele cai sempre. É a única diferença entre as duas.
    """
    dia0, dia1 = d0.day, d1.day
    if europeu:
        dia0, dia1 = min(dia0, 30), min(dia1, 30)
    else:
        if dia0 == 31:
            dia0 = 30
        if dia1 == 31 and dia0 == 30:
            dia1 = 30
    return 360 * (d1.year - d0.year) + 30 * (d1.month - d0.month) + (dia1 - dia0)


def _fracao_act_act(d0: date, d1: date) -> float:
    """ACT/ACT ISDA: soma dos trechos, cada um sobre o seu próprio ano."""
    total = 0.0
    for ano in range(d0.year, d1.year + 1):
        trecho_inicio = max(d0, date(ano, 1, 1))
        trecho_fim = min(d1, date(ano + 1, 1, 1))
        if trecho_fim > trecho_inicio:
            total += (trecho_fim - trecho_inicio).days / (366.0 if isleap(ano) else 365.0)
    return total


def dias(convencao: str, inicio, fim,
         calendario: Optional[Calendario] = None) -> int:
    """Quantos dias a convenção conta entre as duas datas.

    É o numerador da fração: dias úteis na DU/252, corridos nas ACT, e os dias
    da régua de 30 nas 30/360.
    """
    d0, d1 = para_data(inicio), para_data(fim)
    if convencao == DU_252:
        return (calendario or calendario_anbima()).dias_uteis(d0, d1)
    if convencao == T30_360:
        return _dias_30_360(d0, d1, europeu=False)
    if convencao == T30E_360:
        return _dias_30_360(d0, d1, europeu=True)
    return (d1 - d0).days


def base(convencao: str) -> Optional[int]:
    """O denominador da convenção — ``None`` na ACT/ACT, que não tem um fixo."""
    if convencao == DU_252:
        return 252
    if convencao in (ACT_365,):
        return 365
    if convencao == ACT_ACT:
        return None
    return 360


def fracao(convencao: str, inicio, fim,
           calendario: Optional[Calendario] = None) -> float:
    """A fração de ano τ da convenção."""
    d0, d1 = para_data(inicio), para_data(fim)
    if convencao == ACT_ACT:
        return _fracao_act_act(d0, d1)
    denominador = base(convencao)
    return dias(convencao, d0, d1, calendario) / float(denominador)


def fator(taxa: float, convencao: str, regime: str, inicio, fim,
          calendario: Optional[Calendario] = None) -> float:
    """Fator de capitalização da taxa no período, na contagem e no regime dados."""
    tau = fracao(convencao, inicio, fim, calendario)
    if regime == SIMPLES:
        return 1.0 + taxa * tau
    return (1.0 + taxa) ** tau


def descrever(convencao: str, regime: str, inicio, fim,
              calendario: Optional[Calendario] = None) -> tuple:
    """(molde, valores) para a tela bilíngue — a conta que foi feita, por extenso."""
    nome = CONVENCAO_POR_CODIGO.get(convencao, (convencao, ""))[0].split(" — ")[0]
    return ("{nome} · {dias} dias · τ = {tau}", {
        "nome": nome,
        "dias": dias(convencao, inicio, fim, calendario),
        "tau": f"{fracao(convencao, inicio, fim, calendario):.6f}".replace(".", ","),
    })
