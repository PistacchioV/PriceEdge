"""Instrumentos: pernas, agendas e swaps.

A estrutura reproduz, coluna por coluna, o que as planilhas fazem:

    1. Manipulação de datas   -> ``gerar_agenda``  (ajuste de dia útil, DC, DU)
    2. Curvas + interpolação  -> ``curvas.Curva``  (spot e FRA)
    3. Fluxo de repagamento   -> amortização e saldo devedor
    4. Cálculo dos juros      -> exponencial 252 ou linear 360
    5. Valor futuro           -> amortização + juros
    6. Valor presente         -> desconto pela curva da moeda certa
    7. Swap                   -> diferença de VPs, e a taxa que a zera

O erro que as próprias planilhas destacam em vermelho está tratado aqui:
num cross-currency, o fluxo em reais desconta pela curva DI e o fluxo em
dólar pela curva de cupom cambial — nunca pela mesma.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, List, Optional, Sequence

from .calendario import (FOLLOWING, Calendario, calendario_anbima, cronograma,
                         para_data)
from .curvas import Curva
from .erros import ErroDeDado
from .solver import atingir_meta

BULLET = "bullet"
LINEAR = "linear"
PERSONALIZADA = "personalizada"


# ------------------------------------------------------------------- agenda

@dataclass(frozen=True)
class Periodo:
    indice: int
    data_prevista: date
    data_pagamento: date      # ajustada para dia útil
    dc_periodo: int
    dc_total: int
    du_periodo: int
    du_total: int
    anos: float


def gerar_agenda(inicio, datas_pagamento: Sequence,
                 calendario: Optional[Calendario] = None,
                 convencao: str = FOLLOWING) -> List[Periodo]:
    """Monta as colunas de datas a partir das datas de pagamento previstas.

    ``convencao`` é a regra de dia útil aplicada a cada data de liquidação —
    ``following`` reproduz a planilha, ``modified_following`` é o padrão de
    mercado.  A data de início segue a mesma regra.
    """
    cal = calendario or calendario_anbima()
    inicio = para_data(inicio)
    inicio_ajustado = cal.ajusta(inicio, convencao=convencao)

    periodos: List[Periodo] = []
    du_ant = 0
    anterior = inicio_ajustado
    for i, bruta in enumerate(datas_pagamento, start=1):
        prevista = para_data(bruta)
        paga = cal.ajusta(prevista, convencao=convencao)
        dc_total = (paga - inicio_ajustado).days
        du_total = cal.dias_uteis(inicio_ajustado, paga)
        periodos.append(Periodo(
            indice=i,
            data_prevista=prevista,
            data_pagamento=paga,
            dc_periodo=(paga - anterior).days,
            dc_total=dc_total,
            du_periodo=du_total - du_ant,
            du_total=du_total,
            anos=dc_total / 365.0,
        ))
        du_ant, anterior = du_total, paga
    return periodos


def agenda_periodica(inicio, vencimento, meses: int,
                     calendario: Optional[Calendario] = None,
                     convencao: str = FOLLOWING,
                     sem_fluxo: bool = False) -> List[Periodo]:
    """Agenda periódica; ``sem_fluxo`` colapsa tudo num pagamento no vencimento.

    Sem fluxo intermediário o swap vira um zero-cupom: principal e juros
    liquidam de uma vez só no fim, que é como boa parte dos swaps de balcão
    brasileiros é registrada.
    """
    datas = [para_data(vencimento)] if sem_fluxo else cronograma(inicio, vencimento, meses)
    return gerar_agenda(inicio, datas, calendario, convencao)


# -------------------------------------------------------------- amortização

def pesos_amortizacao(n: int, tipo: str = BULLET,
                      personalizada: Optional[Sequence[float]] = None) -> List[float]:
    """Fração do principal amortizada em cada período (soma 1)."""
    if tipo == PERSONALIZADA:
        if not personalizada or len(personalizada) != n:
            raise ErroDeDado("amortização personalizada precisa de um peso por período")
        total = sum(personalizada)
        if abs(total - 1.0) > 1e-9:
            raise ErroDeDado("os pesos de amortização somam {total}, deveriam somar 1",
                         total=f"{total:.6f}")
        return [float(p) for p in personalizada]
    if tipo == LINEAR:
        return [1.0 / n] * n
    return [0.0] * (n - 1) + [1.0]        # bullet


# -------------------------------------------------------------------- fluxo

@dataclass
class Fluxo:
    periodo: Periodo
    saldo: float
    amortizacao: float
    taxa_periodo: float
    juros: float
    valor_futuro: float
    fator_desconto: float
    pv_amortizacao: float
    pv_juros: float

    @property
    def pv(self) -> float:
        return self.pv_amortizacao + self.pv_juros

    def para_dict(self) -> dict:
        p = self.periodo
        return {
            "n": p.indice,
            "data_prevista": p.data_prevista.isoformat(),
            "data_pagamento": p.data_pagamento.isoformat(),
            "dc_periodo": p.dc_periodo, "dc_total": p.dc_total,
            "du_periodo": p.du_periodo, "du_total": p.du_total,
            "saldo": self.saldo, "amortizacao": self.amortizacao,
            "taxa_periodo": self.taxa_periodo, "juros": self.juros,
            "valor_futuro": self.valor_futuro,
            "fator_desconto": self.fator_desconto,
            "pv_amortizacao": self.pv_amortizacao, "pv_juros": self.pv_juros,
            "pv": self.pv,
        }


@dataclass
class ResultadoPerna:
    nome: str
    moeda: str
    fluxos: List[Fluxo]
    fx: float = 1.0            # conversão para a moeda de referência do swap

    @property
    def pv(self) -> float:
        return sum(f.pv for f in self.fluxos) * self.fx

    @property
    def pv_juros(self) -> float:
        return sum(f.pv_juros for f in self.fluxos) * self.fx

    @property
    def pv_amortizacao(self) -> float:
        return sum(f.pv_amortizacao for f in self.fluxos) * self.fx

    @property
    def valor_futuro(self) -> float:
        return sum(f.valor_futuro for f in self.fluxos) * self.fx

    def para_dict(self) -> dict:
        return {
            "nome": self.nome, "moeda": self.moeda, "fx": self.fx,
            "pv": self.pv, "pv_juros": self.pv_juros,
            "pv_amortizacao": self.pv_amortizacao,
            "valor_futuro": self.valor_futuro,
            "fluxos": [f.para_dict() for f in self.fluxos],
        }


# ------------------------------------------------------------------- pernas

def perna_prefixada_exp252(nocional: float, taxa: float, periodos: List[Periodo],
                           curva_desconto: Curva, pesos: List[float],
                           nome: str = "Pré BRL", moeda: str = "BRL") -> ResultadoPerna:
    """Perna pré em reais: juros exponenciais 252, desconto pela curva DI."""
    fluxos, saldo = [], nocional
    for periodo, peso in zip(periodos, pesos):
        amortizacao = nocional * peso
        taxa_periodo = (1.0 + taxa) ** (periodo.du_periodo / 252.0) - 1.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        fd = curva_desconto.fator_desconto(periodo.dc_total, periodo.du_total)
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, fd,
                            amortizacao * fd, juros * fd))
        saldo -= amortizacao
    return ResultadoPerna(nome, moeda, fluxos)


def perna_cdi_spread(nocional: float, spread: float, periodos: List[Periodo],
                     curva_di: Curva, pesos: List[float],
                     nome: str = "CDI + spread", moeda: str = "BRL") -> ResultadoPerna:
    """Perna CDI ± spread.

    O spread é **multiplicativo**, não aditivo — o aviso em vermelho da
    planilha: ``(1 + CDI) * (1 + spread) = (1 + taxa pré)``.  Os juros de cada
    período usam o FRA do DI entre os dois vértices, não a taxa spot.
    """
    fluxos, saldo = [], nocional
    dc_ant = du_ant = 0
    for periodo, peso in zip(periodos, pesos):
        if periodo.du_periodo == 0:
            fra = curva_di.taxa_para(periodo.dc_total, periodo.du_total)
        else:
            fra = curva_di.forward(dc_ant, periodo.dc_total, du_ant, periodo.du_total)
        amortizacao = nocional * peso
        taxa_periodo = ((1.0 + fra) * (1.0 + spread)) ** (periodo.du_periodo / 252.0) - 1.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        fd = curva_di.fator_desconto(periodo.dc_total, periodo.du_total)
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, fd,
                            amortizacao * fd, juros * fd))
        saldo -= amortizacao
        dc_ant, du_ant = periodo.dc_total, periodo.du_total
    return ResultadoPerna(nome, moeda, fluxos)


def perna_cdi_percentual(nocional: float, percentual: float, periodos: List[Periodo],
                         curva_di: Curva, pesos: List[float],
                         nome: str = "% do CDI", moeda: str = "BRL") -> ResultadoPerna:
    """Perna em percentual do CDI — 110% do CDI, 97,5% do CDI.

    Convenção diferente do spread, e a diferença é o ponto todo: o percentual
    incide sobre a **taxa diária**, não sobre a taxa anual.  O fator do período é

        [1 + ((1 + CDI)^(1/252) − 1) · p] ^ DU

    e não ``(1 + p·CDI)^(DU/252)``.  Aplicar o percentual direto na taxa anual
    superestima — ou melhor, subestima — o juro, porque a capitalização diária
    não é linear: com CDI a 14% ao ano, 110% do CDI dá 15,5031% ao ano, e
    não os 15,40% que sairiam de multiplicar a taxa anual por 1,10.
    """
    fluxos, saldo = [], nocional
    dc_ant = du_ant = 0
    for periodo, peso in zip(periodos, pesos):
        if periodo.du_periodo == 0:
            fra = curva_di.taxa_para(periodo.dc_total, periodo.du_total)
        else:
            fra = curva_di.forward(dc_ant, periodo.dc_total, du_ant, periodo.du_total)
        taxa_diaria = (1.0 + fra) ** (1.0 / 252.0) - 1.0
        amortizacao = nocional * peso
        taxa_periodo = (1.0 + taxa_diaria * percentual) ** periodo.du_periodo - 1.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        fd = curva_di.fator_desconto(periodo.dc_total, periodo.du_total)
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, fd,
                            amortizacao * fd, juros * fd))
        saldo -= amortizacao
        dc_ant, du_ant = periodo.dc_total, periodo.du_total
    return ResultadoPerna(nome, moeda, fluxos)


SPREAD = "spread"
PERCENTUAL = "percentual"


def perna_cdi(nocional: float, periodos: List[Periodo], curva_di: Curva,
              pesos: List[float], modo: str = SPREAD, valor: float = 0.0,
              nome: Optional[str] = None) -> ResultadoPerna:
    """Perna CDI nos dois modos de mercado.

    ``modo="spread"``     ``valor`` é o spread multiplicativo (0,025 = +2,5%)
    ``modo="percentual"`` ``valor`` é o percentual do CDI (1,10 = 110%)
    """
    if modo == PERCENTUAL:
        return perna_cdi_percentual(nocional, valor, periodos, curva_di, pesos,
                                    nome=nome or f"{valor * 100:.4g}% do CDI")
    return perna_cdi_spread(nocional, valor, periodos, curva_di, pesos,
                            nome=nome or "CDI ± spread")


def perna_pre_usd(nocional_usd: float, taxa: float, periodos: List[Periodo],
                  curva_cupom: Curva, pesos: List[float], fx: float,
                  nome: str = "Pré USD", moeda: str = "USD") -> ResultadoPerna:
    """Perna pré em dólar: juros lineares 360, desconto pelo cupom cambial.

    O resultado sai em USD; ``fx`` (dólar de partida) converte para reais na
    comparação de VPs.
    """
    fluxos, saldo = [], nocional_usd
    for periodo, peso in zip(periodos, pesos):
        amortizacao = nocional_usd * peso
        taxa_periodo = periodo.dc_periodo * taxa / 360.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        fd = curva_cupom.fator_desconto(periodo.dc_total)
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, fd,
                            amortizacao * fd, juros * fd))
        saldo -= amortizacao
    return ResultadoPerna(nome, moeda, fluxos, fx=fx)


def perna_ipca_capitalizado(nocional: float, taxa_real: float, periodos: List[Periodo],
                            curva_di: Curva, curva_ipca: Curva, pesos: List[float],
                            ni_base: float = 1.0,
                            nome: str = "IPCA capitalizado", moeda: str = "BRL") -> ResultadoPerna:
    """Perna IPCA+ capitalizada.

    A inflação implícita vem das duas curvas da B3:

        inflação = (1 + DI) / (1 + DI x IPCA) - 1

    daí o FRA da inflação por período, o índice acumulado e o número-índice
    projetado.  Principal e juros são corrigidos por ``NI_proj / NI_base``.
    """
    fluxos, saldo = [], nocional
    du_ant = 0
    indice = 1.0
    infl_ant = None
    for periodo, peso in zip(periodos, pesos):
        di = curva_di.taxa(periodo.dc_total)
        real = curva_ipca.taxa(periodo.dc_total)
        inflacao = (1.0 + di) / (1.0 + real) - 1.0
        if infl_ant is None or periodo.du_periodo == 0:
            fra_infl = inflacao
        else:
            f2 = (1.0 + inflacao) ** (periodo.du_total / 252.0)
            f1 = (1.0 + infl_ant) ** (du_ant / 252.0)
            fra_infl = (f2 / f1) ** (252.0 / periodo.du_periodo) - 1.0
        indice *= (1.0 + fra_infl) ** (periodo.du_periodo / 252.0)

        amortizacao = nocional * peso
        taxa_periodo = (1.0 + taxa_real) ** (periodo.du_periodo / 252.0) - 1.0
        juros = taxa_periodo * saldo * indice
        amortizacao_corrigida = amortizacao * indice
        vf = amortizacao_corrigida + juros
        fd = curva_di.fator_desconto(periodo.dc_total, periodo.du_total)
        fluxos.append(Fluxo(periodo, saldo * indice, amortizacao_corrigida,
                            taxa_periodo, juros, vf, fd,
                            amortizacao_corrigida * fd, juros * fd))
        saldo -= amortizacao
        du_ant, infl_ant = periodo.du_total, inflacao
    return ResultadoPerna(nome, moeda, fluxos)


def perna_term_sofr(nocional_usd: float, spread: float, periodos: List[Periodo],
                    curva_sofr, pesos: List[float], inicio, fx: float = 1.0,
                    nome: str = "Term SOFR ± spread", moeda: str = "USD") -> ResultadoPerna:
    """Perna flutuante em dólar sobre Term SOFR, linear 360.

    ``curva_sofr`` é uma ``CurvaTermSOFR`` (bootstrap dos futuros SR3).  O
    spread aqui é aditivo, como é a praxe do mercado de SOFR — ao contrário do
    CDI, onde ele é multiplicativo.

    Os fatores de desconto são tomados a partir de ``inicio``, não da primeira
    data IMM: um swap que comece depois do spot desconta a partir da sua
    própria data, senão o primeiro forward sai inflado.
    """
    fluxos, saldo = [], nocional_usd
    df_ant = 1.0
    for periodo, peso in zip(periodos, pesos):
        df = curva_sofr.fator_desconto_entre(inicio, periodo.data_pagamento)
        dc = periodo.dc_periodo
        forward = (df_ant / df - 1.0) * 360.0 / dc if dc else 0.0
        amortizacao = nocional_usd * peso
        taxa_periodo = (forward + spread) * dc / 360.0
        juros = taxa_periodo * saldo
        vf = amortizacao + juros
        fluxos.append(Fluxo(periodo, saldo, amortizacao, taxa_periodo, juros, vf, df,
                            amortizacao * df, juros * df))
        saldo -= amortizacao
        df_ant = df
    return ResultadoPerna(nome, moeda, fluxos, fx=fx)


# --------------------------------------------------------------------- swap

@dataclass
class Swap:
    """Duas pernas e o que se pergunta delas: MtM, taxa par e risco."""

    nome: str
    ativa: ResultadoPerna
    passiva: ResultadoPerna
    moeda_referencia: str = "BRL"
    fee: float = 0.0

    @property
    def mtm(self) -> float:
        """Diferença de VPs, na ótica de quem está ativo na primeira perna."""
        return self.ativa.pv - self.passiva.pv - self.fee

    @property
    def prazo_medio(self) -> float:
        """Σ(dc · amortização) / Σamortização / 365.

        É o ``SUMPRODUCT(H9:H19; U9:U19)/U6/365`` das planilhas: pondera pelo
        **principal amortizado**, não pelo fluxo de caixa.  Num bullet dá
        exatamente o prazo do swap.
        """
        return _media_ponderada(self.ativa, lambda f: f.amortizacao)

    @property
    def duration(self) -> float:
        """Σ(dc · VP) / ΣVP / 365 — Macaulay em anos.

        ``SUMPRODUCT(H9:H19; AD9:AD19)/AD6/365``: pondera pelo valor presente
        do fluxo inteiro (principal + juros), então fica abaixo do prazo médio
        sempre que houver cupom no meio do caminho.
        """
        return _media_ponderada(self.ativa, lambda f: f.pv)

    def para_dict(self) -> dict:
        return {
            "nome": self.nome,
            "moeda_referencia": self.moeda_referencia,
            "mtm": self.mtm, "fee": self.fee,
            "prazo_medio": self.prazo_medio, "duration": self.duration,
            "ativa": self.ativa.para_dict(),
            "passiva": self.passiva.para_dict(),
        }


def _media_ponderada(perna: ResultadoPerna, peso: Callable[[Fluxo], float]) -> float:
    total = sum(peso(f) for f in perna.fluxos)
    if not total:
        return 0.0
    return sum(f.periodo.dc_total * peso(f) for f in perna.fluxos) / total / 365.0


def taxa_par(construir_swap: Callable[[float], Swap], chute: float = 0.10) -> float:
    """Taxa que zera o MtM — o ``GoalSeek`` das macros, agora explícito."""
    return atingir_meta(lambda x: construir_swap(x).mtm, chute=chute)


def dv01(construir_swap: Callable[[Curva], Swap], curva: Curva,
         bp: float = 0.0001) -> float:
    """Variação do MtM para +1 bp paralelo na curva (coluna "Shift")."""
    base = construir_swap(curva).mtm
    deslocado = construir_swap(curva.deslocada(bp)).mtm
    return deslocado - base
