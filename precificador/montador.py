"""Montador de swap — escolha as duas pontas e monte a estrutura.

Os produtos de ``produtos.py`` são atalhos para as combinações que aparecem nas
planilhas. Aqui as pontas são peças soltas: você escolhe qual recebe, qual
paga, e o montador cuida do resto — cada perna descontando pela curva da sua
própria moeda, que é a regra que não se negocia.

Nem toda combinação faz sentido, e ``validar`` diz quais não fazem antes de
calcular.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .curvas import Curva, CurvaTermSOFR
from .erros import ErroDeDado
from .instrumentos import (PERCENTUAL, SPREAD, Swap, perna_cdi,
                           perna_ipca_capitalizado, perna_pre_usd,
                           perna_prefixada_exp252, perna_term_sofr)
from .produtos import ParametrosSwap, _perna_pre_usd_sofr, _pesos
from .solver import atingir_meta

BRL = "BRL"
USD = "USD"


@dataclass
class Mercado:
    """Os insumos de mercado que as pernas podem pedir."""
    di: Optional[Curva] = None
    cupom: Optional[Curva] = None
    ipca: Optional[Curva] = None
    sofr: Optional[CurvaTermSOFR] = None
    spot: float = 1.0

    def exigir(self, nome: str):
        valor = getattr(self, nome, None)
        if valor is None:
            raise ErroDeDado("esta ponta precisa da curva {curva}, que não foi "
                             "carregada", curva=nome.upper())
        return valor


@dataclass(frozen=True)
class TipoPerna:
    """Uma ponta possível: como se chama, o que pede e como se monta."""
    id: str
    nome: str
    moeda: str
    parametro: str            # rótulo da variável que o solver pode procurar
    chute: float              # ponto de partida do Atingir Meta
    construir: Callable
    exige: tuple = ()
    icone: str = "solar:chart-2-linear"
    resumo: str = ""


def _pre_brl(params, periodos, pesos, mercado, valor, extras):
    return perna_prefixada_exp252(params.nocional, valor, periodos,
                                  mercado.exigir("di"), pesos, nome="Pré BRL")


def _cdi(params, periodos, pesos, mercado, valor, extras):
    modo = extras.get("modo_cdi", SPREAD)
    return perna_cdi(params.nocional, periodos, mercado.exigir("di"), pesos,
                     modo=modo, valor=valor)


def _pre_usd(params, periodos, pesos, mercado, valor, extras):
    spot = mercado.spot
    return perna_pre_usd(params.nocional / spot, valor, periodos,
                         mercado.exigir("cupom"), pesos, fx=spot,
                         nome="Pré USD + var. cambial")


def _ipca(params, periodos, pesos, mercado, valor, extras):
    return perna_ipca_capitalizado(params.nocional, valor, periodos,
                                   mercado.exigir("di"), mercado.exigir("ipca"),
                                   pesos, nome="IPCA+ capitalizado")


def _term_sofr(params, periodos, pesos, mercado, valor, extras):
    return perna_term_sofr(params.nocional, valor, periodos,
                           mercado.exigir("sofr"), pesos, params.inicio)


def _pre_usd_sofr(params, periodos, pesos, mercado, valor, extras):
    return _perna_pre_usd_sofr(params.nocional, valor, periodos,
                               mercado.exigir("sofr"), pesos, params.inicio)


TIPOS: List[TipoPerna] = [
    TipoPerna("pre_brl", "Pré BRL", BRL, "Taxa pré (% a.a. 252)", 0.15,
              _pre_brl, ("di",), "solar:chart-2-linear",
              "Taxa fixa em reais, exponencial 252, descontada pelo DI."),
    TipoPerna("cdi", "CDI (± spread ou % do CDI)", BRL, "Spread ou percentual", 0.02,
              _cdi, ("di",), "solar:pulse-linear",
              "Flutuante em reais. O spread é multiplicativo; o percentual incide "
              "sobre a taxa diária."),
    TipoPerna("ipca", "IPCA+ capitalizado", BRL, "Taxa real (% a.a. 252)", 0.06,
              _ipca, ("di", "ipca"), "solar:graph-up-linear",
              "Principal e juros corrigidos pela inflação implícita das curvas."),
    TipoPerna("pre_usd", "Pré USD + variação cambial", USD, "Taxa pré USD (% a.a. 360)", 0.05,
              _pre_usd, ("cupom",), "solar:dollar-minimalistic-linear",
              "Taxa fixa em dólar, linear 360, descontada pelo cupom cambial."),
    TipoPerna("pre_usd_sofr", "Pré USD (desconto SOFR)", USD, "Taxa pré USD (% a.a. 360)", 0.05,
              _pre_usd_sofr, ("sofr",), "solar:banknote-linear",
              "Taxa fixa em dólar descontada pela própria curva SOFR."),
    TipoPerna("term_sofr", "Term SOFR ± spread", USD, "Spread (% a.a. 360)", 0.005,
              _term_sofr, ("sofr",), "solar:global-linear",
              "Flutuante em dólar sobre o Term SOFR. Spread aditivo."),
]

POR_ID: Dict[str, TipoPerna] = {t.id: t for t in TIPOS}


@dataclass(frozen=True)
class Template:
    """Uma combinação pronta — as estruturas que aparecem nas planilhas."""
    id: str
    nome: str
    ativa: str
    passiva: str
    icone: str
    resumo: str
    valor_ativa: str = ""
    modo_cdi: str = SPREAD


TEMPLATES: List[Template] = [
    Template("pre_cdi", "Pré BRL × CDI ± spread", "pre_brl", "cdi",
             "solar:chart-2-linear",
             "Uma curva só. O spread é multiplicativo: (1+CDI)·(1+spread) = (1+pré).",
             valor_ativa="17"),
    Template("usd_brl", "Pré USD × Pré BRL", "pre_usd", "pre_brl",
             "solar:dollar-minimalistic-linear",
             "Cross-currency. Fluxo em reais desconta no DI, fluxo em dólar no cupom cambial.",
             valor_ativa="10"),
    Template("usd_cdi", "Pré USD × CDI ± spread", "pre_usd", "cdi",
             "solar:card-transfer-linear",
             "Cross-currency com a ponta em reais flutuante. Duas curvas de desconto, "
             "spread multiplicativo.",
             valor_ativa="10"),
    Template("ipca_cdi", "IPCA capitalizado × CDI ± spread", "ipca", "cdi",
             "solar:graph-up-linear",
             "Inflação implícita de (1+DI)/(1+DI×IPCA)−1, capitalizada por período.",
             valor_ativa="6"),
    Template("usd_sofr", "Pré USD × Term SOFR ± spread", "pre_usd_sofr", "term_sofr",
             "solar:global-linear",
             "Bootstrap dos futuros SR3 em datas IMM. Spread aditivo, linear 360.",
             valor_ativa="5"),
]

TEMPLATE_POR_ID: Dict[str, Template] = {t.id: t for t in TEMPLATES}


def insumos_necessarios(id_ativa: str, id_passiva: str) -> set:
    """Quais insumos de mercado as duas pontas escolhidas realmente pedem.

    Serve para a tela mostrar só o que interessa: preço do dólar não aparece
    num Pré × CDI, e futuros SR3 não aparecem em nada que não seja SOFR.
    """
    exige = set()
    for identificador in (id_ativa, id_passiva):
        tipo = POR_ID.get(identificador)
        if tipo:
            exige |= set(tipo.exige)
    insumos = set()
    if exige & {"di", "cupom", "ipca"}:
        insumos.add("curvas_b3")
    if "sofr" in exige:
        insumos.add("sofr")
    # o câmbio só entra quando há uma ponta em dólar contra uma em real
    moedas = {POR_ID[i].moeda for i in (id_ativa, id_passiva) if i in POR_ID}
    if moedas == {BRL, USD}:
        insumos.add("cambio")
    return insumos


def validar(id_ativa: str, id_passiva: str) -> Optional[str]:
    """Devolve a razão pela qual a combinação não fecha, ou ``None`` se fecha."""
    if id_ativa not in POR_ID or id_passiva not in POR_ID:
        return "escolha as duas pontas"
    if id_ativa == id_passiva:
        return ("as duas pontas são iguais — um swap precisa de dois indexadores "
                "diferentes")
    ativa, passiva = POR_ID[id_ativa], POR_ID[id_passiva]
    if {ativa.id, passiva.id} == {"pre_usd", "pre_usd_sofr"}:
        return ("as duas pontas são pré em dólar; muda só a curva de desconto, "
                "não o indexador")
    if ativa.moeda == USD and passiva.moeda == USD:
        usa_sofr = "sofr" in ativa.exige or "sofr" in passiva.exige
        usa_cupom = "cupom" in ativa.exige or "cupom" in passiva.exige
        if usa_sofr and usa_cupom:
            return ("misturar cupom cambial e Term SOFR na mesma moeda desconta as "
                    "pernas em curvas incompatíveis")
    return None


def montar(params: ParametrosSwap, mercado: Mercado,
           id_ativa: str, valor_ativa: float,
           id_passiva: str, valor_passiva: float,
           extras_ativa: Optional[dict] = None,
           extras_passiva: Optional[dict] = None,
           calendario=None) -> Swap:
    """Monta o swap com as duas pontas escolhidas."""
    problema = validar(id_ativa, id_passiva)
    if problema:
        raise ValueError(problema)

    ativa, passiva = POR_ID[id_ativa], POR_ID[id_passiva]
    periodos = params.agenda(calendario)
    pesos = _pesos(params, len(periodos))

    perna_a = ativa.construir(params, periodos, pesos, mercado, valor_ativa,
                              extras_ativa or {})
    perna_p = passiva.construir(params, periodos, pesos, mercado, valor_passiva,
                                extras_passiva or {})

    # a moeda de referência é o real sempre que houver uma ponta em reais
    referencia = BRL if BRL in (ativa.moeda, passiva.moeda) else USD
    nome = f"{ativa.nome} × {passiva.nome}"
    return Swap(nome, perna_a, perna_p, referencia, params.fee)


def resolver(params: ParametrosSwap, mercado: Mercado,
             id_ativa: str, valor_ativa: float,
             id_passiva: str, valor_passiva: float,
             lado: str = "passiva",
             extras_ativa: Optional[dict] = None,
             extras_passiva: Optional[dict] = None,
             calendario=None) -> float:
    """Acha o valor da ponta escolhida que zera o MtM."""
    tipo = POR_ID[id_passiva if lado == "passiva" else id_ativa]
    chute = tipo.chute
    if lado == "passiva" and (extras_passiva or {}).get("modo_cdi") == PERCENTUAL:
        chute = 1.0
    if lado == "ativa" and (extras_ativa or {}).get("modo_cdi") == PERCENTUAL:
        chute = 1.0

    def mtm(x: float) -> float:
        if lado == "passiva":
            return montar(params, mercado, id_ativa, valor_ativa, id_passiva, x,
                          extras_ativa, extras_passiva, calendario).mtm
        return montar(params, mercado, id_ativa, x, id_passiva, valor_passiva,
                      extras_ativa, extras_passiva, calendario).mtm

    return atingir_meta(mtm, chute=chute)
