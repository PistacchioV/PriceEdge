"""Camada de serviço entre o pacote ``precificador`` e as rotas Flask.

Cuida do que é responsabilidade da aplicação e não do modelo: cache das
curvas baixadas da B3, leitura de formulário, montagem dos gráficos e
formatação para exibição.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from precificador import b3, contagem
from precificador.erros import ErroTraduzido
from precificador.calendario import (calendario_anbima, obter_calendario,
                                     para_data, terceira_quarta)
from precificador.curvas import EXP252, PRECO, Curva, CurvaTermSOFR, Vertice
from precificador.calendario import FOLLOWING
from precificador.instrumentos import BULLET, PERSONALIZADA
from precificador.produtos import ParametrosSwap

# --------------------------------------------------------------------- cache

_CACHE: Dict[Tuple[str, str], List[b3.VerticeB3]] = {}

# a convenção vem do catálogo do módulo b3, para não haver duas listas
CONVENCAO_POR_CURVA = dict(b3.CONVENCAO_POR_CODIGO)

# spline nas curvas de juros em real; linear no que é cupom, spread ou preço —
# nesses a B3 já publica ponto a ponto e suavizar inventa curvatura que não há
METODO_POR_CURVA = {cod: ("spline" if conv == EXP252 else "linear")
                    for cod, conv in CONVENCAO_POR_CURVA.items()}


def limpar_cache() -> None:
    _CACHE.clear()


def vertices(codigo: str, data) -> List[b3.VerticeB3]:
    """Vértices da B3, com cache em memória por (curva, data)."""
    d = para_data(data)
    chave = (codigo.upper(), d.isoformat())
    if chave not in _CACHE:
        _CACHE[chave] = b3.extrair_curva(codigo, d)
    return _CACHE[chave]


def curva(codigo: str, data) -> Curva:
    codigo = codigo.upper()
    vs = vertices(codigo, data)
    if not vs:
        raise b3.ErroB3(
            "a B3 não publicou a curva {curva} para {data}. O histórico público "
            "cobre aproximadamente o último mês útil.",
            curva=b3.NOME_POR_CODIGO.get(codigo, codigo),
            data=f"{para_data(data):%d/%m/%Y}"
        )
    return Curva.de_b3(vs, b3.NOME_POR_CODIGO.get(codigo, codigo), data,
                       convencao=CONVENCAO_POR_CURVA.get(codigo, EXP252),
                       metodo=METODO_POR_CURVA.get(codigo, "spline"))


DERIVADAS = [
    ("EURUSD", "EUR/USD a Termo (derivado)", ("EUR", "PTX"),
     "Não existe curva EUR/USD na B3, mas as duas pontas existem: o euro a termo "
     "dividido pelo dólar a termo dá o EUR/USD a termo."),
]

DERIVADA_POR_CODIGO = {cod: (nome, partes, desc) for cod, nome, partes, desc in DERIVADAS}


def curva_derivada(codigo: str, data) -> Curva:
    """Curvas que a B3 não publica mas que saem da razão de duas que ela publica."""
    nome, (numerador, denominador), _ = DERIVADA_POR_CODIGO[codigo]
    de_cima, de_baixo = curva(numerador, data), curva(denominador, data)

    prazos = sorted({(v.dias_uteis, v.dias_corridos) for v in de_cima.vertices}
                    & {(v.dias_uteis, v.dias_corridos) for v in de_baixo.vertices})
    if not prazos:
        raise b3.ErroB3("as curvas {a} e {b} não têm prazos em comum",
                        a=numerador, b=denominador)

    vertices = [Vertice(du, dc, de_cima.taxa_para(dc, du) / de_baixo.taxa_para(dc, du))
                for du, dc in prazos]
    return Curva(nome=nome, data_referencia=para_data(data), vertices=vertices,
                 convencao=PRECO, metodo="linear")


def data_sugerida() -> date:
    """A data de referência que toda tela abre: **hoje**.

    Era D-1, por cautela com o horário de publicação da B3 — e o resultado é
    que metade das telas nascia num dia e a outra metade em outro. Quem monta
    uma curva na tela de NDF e confere na de extração precisa dos dois lados
    falando da mesma data; a diferença de um dia útil não aparece como erro,
    aparece como taxa diferente.

    A B3 publica o arquivo do dia durante o pregão, então hoje costuma existir.
    Quando não existe — fim de semana, feriado, ou antes da publicação — a
    própria extração diz por extenso qual é o problema, e a data continua
    editável em todas as telas.
    """
    return date.today()


def datas_uteis_recentes(quantidade: int = 25) -> List[date]:
    cal = calendario_anbima()
    datas, d = [], data_sugerida()
    while len(datas) < quantidade:
        if cal.eh_dia_util(d):
            datas.append(d)
        d -= timedelta(days=1)
    return datas


# ------------------------------------------------------------------ gráfico

@dataclass
class Grafico:
    """Curva desenhada como caminho SVG puro, sem biblioteca no cliente."""
    largura: int
    altura: int
    caminho: str
    area: str
    pontos_vertices: List[dict]
    rotulos_x: List[dict]
    rotulos_y: List[dict]
    eixo: str = "dc"          # contra o que a curva foi desenhada
    linha_spot: Optional[float] = None   # só no gráfico de NDF


def montar_grafico(curva_obj: Curva, largura: int = 900, altura: int = 300,
                   margem: int = 44) -> Optional[Grafico]:
    vs = curva_obj.vertices
    if len(vs) < 2:
        return None
    usa_du = curva_obj.eixo == "du"
    xs = [(v.dias_uteis if usa_du else v.dias_corridos) for v in vs]
    ys = [v.taxa for v in vs]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if y1 == y0:
        y0, y1 = y0 - 0.001, y1 + 0.001
    folga = (y1 - y0) * 0.12
    y0, y1 = y0 - folga, y1 + folga

    def px(x):
        return margem + (x - x0) / (x1 - x0) * (largura - 2 * margem)

    def py(y):
        return altura - margem - (y - y0) / (y1 - y0) * (altura - 2 * margem)

    amostras = curva_obj.amostrar(passo=max(1, (x1 - x0) // 220 or 1))
    pontos = [(px(p["x"]), py(p["taxa"])) for p in amostras]
    caminho = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pontos)
    area = (caminho + f" L {pontos[-1][0]:.2f},{altura - margem:.2f}"
            f" L {pontos[0][0]:.2f},{altura - margem:.2f} Z")

    passo_vertices = max(1, len(vs) // 40)
    marcadores = [{"x": px(v.dias_uteis if usa_du else v.dias_corridos), "y": py(v.taxa),
                   "dc": v.dias_corridos, "du": v.dias_uteis, "taxa": v.taxa}
                  for v in vs[::passo_vertices]]

    rotulos_x = [{"x": px(x0 + (x1 - x0) * i / 4),
                  "valor": int(x0 + (x1 - x0) * i / 4)} for i in range(5)]
    rotulos_y = [{"y": py(y0 + (y1 - y0) * i / 4),
                  "valor": y0 + (y1 - y0) * i / 4} for i in range(5)]
    return Grafico(largura, altura, caminho, area, marcadores, rotulos_x, rotulos_y,
                   eixo=curva_obj.eixo)


def csv_da_curva(curva_obj: Curva) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["Dias Uteis", "Dias Corridos", "Taxa (% a.a.)"])
    for v in curva_obj.vertices:
        escritor.writerow([v.dias_uteis, v.dias_corridos, f"{v.taxa * 100:.6f}".replace(".", ",")])
    return saida.getvalue()


# --------------------------------------------------------------- formulário

class ErroFormulario(ErroTraduzido, ValueError):
    pass


def _decimal(texto: str, campo: str, padrao: Optional[float] = None) -> float:
    """Lê um número aceitando o padrão brasileiro e o americano.

    Os campos voltam do navegador já formatados (``100.000.000,00``,
    ``2,50000000 %``), então o parser precisa dar conta de separador de milhar.
    A regra é a mesma do ``formatar-campos.js``:

    * com vírgula e ponto, o **último** separador é o decimal e o outro é milhar;
    * só vírgula, é decimal;
    * vários pontos, todos são milhar (``100.000.000``);
    * um ponto só, é decimal (para ``5.15`` continuar sendo cinco e quinze).
    """
    texto = (texto or "").strip().replace("%", "").replace(" ", "").replace(" ", "")
    if not texto:
        if padrao is None:
            raise ErroFormulario("preencha o campo {campo}", campo=campo)
        return padrao

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            normalizado = texto.replace(".", "").replace(",", ".")
        else:
            normalizado = texto.replace(",", "")
    elif "," in texto:
        normalizado = texto.replace(",", ".")
    elif texto.count(".") > 1:
        normalizado = texto.replace(".", "")
    else:
        normalizado = texto

    try:
        return float(normalizado)
    except ValueError:
        raise ErroFormulario("{campo}: “{texto}” não é um número",
                             campo=campo, texto=texto) from None


def numero_do_form(valores, campo: str, rotulo: str, padrao=None) -> float:
    """Número solto (nocional, spot, fee) — sem conversão de percentual."""
    return _decimal(valores.get(campo), rotulo, padrao)


def taxa_do_form(valores, campo: str, rotulo: str, padrao=None) -> float:
    """Aceita 17, 17%, 0,17 — sempre devolve decimal."""
    bruto = (valores.get(campo) or "").strip()
    numero = _decimal(bruto, rotulo, padrao)
    return numero / 100.0 if abs(numero) >= 1.0 or "%" in bruto else numero


def parametros_do_form(valores) -> ParametrosSwap:
    inicio = valores.get("inicio") or ""
    vencimento = valores.get("vencimento") or ""
    if not inicio or not vencimento:
        raise ErroFormulario("informe as datas de início e vencimento")
    try:
        inicio_d, vencimento_d = para_data(inicio), para_data(vencimento)
    except ValueError as exc:
        raise ErroFormulario.de(exc) from None

    amortizacao = valores.get("amortizacao") or BULLET
    pesos = None
    if amortizacao == PERSONALIZADA:
        bruto = (valores.get("pesos") or "").replace(";", ",")
        try:
            pesos = [float(p.strip()) / 100.0 for p in bruto.split(",") if p.strip()]
        except ValueError:
            raise ErroFormulario("pesos de amortização inválidos") from None

    sem_fluxo = str(valores.get("sem_fluxo") or "").lower() in ("1", "on", "true", "sim")
    try:
        return ParametrosSwap(
            inicio=inicio_d, vencimento=vencimento_d,
            nocional=_decimal(valores.get("nocional"), "nocional"),
            meses_periodo=int(valores.get("meses_periodo") or 6),
            amortizacao=amortizacao, pesos=pesos,
            fee=_decimal(valores.get("fee"), "fee", 0.0),
            convencao_dia_util=valores.get("convencao_dia_util") or FOLLOWING,
            sem_fluxo=sem_fluxo,
        )
    except ValueError as exc:
        raise ErroFormulario.de(exc) from None


# ------------------------------------------------------------- Term SOFR ---

def datas_imm_a_partir_de(data_spot, quantidade: int) -> List[date]:
    """Datas IMM (3ª quarta de mar/jun/set/dez) a partir do spot."""
    d = para_data(data_spot)
    datas, ano, mes = [], d.year, 3 * ((d.month - 1) // 3) + 3
    while len(datas) < quantidade:
        imm = terceira_quarta(ano, mes)
        if imm > d:
            datas.append(imm)
        mes += 3
        if mes > 12:
            mes, ano = mes - 12, ano + 1
    return datas


def curva_sofr_padrao(data_spot, precos: List[float],
                      taxas_term: Optional[dict] = None) -> CurvaTermSOFR:
    """Curva Term SOFR: taxas da CME no trecho curto, futuros SR3 no longo.

    As datas IMM são geradas a partir do spot, então a curva acompanha a data
    do contrato em vez de ficar presa aos vencimentos da planilha.
    """
    datas = datas_imm_a_partir_de(data_spot, len(precos) + 1)
    forwards = [(100.0 - p) / 100.0 for p in precos]
    return CurvaTermSOFR(para_data(data_spot), datas, forwards,
                         taxas_term=taxas_term or {})


def grafico_ndf(pontos, spot: float, largura: int = 900, altura: int = 280,
                margem: int = 52) -> Optional[Grafico]:
    """Curva de dólar a termo desenhada como caminho SVG."""
    if len(pontos) < 2:
        return None
    xs = [p.dias_corridos for p in pontos]
    ys = [p.ndf for p in pontos] + [spot]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if x1 == x0:
        return None
    if y1 == y0:
        y0, y1 = y0 - 0.01, y1 + 0.01
    folga = (y1 - y0) * 0.15
    y0, y1 = y0 - folga, y1 + folga

    def px(x):
        return margem + (x - x0) / (x1 - x0) * (largura - 2 * margem)

    def py(y):
        return altura - margem - (y - y0) / (y1 - y0) * (altura - 2 * margem)

    coords = [(px(p.dias_corridos), py(p.ndf)) for p in pontos]
    caminho = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
    area = (caminho + f" L {coords[-1][0]:.2f},{altura - margem:.2f}"
            f" L {coords[0][0]:.2f},{altura - margem:.2f} Z")
    marcadores = [{"x": x, "y": y, "dc": p.dias_corridos, "du": p.dias_uteis,
                   "taxa": p.ndf, "data": p.data}
                  for (x, y), p in zip(coords, pontos)]
    rotulos_x = [{"x": px(x0 + (x1 - x0) * i / 4),
                  "valor": int(x0 + (x1 - x0) * i / 4)} for i in range(5)]
    rotulos_y = [{"y": py(y0 + (y1 - y0) * i / 4),
                  "valor": y0 + (y1 - y0) * i / 4} for i in range(5)]
    grafico = Grafico(largura, altura, caminho, area, marcadores, rotulos_x, rotulos_y)
    grafico.linha_spot = py(spot)
    return grafico


# ------------------------------------------------------------------ EURIBOR

CORES_EURIBOR = ["#67e8f9", "#fbbf24", "#f87171", "#38bdf8", "#a3a3a3"]


def series_euribor(curva, largura: int = 900, altura: int = 320,
                   margem_x: int = 52, margem_y: int = 34) -> dict:
    """Uma linha por prazo, sobre o mesmo par de eixos.

    Cinco séries no mesmo gráfico só ficam legíveis com escala compartilhada;
    por isso o eixo y cobre o intervalo de todas elas, não o de cada uma.
    """
    datas = curva.datas
    if len(datas) < 2:
        return {"series": [], "escala_x": [], "escala_y": []}

    tabela = curva.por_data()
    valores = [v for linha in tabela.values() for v in linha.values()]
    y0, y1 = min(valores), max(valores)
    if y1 == y0:
        y0, y1 = y0 - 0.001, y1 + 0.001
    folga = (y1 - y0) * 0.12
    y0, y1 = max(0.0, y0 - folga), y1 + folga

    def px(i):
        return margem_x + i / (len(datas) - 1) * (largura - 2 * margem_x)

    def py(v):
        return altura - margem_y - (v - y0) / (y1 - y0) * (altura - 2 * margem_y)

    series = []
    for cor, tenor in zip(CORES_EURIBOR, curva.tenores):
        pontos = [(px(i), py(tabela[d][tenor]))
                  for i, d in enumerate(datas) if tenor in tabela[d]]
        if len(pontos) < 2:
            continue
        series.append({
            "tenor": tenor, "cor": cor,
            "caminho": "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pontos),
        })

    escala_x = []
    for i in range(5):
        indice = round(i * (len(datas) - 1) / 4)
        escala_x.append({"x": px(indice), "rotulo": datas[indice].strftime("%m/%Y")})

    escala_y = [{"y": py(y0 + (y1 - y0) * i / 4),
                 "rotulo": f"{(y0 + (y1 - y0) * i / 4) * 100:.2f}%".replace(".", ",")}
                for i in range(5)]
    return {"series": series, "escala_x": escala_x, "escala_y": escala_y}


CORES_SOFR = ["#67e8f9", "#fbbf24", "#f87171", "#a3a3a3"]


def series_sofr(historico, largura: int = 900, altura: int = 320,
                margem_x: int = 52, margem_y: int = 34) -> dict:
    """As séries do SOFR realizado no mesmo par de eixos."""
    from precificador.sofr import CAMPOS as CAMPOS_SOFR

    datas = historico.datas
    if len(datas) < 2:
        return {"series": [], "escala_x": [], "escala_y": []}

    tabela = historico.por_data()
    campos = historico.campos
    valores = [linha[c] for linha in tabela.values() for c in campos if c in linha]
    if not valores:
        return {"series": [], "escala_x": [], "escala_y": []}
    y0, y1 = min(valores), max(valores)
    if y1 == y0:
        y0, y1 = y0 - 0.001, y1 + 0.001
    folga = (y1 - y0) * 0.12
    y0, y1 = max(0.0, y0 - folga), y1 + folga

    def px(i):
        return margem_x + i / (len(datas) - 1) * (largura - 2 * margem_x)

    def py(v):
        return altura - margem_y - (v - y0) / (y1 - y0) * (altura - 2 * margem_y)

    rotulos = dict(CAMPOS_SOFR)
    series = []
    for cor, campo in zip(CORES_SOFR, campos):
        pontos = [(px(i), py(tabela[d][campo]))
                  for i, d in enumerate(datas) if campo in tabela[d]]
        if len(pontos) < 2:
            continue
        series.append({"tenor": rotulos.get(campo, campo), "cor": cor,
                       "caminho": "M " + " L ".join(f"{x:.2f},{y:.2f}"
                                                    for x, y in pontos)})

    escala_x = [{"x": px(round(i * (len(datas) - 1) / 4)),
                 "rotulo": datas[round(i * (len(datas) - 1) / 4)].strftime("%m/%Y")}
                for i in range(5)]
    escala_y = [{"y": py(y0 + (y1 - y0) * i / 4),
                 "rotulo": f"{(y0 + (y1 - y0) * i / 4) * 100:.2f}%".replace(".", ",")}
                for i in range(5)]
    return {"series": series, "escala_x": escala_x, "escala_y": escala_y}


def curvas_da_moeda(moeda, data) -> dict:
    """Baixa as curvas que a moeda escolhida precisa, e só elas.

    O que volta é o par (DI, curva da moeda) já pronto para ``curva_ndf``, mais
    a lista do que foi efetivamente baixado, para a tela mostrar de onde veio
    cada número. As curvas saem todas na mesma grade de vértices da B3 — o que
    a moeda escolhe é qual arquivo desce e sob que convenção ele é lido.
    """
    from precificador.produtos import (MODO_CUPOM, MODO_IMPLICITO, MODO_MANUAL,
                                       MODO_PRECO)

    di = None if moeda.modo == MODO_PRECO else curva("PRE", data)
    cupom = preco = None

    if moeda.modo == MODO_CUPOM:
        cupom = curva(moeda.curva_cupom, data)
    elif moeda.modo in (MODO_IMPLICITO, MODO_PRECO):
        preco = (curva_derivada(moeda.curva_preco, data)
                 if moeda.curva_preco in DERIVADA_POR_CODIGO
                 else curva(moeda.curva_preco, data))
    elif moeda.modo != MODO_MANUAL:
        raise ErroFormulario("modo de moeda desconhecido: {modo}", modo=moeda.modo)

    return {"di": di, "cupom": cupom, "preco": preco,
            "usadas": [c for c in (di, cupom, preco) if c is not None]}


def spot_da_curva(moeda, data):
    """Spot lido do primeiro vértice da curva de preço, quando existe uma.

    A B3 ancora as curvas de preço a termo no spot do dia, então o vértice mais
    curto é a melhor cotação disponível sem sair para outra fonte. Devolve
    ``None`` para as moedas que não têm curva de preço.
    """
    if not moeda.curva_preco:
        return None
    try:
        c = (curva_derivada(moeda.curva_preco, data)
             if moeda.curva_preco in DERIVADA_POR_CODIGO
             else curva(moeda.curva_preco, data))
    except (b3.ErroB3, KeyError):
        return None
    return c.vertices[0].taxa if c.vertices else None


def contagens_lado_a_lado(inicio, fim, calendario: str = "ANBIMA") -> list:
    """Cada convenção de contagem no mesmo período, para comparar.

    O número de dias e o τ mudam de convenção para convenção, e a diferença é
    invisível quando só se olha uma. Lado a lado ela aparece: os mesmos seis
    meses valem 0,4881 de ano em DU/252 e 0,5028 em ACT/360.
    """
    cal = obter_calendario(calendario)
    linhas = []
    for codigo, nome, _ in contagem.CONVENCOES:
        linhas.append({
            "codigo": codigo, "nome": nome,
            "dias": contagem.dias(codigo, inicio, fim, cal),
            "base": contagem.base(codigo),
            "fracao": contagem.fracao(codigo, inicio, fim, cal),
        })
    return linhas
