"""CDI realizado — série diária do Banco Central e acúmulo entre duas datas.

Isto **não** é projeção: é o que o CDI de fato rendeu no período, dia a dia, do
jeito que a calculadora de renda fixa da B3 faz na aba "DI". Por isso a data
final não pode passar de hoje.

Fonte: série 4389 do SGS — "Taxa de juros CDI anualizada base 252".

    https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados
        ?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa

O acúmulo segue a convenção do mercado:

    fator = Π [ 1 + ((1 + DI_k)^(1/252) − 1) · p ]

com um termo por **dia útil publicado no intervalo [início, fim)** — a taxa de
um dia rende naquele dia, então a do dia final não entra. Foi exatamente isso
que fez o número bater com a calculadora da B3: 01/01/2026 a 06/09/2026 a 100%
dá fator 1,09550031, e o último DI que entra na conta é o de 04/09, a sexta-feira
anterior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from . import rede
from .erros import ErroDeFonte
from .calendario import para_data

SGS_CDI = 4389
SGS_SELIC = 11
API = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"


class ErroBCB(ErroDeFonte):
    """Falha ao obter a série do Banco Central."""


@dataclass(frozen=True)
class FixingCDI:
    data: date
    taxa: float          # decimal ao ano, base 252 (0.149 = 14,90%)


def serie(inicio, fim, codigo: int = SGS_CDI, timeout: int = 40) -> List[FixingCDI]:
    """Série diária do SGS entre as duas datas, em ordem crescente.

    O BCB publica com um dia de defasagem, então o fixing de ontem pode ainda
    não estar lá. O acúmulo simplesmente usa o que existe e informa até onde foi.
    """
    d0, d1 = para_data(inicio), para_data(fim)
    if d1 < d0:
        raise ValueError("a data final não pode ser anterior à inicial")
    url = (f"{API.format(serie=codigo)}?formato=json"
           f"&dataInicial={d0:%d/%m/%Y}&dataFinal={d1:%d/%m/%Y}")
    try:
        bruto = rede.obter_json(url, timeout=timeout)
    except rede.ErroRede as exc:
        raise ErroBCB(f"não foi possível obter a série {codigo} do BCB: {exc}") from exc

    fixings = []
    for linha in bruto:
        try:
            fixings.append(FixingCDI(para_data(linha["data"]),
                                     float(linha["valor"]) / 100.0))
        except (KeyError, ValueError):
            continue
    return sorted(fixings, key=lambda f: f.data)


@dataclass
class DiaCDI:
    data: date
    taxa: float
    fator_dia: float
    fator_acumulado: float


@dataclass
class ResultadoCDI:
    inicio: date
    fim: date
    percentual: float
    fator: float
    taxa_periodo: float
    taxa_anual_equivalente: float
    valor_base: float
    valor_calculado: float
    dias_uteis: int
    dias_corridos: int
    primeiro: Optional[date]
    ultimo: Optional[date]
    arredondado: bool
    dias: List[DiaCDI]


def acumular(fixings: List[FixingCDI], inicio, fim, percentual: float = 1.0,
             valor: float = 1000.0, arredondar: bool = False) -> ResultadoCDI:
    """Acumula o CDI publicado no intervalo [início, fim).

    ``arredondar=True`` reproduz o padrão B3/CETIP, que trunca o fator diário na
    8ª casa antes de multiplicar. Desligado — o padrão aqui — o fator roda em
    precisão plena.
    """
    d0, d1 = para_data(inicio), para_data(fim)
    if d1 <= d0:
        raise ValueError("a data final tem que ser posterior à inicial")

    usados = [f for f in fixings if d0 <= f.data < d1]
    if not usados:
        raise ErroBCB(
            f"o Banco Central não publicou CDI entre {d0:%d/%m/%Y} e {d1:%d/%m/%Y}. "
            "A série tem um dia de defasagem e não cobre datas futuras.")

    fator = 1.0
    linhas: List[DiaCDI] = []
    for f in usados:
        fator_dia = (1.0 + f.taxa) ** (1.0 / 252.0)
        if arredondar:
            fator_dia = round(fator_dia, 8)
        fator_dia = 1.0 + (fator_dia - 1.0) * percentual
        if arredondar:
            fator_dia = round(fator_dia, 16)
        fator *= fator_dia
        linhas.append(DiaCDI(f.data, f.taxa, fator_dia, fator))

    dias_uteis = len(usados)
    equivalente = fator ** (252.0 / dias_uteis) - 1.0 if dias_uteis else 0.0
    return ResultadoCDI(
        inicio=d0, fim=d1, percentual=percentual,
        fator=fator, taxa_periodo=fator - 1.0,
        taxa_anual_equivalente=equivalente,
        valor_base=valor, valor_calculado=valor * fator,
        dias_uteis=dias_uteis, dias_corridos=(d1 - d0).days,
        primeiro=usados[0].data, ultimo=usados[-1].data,
        arredondado=arredondar, dias=linhas,
    )


def acumular_do_bcb(inicio, fim, percentual: float = 1.0, valor: float = 1000.0,
                    arredondar: bool = False) -> ResultadoCDI:
    """Busca a série e acumula — o caminho curto para a tela."""
    return acumular(serie(inicio, fim), inicio, fim, percentual, valor, arredondar)
