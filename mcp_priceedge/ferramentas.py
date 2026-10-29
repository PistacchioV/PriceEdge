"""As ferramentas que o servidor MCP expõe — o PriceEdge visto por um agente.

Cada ferramenta monta o mesmo formulário que a tela montaria e chama o mesmo
código da rota. Assim não existem duas precificações: o número que o agente
recebe é, por construção, o número que a tela mostra para os mesmos insumos.

Convenção das entradas: taxa em **percentual** (14,65 para 14,65% a.a.),
número solto (spot, nocional, strike) como número. As saídas devolvem as taxas
em **decimal** (0.1465), que é como o pacote as guarda.
"""

from __future__ import annotations

import dataclasses
import math
from datetime import date, timedelta
from typing import Callable, Dict, List

from werkzeug.datastructures import MultiDict

from precificador import anbima, b3, cambio, cdi, inflacao_implicita, montador
from precificador.calendario import (CALENDARIOS_DISPONIVEIS, obter_calendario,
                                     para_data)
from precificador.curvas import EXP252
from precificador.instrumentos import BULLET, LINEAR, PERCENTUAL, SPREAD, STRING, VANILLA
from precificador.produtos import DIRECOES, MOEDAS_NDF, PROGRESSOES
from webapp import rotas, servicos

# ----------------------------------------------------------------- saída


def json_puro(obj):
    """Qualquer resultado do pacote em algo que o ``json`` aceita."""
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, date):
        return obj.isoformat()
    if hasattr(obj, "para_dict"):
        return json_puro(obj.para_dict())
    if dataclasses.is_dataclass(obj):
        return {f.name: json_puro(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): json_puro(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_puro(v) for v in obj]
    return str(obj)


# ----------------------------------------------------------------- entrada


def _pct(valor) -> str:
    """Taxa em percentual para o leitor de formulário — o "%" força o /100."""
    return "" if valor is None or valor == "" else f"{valor}%"


def _num(valor) -> str:
    return "" if valor is None or valor == "" else repr(float(valor))


def _data(valor, padrao=None) -> str:
    if not valor:
        return (padrao or servicos.data_sugerida()).isoformat()
    return para_data(valor).isoformat()


# ------------------------------------------------------------- ferramentas


def curva_b3(codigo: str = "PRE", data: str = "") -> dict:
    c = servicos.curva(codigo, _data(data))
    return {**c.para_dict(), "codigo": codigo.upper(),
            "observacao": "taxas em decimal; du = dias úteis, dc = dias corridos"}


def taxa_na_curva(datas: List[str], codigo: str = "PRE", data_base: str = "") -> dict:
    """A taxa da curva em cada data, com DU/DC e a taxa a termo entre elas."""
    base = para_data(_data(data_base))
    c = servicos.curva(codigo, base.isoformat())
    cal = obter_calendario("ANBIMA")
    linhas, anterior = [], None
    for texto in datas:
        alvo = para_data(texto)
        dc = (alvo - base).days
        if dc <= 0:
            raise servicos.ErroFormulario(
                "a data {data} não é posterior à data-base", data=f"{alvo:%d/%m/%Y}")
        du = cal.dias_uteis(base, alvo)
        taxa = c.taxa_para(dc, du)
        linha = {"data": alvo, "dc": dc, "du": du, "taxa": taxa,
                 "fora_da_curva": dc > c.prazo_maximo if c.prazo_maximo else False}
        # forward 252 entre esta data e a anterior: é o que o mercado precifica
        # para o período, e a leitura natural de Copom em DI1
        if anterior and c.convencao == EXP252 and du > anterior["du"]:
            fator = (1 + taxa) ** (du / 252) / (1 + anterior["taxa"]) ** (anterior["du"] / 252)
            linha["termo_desde_anterior"] = fator ** (252 / (du - anterior["du"])) - 1
        linhas.append(linha)
        anterior = linha
    return {"curva": c.nome, "codigo": codigo.upper(), "data_base": base,
            "convencao": c.convencao, "linhas": linhas}


def dias_uteis(inicio: str, fim: str, calendario: str = "ANBIMA") -> dict:
    d0, d1 = para_data(inicio), para_data(fim)
    cal = obter_calendario(calendario)
    return {"inicio": d0, "fim": d1, "calendario": cal.nome,
            "dias_uteis": cal.dias_uteis(d0, d1), "dias_corridos": (d1 - d0).days,
            "convencoes": servicos.contagens_lado_a_lado(d0, d1, calendario)}


def ptax(moeda: str = "USD", data: str = "") -> dict:
    p = cambio.ptax_moeda(moeda.upper(), data or None)
    return {**json_puro(p), "media": p.media}


def cdi_acumulado(inicio: str, fim: str, percentual: float = 100.0,
                  valor: float = 1000.0) -> dict:
    r = cdi.acumular_do_bcb(inicio, fim, percentual=percentual / 100.0, valor=valor)
    saida = json_puro(r)
    saida.pop("dias", None)                 # a série diária inteira é ruído aqui
    return saida


def precificar_swap(perna_ativa: str = "pre_brl", perna_passiva: str = "cdi",
                    resolver: str = "ativa", valor_ativa=None, valor_passiva=None,
                    inicio: str = "", vencimento: str = "", nocional: float = 100e6,
                    modo_cdi: str = SPREAD, estrutura_cdi: str = VANILLA,
                    meses_periodo: int = 6, amortizacao: str = BULLET,
                    fee: float = 0.0, data_curva: str = "", spot: float = None,
                    calendario: str = "ANBIMA", sofr_precos: List[float] = None,
                    term_sofr: List[float] = None, incluir_fluxos: bool = False) -> dict:
    hoje = servicos.data_sugerida()
    inicio_d = para_data(_data(inicio, hoje))
    venc = vencimento or date(inicio_d.year + 5, inicio_d.month, inicio_d.day).isoformat()

    def valor(perna, bruto):
        if bruto is None or bruto == "":
            return ""
        # % do CDI vai como número (100 = 100%); o resto é taxa em percentual
        return _num(bruto) if perna == "cdi" and modo_cdi == PERCENTUAL else _pct(bruto)

    form = MultiDict({
        "perna_ativa": perna_ativa, "perna_passiva": perna_passiva,
        "resolver": resolver, "valor_ativa": valor(perna_ativa, valor_ativa),
        "valor_passiva": valor(perna_passiva, valor_passiva),
        "inicio": inicio_d.isoformat(), "vencimento": _data(venc),
        "data_curva": _data(data_curva, inicio_d), "nocional": _num(nocional),
        "modo_cdi": modo_cdi, "estrutura_cdi": estrutura_cdi,
        "meses_periodo": str(int(meses_periodo)), "amortizacao": amortizacao,
        "fee": _num(fee), "calendario": calendario, "spot": _num(spot or 5.0),
        "convencao_dia_util": "modified_following",
        "sofr": ", ".join(str(p) for p in (sofr_precos or rotas.SOFR_PADRAO)),
        "term_sofr": ", ".join(str(t) for t in (term_sofr or [])),
    })
    r = rotas._montar_personalizado(form)
    swap = r["swap"]
    saida = {
        "nome": swap.nome, "moeda": r["moeda"],
        "solucao": r["solucao"], "comparacao_vanilla_string": r["comparacao"],
        "mtm": swap.mtm, "fee": swap.fee, "duration_anos": swap.duration,
        "prazo_medio_anos": swap.prazo_medio,
        "pv_ativa": swap.ativa.pv, "pv_passiva": swap.passiva.pv,
        "curvas": r["curvas"], "data_curva": r["data_curva"],
        "calendario": r["calendario"],
        "observacao": ("solucao.valor é a taxa (decimal) da ponta resolvida que zera "
                       "o MtM; com percentual=true é a fração do CDI (1.05 = 105%)"),
    }
    if incluir_fluxos:
        saida["ativa"], saida["passiva"] = swap.ativa, swap.passiva
    return json_puro(saida)


def curva_ndf(spot: float = None, moeda: str = "USD", vencimento: str = "",
              datas: List[str] = None, quantidade: int = 12,
              progressao: str = "mensal", data_curva: str = "",
              taxa_estrangeira: float = None, primeiro_futuro: float = None,
              segundo_futuro: float = None, direcao: str = "saida") -> dict:
    data_txt = _data(data_curva)
    if spot is None:
        spot = servicos.spot_da_curva(rotas.moeda_ndf(moeda), data_txt)
        if spot is None:
            raise servicos.ErroFormulario("preencha o campo {campo}", campo="spot")
    form = MultiDict({
        "spot": _num(spot), "moeda": moeda.upper(), "vencimento": vencimento or "",
        "datas": ", ".join(datas or []), "quantidade": str(quantidade),
        "progressao": progressao, "data_curva": data_txt, "calendario": "ANBIMA",
        "taxa_estrangeira": _pct(taxa_estrangeira),
        "primeiro_futuro": _num(primeiro_futuro), "segundo_futuro": _num(segundo_futuro),
        "direcao": direcao,
    })
    r = rotas._montar_ndf(form)
    return json_puro({
        "moeda": r["moeda"].codigo, "par": r["moeda"].par, "data_base": r["base"],
        "spot": r["spot"], "spot_efetivo": r["spot_efetivo"],
        "casado": r["casado_com_sinal"], "rolagem": r["rolagem"],
        "curvas": [c.nome for c in r["curvas"]], "pontos": r["pontos"],
    })


def precificar_opcao_fx(spot: float, vencimento: str, pernas: List[dict],
                        inicio: str = "", nocional: float = 1e6,
                        moeda_nocional: str = "USD", vol: float = None,
                        smile: List[float] = None, taxa_dom: float = None,
                        taxa_est: float = None, resolver_strike: int = None,
                        premio_alvo: float = 0.0, spread: float = None,
                        fee: float = None) -> dict:
    if not 1 <= len(pernas) <= rotas.MAX_PERNAS_OPCAO:
        raise servicos.ErroFormulario(
            "uma estrutura tem de 1 a {n} opções", n=rotas.MAX_PERNAS_OPCAO)
    if smile is None and vol is None and not all(p.get("vol") for p in pernas):
        raise servicos.ErroFormulario("informe vol, smile ou a vol de cada perna")
    form = {
        "inicio": _data(inicio), "vencimento": _data(vencimento), "spot": _num(spot),
        "nocional": _num(nocional), "moeda_nocional": moeda_nocional.upper(),
        "fonte_vol": "smile" if smile else "unica", "vol": _pct(vol or 0.0),
        "smile": "; ".join(str(v) for v in (smile or [])),
        "taxa_dom": _pct(taxa_dom), "taxa_est": _pct(taxa_est),
        "resolver_strike": str(resolver_strike) if resolver_strike else "",
        "premio_alvo": _num(premio_alvo), "spread": _pct(spread), "fee": _pct(fee),
    }
    for i, perna in enumerate(pernas, start=1):
        form.update({f"usar{i}": "1", f"tipo{i}": perna.get("tipo", "call"),
                     f"lado{i}": perna.get("lado", "comprada"),
                     f"strike{i}": _num(perna.get("strike")),
                     f"vol{i}": _pct(perna.get("vol"))})
    r = rotas._precificar_opcao(MultiDict(form))
    pernas_saida = []
    for numero, res in zip(r["numeros"], r["pernas"]):
        a = res.avaliacao
        pernas_saida.append({
            "opcao": numero, "tipo": res.perna.tipo, "lado": res.perna.lado,
            "strike": a.strike, "vol": a.vol, "premio_unitario": a.premio,
            "premio_total_brl": res.premio_total, "delta_posicao_usd": res.delta_posicao,
            "vega_posicao_brl": res.vega_posicao, "gregas_unitarias": a.gregas,
            "situacao": a.situacao,
        })
    return json_puro({
        "premio_liquido_brl": r["liquido"],
        "sinal": "positivo = prêmio recebido; negativo = pago",
        "strike_resolvido": r["strike_resolvido"], "pernas": pernas_saida,
        "delta_usd": r["delta"], "vega_brl": r["vega"],
        "spot": r["spot"], "forward": r["forward"], "du": r["du"], "dc": r["dc"],
        "quantidade_usd": r["quantidade"], "nocional_brl": r["nocional_brl"],
        "taxa_dom": r["taxa_dom"], "taxa_est": r["taxa_est"],
        "fontes_taxa": r["fontes_taxa"], "beneficio_taxa": r["beneficio"],
    })


def inflacao_implicita_ntnb(data: str = "") -> dict:
    referencia = para_data(_data(data))
    titulos = anbima.baixar(referencia)
    avisos, taxa_pre, cdi_do_dia = [], None, None
    try:
        taxa_pre = servicos.curva("PRE", referencia.isoformat()).taxa_para
    except Exception as exc:                       # noqa: BLE001 — degrada
        avisos.append(f"sem curva DI x Pré: {exc}")
    try:
        fixings = [f for f in cdi.serie(referencia - timedelta(days=10), referencia)
                   if f.data <= referencia]
        cdi_do_dia = fixings[-1].taxa if fixings else None
    except Exception as exc:                       # noqa: BLE001
        avisos.append(f"sem CDI do BCB: {exc}")
    linhas = inflacao_implicita.calcular(titulos, taxa_pre=taxa_pre, cdi=cdi_do_dia)
    vna, _ = inflacao_implicita.vna_do_dia(linhas)
    outros = {t: [{"vencimento": x.vencimento, "taxa_indicativa": x.taxa_indicativa,
                   "pu": x.pu} for x in lista]
              for t, lista in anbima.por_tipo(titulos).items() if t != anbima.NTN_B}
    return json_puro({
        "referencia": referencia, "cdi_do_dia": cdi_do_dia, "vna_ntnb": vna,
        "ntnb": [{**json_puro(l), "duration_anos": l.duration_anos} for l in linhas],
        "outros_titulos": outros, "avisos": avisos,
        "fonte": "boletim de títulos públicos ANBIMA + curva DI x Pré B3 + CDI BCB",
    })


# ------------------------------------------------------------- catálogo

_DATA = {"type": "string", "description": "AAAA-MM-DD ou dd/mm/aaaa"}
_CURVAS = [cod for cod, *_ in b3.CURVAS_COMPLETAS]
_PERNAS = [t.id for t in montador.TIPOS]
_CALENDARIOS = [nome for nome, *_ in CALENDARIOS_DISPONIVEIS]


def _obj(propriedades: dict, obrigatorios=()) -> dict:
    return {"type": "object", "properties": propriedades,
            "required": list(obrigatorios), "additionalProperties": False}


CATALOGO: Dict[str, dict] = {
    "curva_b3": {
        "description": ("Vértices de uma curva de juros/cupom/preço da B3 (taxas referenciais). "
                        "PRE = DI x Pré, DIC = DI x IPCA (juro real), DOC = cupom cambial limpo. "
                        "Data vazia = último dia útil publicado."),
        "inputSchema": _obj({"codigo": {"type": "string", "enum": _CURVAS, "default": "PRE"},
                             "data": _DATA}),
    },
    "taxa_na_curva": {
        "description": ("Taxa interpolada de uma curva da B3 em datas específicas (ex.: datas de "
                        "Copom, vencimentos de DI1), com DU/DC e a taxa a termo entre datas "
                        "consecutivas (forward 252)."),
        "inputSchema": _obj({"datas": {"type": "array", "items": _DATA, "minItems": 1},
                             "codigo": {"type": "string", "enum": _CURVAS, "default": "PRE"},
                             "data_base": _DATA}, ["datas"]),
    },
    "dias_uteis": {
        "description": "Dias úteis e corridos entre duas datas, e a fração de ano em cada convenção.",
        "inputSchema": _obj({"inicio": _DATA, "fim": _DATA,
                             "calendario": {"type": "string", "enum": _CALENDARIOS,
                                            "default": "ANBIMA"}}, ["inicio", "fim"]),
    },
    "ptax": {
        "description": "PTAX do Banco Central (compra, venda, média) da moeda numa data.",
        "inputSchema": _obj({"moeda": {"type": "string", "default": "USD"}, "data": _DATA}),
    },
    "cdi_acumulado": {
        "description": "CDI realizado (série do BCB) acumulado entre duas datas, a um % do CDI.",
        "inputSchema": _obj({"inicio": _DATA, "fim": _DATA,
                             "percentual": {"type": "number", "default": 100,
                                            "description": "% do CDI (100 = 100%)"},
                             "valor": {"type": "number", "default": 1000}},
                            ["inicio", "fim"]),
    },
    "precificar_swap": {
        "description": (
            "Precifica um swap com as curvas da B3 do dia e resolve a taxa par da ponta "
            "escolhida (a que zera o MtM). Pernas: pre_brl, cdi (spread ou % do CDI), ipca "
            "(IPCA+ capitalizado), pre_usd (+variação cambial), pre_usd_sofr, term_sofr. "
            "IPCA×CDI aceita estrutura vanilla ou string e devolve as duas para comparar. "
            "Taxas de entrada em % a.a. (14.5 = 14,5%)."),
        "inputSchema": _obj({
            "perna_ativa": {"type": "string", "enum": _PERNAS, "default": "pre_brl"},
            "perna_passiva": {"type": "string", "enum": _PERNAS, "default": "cdi"},
            "resolver": {"type": "string", "enum": ["ativa", "passiva"], "default": "ativa",
                         "description": "qual ponta tem a taxa calculada"},
            "valor_ativa": {"type": "number", "description": "taxa/spread da ativa em %; "
                            "% do CDI como 105 para 105%"},
            "valor_passiva": {"type": "number"},
            "inicio": _DATA, "vencimento": _DATA,
            "nocional": {"type": "number", "default": 100000000},
            "modo_cdi": {"type": "string", "enum": [SPREAD, PERCENTUAL], "default": SPREAD},
            "estrutura_cdi": {"type": "string", "enum": [VANILLA, STRING], "default": VANILLA},
            "meses_periodo": {"type": "integer", "default": 6},
            "amortizacao": {"type": "string", "enum": [BULLET, LINEAR], "default": BULLET},
            "fee": {"type": "number", "default": 0},
            "data_curva": _DATA,
            "spot": {"type": "number", "description": "USD/BRL, para as pernas em dólar"},
            "calendario": {"type": "string", "enum": _CALENDARIOS, "default": "ANBIMA"},
            "sofr_precos": {"type": "array", "items": {"type": "number"},
                            "description": "preços dos futuros SR3 (pernas SOFR)"},
            "term_sofr": {"type": "array", "items": {"type": "number"},
                          "description": "Term SOFR 1M, 3M, 6M, 12M em %"},
            "incluir_fluxos": {"type": "boolean", "default": False},
        }),
    },
    "curva_ndf": {
        "description": ("Curva a termo (NDF) da moeda contra o real, com DI e cupom da B3: "
                        "preço a termo, pontos e carry por vencimento. Spot vazio = lido da "
                        "curva de preço da B3. Casado/rolagem só para USD."),
        "inputSchema": _obj({
            "spot": {"type": "number"},
            "moeda": {"type": "string", "enum": [m.codigo for m in MOEDAS_NDF],
                      "default": "USD"},
            "vencimento": _DATA,
            "datas": {"type": "array", "items": _DATA},
            "quantidade": {"type": "integer", "default": 12},
            "progressao": {"type": "string", "enum": list(PROGRESSOES), "default": "mensal"},
            "data_curva": _DATA,
            "taxa_estrangeira": {"type": "number", "description": "% a.a., moedas sem curva"},
            "primeiro_futuro": {"type": "number"}, "segundo_futuro": {"type": "number"},
            "direcao": {"type": "string", "enum": [d for d, _ in DIRECOES], "default": "saida"},
        }),
    },
    "precificar_opcao_fx": {
        "description": (
            "Opções de dólar (USD/BRL) por Garman-Kohlhagen: até 4 pernas (call/put, "
            "comprada/vendida) — collar, call/put spread, three-way, four-way, straddle, "
            "strangle, box. Taxas vazias = curvas PRE e DOC da B3. Vol única, por perna ou "
            "smile B3 (11 vols por delta, Δ1..Δ99). resolver_strike = nº da perna (1..4) "
            "cujo strike é calculado para o prêmio líquido atingir premio_alvo (0 = custo zero). "
            "spread/fee calculam o benefício all-in num empréstimo CDI+."),
        "inputSchema": _obj({
            "spot": {"type": "number"}, "vencimento": _DATA, "inicio": _DATA,
            "pernas": {"type": "array", "minItems": 1, "maxItems": 4, "items": _obj({
                "tipo": {"type": "string", "enum": ["call", "put"]},
                "lado": {"type": "string", "enum": ["comprada", "vendida"]},
                "strike": {"type": "number"},
                "vol": {"type": "number", "description": "% a.a."}}, ["tipo", "lado"])},
            "nocional": {"type": "number", "default": 1000000},
            "moeda_nocional": {"type": "string", "enum": ["USD", "BRL"], "default": "USD"},
            "vol": {"type": "number", "description": "vol única em % a.a."},
            "smile": {"type": "array", "items": {"type": "number"}, "minItems": 11,
                      "maxItems": 11},
            "taxa_dom": {"type": "number", "description": "DI % a.a. 252"},
            "taxa_est": {"type": "number", "description": "cupom cambial % a.a. linear 360"},
            "resolver_strike": {"type": "integer", "minimum": 1, "maximum": 4},
            "premio_alvo": {"type": "number", "default": 0},
            "spread": {"type": "number", "description": "spread CDI+ do empréstimo, %"},
            "fee": {"type": "number", "description": "fee flat em %"},
        }, ["spot", "vencimento", "pernas"]),
    },
    "inflacao_implicita_ntnb": {
        "description": ("Boletim de títulos públicos da ANBIMA na data: NTN-B com juro real, "
                        "duration, pré DI no prazo e inflação implícita (breakeven), VNA do dia, "
                        "e as taxas indicativas de LTN, NTN-F e LFT."),
        "inputSchema": _obj({"data": _DATA}),
    },
}

EXECUTORES: Dict[str, Callable[..., dict]] = {
    "curva_b3": curva_b3, "taxa_na_curva": taxa_na_curva, "dias_uteis": dias_uteis,
    "ptax": ptax, "cdi_acumulado": cdi_acumulado, "precificar_swap": precificar_swap,
    "curva_ndf": curva_ndf, "precificar_opcao_fx": precificar_opcao_fx,
    "inflacao_implicita_ntnb": inflacao_implicita_ntnb,
}


def executar(nome: str, argumentos: dict) -> dict:
    return json_puro(EXECUTORES[nome](**argumentos))
