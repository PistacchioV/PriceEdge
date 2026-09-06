"""Liquidação de swap — quanto de fato se paga, e sobre qual saldo.

A tela de precificação responde "quanto vale hoje": desconta fluxo futuro pelas
curvas da B3 e devolve MtM e taxa par. Esta responde a outra pergunta, a que
aparece no dia do caixa: **quanto uma parte paga à outra**. São contas
diferentes e nenhuma substitui a outra.

Três diferenças que valem por todo o módulo:

1. **Índice realizado, não projetado.** O CDI vem da série 4389 do Banco
   Central, dia a dia, e a variação cambial vem da PTAX publicada. Nada aqui
   sai de curva interpolada — é o que aconteceu. Por isso o fim do fluxo não
   pode passar de hoje quando alguma ponta é indexada.

2. **A base é o notional remanescente.** Num swap com amortização o principal
   cai a cada pagamento, e o que rende no fluxo seguinte é o que sobrou.
   Aplicar o notional original num swap já amortizado infla o ajuste na
   proporção exata do que já foi pago, e o erro passa despercebido porque a
   conta continua fechando consigo mesma. Aqui o saldo remanescente é campo de
   entrada, e é ele — não o notional de registro — que multiplica o fator das
   duas pontas.

3. **Só a diferença liquida.** O principal do swap é nocional: não troca de
   mãos. O que passa de uma parte para a outra é ``VF_ativa − VF_passiva``, e
   quem tem o resultado negativo paga.

As três datas não são a mesma coisa e o módulo as separa de propósito:

    data da operação   contratação — conta o prazo para a tabela do IR
    início do fluxo    onde os índices começam a acumular
    fim do fluxo       onde param, e a data do ajuste

Cada ponta escolhe a sua contagem de dias e o seu regime — DU/252, ACT/360,
ACT/365, 30/360, 30E/360 ou ACT/ACT, composto ou simples. O módulo ``contagem``
guarda essa parte; aqui entra apenas o τ que ela devolve:

    Pré              F = cap(i, τ)
    % do CDI         F = Π [ 1 + ((1 + DI_k)^(1/252) − 1) · p ]
    CDI + spread     F = Π (1 + DI_k)^(1/252) · cap(s, τ)
    Cambial          F = cap(c, τ)
    SOFR composto    F = Π (1 + SOFR_k · n/360) · cap(s, τ)
    Term SOFR        F = cap(fixing + s, τ)
    EURIBOR          F = cap(fixing + s, τ)
    IPCA             F = (NI_final / NI_inicial) · cap(c, τ)
    Equity           F = (preço_final / preço_inicial) · cap(s, τ)

e uma ponta em moeda estrangeira multiplica tudo isso pela variação cambial,
``fixing_final / fixing_inicial``. As duas metades ficam guardadas separadas no
resultado: dá para ver se o ajuste veio do índice ou do câmbio.

onde ``cap(i, τ)`` é ``(1+i)^τ`` no regime composto e ``1 + i·τ`` no simples.

O acúmulo do CDI é a exceção que não se escolhe: ele é um produto de fatores
diários ``(1 + DI_k)^(1/252)``, um por fixing publicado, e essa capitalização
diária **é** a definição do índice. A contagem escolhida na ponta de CDI vale
para o spread, não para o produto — e a tela diz isso.

A PTAX que entra nas pontas cambiais é a de **fechamento do dia útil anterior**
a cada data, que é como o swap registrado na B3 define a variação cambial. Quem
tiver a confirmação na mão digita as duas e a busca sai do caminho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from . import cambio, cdi, contagem, euribor, sofr
from .calendario import (Calendario, calendario_anbima, calendario_sofr,
                         para_data)
from .renda_fixa import aliquota_ir

PRE = "pre"
CDI_PERCENTUAL = "cdi_percentual"
CDI_SPREAD = "cdi_spread"
CAMBIO = "cambio"
SOFR = "sofr"
TERM_SOFR = "term_sofr"
EURIBOR = "euribor"
IPCA = "ipca"
EQUITY = "equity"
FATOR = "fator"

INDEXADORES = [
    (PRE, "Pré — taxa fixa ao ano"),
    (CDI_PERCENTUAL, "CDI — % do CDI realizado"),
    (CDI_SPREAD, "CDI + spread realizado"),
    (CAMBIO, "Variação cambial + cupom"),
    (SOFR, "SOFR composto realizado + spread"),
    (TERM_SOFR, "Term SOFR do fixing + spread"),
    (EURIBOR, "EURIBOR do fixing + spread"),
    (IPCA, "IPCA por número-índice + cupom real"),
    (EQUITY, "Equity — ação ou índice, por variação de preço"),
    (FATOR, "Fator acumulado digitado"),
]
INDEXADOR_POR_CODIGO = dict(INDEXADORES)

# indexadores que leem o que já aconteceu: o fluxo não pode terminar no futuro
REALIZADOS = {CDI_PERCENTUAL, CDI_SPREAD, CAMBIO, SOFR, EURIBOR}

# indexadores cujo fluxo é denominado em moeda estrangeira. Todos eles pedem o
# par de fixings que traz a ponta de volta para reais — sem isso a variação
# cambial some da conta e o ajuste sai no tamanho errado.
# equity entra aqui porque um índice estrangeiro — S&P, Nasdaq, Euro Stoxx —
# rende na moeda dele e só vira reais depois da conversão
COM_MOEDA = {CAMBIO, SOFR, TERM_SOFR, EURIBOR, EQUITY}

# a moeda de cada índice, quando ele tem uma só
MOEDA_DO_INDEXADOR = {SOFR: "USD", TERM_SOFR: "USD", EURIBOR: "EUR"}

SEM_CONVERSAO = "BRL"

# moedas que a ponta aceita — as que o Banco Central boletina
MOEDAS = [(SEM_CONVERSAO, "Real — fluxo já em reais, sem conversão"),
          ("USD", "Dólar dos Estados Unidos"), ("EUR", "Euro"),
          ("GBP", "Libra esterlina"), ("JPY", "Iene"), ("CHF", "Franco suíço")]

TENORES_EURIBOR = list(euribor.TENORES)
TENORES_TERM_SOFR = ["1 month", "3 month", "6 month", "12 month"]

# indexadores de taxa a termo: a taxa é fixada antes do fluxo começar, e a data
# em que ela foi lida é campo próprio. O padrão do mercado é D-2 úteis do
# início — dois dias para o fixing publicado virar a taxa do período.
COM_FIXING = {TERM_SOFR, EURIBOR}
DEFASAGEM_FIXING = 2

ATIVA = "ativa"
PASSIVA = "passiva"

SOBRE_ORIGINAL = "original"
SOBRE_REMANESCENTE = "remanescente"

BASES_AMORTIZACAO = [
    (SOBRE_ORIGINAL, "Sobre o valor original — parcela constante"),
    (SOBRE_REMANESCENTE, "Sobre o saldo remanescente — parcela decrescente"),
]


class ErroLiquidacao(ValueError):
    """Dado que falta ou não fecha para liquidar."""


def amortizar(nocional_original: float, saldo: float, percentual: float,
              base: str = SOBRE_ORIGINAL) -> float:
    """Quanto o percentual de amortização vale em dinheiro.

    Os mesmos "10%" dão dois números diferentes conforme a base, e a diferença
    cresce a cada parcela paga. Sobre o **valor original** a parcela é constante
    — 10% de 100 milhões são 10 milhões no primeiro fluxo e no último. Sobre o
    **saldo remanescente** ela é decrescente: 10% de um saldo de 60 milhões são
    6 milhões, e o principal nunca zera por amortização percentual.

    A amortização acontece **no fim do fluxo**: ela não entra no fator deste
    período, que rendeu sobre o saldo de abertura. Ela define o saldo do fluxo
    seguinte.
    """
    if percentual <= 0:
        return 0.0
    referencia = saldo if base == SOBRE_REMANESCENTE else nocional_original
    return min(saldo, referencia * percentual)


# ---------------------------------------------------------------- as pontas

@dataclass
class Ponta:
    """Como uma ponta do swap é remunerada.

    ``taxa`` é sempre decimal: 0,14 para 14% a.a. pré, 1,10 para 110% do CDI,
    0,02 para CDI+2%, 0,0325 para um cupom cambial de 3,25%.
    """
    indexador: str
    taxa: float = 0.0
    convencao: str = contagem.DU_252
    regime: str = contagem.COMPOSTO
    moeda: str = "USD"
    ptax_inicial: Optional[float] = None
    ptax_final: Optional[float] = None
    ni_inicial: Optional[float] = None
    ni_final: Optional[float] = None
    fator_manual: Optional[float] = None
    ativo: str = ""                        # equity: ticker ou nome do índice
    preco_inicial: Optional[float] = None  # equity
    preco_final: Optional[float] = None    # equity
    tenor: str = "3 month"                 # EURIBOR e Term SOFR
    data_fixing: Optional[date] = None     # padrão: D-2 úteis do início
    taxa_indice: Optional[float] = None    # Term SOFR entra digitado (licenciado)
    lookback: int = 0                      # SOFR composto
    shift: int = 0                         # SOFR composto


@dataclass
class PontaLiquidada:
    """A ponta depois da conta: fator, valor e de onde o fator saiu."""
    indexador: str
    fator: float
    nocional: float
    valor: float
    descricao: tuple = ("", {})    # (molde, valores) — a tela é bilíngue
    convencao: str = contagem.DU_252
    regime: str = contagem.COMPOSTO
    dias_contados: int = 0         # o numerador da convenção escolhida
    fracao_de_ano: float = 0.0     # τ
    contagem_vale_para_spread: bool = False
    dias_uteis: int = 0
    dias_corridos: int = 0
    moeda: Optional[str] = None
    fator_cambial: float = 1.0     # (fixing final / fixing inicial)
    fator_do_indice: float = 1.0   # o que a ponta rendeu na moeda dela
    ptax_inicial: Optional[float] = None
    ptax_final: Optional[float] = None
    data_ptax_inicial: Optional[date] = None
    data_ptax_final: Optional[date] = None
    data_fixing: Optional[date] = None
    taxa_do_fixing: Optional[float] = None
    tenor: Optional[str] = None
    ativo: Optional[str] = None
    preco_inicial: Optional[float] = None
    preco_final: Optional[float] = None
    fixings: List = field(default_factory=list)

    @property
    def juros(self) -> float:
        return self.valor - self.nocional


def _numero(valor: float, casas: int = 4) -> str:
    """Número já no padrão brasileiro, para entrar no molde da descrição."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _ptax_do_dia_anterior(moeda: str, referencia: date) -> cambio.Ptax:
    """PTAX de fechamento do dia útil anterior — a convenção do contrato.

    A busca já anda para trás sozinha até dez dias, o que resolve fim de semana,
    feriado e o dia corrente antes das 13h.
    """
    return cambio.ptax_moeda(moeda, referencia - timedelta(days=1))


def data_de_fixing(inicio, calendario: Optional[Calendario] = None,
                   defasagem: int = DEFASAGEM_FIXING) -> date:
    """A data em que a taxa a termo foi lida — D-2 úteis do início do fluxo.

    EURIBOR e Term SOFR são taxas *forward-looking*: valem para o período
    inteiro e são fixadas antes de ele começar. Dois dias úteis é a defasagem
    padrão, e ela não é decoração — num fim de trimestre a taxa de D-2 e a de
    D-1 podem estar a vários pontos-base de distância.
    """
    cal = calendario or calendario_anbima()
    return cal.workday(para_data(inicio), -abs(defasagem))


def _fixing_euribor(tenor: str, quando: date) -> tuple:
    """Fixing da EURIBOR no prazo e na data — ou o último publicado antes dela."""
    curva = euribor.carregar()
    data, linha = curva.em(quando)
    if not linha or tenor not in linha:
        raise ErroLiquidacao(
            f"não há fixing de EURIBOR {tenor} publicado até {quando:%d/%m/%Y}")
    return data, linha[tenor] / 100.0


def _fator_cambial(ponta: Ponta, d0: date, d1: date) -> tuple:
    """(fator, fixing inicial, fixing final, data inicial, data final).

    Sem conversão quando o fluxo já está em reais. Com conversão, os dois
    fixings entram digitados ou vêm da PTAX do dia útil anterior a cada data.
    """
    if ponta.indexador not in COM_MOEDA or ponta.moeda == SEM_CONVERSAO:
        return 1.0, None, None, None, None
    p0, p1 = ponta.ptax_inicial, ponta.ptax_final
    data0 = data1 = None
    if p0 is None or p1 is None:
        b0 = _ptax_do_dia_anterior(ponta.moeda, d0)
        b1 = _ptax_do_dia_anterior(ponta.moeda, d1)
        p0 = p0 if p0 is not None else b0.venda
        p1 = p1 if p1 is not None else b1.venda
        data0, data1 = b0.data, b1.data
    if not p0:
        raise ErroLiquidacao("o fixing inicial da moeda não pode ser zero")
    return p1 / p0, p0, p1, data0, data1


def liquidar_ponta(ponta: Ponta, nocional: float, inicio, fim,
                   calendario: Optional[Calendario] = None,
                   arredondar_di: bool = False) -> PontaLiquidada:
    """Fator acumulado da ponta no fluxo, aplicado ao notional remanescente.

    O fator de uma ponta em moeda estrangeira tem duas metades que o módulo
    guarda separadas: o que ela rendeu **na moeda dela** e a variação cambial
    que a traz de volta para reais. Juntas viram um número só; separadas, dá
    para ver qual das duas explicou o ajuste.
    """
    cal = calendario or calendario_anbima()
    d0, d1 = para_data(inicio), para_data(fim)
    tau = contagem.fracao(ponta.convencao, d0, d1, cal)
    fx, p0, p1, data_p0, data_p1 = _fator_cambial(ponta, d0, d1)
    comum = dict(
        indexador=ponta.indexador, nocional=nocional,
        convencao=ponta.convencao, regime=ponta.regime,
        dias_contados=contagem.dias(ponta.convencao, d0, d1, cal),
        fracao_de_ano=tau,
        dias_uteis=cal.dias_uteis(d0, d1), dias_corridos=(d1 - d0).days,
        moeda=ponta.moeda if ponta.indexador in COM_MOEDA else None,
        fator_cambial=fx, ptax_inicial=p0, ptax_final=p1,
        data_ptax_inicial=data_p0, data_ptax_final=data_p1,
    )

    def capitalizar(taxa: float) -> float:
        return contagem.fator(taxa, ponta.convencao, ponta.regime, d0, d1, cal)

    def montar(indice: float, descricao: tuple, **extra) -> PontaLiquidada:
        fator = fx * indice
        return PontaLiquidada(fator=fator, valor=nocional * fator,
                              fator_do_indice=indice, descricao=descricao,
                              **comum, **extra)

    if ponta.indexador == PRE:
        return montar(capitalizar(ponta.taxa),
                      ("{taxa}% a.a. sobre τ = {tau}",
                       {"taxa": _numero(ponta.taxa * 100), "tau": _numero(tau, 6)}))

    if ponta.indexador in (CDI_PERCENTUAL, CDI_SPREAD):
        com_spread = ponta.indexador == CDI_SPREAD
        acumulado = cdi.acumular(cdi.serie(d0, d1), d0, d1, valor=1.0,
                                 percentual=1.0 if com_spread else ponta.taxa,
                                 arredondar=arredondar_di)
        indice = acumulado.fator
        if com_spread:
            # o produto diário é a definição do índice; a contagem escolhida
            # capitaliza só o spread, que é onde ela de fato tem escolha
            indice *= capitalizar(ponta.taxa)
            molde = "CDI + {taxa}% em {du} dias úteis publicados"
            valores = {"taxa": _numero(ponta.taxa * 100), "du": acumulado.dias_uteis}
        else:
            molde = "{taxa}% do CDI em {du} dias úteis publicados"
            valores = {"taxa": _numero(ponta.taxa * 100, 2), "du": acumulado.dias_uteis}
        return montar(indice, (molde, valores), fixings=acumulado.dias,
                      contagem_vale_para_spread=com_spread)

    if ponta.indexador == CAMBIO:
        return montar(
            capitalizar(ponta.taxa),
            ("variação de {variacao}% mais cupom de {taxa}% sobre τ = {tau}",
             {"variacao": _numero((fx - 1) * 100), "taxa": _numero(ponta.taxa * 100),
              "tau": _numero(tau, 6)}))

    if ponta.indexador == SOFR:
        composto = sofr.compor(sofr.serie_sofr(d0, d1), d0, d1,
                               lookback=ponta.lookback, shift=ponta.shift,
                               calendario=calendario_sofr())
        indice = composto.fator * capitalizar(ponta.taxa)
        return montar(
            indice,
            ("SOFR composto de {sofr}% mais spread de {taxa}% em {dc} dias corridos",
             {"sofr": _numero(composto.taxa_composta * 100),
              "taxa": _numero(ponta.taxa * 100), "dc": composto.dias_corridos}),
            fixings=composto.dias, taxa_do_fixing=composto.taxa_composta)

    if ponta.indexador in (TERM_SOFR, EURIBOR):
        quando = ponta.data_fixing or data_de_fixing(d0, cal)
        if ponta.indexador == EURIBOR:
            # a base local guarda o histórico; o Term SOFR da CME é licenciado
            # e não pode ser redistribuído, então ele entra digitado
            quando, taxa_indice = _fixing_euribor(ponta.tenor, quando)
        elif ponta.taxa_indice is None:
            raise ErroLiquidacao(
                "o Term SOFR é licenciado pela CME e não tem fonte pública — "
                "informe a taxa do fixing")
        else:
            taxa_indice = ponta.taxa_indice
        indice = capitalizar(taxa_indice + ponta.taxa)
        nome = "Term SOFR" if ponta.indexador == TERM_SOFR else "EURIBOR"
        return montar(
            indice,
            ("{nome} {tenor} de {indice}% mais spread de {taxa}%, fixado em {quando}",
             {"nome": nome, "tenor": ponta.tenor, "indice": _numero(taxa_indice * 100, 5),
              "taxa": _numero(ponta.taxa * 100), "quando": f"{quando:%d/%m/%Y}"}),
            data_fixing=quando, taxa_do_fixing=taxa_indice, tenor=ponta.tenor)

    if ponta.indexador == EQUITY:
        if not ponta.preco_inicial or ponta.preco_final is None:
            raise ErroLiquidacao(
                "a ponta de equity precisa do preço inicial e do preço final")
        retorno = ponta.preco_final / ponta.preco_inicial
        return montar(
            retorno * capitalizar(ponta.taxa),
            ("{ativo} variou {retorno}% mais spread de {taxa}%",
             {"ativo": ponta.ativo or "equity",
              "retorno": _numero((retorno - 1) * 100),
              "taxa": _numero(ponta.taxa * 100)}),
            ativo=ponta.ativo or None, preco_inicial=ponta.preco_inicial,
            preco_final=ponta.preco_final)

    if ponta.indexador == IPCA:
        if not ponta.ni_inicial or ponta.ni_final is None:
            raise ErroLiquidacao(
                "a ponta de IPCA precisa do número-índice inicial e do final")
        correcao = ponta.ni_final / ponta.ni_inicial
        return montar(
            correcao * capitalizar(ponta.taxa),
            ("correção de {correcao}% mais cupom real de {taxa}% a.a.",
             {"correcao": _numero((correcao - 1) * 100),
              "taxa": _numero(ponta.taxa * 100)}))

    if ponta.indexador == FATOR:
        if ponta.fator_manual is None:
            raise ErroLiquidacao("informe o fator acumulado da ponta")
        return montar(ponta.fator_manual, ("fator digitado", {}))

    raise ErroLiquidacao(f"indexador desconhecido: {ponta.indexador}")


# ------------------------------------------------------------- a liquidação

@dataclass
class ResultadoLiquidacao:
    data_operacao: date
    inicio: date
    fim: date
    nocional: float
    nocional_original: float
    percentual_amortizacao: float
    base_amortizacao: str
    valor_amortizado: float
    saldo_seguinte: float
    ativa: PontaLiquidada
    passiva: PontaLiquidada
    ajuste_bruto: float
    quem_recebe: str
    dias_corridos: int
    dias_uteis: int
    dias_da_operacao: int
    aliquota_ir: float
    ir: float
    ajuste_liquido: float

    @property
    def diferenca_de_fator(self) -> float:
        """O ajuste em pontos de fator — o que sobra por real de notional."""
        return self.ativa.fator - self.passiva.fator


def liquidar(data_operacao, inicio, fim, nocional: float,
             ponta_ativa: Ponta, ponta_passiva: Ponta,
             nocional_original: Optional[float] = None,
             percentual_amortizacao: float = 0.0,
             base_amortizacao: str = SOBRE_ORIGINAL,
             calendario: Optional[Calendario] = None,
             arredondar_di: bool = False,
             reter_ir: bool = True) -> ResultadoLiquidacao:
    """Ajuste a pagar entre as duas pontas no fim do fluxo.

    ``nocional`` é o saldo remanescente na data de início do fluxo — o valor
    que de fato rende, já líquido das amortizações anteriores. As duas pontas
    acumulam sobre ele.

    ``percentual_amortizacao`` é o quanto do principal amortiza no fim deste
    fluxo, e ``base_amortizacao`` diz sobre o quê: o valor original de registro
    (``nocional_original``, que cai no remanescente quando não é informado) ou o
    próprio saldo remanescente. A amortização não muda o ajuste deste período —
    ela define o saldo que abre o próximo.

    ``reter_ir`` aplica a tabela regressiva sobre o resultado positivo, contada
    da **data da operação** até o fim do fluxo, que é o prazo que a legislação
    olha. É o que a fonte pagadora retém na liquidação.
    """
    cal = calendario or calendario_anbima()
    dop = para_data(data_operacao)
    d0, d1 = para_data(inicio), para_data(fim)

    if d1 <= d0:
        raise ErroLiquidacao("o fim do fluxo tem que ser posterior ao início")
    if d0 < dop:
        raise ErroLiquidacao(
            f"o fluxo não pode começar ({d0:%d/%m/%Y}) antes da operação "
            f"({dop:%d/%m/%Y})")
    if nocional <= 0:
        raise ErroLiquidacao("o notional remanescente tem que ser positivo")

    indexadores = {ponta_ativa.indexador, ponta_passiva.indexador}
    if indexadores & REALIZADOS and d1 > date.today():
        raise ErroLiquidacao(
            "a liquidação usa índice realizado, não projeção — o fim do fluxo "
            f"não pode passar de hoje ({date.today():%d/%m/%Y})")

    original = float(nocional_original) if nocional_original else float(nocional)
    if original < nocional:
        raise ErroLiquidacao(
            "o notional remanescente não pode ser maior que o valor original")
    amortizado = amortizar(original, nocional, percentual_amortizacao,
                           base_amortizacao)

    ativa = liquidar_ponta(ponta_ativa, nocional, d0, d1, cal, arredondar_di)
    passiva = liquidar_ponta(ponta_passiva, nocional, d0, d1, cal, arredondar_di)

    bruto = ativa.valor - passiva.valor
    dias_operacao = (d1 - dop).days
    pct_ir = aliquota_ir(dias_operacao) if (reter_ir and bruto > 0) else 0.0
    ir = bruto * pct_ir if pct_ir else 0.0

    return ResultadoLiquidacao(
        data_operacao=dop, inicio=d0, fim=d1, nocional=float(nocional),
        nocional_original=original,
        percentual_amortizacao=percentual_amortizacao,
        base_amortizacao=base_amortizacao,
        valor_amortizado=amortizado, saldo_seguinte=nocional - amortizado,
        ativa=ativa, passiva=passiva, ajuste_bruto=bruto,
        quem_recebe=ATIVA if bruto > 0 else PASSIVA,
        dias_corridos=(d1 - d0).days, dias_uteis=cal.dias_uteis(d0, d1),
        dias_da_operacao=dias_operacao,
        aliquota_ir=pct_ir, ir=ir, ajuste_liquido=bruto - ir,
    )
