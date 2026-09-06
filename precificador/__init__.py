"""precificador — precificação de swaps de balcão a partir das curvas da B3.

Porte das planilhas VBA de *Precificação Swap* para um pacote Python.

    calendario    dias úteis ANBIMA, WORKDAY/NETWORKDAYS, cronogramas
    interpolacao  spline cúbica natural (a UDF cubic_spline), linear, flat-forward
    b3            extração das Taxas Referenciais da B3
    curvas        curvas de juros: taxa spot, fator de desconto, FRA
    instrumentos  pernas, agendas e o swap
    produtos      os quatro swaps das planilhas, prontos para uso
    solver        o Atingir Meta (GoalSeek) das macros
"""

from .calendario import Calendario, calendario_anbima, calendario_us_br, obter_calendario
from .curvas import EXP252, LIN360, Curva, CurvaTermSOFR, Vertice
from .instrumentos import BULLET, LINEAR, PERSONALIZADA, Swap, agenda_periodica, taxa_par
from .interpolacao import SplineNatural, cubic_spline, flat_forward, interpolar, linear
from .produtos import (NumeroIndice, ParametrosSwap, pre_brl_par, pre_par_cdi,
                       pre_usd_par, spread_par_cdi, spread_par_ipca, spread_par_sofr,
                       swap_ipca_x_cdi, swap_pre_usd_x_pre_brl,
                       swap_pre_usd_x_term_sofr, swap_pre_x_cdi)

__version__ = "1.0.0"

__all__ = [
    "Calendario", "calendario_anbima", "calendario_us_br", "obter_calendario",
    "Curva", "CurvaTermSOFR", "Vertice", "EXP252", "LIN360",
    "SplineNatural", "cubic_spline", "linear", "flat_forward", "interpolar",
    "Swap", "agenda_periodica", "taxa_par", "BULLET", "LINEAR", "PERSONALIZADA",
    "ParametrosSwap", "NumeroIndice",
    "swap_pre_x_cdi", "spread_par_cdi", "pre_par_cdi",
    "swap_pre_usd_x_pre_brl", "pre_brl_par", "pre_usd_par",
    "swap_ipca_x_cdi", "spread_par_ipca",
    "swap_pre_usd_x_term_sofr", "spread_par_sofr",
    "__version__",
]
