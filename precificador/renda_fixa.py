"""Calculadora de renda fixa — prefixado, CDI e IPCA+.

Cobre o mesmo terreno da calculadora da B3
(https://calculadorarendafixa.com.br), com uma diferença deliberada no
tratamento do DI, explicada em ``fator_di``.

Convenções:

* juros em dias úteis, base 252, para prefixado, CDI e a parte real do IPCA+;
* correção do IPCA por dias corridos entre aniversários (aqui simplificada
  para o acumulado do período, já que a projeção entra pronta);
* IR regressivo sobre o rendimento, e IOF regressivo em resgate com menos de
  30 dias corridos;
* LCI, LCA, CRI, CRA, LIG e debênture incentivada são isentos de IR para
  pessoa física.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .calendario import Calendario, calendario_anbima, para_data
from .erros import ErroDeDado

PREFIXADO = "prefixado"
CDI_PERCENTUAL = "cdi_percentual"
CDI_SPREAD = "cdi_spread"
IPCA_MAIS = "ipca_mais"
CDI_REALIZADO = "cdi_realizado"

INDEXADORES = [
    (CDI_REALIZADO, "% do CDI — acumulado realizado (BCB)"),
    (CDI_PERCENTUAL, "% do CDI — projetado"),
    (CDI_SPREAD, "CDI + spread — projetado"),
    (PREFIXADO, "Prefixado (% a.a. 252)"),
    (IPCA_MAIS, "IPCA + taxa real"),
]

# indexadores que olham para trás: a data final não pode passar de hoje
RETROATIVOS = {CDI_REALIZADO}

ISENTOS = {"lci", "lca", "cri", "cra", "lig", "debenture_incentivada", "poupanca"}

PRODUTOS_RF = [
    ("cdb", "CDB / RDB", False),
    ("lci", "LCI / LCA", True),
    ("cri", "CRI / CRA", True),
    ("debenture", "Debênture comum", False),
    ("debenture_incentivada", "Debênture incentivada", True),
    ("tesouro", "Tesouro Direto", False),
    ("lig", "LIG", True),
]

# IOF regressivo: percentual do rendimento retido por dia corrido de aplicação
_IOF = [96, 93, 90, 86, 83, 80, 76, 73, 70, 66, 63, 60, 56, 53, 50, 46,
        43, 40, 36, 33, 30, 26, 23, 20, 16, 13, 10, 6, 3, 0]


def aliquota_ir(dias_corridos: int) -> float:
    """Tabela regressiva do IR sobre o rendimento."""
    if dias_corridos <= 180:
        return 0.225
    if dias_corridos <= 360:
        return 0.20
    if dias_corridos <= 720:
        return 0.175
    return 0.15


def aliquota_iof(dias_corridos: int) -> float:
    """IOF regressivo — zera a partir do 30º dia corrido."""
    if dias_corridos < 1:
        return 0.96
    if dias_corridos >= 30:
        return 0.0
    return _IOF[dias_corridos - 1] / 100.0


def fator_di(taxa_anual: float, dias_uteis: int, percentual: float = 1.0,
             spread: float = 0.0, arredondar: bool = False) -> float:
    """Fator de capitalização do DI para o número de dias úteis.

        fator_dia = (1 + DI) ^ (1/252)
        fator     = [1 + (fator_dia − 1) · p] ^ DU        (percentual do CDI)
        fator     = [(1 + DI)(1 + s)] ^ (DU/252)          (CDI + spread)

    **Sobre o arredondamento.** O padrão B3/CETIP arredonda o fator diário na
    8ª casa decimal antes de acumular, e a calculadora pública da B3 faz isso.
    Aqui o padrão é ``arredondar=False``: o fator roda em precisão plena.

    A diferença é pequena por dia e cresce com o prazo — num CDB de cinco anos
    a 14% ela chega à casa dos centavos por milhão. Quem precisa bater com o
    extrato da B3 liga ``arredondar=True``; quem está precificando prefere o
    número sem truncar, que é o que a curva devolve.
    """
    if dias_uteis <= 0:
        return 1.0
    if spread:
        base = (1.0 + taxa_anual) * (1.0 + spread)
        return base ** (dias_uteis / 252.0)
    fator_dia = (1.0 + taxa_anual) ** (1.0 / 252.0)
    if arredondar:
        fator_dia = round(fator_dia, 8)
    diario = 1.0 + (fator_dia - 1.0) * percentual
    if arredondar:
        diario = round(diario, 16)
    return diario ** dias_uteis


def fator_prefixado(taxa_anual: float, dias_uteis: int) -> float:
    return (1.0 + taxa_anual) ** (dias_uteis / 252.0)


@dataclass
class ResultadoRendaFixa:
    valor_aplicado: float
    valor_bruto: float
    rendimento_bruto: float
    iof: float
    ir: float
    aliquota_ir: float
    aliquota_iof: float
    valor_liquido: float
    rendimento_liquido: float
    dias_corridos: int
    dias_uteis: int
    fator: float
    taxa_periodo: float
    taxa_anual_equivalente: float
    taxa_liquida_anual: float
    isento: bool

    def para_dict(self) -> dict:
        return dict(self.__dict__)


def calcular(valor: float, inicio, vencimento, indexador: str, taxa: float,
             cdi_projetado: float = 0.0, ipca_projetado: float = 0.0,
             produto: str = "cdb", arredondar_di: bool = False,
             calendario: Optional[Calendario] = None,
             fator_pronto: Optional[float] = None,
             dias_uteis: Optional[int] = None) -> ResultadoRendaFixa:
    """Calcula bruto, impostos e líquido de uma aplicação de renda fixa.

    ``taxa`` é a remuneração contratada, em decimal: 0,14 para 14% a.a.
    prefixado, 1,10 para 110% do CDI, 0,02 para CDI+2%, 0,06 para IPCA+6%.

    ``fator_pronto`` curto-circuita o cálculo do fator — é como entra o CDI
    realizado, que vem acumulado dia a dia da série do Banco Central. O resto
    (IR, IOF, taxas equivalentes) é o mesmo caminho.
    """
    cal = calendario or calendario_anbima()
    d0, d1 = para_data(inicio), para_data(vencimento)
    if d1 <= d0:
        raise ErroDeDado("o vencimento tem que ser posterior à aplicação")

    dc = (d1 - d0).days
    du = dias_uteis if dias_uteis is not None else cal.dias_uteis(d0, d1)

    if fator_pronto is not None:
        fator = fator_pronto
    elif indexador == PREFIXADO:
        fator = fator_prefixado(taxa, du)
    elif indexador == CDI_PERCENTUAL:
        fator = fator_di(cdi_projetado, du, percentual=taxa,
                         arredondar=arredondar_di)
    elif indexador == CDI_SPREAD:
        fator = fator_di(cdi_projetado, du, spread=taxa,
                         arredondar=arredondar_di)
    elif indexador == IPCA_MAIS:
        anos = du / 252.0
        fator = ((1.0 + ipca_projetado) ** (dc / 365.0)) * ((1.0 + taxa) ** anos)
    else:
        raise ErroDeDado("indexador desconhecido: {indexador}", indexador=indexador)

    bruto = valor * fator
    rendimento = bruto - valor

    isento = produto in ISENTOS
    pct_iof = aliquota_iof(dc)
    iof = rendimento * pct_iof if rendimento > 0 else 0.0
    pct_ir = 0.0 if isento else aliquota_ir(dc)
    ir = (rendimento - iof) * pct_ir if rendimento > 0 else 0.0

    liquido = bruto - iof - ir
    rendimento_liquido = liquido - valor

    taxa_periodo = fator - 1.0
    anos_uteis = du / 252.0 if du else (dc / 365.0)
    equivalente = fator ** (1.0 / anos_uteis) - 1.0 if anos_uteis > 0 else 0.0
    liquida = ((liquido / valor) ** (1.0 / anos_uteis) - 1.0) if anos_uteis > 0 else 0.0

    return ResultadoRendaFixa(
        valor_aplicado=valor, valor_bruto=bruto, rendimento_bruto=rendimento,
        iof=iof, ir=ir, aliquota_ir=pct_ir, aliquota_iof=pct_iof,
        valor_liquido=liquido, rendimento_liquido=rendimento_liquido,
        dias_corridos=dc, dias_uteis=du, fator=fator, taxa_periodo=taxa_periodo,
        taxa_anual_equivalente=equivalente, taxa_liquida_anual=liquida,
        isento=isento,
    )


def diferenca_arredondamento(taxa_anual: float, dias_uteis: int,
                             percentual: float = 1.0,
                             valor: float = 1_000_000.0) -> dict:
    """Quanto o arredondamento na 8ª casa custa, em reais, no prazo dado.

    Serve para mostrar por que o padrão aqui é não arredondar.
    """
    cheio = fator_di(taxa_anual, dias_uteis, percentual, arredondar=False)
    truncado = fator_di(taxa_anual, dias_uteis, percentual, arredondar=True)
    return {
        "fator_sem_arredondar": cheio,
        "fator_arredondado": truncado,
        "diferenca_fator": cheio - truncado,
        "diferenca_reais": (cheio - truncado) * valor,
    }
