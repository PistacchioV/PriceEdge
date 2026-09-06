"""Rotas da aplicação."""

from __future__ import annotations

from datetime import date, timedelta

from flask import (Blueprint, Response, jsonify, redirect, render_template,
                   request, url_for)

from precificador import (b3, cambio, cdi, euribor, fontes, glossario,
                          montador, rede, renda_fixa, sofr)
from precificador.calendario import (CALENDARIOS_DISPONIVEIS, CONVENCOES_DIA_UTIL,
                                     MODIFIED_FOLLOWING, calendario_anbima,
                                     obter_calendario, para_data, soma_meses)
from precificador.curvas import TENORES_TERM
from precificador.instrumentos import (BULLET, LINEAR, PERCENTUAL,
                                       PERSONALIZADA, SPREAD)
from precificador.interpolacao import METODOS, interpolar
from precificador.erros import ErroDeFonte
from precificador.produtos import (MOEDAS_NDF, MODO_MANUAL, MODO_PRECO,
                                   PROGRESSOES, NumeroIndice, casado, curva_ndf,
                                   moeda_ndf,
                                   escada_datas, rolagem)
from precificador.solver import SemConvergencia

from . import servicos

bp = Blueprint("principal", __name__)

PRODUTOS = [
    {"id": "pre_cdi", "nome": "Pré BRL × CDI ± spread",
     "curvas": ["PRE"], "icone": "solar:chart-2-linear",
     "resumo": "Uma curva só. O spread é multiplicativo: (1+CDI)·(1+spread) = (1+pré)."},
    {"id": "usd_brl", "nome": "Pré USD × Pré BRL",
     "curvas": ["PRE", "DOC"], "icone": "solar:dollar-minimalistic-linear",
     "resumo": "Cross-currency. Fluxo em reais desconta no DI, fluxo em dólar no cupom cambial."},
    {"id": "usd_cdi", "nome": "Pré USD × CDI ± spread",
     "curvas": ["PRE", "DOC"], "icone": "solar:card-transfer-linear",
     "resumo": "Cross-currency com a ponta em reais flutuante. Duas curvas de desconto, spread multiplicativo."},
    {"id": "ipca_cdi", "nome": "IPCA capitalizado × CDI ± spread",
     "curvas": ["PRE", "DIC"], "icone": "solar:graph-up-linear",
     "resumo": "Inflação implícita de (1+DI)/(1+DI×IPCA)−1, capitalizada por período."},
    {"id": "usd_sofr", "nome": "Pré USD × Term SOFR ± spread",
     "curvas": [], "icone": "solar:global-linear",
     "resumo": "Bootstrap dos futuros SR3 em datas IMM. Spread aditivo, linear 360."},
]
PRODUTO_POR_ID = {p["id"]: p for p in PRODUTOS}

SOFR_PADRAO = [96.345, 96.38, 96.42, 96.46, 96.49, 96.51, 96.52, 96.53]

# vem do pacote: acrescentar um calendário lá o faz aparecer na tela sozinho
CALENDARIOS = [(nome, f"{nome} — {descricao}")
               for nome, _, descricao in CALENDARIOS_DISPONIVEIS]


# ------------------------------------------------------------------- painel

@bp.route("/")
def painel():
    return render_template("painel.html", produtos=PRODUTOS,
                           curvas=b3.CURVAS, data_sugerida=servicos.data_sugerida())


# ------------------------------------------------------------------- curvas

@bp.route("/curvas")
def curvas():
    codigo = (request.args.get("curva") or "PRE").upper()
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    contexto = {
        "curvas_disponiveis": b3.CURVAS_COMPLETAS,
        "derivadas": servicos.DERIVADAS,
        "codigo": codigo, "data": data_txt,
        "datas_recentes": servicos.datas_uteis_recentes(),
        "curva": None, "grafico": None, "erro": None,
    }
    if request.args.get("extrair") is not None or request.args.get("curva"):
        try:
            obj = (servicos.curva_derivada(codigo, data_txt)
                   if codigo in servicos.DERIVADA_POR_CODIGO
                   else servicos.curva(codigo, data_txt))
            contexto["curva"] = obj
            contexto["grafico"] = servicos.montar_grafico(obj)
        except (ErroDeFonte, ValueError) as exc:
            contexto["erro"] = str(exc)
    return render_template("curvas.html", **contexto)


@bp.route("/curvas/csv")
def curvas_csv():
    codigo = (request.args.get("curva") or "PRE").upper()
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        obj = (servicos.curva_derivada(codigo, data_txt)
               if codigo in servicos.DERIVADA_POR_CODIGO
               else servicos.curva(codigo, data_txt))
    except (ErroDeFonte, ValueError) as exc:
        return Response(str(exc), status=404, mimetype="text/plain; charset=utf-8")
    nome = f"curva_{codigo}_{para_data(data_txt):%Y%m%d}.csv"
    return Response(servicos.csv_da_curva(obj), content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/api/curvas/<codigo>")
def api_curva(codigo: str):
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        return jsonify(servicos.curva(codigo, data_txt).para_dict())
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": str(exc)}), 404


@bp.route("/api/interpolar/<codigo>")
def api_interpolar(codigo: str):
    """Taxa interpolada para um prazo, com o método escolhido."""
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        dc = float(request.args.get("dc", 0))
        obj = servicos.curva(codigo, data_txt)
        obj.metodo = request.args.get("metodo", obj.metodo)
        return jsonify({"dc": dc, "taxa": obj.taxa(dc), "metodo": obj.metodo})
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": str(exc)}), 400


# ------------------------------------------------------------- interpolação

@bp.route("/interpolar", methods=["GET", "POST"])
def interpolador():
    contexto = {"metodos": list(METODOS), "resultado": None, "erro": None,
                "x_txt": "", "y_txt": "", "alvos_txt": "", "metodo": "spline",
                "extrapolar": "flat", "curvas_disponiveis": b3.CURVAS_COMPLETAS,
                "data_sugerida": servicos.data_sugerida()}
    if request.method == "POST":
        contexto.update({
            "x_txt": request.form.get("x", ""),
            "y_txt": request.form.get("y", ""),
            "alvos_txt": request.form.get("alvos", ""),
            "metodo": request.form.get("metodo", "spline"),
            "extrapolar": request.form.get("extrapolar", "flat"),
        })
        try:
            xs = _numeros(contexto["x_txt"], "eixo x")
            ys = _numeros(contexto["y_txt"], "eixo y")
            alvos = _numeros(contexto["alvos_txt"], "pontos a interpolar")
            if len(xs) != len(ys):
                raise ValueError(f"o eixo x tem {len(xs)} pontos e o y tem {len(ys)}")
            if len(xs) < 2:
                raise ValueError("são necessários pelo menos dois pontos")
            linhas = []
            for alvo in alvos:
                valor = interpolar(xs, ys, alvo, metodo=contexto["metodo"],
                                   **({} if contexto["metodo"] == "flat_forward"
                                      else {"extrapolar": contexto["extrapolar"]}))
                linhas.append({"x": alvo, "y": valor,
                               "fora": alvo < min(xs) or alvo > max(xs)})
            contexto["resultado"] = {"linhas": linhas, "n": len(xs),
                                     "dominio": (min(xs), max(xs))}
        except ValueError as exc:
            contexto["erro"] = str(exc)
    return render_template("interpolar.html", **contexto)


@bp.route("/interpolar/carregar")
def interpolar_carregar():
    """Devolve os vértices de uma curva da B3 já no formato do formulário."""
    codigo = (request.args.get("curva") or "PRE").upper()
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        obj = servicos.curva(codigo, data_txt)
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": str(exc)}), 404
    return jsonify({
        "x": "\n".join(str(v.dias_corridos) for v in obj.vertices),
        "y": "\n".join(f"{v.taxa * 100:.4f}" for v in obj.vertices),
        "nome": obj.nome,
    })


def _numeros(texto: str, campo: str):
    """Lê uma lista de números tolerando os dois padrões decimais.

    A vírgula é ambígua: em “14,65 14,64” ela é decimal, em “96.345, 96.38” é
    separador.  A regra é resolvida por token — vírgula sobrando na ponta cai
    fora, vírgula convivendo com ponto (ou repetida) separa, vírgula sozinha é
    decimal.
    """
    bruto = (texto or "").replace(";", " ").replace("\t", " ").replace("\n", " ")
    valores = []
    for token in bruto.split():
        token = token.strip(",")
        if not token:
            continue
        if token.count(",") >= 2 or ("," in token and "." in token):
            pedacos = [p for p in token.split(",") if p]
        elif "," in token:
            pedacos = [token.replace(",", ".")]
        else:
            pedacos = [token]
        for pedaco in pedacos:
            try:
                valores.append(float(pedaco))
            except ValueError:
                raise ValueError(f"{campo}: “{pedaco}” não é um número") from None
    if not valores:
        raise ValueError(f"{campo}: nada foi informado")
    return valores


# ------------------------------------------------------------- precificação

@bp.route("/precificar", methods=["GET", "POST"])
def precificar():
    """Swap personalizado — a tela geral, com templates para as estruturas prontas."""
    hoje = servicos.data_sugerida()
    template = montador.TEMPLATE_POR_ID.get(request.values.get("template") or "")

    contexto = {
        "tipos": montador.TIPOS,
        "templates": montador.TEMPLATES,
        "template_ativo": template.id if template else "",
        "form": _form_do_construtor(hoje, template),
        "amortizacoes": [(BULLET, "Bullet — principal no vencimento"),
                         (LINEAR, "Linear — amortização constante"),
                         (PERSONALIZADA, "Personalizada (% por período)")],
        "convencoes": CONVENCOES_DIA_UTIL,
        "calendarios": CALENDARIOS,
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _montar_personalizado(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, SemConvergencia, ValueError) as exc:
            contexto["erro"] = str(exc)

    contexto["insumos"] = montador.insumos_necessarios(
        contexto["form"].get("perna_ativa", "pre_brl"),
        contexto["form"].get("perna_passiva", "cdi"))
    return render_template("precificar.html", **contexto)


@bp.route("/montar")
def montar_swap():
    """Endereço antigo do construtor — hoje ele é a própria tela de precificar."""
    return redirect(url_for("principal.precificar", **request.args))


def _form_do_construtor(hoje: date, template=None) -> dict:
    padrao = {
        "data_curva": hoje.isoformat(), "inicio": hoje.isoformat(),
        "vencimento": date(hoje.year + 5, hoje.month, hoje.day).isoformat(),
        "nocional": "100.000.000,00", "meses_periodo": "6",
        "amortizacao": BULLET, "fee": "0", "calendario": "ANBIMA",
        "convencao_dia_util": MODIFIED_FOLLOWING, "sem_fluxo": "",
        "perna_ativa": "pre_brl", "valor_ativa": "17",
        "perna_passiva": "cdi", "valor_passiva": "",
        "modo_cdi": SPREAD, "resolver": "passiva", "spot": "5,15",
        "sofr": ", ".join(str(preco) for preco in SOFR_PADRAO),
        "term_sofr": "3,64637, 3,65811, 3,67358, 3,73148",
    }
    if template:
        padrao.update({
            "perna_ativa": template.ativa, "perna_passiva": template.passiva,
            "valor_ativa": template.valor_ativa, "valor_passiva": "",
            "modo_cdi": template.modo_cdi,
        })
    return padrao


# ------------------------------------------------------------------- NDF ----

@bp.route("/ndf", methods=["GET", "POST"])
def ndf():
    """Non deliverable forward — porte da planilha *NDF com extração de curvas B3*."""
    hoje = servicos.data_sugerida()
    contexto = {
        "form": {
            "data_curva": hoje.isoformat(), "moeda": "USD", "spot": "5,10",
            "ptax": "", "taxa_estrangeira": "", "primeiro_futuro": "5125",
            "segundo_futuro": "5150", "progressao": "mensal", "quantidade": "12",
            "calendario": "ANBIMA", "datas": "", "vencimento": "",
        },
        "progressoes": [(chave, rotulo) for chave, (rotulo, _) in PROGRESSOES.items()],
        "calendarios": CALENDARIOS,
        "moedas": MOEDAS_NDF,
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _montar_ndf(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = str(exc)
    return render_template("ndf.html", **contexto)


def _montar_ndf(form) -> dict:
    data_curva = form.get("data_curva") or servicos.data_sugerida().isoformat()
    base = para_data(data_curva)
    moeda = moeda_ndf(form.get("moeda"))
    spot = servicos.numero_do_form(form, "spot", "spot D+2")
    cal = obter_calendario(form.get("calendario") or "ANBIMA")

    # a moeda escolhida manda em quais curvas descem da B3 — e nos vértices delas
    fontes = servicos.curvas_da_moeda(moeda, data_curva)

    estrangeira = 0.0
    if moeda.modo == MODO_MANUAL:
        estrangeira = servicos.numero_do_form(
            form, "taxa_estrangeira", "juro da moeda estrangeira") / 100.0

    vencimento = (form.get("vencimento") or "").strip()
    bruto = (form.get("datas") or "").replace(";", ",").replace("\n", ",")
    especificas = [d.strip() for d in bruto.split(",") if d.strip()]
    if vencimento:
        # um vencimento específico manda em tudo: é o NDF de um contrato
        try:
            datas = [para_data(vencimento)]
        except ValueError as exc:
            raise servicos.ErroFormulario(f"vencimento inválido: {exc}") from None
        if datas[0] <= base:
            raise servicos.ErroFormulario(
                "o vencimento do NDF tem que ser posterior à data-base das curvas")
    elif especificas:
        try:
            datas = [para_data(d) for d in especificas]
        except ValueError as exc:
            raise servicos.ErroFormulario(
                f"data específica inválida: {exc}. Use AAAA-MM-DD ou dd/mm/aaaa.") from None
    else:
        quantidade = int(servicos.numero_do_form(form, "quantidade", "quantidade", 12))
        datas = escada_datas(base, form.get("progressao") or "mensal",
                             max(1, min(quantidade, 120)), cal)

    pontos = curva_ndf(base, spot, fontes["di"], fontes["cupom"], datas, cal,
                       fontes["preco"], moeda, estrangeira)
    if not pontos:
        raise servicos.ErroFormulario("nenhum vencimento posterior à data-base")

    # casado e rolagem são do pregão de dólar: não existem para as outras moedas
    dolar = moeda.codigo == "USD"
    primeiro = servicos.numero_do_form(form, "primeiro_futuro", "1º futuro", 0.0)
    segundo = servicos.numero_do_form(form, "segundo_futuro", "2º futuro", 0.0)

    return {
        "base": base, "spot": spot, "pontos": pontos, "moeda": moeda,
        "d_menos_1": cal.workday(base, -1),
        "casado": casado(primeiro, spot) if dolar and primeiro else None,
        "rolagem": rolagem(primeiro, segundo) if dolar and primeiro and segundo else None,
        "curvas": fontes["usadas"],
        "sem_di": moeda.modo == MODO_PRECO,
        "calendario": cal.nome,
        "grafico": servicos.grafico_ndf(pontos, spot),
    }


@bp.route("/api/ndf/spot")
def api_ndf_spot():
    """Spot da moeda escolhida, lido do vértice mais curto da curva de preço."""
    moeda = moeda_ndf(request.args.get("moeda"))
    data = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        valor = servicos.spot_da_curva(moeda, data)
    except b3.ErroB3 as exc:
        return jsonify({"erro": str(exc)}), 502
    return jsonify({
        "moeda": moeda.codigo, "par": moeda.par, "casas": moeda.casas,
        "spot": valor, "padrao": moeda.spot_padrao,
        "origem": moeda.curva_preco,
    })


@bp.route("/api/cambio")
def api_cambio():
    """Cotação de fechamento da moeda pedida, e o DOL só quando ela é o dólar.

    O botão da tela mandava buscar sempre a PTAX do dólar, o que enchia o campo
    de spot com 5,12 numa curva de euro e fazia as duas moedas desenharem a
    mesma coisa. Agora a moeda vem no pedido e manda no que é buscado.
    """
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    moeda = moeda_ndf(request.args.get("moeda"))

    if moeda.modo == MODO_MANUAL:
        return jsonify({"erro": "escolha uma moeda antes de buscar a cotação — "
                                "no modo de moeda livre o spot é digitado."}), 400

    # o cross não tem par contra o real: o spot dele é a paridade da moeda-base
    codigo_bcb = "EUR" if moeda.codigo == "EURUSD" else moeda.codigo
    try:
        base = para_data(data_txt)
        cotacao = cambio.ptax_moeda(codigo_bcb, base)
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": str(exc)}), 502

    if moeda.codigo == "EURUSD":
        spot, fonte = cotacao.contra_dolar, "Banco Central — paridade EUR/USD"
    else:
        spot, fonte = cotacao.venda, f"Banco Central — PTAX {codigo_bcb}"
    if spot is None:
        return jsonify({"erro": f"o BCB não publicou paridade de {codigo_bcb} "
                                f"em {cotacao.data:%d/%m/%Y}"}), 502

    resposta = {
        "moeda": moeda.codigo, "par": moeda.par, "casas": moeda.casas,
        "spot": spot, "spot_data": cotacao.data.isoformat(),
        "spot_compra": cotacao.compra, "spot_venda": cotacao.venda,
        "paridade": cotacao.contra_dolar,
        "futuros": [], "fonte_spot": fonte, "fonte_futuros": None,
    }

    # casado e rolagem são do pregão de dólar; as outras moedas não têm futuro na B3
    if moeda.codigo == "USD":
        try:
            ptx = servicos.curva("PTX", data_txt)
            futuros = cambio.futuros_dol(base, ptx, 2)
            resposta["futuros"] = [
                {"vencimento": f.vencimento.isoformat(), "pontos": f.preco,
                 "taxa": f.taxa, "dc": f.dias_corridos} for f in futuros]
            resposta["fonte_futuros"] = "B3 — curva PTX (dólar a termo)"
        except (ErroDeFonte, ValueError):
            pass                      # sem a curva, o spot sozinho já serve

    return jsonify(resposta)


# ------------------------------------------------------------- montador ----

def _montar_personalizado(form) -> dict:
    id_ativa = form.get("perna_ativa") or "pre_brl"
    id_passiva = form.get("perna_passiva") or "cdi"
    problema = montador.validar(id_ativa, id_passiva)
    if problema:
        raise servicos.ErroFormulario(problema)

    params = servicos.parametros_do_form(form)
    cal = obter_calendario(form.get("calendario") or "ANBIMA")
    data_curva = form.get("data_curva") or servicos.data_sugerida().isoformat()
    modo_cdi = form.get("modo_cdi") or SPREAD

    ativa, passiva = montador.POR_ID[id_ativa], montador.POR_ID[id_passiva]
    exigencias = set(ativa.exige) | set(passiva.exige)

    mercado = montador.Mercado(spot=servicos.numero_do_form(form, "spot", "spot", 5.0))
    if "di" in exigencias:
        mercado.di = servicos.curva("PRE", data_curva)
    if "cupom" in exigencias:
        mercado.cupom = servicos.curva("DOC", data_curva)
    if "ipca" in exigencias:
        mercado.ipca = servicos.curva("DIC", data_curva)
    if "sofr" in exigencias:
        precos = _numeros(form.get("sofr") or "", "preços dos futuros SOFR")
        term = _numeros(form.get("term_sofr") or "", "taxas Term SOFR") \
            if (form.get("term_sofr") or "").strip() else []
        mercado.sofr = servicos.curva_sofr_padrao(
            params.inicio, precos,
            {meses: taxa / 100.0 for meses, taxa in zip(TENORES_TERM, term)})

    extras = {"modo_cdi": modo_cdi}
    lado = form.get("resolver") or "passiva"

    def ler(campo: str, tipo) -> float:
        if tipo.id == "cdi" and modo_cdi == PERCENTUAL:
            bruto = servicos.numero_do_form(form, campo, tipo.parametro, 100.0)
            return bruto / 100.0 if bruto > 5 else bruto
        return servicos.taxa_do_form(form, campo, tipo.parametro, 0.0)

    valor_ativa = ler("valor_ativa", ativa)
    valor_passiva = ler("valor_passiva", passiva)

    resolvido = montador.resolver(params, mercado, id_ativa, valor_ativa,
                                  id_passiva, valor_passiva, lado,
                                  extras, extras, cal)
    if lado == "passiva":
        valor_passiva = resolvido
        tipo_resolvido = passiva
    else:
        valor_ativa = resolvido
        tipo_resolvido = ativa

    swap = montador.montar(params, mercado, id_ativa, valor_ativa, id_passiva,
                           valor_passiva, extras, extras, cal)

    percentual = tipo_resolvido.id == "cdi" and modo_cdi == PERCENTUAL
    curvas = [c for c in (mercado.di, mercado.cupom, mercado.ipca) if c is not None]
    return {
        "swap": swap,
        "solucao": {"rotulo": tipo_resolvido.parametro, "valor": resolvido,
                    "percentual": percentual, "lado": lado},
        "curvas": [{"nome": c.nome, "vertices": len(c.vertices),
                    "convencao": c.convencao, "metodo": c.metodo, "eixo": c.eixo,
                    "prazo_maximo": c.prazo_maximo} for c in curvas],
        "ativa": ativa, "passiva": passiva,
        "data_curva": data_curva, "calendario": cal.nome,
        "moeda": swap.moeda_referencia,
    }


# ------------------------------------------------------------- SOFR índice --

@bp.route("/sofr", methods=["GET", "POST"])
def sofr_indice():
    """SOFR realizado: composição do overnight com lookback e observation shift."""
    hoje = date.today()
    contexto = {
        "form": {
            "inicio": (hoje - timedelta(days=90)).isoformat(),
            "fim": hoje.isoformat(),
            "lookback": "0", "shift": "0",
        },
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _compor_sofr(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = str(exc)
    return render_template("sofr.html", **contexto)


def _compor_sofr(form) -> dict:
    inicio = para_data(form.get("inicio") or "")
    fim = para_data(form.get("fim") or "")
    lookback = int(servicos.numero_do_form(form, "lookback", "lookback", 0))
    shift = int(servicos.numero_do_form(form, "shift", "observation shift", 0))
    for nome, valor in (("lookback", lookback), ("observation shift", shift)):
        if valor < 0 or valor > 15:
            raise servicos.ErroFormulario(
                f"o {nome} tem que ficar entre 0 e 15 dias úteis")

    # margem para trás: lookback e shift buscam fixings antes do início
    margem = 40 + (lookback + shift) * 2
    fixings = sofr.serie_sofr(inicio - timedelta(days=margem), fim + timedelta(days=1))
    if not fixings:
        raise sofr.ErroFed("o NY Fed não devolveu fixings para esse intervalo")

    resultado = sofr.compor(fixings, inicio, fim, lookback, shift)

    conferencia = None
    try:
        indice = sofr.serie_indice(inicio - timedelta(days=5), fim + timedelta(days=1))
        taxa_indice = sofr.compor_por_indice(indice, inicio, fim)
        conferencia = {
            "taxa": taxa_indice,
            "diferenca_bp": (taxa_indice - resultado.taxa_composta) * 10000.0,
        }
    except (ErroDeFonte, ValueError):
        conferencia = None      # o índice não cobre a janela; segue sem conferência

    return {
        "r": resultado, "conferencia": conferencia,
        "convencao": sofr.convencao(lookback, shift),
        "ultimo_fixing": fixings[-1],
        "primeiro_fixing": fixings[0],
    }


# -------------------------------------------------------------- Term SOFR --

@bp.route("/term-sofr")
def term_sofr():
    """Estrutura a termo realizada do SOFR, com base histórica local."""
    hoje = date.today()
    referencia = para_data(request.args.get("referencia") or hoje.isoformat())
    meses = int(request.args.get("meses") or 6)

    contexto = {
        "historico": None, "erro": None, "tabela": {}, "campos": sofr.CAMPOS,
        "referencia": referencia, "meses": meses, "hoje": hoje.isoformat(),
        "vigente": None, "taxas_vigentes": {}, "base": None,
        "series": [], "escala_x": [], "escala_y": [],
    }
    try:
        completo = sofr.carregar_historico()
        if not completo.datas:
            raise sofr.ErroFed("a base local está vazia e o NY Fed não respondeu")
        vigente, taxas = completo.em(referencia)
        recorte = completo.janela(soma_meses(referencia, -meses), referencia)
        contexto.update({
            "historico": recorte, "tabela": recorte.por_data(),
            "vigente": vigente, "taxas_vigentes": taxas,
            "base": {"inicio": completo.inicio, "fim": completo.fim,
                     "dias": len(completo.datas)},
        })
        contexto.update(servicos.series_sofr(recorte))
    except sofr.ErroFed as exc:
        contexto["erro"] = str(exc)
    return render_template("term_sofr.html", **contexto)


@bp.route("/term-sofr/csv")
def term_sofr_csv():
    historico = sofr.HistoricoSOFR.da_base()
    if not historico.datas:
        return Response("base vazia", status=404, mimetype="text/plain; charset=utf-8")
    campos = historico.campos
    linhas = ["Data;" + ";".join(rotulo for c, rotulo in sofr.CAMPOS if c in campos)
              + ";SOFR Index"]
    tabela = historico.por_data()
    for d in historico.datas:
        linha = tabela[d]
        valores = [f"{linha[c] * 100:.5f}".replace(".", ",") if c in linha else ""
                   for c in campos]
        indice = f"{linha['indice']:.8f}".replace(".", ",") if "indice" in linha else ""
        linhas.append(f"{d:%d/%m/%Y};" + ";".join(valores) + f";{indice}")
    nome = f"sofr_{historico.inicio:%Y%m%d}_{historico.fim:%Y%m%d}.csv"
    return Response("\n".join(linhas) + "\n", content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/term-sofr/sincronizar", methods=["POST"])
def term_sofr_sincronizar():
    try:
        return jsonify(sofr.sincronizar(profundo=True))
    except sofr.ErroFed as exc:
        return jsonify({"erro": str(exc)}), 502


# ---------------------------------------------------------------- EURIBOR --

@bp.route("/euribor")
def euribor_diario():
    """EURIBOR diário: base histórica local, atualizada com a janela da fonte."""
    hoje = date.today()
    referencia = para_data(request.args.get("referencia") or hoje.isoformat())
    meses = int(request.args.get("meses") or 6)

    contexto = {
        "curva": None, "erro": None, "tabela": {}, "url_fonte": euribor.PAGINA,
        "series": [], "escala_x": [], "escala_y": [],
        "referencia": referencia, "meses": meses, "hoje": hoje.isoformat(),
        "vigente": None, "taxas_vigentes": {}, "base": None,
    }
    try:
        completa = euribor.carregar()
        if not completa.datas:
            raise euribor.ErroEuribor(
                "a base local está vazia e a fonte não respondeu — tente de novo em "
                "instantes")
        vigente, taxas = completa.em(referencia)
        recorte = completa.janela(soma_meses(referencia, -meses), referencia)
        contexto.update({
            "curva": recorte, "tabela": recorte.por_data(),
            "vigente": vigente, "taxas_vigentes": taxas,
            "base": {"inicio": completa.inicio, "fim": completa.fim,
                     "dias": len(completa.datas)},
        })
        contexto.update(servicos.series_euribor(recorte))
    except euribor.ErroEuribor as exc:
        contexto["erro"] = str(exc)
    return render_template("euribor.html", **contexto)


@bp.route("/euribor/sincronizar", methods=["POST"])
def euribor_sincronizar():
    """Puxa o histórico completo da fonte para a base local."""
    try:
        relatorio = euribor.sincronizar(profundo=True, passo=5)
    except euribor.ErroEuribor as exc:
        return jsonify({"erro": str(exc)}), 502
    return jsonify(relatorio)


@bp.route("/euribor/csv")
def euribor_csv():
    """Repassa a exportação da fonte, já limpa das colunas do gráfico."""
    try:
        curva = euribor.carregar()
    except euribor.ErroEuribor as exc:
        return Response(str(exc), status=502, mimetype="text/plain; charset=utf-8")
    linhas = ["Data;" + ";".join(curva.tenores)]
    tabela = curva.por_data()
    for d in curva.datas:
        valores = [f"{tabela[d][t] * 100:.3f}".replace(".", ",") if t in tabela[d] else ""
                   for t in curva.tenores]
        linhas.append(f"{d:%d/%m/%Y};" + ";".join(valores))
    nome = f"euribor_{curva.inicio:%Y%m%d}_{curva.fim:%Y%m%d}.csv"
    return Response("\n".join(linhas) + "\n", content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/api/euribor")
def api_euribor():
    try:
        curva = euribor.carregar()
    except euribor.ErroEuribor as exc:
        return jsonify({"erro": str(exc)}), 502
    tabela = curva.por_data()
    return jsonify({
        "fonte": euribor.PAGINA,
        "inicio": curva.inicio.isoformat(), "fim": curva.fim.isoformat(),
        "tenores": curva.tenores,
        "observacoes": [{"data": d.isoformat(),
                         "taxas": {t: tabela[d][t] for t in curva.tenores if t in tabela[d]}}
                        for d in curva.datas],
    })


# ------------------------------------------------------------- renda fixa --

@bp.route("/renda-fixa", methods=["GET", "POST"])
def calculadora_renda_fixa():
    hoje = date.today()
    contexto = {
        "form": {
            "valor": "1.000,00",
            "inicio": date(hoje.year, 1, 1).isoformat(),
            "vencimento": hoje.isoformat(),
            "produto": "cdb", "indexador": renda_fixa.CDI_REALIZADO,
            "taxa": "100", "cdi": "14", "ipca": "4,5", "arredondar_di": "",
        },
        "indexadores": renda_fixa.INDEXADORES,
        "produtos_rf": renda_fixa.PRODUTOS_RF,
        "retroativos": sorted(renda_fixa.RETROATIVOS),
        "hoje": hoje.isoformat(),
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _calcular_renda_fixa(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = str(exc)
    return render_template("renda_fixa.html", **contexto)


def _calcular_renda_fixa(form) -> dict:
    indexador = form.get("indexador") or renda_fixa.CDI_REALIZADO
    valor = servicos.numero_do_form(form, "valor", "valor aplicado")
    inicio = para_data(form.get("inicio") or "")
    vencimento = para_data(form.get("vencimento") or "")

    percentuais = (renda_fixa.CDI_PERCENTUAL, renda_fixa.CDI_REALIZADO)
    bruto_taxa = servicos.numero_do_form(form, "taxa", "taxa")
    if indexador in percentuais:
        taxa = bruto_taxa / 100.0 if bruto_taxa > 5 else bruto_taxa
    else:
        taxa = servicos.taxa_do_form(form, "taxa", "taxa")

    arredondar = str(form.get("arredondar_di") or "").lower() in ("1", "on", "true")
    acumulado = None
    fator_pronto = dias_uteis = None

    if indexador in renda_fixa.RETROATIVOS:
        # é acúmulo do que já aconteceu: a data final não passa de hoje
        if vencimento > date.today():
            raise servicos.ErroFormulario(
                "o CDI acumulado é o realizado, não uma projeção — a data final "
                f"não pode passar de hoje ({date.today():%d/%m/%Y})")
        acumulado = cdi.acumular_do_bcb(inicio, vencimento, percentual=taxa,
                                        valor=valor, arredondar=arredondar)
        fator_pronto, dias_uteis = acumulado.fator, acumulado.dias_uteis

    resultado = renda_fixa.calcular(
        valor=valor, inicio=inicio, vencimento=vencimento, indexador=indexador,
        taxa=taxa, cdi_projetado=servicos.taxa_do_form(form, "cdi", "CDI projetado", 0.0),
        ipca_projetado=servicos.taxa_do_form(form, "ipca", "IPCA projetado", 0.0),
        produto=form.get("produto") or "cdb", arredondar_di=arredondar,
        fator_pronto=fator_pronto, dias_uteis=dias_uteis,
    )

    comparacao = None
    if indexador == renda_fixa.CDI_REALIZADO and acumulado is not None:
        # o mesmo acúmulo com a outra regra de arredondamento, para comparar
        outro = cdi.acumular([cdi.FixingCDI(d.data, d.taxa) for d in acumulado.dias],
                             acumulado.inicio, acumulado.fim, percentual=taxa,
                             valor=valor, arredondar=not arredondar)
        cheio = acumulado if not arredondar else outro
        truncado = outro if not arredondar else acumulado
        comparacao = {
            "fator_sem_arredondar": cheio.fator,
            "fator_arredondado": truncado.fator,
            "diferenca_fator": cheio.fator - truncado.fator,
            "diferenca_reais": (cheio.fator - truncado.fator) * valor,
        }
    elif indexador in (renda_fixa.CDI_PERCENTUAL, renda_fixa.CDI_SPREAD):
        comparacao = renda_fixa.diferenca_arredondamento(
            servicos.taxa_do_form(form, "cdi", "CDI projetado", 0.0),
            resultado.dias_uteis,
            taxa if indexador == renda_fixa.CDI_PERCENTUAL else 1.0,
            valor=valor)

    return {"r": resultado, "comparacao": comparacao, "indexador": indexador,
            "acumulado": acumulado}


# -------------------------------------------------------------- metodologia

@bp.route("/metodologia")
def metodologia():
    return render_template("metodologia.html", curvas=b3.CURVAS_COMPLETAS,
                           fontes=fontes.por_grupo(), glossario=glossario.por_grupo(),
                           rede=rede.diagnostico())


@bp.route("/ni-pro-rata", methods=["GET", "POST"])
def ni_pro_rata():
    contexto = {"resultado": None, "erro": None,
                "form": {"ni_anterior": "7545.53", "projecao": "0.68",
                         "data": servicos.data_sugerida().isoformat(),
                         "vne": "1000", "ni_partida": "7545.53"}}
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            ni = NumeroIndice(
                ni_anterior=servicos.numero_do_form(request.form, "ni_anterior", "NIk-1"),
                projecao_mensal=servicos.numero_do_form(
                    request.form, "projecao", "projeção mensal") / 100.0,
                data_referencia=para_data(request.form.get("data")),
            )
            vne = servicos.numero_do_form(request.form, "vne", "VNE")
            ni_partida = servicos.numero_do_form(request.form, "ni_partida", "NI de partida")
            contexto["resultado"] = {
                "data_base": ni.data_base, "proxima_base": ni.proxima_base,
                "ni_cheio": ni.ni_cheio, "ni_atual": ni.ni_pro_rata(),
                "correcao": ni.ni_pro_rata() / ni_partida,
                "vna": ni.vna(vne, ni_partida),
                "dup": calendario_anbima().dias_uteis(ni.data_base, ni.data_referencia),
                "dut": calendario_anbima().dias_uteis(ni.data_base, ni.proxima_base),
            }
        except (ValueError, servicos.ErroFormulario, ErroDeFonte) as exc:
            contexto["erro"] = str(exc)
    return render_template("ni_pro_rata.html", **contexto)
