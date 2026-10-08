"""Rotas da aplicação."""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from flask import (Blueprint, Response, jsonify, redirect, render_template,
                   request, url_for)

from precificador import (anbima, anbima_datasets, b3, cambio, cdi, contagem,
                          cotacoes, euribor,
                          fontes, glossario, inflacao_implicita, ipca, liquidacao,
                          montador, opcoes_fx, rede, renda_fixa, sofr,
                          term_sofr as term)
from precificador.calendario import (CALENDARIOS_DISPONIVEIS, CONVENCOES_DIA_UTIL,
                                     MODIFIED_FOLLOWING, calendario_anbima,
                                     obter_calendario, para_data, soma_meses)
from precificador.curvas import TENORES_TERM
from precificador.instrumentos import (BULLET, LINEAR, PERCENTUAL,
                                       PERSONALIZADA, SPREAD, STRING, VANILLA)
from precificador.interpolacao import METODOS, interpolar
from precificador.erros import ErroDeDado, ErroDeFonte
from precificador.produtos import (DIRECOES, MOEDAS_NDF, MODO_MANUAL, MODO_PRECO,
                                   PROGRESSOES, SAIDA, NumeroIndice, casado,
                                   curva_ndf, moeda_ndf, escada_datas, rolagem,
                                   sinal_do_casado, spot_com_casado)
from precificador.solver import SemConvergencia

from . import idiomas, servicos

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
            contexto["erro"] = idiomas.mensagem(exc)
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
        return Response(idiomas.mensagem(exc), status=404, mimetype="text/plain; charset=utf-8")
    nome = f"curva_{codigo}_{para_data(data_txt):%Y%m%d}.csv"
    return Response(servicos.csv_da_curva(obj), content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/api/curvas/<codigo>")
def api_curva(codigo: str):
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        return jsonify(servicos.curva(codigo, data_txt).para_dict())
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": idiomas.mensagem(exc)}), 404


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
        return jsonify({"erro": idiomas.mensagem(exc)}), 400


# ------------------------------------------------------------- interpolação

@bp.route("/interpolar", methods=["GET", "POST"])
def interpolador():
    """Interpola uma curva em datas: o prazo em dias sai da data-base."""
    base_padrao = servicos.data_sugerida()
    contexto = {"metodos": list(METODOS), "resultado": None, "erro": None,
                "x_txt": "", "y_txt": "", "metodo": "spline",
                "extrapolar": "flat", "curvas_disponiveis": b3.CURVAS_COMPLETAS,
                "curva": "PRE", "data_base": base_padrao.isoformat(),
                "datas": [soma_meses(base_padrao, 6).isoformat()]}
    if request.method == "POST":
        contexto.update({
            "x_txt": request.form.get("x", ""),
            "y_txt": request.form.get("y", ""),
            "metodo": request.form.get("metodo", "spline"),
            "extrapolar": request.form.get("extrapolar", "flat"),
            # a curva escolhida fica escolhida depois do POST
            "curva": request.form.get("curva") or "PRE",
            "data_base": request.form.get("data_base") or base_padrao.isoformat(),
            "datas": [d for d in request.form.getlist("datas") if d.strip()] or [""],
        })
        try:
            xs = _numeros(contexto["x_txt"], "eixo x")
            ys = _numeros(contexto["y_txt"], "eixo y")
            if len(xs) != len(ys):
                raise ValueError(f"o eixo x tem {len(xs)} pontos e o y tem {len(ys)}")
            if len(xs) < 2:
                raise ValueError("são necessários pelo menos dois pontos")
            base = para_data(contexto["data_base"])
            datas = [para_data(d) for d in contexto["datas"] if d]
            if not datas:
                raise servicos.ErroFormulario("informe pelo menos uma data a interpolar")
            cal = calendario_anbima()
            linhas = []
            for data in datas:
                # o eixo x da B3 é em dias corridos a partir da data-base
                alvo = (data - base).days
                if alvo <= 0:
                    raise servicos.ErroFormulario(
                        "a data {data} não é posterior à data-base", data=data.strftime("%d/%m/%Y"))
                valor = interpolar(xs, ys, alvo, metodo=contexto["metodo"],
                                   **({} if contexto["metodo"] == "flat_forward"
                                      else {"extrapolar": contexto["extrapolar"]}))
                linhas.append({"data": data, "x": alvo, "du": cal.dias_uteis(base, data),
                               "y": valor, "fora": alvo < min(xs) or alvo > max(xs)})
            contexto["resultado"] = {"linhas": linhas, "n": len(xs),
                                     "dominio": (min(xs), max(xs))}
        except ValueError as exc:
            contexto["erro"] = idiomas.mensagem(exc)
    return render_template("interpolar.html", **contexto)


@bp.route("/interpolar/carregar")
def interpolar_carregar():
    """Devolve os vértices de uma curva da B3 já no formato do formulário."""
    codigo = (request.args.get("curva") or "PRE").upper()
    data_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        obj = servicos.curva(codigo, data_txt)
    except (ErroDeFonte, ValueError) as exc:
        return jsonify({"erro": idiomas.mensagem(exc)}), 404
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
            contexto["erro"] = idiomas.mensagem(exc)

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
        # resolve a ativa por padrão: dado CDI flat, que taxa pré zera o MtM
        "perna_ativa": "pre_brl", "valor_ativa": "",
        "perna_passiva": "cdi", "valor_passiva": "0",
        "modo_cdi": SPREAD, "estrutura_cdi": VANILLA, "resolver": "ativa",
        "spot": "5,15",
        "sofr": ", ".join(str(preco) for preco in SOFR_PADRAO),
        "term_sofr": "3,64637, 3,65811, 3,67358, 3,73148",
    }
    if template:
        padrao.update({
            "perna_ativa": template.ativa, "perna_passiva": template.passiva,
            "valor_ativa": template.valor_ativa,
            "valor_passiva": template.valor_passiva,
            "modo_cdi": template.modo_cdi,
            "estrutura_cdi": template.estrutura_cdi,
            "resolver": template.resolver,
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
        "direcoes": DIRECOES,
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _montar_ndf(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = idiomas.mensagem(exc)
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

    # casado e rolagem são do pregão de dólar: não existem para as outras moedas
    dolar = moeda.codigo == "USD"
    primeiro = servicos.numero_do_form(form, "primeiro_futuro", "1º futuro", 0.0)
    segundo = servicos.numero_do_form(form, "segundo_futuro", "2º futuro", 0.0)
    valor_casado = casado(primeiro, spot) if dolar and primeiro else None

    # o casado entra no preço com o sinal do fluxo, então ele é calculado antes
    # da curva: quem precifica é o spot já ajustado, não o spot digitado
    direcao = form.get("direcao") or SAIDA
    spot_efetivo = spot_com_casado(spot, valor_casado, direcao)

    pontos = curva_ndf(base, spot_efetivo, fontes["di"], fontes["cupom"], datas,
                       cal, fontes["preco"], moeda, estrangeira)
    if not pontos:
        raise servicos.ErroFormulario("nenhum vencimento posterior à data-base")

    return {
        "base": base, "spot": spot, "spot_efetivo": spot_efetivo,
        "pontos": pontos, "moeda": moeda,
        "d_menos_1": cal.workday(base, -1),
        "casado": valor_casado,
        "casado_com_sinal": (valor_casado * sinal_do_casado(direcao)
                             if valor_casado is not None else None),
        "direcao": direcao, "sinal": sinal_do_casado(direcao),
        "ajustado": valor_casado is not None and spot_efetivo != spot,
        "rolagem": rolagem(primeiro, segundo) if dolar and primeiro and segundo else None,
        "curvas": fontes["usadas"],
        "sem_di": moeda.modo == MODO_PRECO,
        "calendario": cal.nome,
        "grafico": servicos.grafico_ndf(pontos, spot_efetivo),
    }


@bp.route("/api/ndf/spot")
def api_ndf_spot():
    """Spot da moeda escolhida, lido do vértice mais curto da curva de preço."""
    moeda = moeda_ndf(request.args.get("moeda"))
    data = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        valor = servicos.spot_da_curva(moeda, data)
    except b3.ErroB3 as exc:
        return jsonify({"erro": idiomas.mensagem(exc)}), 502
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
        return jsonify({"erro": idiomas.mensagem(exc)}), 502

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

    # vanilla ou string só se pergunta num IPCA+ contra CDI
    ipca_cdi = {id_ativa, id_passiva} == {"ipca", "cdi"}
    estrutura = (form.get("estrutura_cdi") or VANILLA) if ipca_cdi else VANILLA
    extras = {"modo_cdi": modo_cdi, "estrutura_cdi": estrutura}
    lado = form.get("resolver") or "ativa"

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

    # As duas estruturas lado a lado: a mesma pergunta resolvida no vanilla e
    # no string. A diferença é o que o cliente ganha (ou paga) por quebrar o swap.
    comparacao = None
    if ipca_cdi:
        outra = VANILLA if estrutura == STRING else STRING
        outros = {"modo_cdi": modo_cdi, "estrutura_cdi": outra}
        # o valor da ponta resolvida é ignorado pelo resolver, que varia ele
        a_outra = montador.resolver(params, mercado, id_ativa, valor_ativa,
                                    id_passiva, valor_passiva, lado,
                                    outros, outros, cal)
        valores = {estrutura: resolvido, outra: a_outra}
        perna_cdi = swap.passiva if id_passiva == "cdi" else swap.ativa
        comparacao = {
            "vanilla": valores[VANILLA], "string": valores[STRING],
            "estrutura": estrutura,
            "soma_principais": (sum(f.amortizacao for f in perna_cdi.fluxos)
                                if estrutura == STRING else None),
            "nocional": params.nocional,
        }

    return {
        "comparacao": comparacao,
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
            contexto["erro"] = idiomas.mensagem(exc)
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
    # a referência é a mesma de toda a aplicação; `hoje` fica só como teto do campo
    referencia = para_data(request.args.get("referencia")
                           or servicos.data_sugerida().isoformat())
    meses = int(request.args.get("meses") or 6)

    contexto = {
        "historico": None, "erro": None, "tabela": {}, "campos": sofr.CAMPOS,
        "referencia": referencia, "meses": meses, "hoje": hoje.isoformat(),
        "vigente": None, "taxas_vigentes": {}, "base": None,
        "series": [], "escala_x": [], "escala_y": [],
        # a curva a termo da CME é importada, não baixada — ver a rota abaixo
        "termo": _termo_importado(referencia, meses),
        "campos_termo": term.CAMPOS,
        "importacao": request.args.get("importado"),
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
        contexto["erro"] = idiomas.mensagem(exc)
    return render_template("term_sofr.html", **contexto)


def _termo_importado(referencia, meses: int) -> dict:
    """A curva a termo da CME que o usuário importou, se importou.

    Ela não desce de fonte nenhuma: é licenciada, e quem tem a licença traz o
    arquivo. Base vazia não é erro — é o estado normal de quem ainda não
    importou, e a tela mostra a área de arrastar em vez de um aviso.
    """
    base = term.carregar()
    if base.vazio:
        return {"vazio": True}
    vigente, taxas = base.em(referencia)
    recorte = base.janela(soma_meses(para_data(referencia), -meses), referencia)
    return {
        "vazio": False, "vigente": vigente, "taxas": taxas,
        "tabela": recorte.por_data(), "datas": recorte.datas,
        "campos": recorte.campos,
        "base": {"inicio": base.inicio, "fim": base.fim, "dias": len(base.datas)},
    }


@bp.route("/term-sofr/importar", methods=["POST"])
def term_sofr_importar():
    """Recebe o relatório da B3 e guarda as cotações de Term SOFR."""
    arquivo = request.files.get("arquivo")
    if arquivo is None or not (arquivo.filename or "").strip():
        return jsonify({"erro": "nenhum arquivo enviado"}), 400
    try:
        resultado = term.importar(arquivo.filename, arquivo.read())
    except (term.ErroTermSOFR, ValueError) as exc:
        return jsonify({"erro": idiomas.mensagem(exc)}), 422

    return jsonify({
        "ok": True,
        "arquivo": arquivo.filename,
        "linhas_lidas": resultado.linhas_lidas,
        "aproveitadas": resultado.aproveitadas,
        "novas": resultado.novas,
        "atualizadas": resultado.atualizadas,
        "inicio": resultado.inicio.isoformat() if resultado.inicio else None,
        "fim": resultado.fim.isoformat() if resultado.fim else None,
        "tickers": resultado.tickers,
        "ignorados": resultado.ignorados,
    })


@bp.route("/api/term-sofr/taxa")
def api_term_sofr_taxa():
    """A taxa importada de um prazo numa data — para a tela de liquidação.

    É o que tira o Term SOFR da digitação: quem importou o arquivo não precisa
    copiar o número de volta na mão.
    """
    base = term.carregar()
    if base.vazio:
        return jsonify({"erro": "nenhuma cotação de Term SOFR importada"}), 404
    try:
        meses = int(request.args.get("meses") or 3)
    except ValueError:
        return jsonify({"erro": "prazo inválido"}), 400
    quando = request.args.get("data") or date.today().isoformat()
    vigente, _ = base.em(quando)
    taxa = base.taxa(meses, quando)
    if taxa is None:
        return jsonify({"erro": f"não há Term SOFR de {meses} meses até "
                                f"{para_data(quando):%d/%m/%Y}"}), 404
    return jsonify({"taxa": taxa, "percentual": taxa * 100.0,
                    "data": vigente.isoformat() if vigente else None,
                    "meses": meses})


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
        return jsonify({"erro": idiomas.mensagem(exc)}), 502


# ---------------------------------------------------------------- EURIBOR --

@bp.route("/euribor")
def euribor_diario():
    """EURIBOR diário: base histórica local, atualizada com a janela da fonte."""
    hoje = date.today()
    # a referência é a mesma de toda a aplicação; `hoje` fica só como teto do campo
    referencia = para_data(request.args.get("referencia")
                           or servicos.data_sugerida().isoformat())
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
        contexto["erro"] = idiomas.mensagem(exc)
    return render_template("euribor.html", **contexto)


@bp.route("/euribor/sincronizar", methods=["POST"])
def euribor_sincronizar():
    """Puxa o histórico completo da fonte para a base local."""
    try:
        relatorio = euribor.sincronizar(profundo=True, passo=5)
    except euribor.ErroEuribor as exc:
        return jsonify({"erro": idiomas.mensagem(exc)}), 502
    return jsonify(relatorio)


@bp.route("/euribor/csv")
def euribor_csv():
    """Repassa a exportação da fonte, já limpa das colunas do gráfico."""
    try:
        curva = euribor.carregar()
    except euribor.ErroEuribor as exc:
        return Response(idiomas.mensagem(exc), status=502, mimetype="text/plain; charset=utf-8")
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
        return jsonify({"erro": idiomas.mensagem(exc)}), 502
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
            contexto["erro"] = idiomas.mensagem(exc)
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


# ----------------------------------------------------------------- cotações

@bp.route("/cotacoes", methods=["GET", "POST"])
def cotacoes_pagina():
    """Histórico de PTAX, ações e commodities — porte da tela Quotes."""
    hoje = date.today()
    contexto = {
        "form": {
            "tipo": cotacoes.PTAX, "instrumento": "USD",
            # um mês para trás: quem abre a tela quer o histórico recente,
            # não dois campos de data em branco
            "inicio": (hoje - timedelta(days=30)).isoformat(),
            "fim": hoje.isoformat(),
        },
        "tipos": cotacoes.TIPOS,
        # o catálogo inteiro — famílias de vencimento inclusive — viaja para a
        # busca da tela: são ~500 itens, e uma ida ao servidor a cada tecla
        # deixaria a lista piscando enquanto ela não volta
        "catalogos": {t: cotacoes.catalogo(t) for t, *_ in cotacoes.TIPOS},
        "hoje": hoje.isoformat(),
        "resultado": None, "erro": None,
    }
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _buscar_cotacoes(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = idiomas.mensagem(exc)
    return render_template("cotacoes.html", **contexto)


def _buscar_cotacoes(form) -> dict:
    tipo = form.get("tipo") or cotacoes.PTAX
    instrumento = (form.get("instrumento") or "").strip()
    if not instrumento:
        raise servicos.ErroFormulario("escolha o instrumento")
    saida = cotacoes.historico(tipo, instrumento, form.get("inicio") or "",
                               form.get("fim") or "")
    saida["tipo"] = tipo
    saida["instrumento"] = instrumento
    saida["nome_do_tipo"] = cotacoes.TIPO_POR_CODIGO.get(tipo, (tipo, ""))[0]
    return saida


@bp.route("/cotacoes/csv")
def cotacoes_csv():
    """A mesma tabela em CSV — quem confere contra a planilha não redigita."""
    tipo = request.args.get("tipo") or cotacoes.PTAX
    instrumento = (request.args.get("instrumento") or "").strip()
    try:
        dados = cotacoes.historico(tipo, instrumento, request.args.get("inicio") or "",
                                   request.args.get("fim") or "")
    except (ErroDeFonte, ValueError) as exc:
        return Response(idiomas.mensagem(exc), status=404, mimetype="text/plain; charset=utf-8")

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(dados["colunas"])
    escritor.writerows(dados["linhas"])
    nome = f"cotacoes_{dados['simbolo'].replace('=', '').replace('.', '_')}.csv"
    return Response(buffer.getvalue(), content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/api/cotacoes/simbolo")
def api_simbolo():
    """O símbolo de um código digitado — ``BOF6`` → ``ZLF26.CBT``.

    A busca da tela pergunta aqui em vez de resolver sozinha: a regra das
    famílias (miolo tem de ser mês+ano, prefixo mais longo vence, ano de dois
    dígitos) mora no pacote, e uma cópia em JavaScript seria uma segunda verdade
    para a mesma pergunta. Código sem correspondência volta com símbolo vazio.
    """
    tipo = request.args.get("tipo") or ""
    if tipo not in dict((t, n) for t, n, _ in cotacoes.TIPOS):
        return jsonify({"erro": f"tipo desconhecido: {tipo}"}), 404
    codigo = request.args.get("codigo") or ""
    simbolo = codigo.strip().upper() if tipo == cotacoes.PTAX else cotacoes.simbolo_de(tipo, codigo)
    return jsonify({"codigo": codigo, "simbolo": simbolo or ""})


@bp.route("/api/cotacoes/instrumentos/<tipo>")
def api_instrumentos(tipo: str):
    """Os instrumentos de um tipo, para a tela trocar a lista sem recarregar."""
    if tipo not in dict((t, n) for t, n, _ in cotacoes.TIPOS):
        return jsonify({"erro": f"tipo desconhecido: {tipo}"}), 404
    return jsonify({"instrumentos": cotacoes.instrumentos(tipo)})


# --------------------------------------------------- inflação implícita ---

@bp.route("/inflacao-implicita")
def inflacao_implicita_pagina():
    """Boletim de títulos públicos da ANBIMA e a inflação implícita das NTN-B.

    A data é a do boletim — o mesmo "Consultar" da página da ANBIMA. Cada fonte
    falha sozinha: sem a curva DI da B3, a tela continua com o boletim e com a
    coluna contra o CDI; sem o CDI, continua com a curva. Só a falta do
    boletim derruba a página, porque sem ele não há juro real para comparar.
    """
    referencia_txt = request.args.get("data") or servicos.data_sugerida().isoformat()
    contexto = {
        "form": {"data": referencia_txt}, "hoje": date.today().isoformat(),
        "tipos": anbima.TIPOS, "grupos": {}, "linhas": [], "avisos": [],
        "erro": None, "referencia": None, "vna": None, "cdi": None,
        "curva_data": None, "pagina_anbima": anbima.PAGINA,
        "series": [], "escala_x": [], "escala_y": [],
    }
    try:
        referencia = para_data(referencia_txt)
        titulos = anbima.baixar(referencia)
    except (ErroDeFonte, ValueError) as exc:
        contexto["erro"] = idiomas.mensagem(exc)
        return render_template("inflacao_implicita.html", **contexto)

    taxa_pre = None
    try:
        curva = servicos.curva("PRE", referencia.isoformat())
        taxa_pre, contexto["curva_data"] = curva.taxa_para, referencia
    except (ErroDeFonte, ValueError) as exc:
        contexto["avisos"].append(idiomas.mensagem(exc))

    cdi_do_dia = None
    try:
        fixings = [f for f in cdi.serie(referencia - timedelta(days=10), referencia)
                   if f.data <= referencia]
        if fixings:
            cdi_do_dia = fixings[-1].taxa
    except (ErroDeFonte, ValueError) as exc:
        contexto["avisos"].append(idiomas.mensagem(exc))

    linhas = inflacao_implicita.calcular(titulos, taxa_pre=taxa_pre, cdi=cdi_do_dia)
    vna, _ = inflacao_implicita.vna_do_dia(linhas)
    cores = servicos.CORES_IMPLICITA
    contexto.update({
        "referencia": referencia, "grupos": anbima.por_tipo(titulos),
        "linhas": linhas, "vna": vna, "cdi": cdi_do_dia})
    contexto.update(servicos.series_xy([
        {"rotulo": "Pré DI no prazo", "cor": cores["pre"],
         "pontos": [(l.duration_anos, l.pre) for l in linhas if l.pre is not None]},
        {"rotulo": "Juro real NTN-B", "cor": cores["real"],
         "pontos": [(l.duration_anos, l.juro_real) for l in linhas]},
        {"rotulo": "Inflação implícita", "cor": cores["implicita"],
         "pontos": [(l.duration_anos, l.implicita) for l in linhas
                    if l.implicita is not None]},
    ]))
    return render_template("inflacao_implicita.html", **contexto)


# ------------------------------------------------------ ANBIMA datasets ---

LIMITE_DE_LINHAS = 2000        # o que a tela desenha; o CSV leva tudo


def _filtrar(tabela, termo: str):
    termo = (termo or "").strip().upper()
    if not termo:
        return tabela.linhas
    return [l for l in tabela.linhas if termo in " ".join(l).upper()]


@bp.route("/anbima-datasets")
def anbima_datasets_pagina():
    """Os datasets do ANBIMA Data, cada um pela porta que tem, salvos localmente.

    ``data`` consulta um dataset diário (e salva); ``ver`` abre uma data já
    salva, sem rede. Sem nenhum dos dois, a tela abre sem buscar: o arquivo de
    fundos tem 8 MB, e baixá-lo a cada visita seria pagar por uma consulta que
    ninguém pediu.
    """
    slug = request.args.get("dataset") or anbima_datasets.DISPONIVEIS[0].slug
    contexto = {
        "form": {"dataset": slug, "data": request.args.get("data")
                 or servicos.data_sugerida().isoformat(),
                 "filtro": request.args.get("filtro") or ""},
        "hoje": date.today().isoformat(), "catalogo": anbima_datasets.CATALOGO,
        "pagina_datasets": anbima_datasets.PAGINA_DATASETS,
        "dataset": None, "salvos": [], "publicado": None, "tabela": None,
        "linhas": [], "total_filtrado": 0, "limite": LIMITE_DE_LINHAS,
        "erro": request.args.get("erro"), "aviso": request.args.get("aviso"),
    }
    try:
        ds = anbima_datasets.dataset(slug)
        contexto["dataset"] = ds
        if request.args.get("ver"):
            contexto["tabela"] = anbima_datasets.abrir(slug, para_data(request.args["ver"]))
        elif request.args.get("data") and ds.fonte == anbima_datasets.DIARIO:
            contexto["tabela"] = anbima_datasets.baixar(slug, para_data(request.args["data"]))
        if ds.fonte == anbima_datasets.CMS_PUBLICO:
            contexto["publicado"] = anbima_datasets.versao_publicada(slug)
    except (ErroDeFonte, ValueError) as exc:
        contexto["erro"] = idiomas.mensagem(exc)
    if contexto["dataset"]:
        contexto["salvos"] = anbima_datasets.salvos(slug)
    if contexto["tabela"]:
        filtradas = _filtrar(contexto["tabela"], contexto["form"]["filtro"])
        contexto["total_filtrado"] = len(filtradas)
        contexto["linhas"] = filtradas[:LIMITE_DE_LINHAS]
    return render_template("anbima_datasets.html", **contexto)


def _voltar(slug: str, **extra):
    return redirect(url_for("principal.anbima_datasets_pagina", dataset=slug, **extra))


@bp.route("/anbima-datasets/publicado", methods=["POST"])
def anbima_datasets_publicado():
    """Baixa a versão que o ANBIMA Data publicou e salva — porta CMS."""
    slug = request.form.get("dataset") or ""
    try:
        salvo = anbima_datasets.baixar_publicado(slug)
    except (ErroDeFonte, ValueError) as exc:
        return _voltar(slug, erro=idiomas.mensagem(exc))
    return _voltar(slug, ver=salvo.referencia.isoformat())


@bp.route("/anbima-datasets/importar", methods=["POST"])
def anbima_datasets_importar():
    """O arquivo que a pessoa baixou no ANBIMA Data — porta IMPORTACAO."""
    slug = request.form.get("dataset") or ""
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        return _voltar(slug, erro=idiomas.mensagem(
            servicos.ErroFormulario("escolha o arquivo baixado do ANBIMA Data")))
    data_txt = (request.form.get("data") or "").strip()
    try:
        salvos = anbima_datasets.importar(slug, para_data(data_txt) if data_txt else None,
                                          arquivo.filename, arquivo.read())
    except (ErroDeFonte, ValueError) as exc:
        return _voltar(slug, erro=idiomas.mensagem(exc))
    # abre na data mais recente e diz quantas entraram: um arquivo de cinco dias
    # que mostrasse só um faria parecer que os outros quatro se perderam
    datas = ", ".join(f"{s.referencia:%d/%m/%Y}" for s in salvos)
    aviso = idiomas.mensagem(anbima_datasets.ErroDataset(
        "{n} data(s) importada(s) e salva(s): {datas}", n=len(salvos), datas=datas))
    return _voltar(slug, ver=salvos[-1].referencia.isoformat(), aviso=aviso)


@bp.route("/anbima-datasets/csv")
def anbima_datasets_csv():
    """CSV da data — da base local quando já salva, da ANBIMA quando diário."""
    slug = request.args.get("dataset") or ""
    referencia = request.args.get("data") or servicos.data_sugerida().isoformat()
    try:
        try:
            tabela = anbima_datasets.abrir(slug, para_data(referencia))
        except anbima_datasets.ErroDataset:
            tabela = anbima_datasets.baixar(slug, para_data(referencia))
    except (ErroDeFonte, ValueError) as exc:
        return Response(idiomas.mensagem(exc), status=404, mimetype="text/plain")
    nome = f"{slug}_{tabela.referencia:%Y%m%d}.csv"
    # BOM: sem ele o Excel abre o UTF-8 como latin-1 e estraga os acentos
    return Response("\ufeff" + anbima_datasets.para_csv(tabela), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


# --------------------------------------------------------------- liquidação

def _fixing_padrao(inicio: str, indexador: str = "") -> str:
    """A data de fixing que o motor usaria: D-2 dias úteis do início do fluxo.

    A tela mostra o padrão em vez de deixar o campo em branco. Quem confere uma
    liquidação precisa **ver** de que dia a taxa a termo saiu: num fim de
    trimestre, D-2 e D-1 estão a vários pontos-base de distância, e um campo
    vazio esconde a escolha em vez de declará-la.

    O dia útil sai do calendário do **índice** — SOFR no Term SOFR, TARGET2 na
    EURIBOR —, que é o mesmo que o motor usa. Por isso cada ponta tem o seu
    padrão: num feriado americano que não é europeu, as duas datas diferem.

    Volta vazio quando a data não dá pé; a tela então deixa o campo em branco e
    o motor decide, que é como era antes.
    """
    try:
        return liquidacao.data_de_fixing(para_data(inicio),
                                         indexador=indexador).isoformat()
    except (ValueError, TypeError, ErroDeDado):
        return ""


@bp.route("/liquidacao", methods=["GET", "POST"])
def liquidacao_swap():
    """Valor de liquidação de um swap — o ajuste que uma parte paga à outra."""
    hoje = date.today()
    ano_passado = date(hoje.year - 1, hoje.month, 1)
    contexto = {
        "form": {
            "data_operacao": ano_passado.isoformat(),
            "inicio": ano_passado.isoformat(), "fim": hoje.isoformat(),
            "vencimento": "", "base_ajuste": liquidacao.BASE_AUTOMATICA,
            "nocional": "10.000.000,00", "nocional_original": "10.000.000,00",
            "amortizacao": "0", "base_amortizacao": liquidacao.SOBRE_ORIGINAL,
            "calendario": "ANBIMA", "arredondar_di": "", "reter_ir": "1",
        },
        "indexadores": liquidacao.INDEXADORES,
        "convencoes": contagem.CONVENCOES,
        "regimes": contagem.REGIMES,
        "moedas": liquidacao.MOEDAS,
        "bases_amortizacao": liquidacao.BASES_AMORTIZACAO,
        "bases_ajuste": liquidacao.BASES_DE_AJUSTE,
        "convencao_padrao": {codigo: list(liquidacao.convencao_padrao(codigo))
                             for codigo, _ in liquidacao.INDEXADORES},
        "tenores_euribor": liquidacao.TENORES_EURIBOR,
        "calendarios": CALENDARIOS,
        "fixings_ipca": ipca.FIXINGS,
        "hoje": hoje.isoformat(),
        # um padrão por ponta: o calendário é o do índice de cada uma
        "fixings_padrao": {},
        "resultado": None, "erro": None,
    }
    # cada ponta repete os mesmos campos com o seu prefixo
    padrao = {
        "ativa": dict(indexador=liquidacao.PRE, taxa="14"),
        "passiva": dict(indexador=liquidacao.CDI, taxa="0", percentual="100"),
    }
    for lado, escolhas in padrao.items():
        convencao, regime = liquidacao.convencao_padrao(escolhas["indexador"])
        contexto["form"].update({
            f"{lado}_indexador": escolhas["indexador"], f"{lado}_taxa": escolhas["taxa"],
            f"{lado}_percentual": escolhas.get("percentual", "100"),
            f"{lado}_convencao": convencao, f"{lado}_regime": regime,
            f"{lado}_moeda": liquidacao.SEM_CONVERSAO,
            f"{lado}_ptax_inicial": "", f"{lado}_ptax_final": "",
            f"{lado}_ptax_offset": "1", f"{lado}_multiplicador": "",
            f"{lado}_ni_inicial": "", f"{lado}_ni_final": "", f"{lado}_fator": "",
            f"{lado}_ipca_fixing": ipca.DIGITADO,
            f"{lado}_tenor": "3 month",
            f"{lado}_data_fixing": _fixing_padrao(contexto["form"]["inicio"],
                                                  escolhas["indexador"]),
            f"{lado}_taxa_indice": "", f"{lado}_lookback": "0", f"{lado}_shift": "0",
            f"{lado}_ativo": "", f"{lado}_preco_inicial": "", f"{lado}_preco_final": "",
        })

    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _liquidar(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ValueError) as exc:
            contexto["erro"] = idiomas.mensagem(exc)

    # recalculado depois do formulário: é por ele que o script sabe se a data
    # no campo ainda é a automática ou se alguém digitou a dela
    contexto["fixings_padrao"] = {
        lado: _fixing_padrao(contexto["form"].get("inicio") or "",
                             contexto["form"].get(f"{lado}_indexador") or "")
        for lado in ("ativa", "passiva")}
    return render_template("liquidacao.html", **contexto)


def _ponta_do_form(form, prefixo: str) -> liquidacao.Ponta:
    """Lê uma das duas pontas — só os campos que o indexador escolhido usa."""
    def campo(nome: str) -> str:
        return f"{prefixo}_{nome}"

    def texto(nome: str) -> str:
        return (form.get(campo(nome)) or "").strip()

    def opcional(nome: str, rotulo: str):
        return servicos.numero_do_form(form, campo(nome), rotulo) if texto(nome) else None

    indexador = form.get(campo("indexador")) or liquidacao.PRE
    lado = "ativa" if prefixo == "ativa" else "passiva"
    taxa = 0.0
    if indexador != liquidacao.FATOR:
        taxa = servicos.taxa_do_form(form, campo("taxa"), f"taxa da ponta {lado}", 0.0)
    return liquidacao.Ponta(
        indexador=indexador, taxa=taxa,
        convencao=form.get(campo("convencao")) or contagem.DU_252,
        regime=form.get(campo("regime")) or contagem.COMPOSTO,
        moeda=form.get(campo("moeda")) or liquidacao.SEM_CONVERSAO,
        ptax_inicial=opcional("ptax_inicial", f"fixing inicial da ponta {lado}"),
        ptax_final=opcional("ptax_final", f"fixing final da ponta {lado}"),
        ni_inicial=opcional("ni_inicial", f"número-índice inicial da ponta {lado}"),
        ni_final=opcional("ni_final", f"número-índice final da ponta {lado}"),
        ipca_fixing=form.get(campo("ipca_fixing")) or ipca.DIGITADO,
        ptax_offset=int(texto("ptax_offset") or 1),
        multiplicador=(opcional("multiplicador", f"multiplicador da ponta {lado}")
                       if texto("multiplicador") else 1.0),
        percentual=(servicos.taxa_do_form(form, campo("percentual"),
                                          f"percentual do CDI da ponta {lado}", 1.0)
                    if texto("percentual") else 1.0),
        fator_manual=opcional("fator", f"fator da ponta {lado}"),
        ativo=texto("ativo"),
        preco_inicial=opcional("preco_inicial", f"preço inicial da ponta {lado}"),
        preco_final=opcional("preco_final", f"preço final da ponta {lado}"),
        tenor=form.get(campo("tenor")) or "3 month",
        data_fixing=para_data(texto("data_fixing")) if texto("data_fixing") else None,
        taxa_indice=(servicos.taxa_do_form(form, campo("taxa_indice"),
                                           f"taxa do fixing da ponta {lado}")
                     if texto("taxa_indice") else None),
        lookback=int(texto("lookback") or 0), shift=int(texto("shift") or 0),
    )


def _liquidar(form) -> dict:
    def ligado(campo: str) -> bool:
        return str(form.get(campo) or "").lower() in ("1", "on", "true")

    calendario = form.get("calendario") or "ANBIMA"
    resultado = liquidacao.liquidar(
        data_operacao=para_data(form.get("data_operacao") or ""),
        inicio=para_data(form.get("inicio") or ""),
        fim=para_data(form.get("fim") or ""),
        nocional=servicos.numero_do_form(form, "nocional", "notional remanescente"),
        ponta_ativa=_ponta_do_form(form, "ativa"),
        ponta_passiva=_ponta_do_form(form, "passiva"),
        vencimento=(para_data(form.get("vencimento"))
                    if (form.get("vencimento") or "").strip() else None),
        base_ajuste=form.get("base_ajuste") or liquidacao.BASE_AUTOMATICA,
        nocional_original=servicos.numero_do_form(form, "nocional_original",
                                                  "notional original", 0.0),
        percentual_amortizacao=servicos.taxa_do_form(form, "amortizacao",
                                                     "amortização", 0.0),
        base_amortizacao=form.get("base_amortizacao") or liquidacao.SOBRE_ORIGINAL,
        calendario=obter_calendario(calendario),
        arredondar_di=ligado("arredondar_di"), reter_ir=ligado("reter_ir"),
    )
    return {"r": resultado,
            "comparacao": servicos.contagens_lado_a_lado(resultado.inicio,
                                                         resultado.fim, calendario)}


@bp.route("/api/liquidacao/fixing")
def api_fixing_padrao():
    """D-2 dias úteis de uma data, no calendário pedido.

    A tela chama isto quando o início do fluxo ou o calendário mudam: o feriado
    é do pacote, e reimplementar a contagem em JavaScript daria duas verdades
    para a mesma pergunta — a do navegador e a do motor — que divergiriam no
    primeiro Carnaval.
    """
    data = _fixing_padrao(request.args.get("inicio") or "",
                          request.args.get("indexador") or "")
    return jsonify({"data": data})


# -------------------------------------------------------------- metodologia

@bp.route("/metodologia")
def metodologia():
    return render_template("metodologia.html", curvas=b3.CURVAS_COMPLETAS,
                           fontes=fontes.por_grupo(), glossario=glossario.por_grupo(),
                           rede=rede.diagnostico())


@bp.route("/api/rede/testar")
def api_testar_rede():
    """Bate em cada fonte e devolve o que aconteceu, uma por uma.

    "Deu erro na api" não diz qual api, nem se o problema é a fonte, a saída da
    rede ou a autenticação. Lado a lado, o resultado responde sozinho.
    """
    return jsonify({"fontes": rede.testar_fontes(),
                    "diagnostico": rede.diagnostico()})


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
            contexto["erro"] = idiomas.mensagem(exc)
    return render_template("ni_pro_rata.html", **contexto)


# --------------------------------------------------------- opções de câmbio --

# Estruturas prontas: (tipo, posição, strike) por perna, até quatro. Os strikes
# partem de um spot de 5,15; o resumo diz o que a estrutura faz, do ponto de
# vista de quem a monta.
_ESTRUTURAS_OPCAO = {
    "unica": ("Uma opção", "solar:tag-price-linear",
              "Uma call ou uma put, comprada ou vendida.",
              [("call", "comprada", "5,30")]),
    "call_spread": ("Call spread", "solar:graph-up-linear",
                    "Compra a call de strike baixo e vende a de strike alto: proteção contra a alta do dólar até um teto, mais barata que a call sozinha.",
                    [("call", "comprada", "5,30"), ("call", "vendida", "5,70")]),
    "put_spread": ("Put spread", "solar:graph-down-linear",
                   "Compra a put de strike alto e vende a de strike baixo: proteção contra a queda do dólar até um piso.",
                   [("put", "comprada", "5,00"), ("put", "vendida", "4,70")]),
    "collar": ("Collar", "solar:shield-linear",
               "Vende a call (cap) e compra a put (floor): o dólar fica numa banda, e o prêmio da call paga a put. É a estrutura da planilha.",
               [("call", "vendida", "5,80"), ("put", "comprada", "5,00")]),
    "three_way": ("Three way", "solar:layers-minimalistic-linear",
                  "Collar com uma put vendida abaixo do floor: a proteção vale só até o strike dela, e o prêmio extra barateia a estrutura.",
                  [("call", "vendida", "5,80"), ("put", "comprada", "5,00"), ("put", "vendida", "4,70")]),
    "four_way": ("Four way", "solar:widget-4-linear",
                 "Put spread comprado contra call spread vendido: proteção numa faixa embaixo, risco limitado numa faixa em cima.",
                 [("call", "vendida", "5,60"), ("call", "comprada", "5,90"),
                  ("put", "comprada", "5,00"), ("put", "vendida", "4,70")]),
    "straddle": ("Straddle", "solar:sort-vertical-linear",
                 "Call e put compradas no mesmo strike: ganha com movimento forte para qualquer lado, paga a vol.",
                 [("call", "comprada", "5,15"), ("put", "comprada", "5,15")]),
    "strangle": ("Strangle", "solar:arrows-diagonal-linear",
                 "Call e put compradas fora do dinheiro: como o straddle, mais barato e precisando de um movimento maior.",
                 [("call", "comprada", "5,50"), ("put", "comprada", "4,80")]),
    "box": ("Box", "solar:box-linear",
            "Call spread comprado e put spread comprado nos mesmos strikes: o payoff é fixo (K2 − K1), então o prêmio é só esse valor descontado pelo DI — uma taxa pré sintética.",
            [("call", "comprada", "5,00"), ("call", "vendida", "5,50"),
             ("put", "comprada", "5,50"), ("put", "vendida", "5,00")]),
}
MAX_PERNAS_OPCAO = 4
_SMILE_PADRAO = "20,40; 19,81; 19,11; 17,26; 16,06; 15,03; 14,29; 13,98; 13,66; 13,68; 13,72"


def _form_opcao(modelo: str) -> dict:
    hoje = servicos.data_sugerida()
    form = {
        "modelo": modelo, "inicio": hoje.isoformat(),
        "vencimento": soma_meses(hoje, 12).isoformat(),
        "spot": "5,15", "nocional": "20.000.000,00",
        "taxa_dom": "", "taxa_est": "", "vol": "15,00", "fonte_vol": "unica",
        "smile": _SMILE_PADRAO, "spread": "", "fee": "",
    }
    pernas = _ESTRUTURAS_OPCAO[modelo][3]
    for i in range(1, MAX_PERNAS_OPCAO + 1):
        tipo, lado, strike = pernas[i - 1] if i <= len(pernas) else ("call", "comprada", "")
        form.update({f"tipo{i}": tipo, f"lado{i}": lado, f"strike{i}": strike,
                     f"usar{i}": "1" if i <= len(pernas) else "", f"vol{i}": ""})
    if modelo == "collar":
        # o exemplo da planilha: smile da B3 e o benefício de taxa num CDI + 2,5%
        form.update({"fonte_vol": "smile", "spread": "2,50", "fee": "1,00"})
    form.update({"resolver_strike": "", "premio_alvo": "0,00"})
    return form


@bp.route("/opcoes-fx", methods=["GET", "POST"])
def opcoes_fx_pagina():
    """Price an option — Garman-Kohlhagen, porte da planilha do collar."""
    modelo = request.values.get("modelo") or "unica"
    if modelo not in _ESTRUTURAS_OPCAO:
        modelo = "unica"
    contexto = {"form": _form_opcao(modelo), "resultado": None, "erro": None,
                "deltas": opcoes_fx.DELTAS_B3, "estruturas": _ESTRUTURAS_OPCAO,
                "n_pernas": MAX_PERNAS_OPCAO}
    if request.method == "POST":
        contexto["form"] = {k: v for k, v in request.form.items()}
        try:
            contexto["resultado"] = _precificar_opcao(request.form)
        except (servicos.ErroFormulario, ErroDeFonte, ErroDeDado, ValueError) as exc:
            contexto["erro"] = idiomas.mensagem(exc)
    return render_template("opcoes_fx.html", **contexto)


def _precificar_opcao(form) -> dict:
    inicio = para_data(form.get("inicio") or "")
    vencimento = para_data(form.get("vencimento") or "")
    if vencimento <= inicio:
        raise servicos.ErroFormulario("o vencimento da opção tem que ser depois da data de início")
    cal = obter_calendario("ANBIMA")
    du = cal.dias_uteis(inicio, vencimento)
    dc = (vencimento - inicio).days
    t = du / 252.0
    spot = servicos.numero_do_form(form, "spot", "spot")

    # Taxa vazia = lida na curva da B3 da data de início, no prazo da opção:
    # DI x Pré para o real, cupom cambial limpo (DOC) para o dólar.
    fontes_taxa = {}
    if (form.get("taxa_dom") or "").strip():
        taxa_dom = servicos.taxa_do_form(form, "taxa_dom", "taxa doméstica")
        fontes_taxa["dom"] = "informada"
    else:
        taxa_dom = servicos.curva("PRE", inicio.isoformat()).taxa_para(dc, du)
        fontes_taxa["dom"] = "curva DI x Pré · B3"
    if (form.get("taxa_est") or "").strip():
        taxa_est = servicos.taxa_do_form(form, "taxa_est", "cupom cambial")
        fontes_taxa["est"] = "informada"
    else:
        taxa_est = servicos.curva("DOC", inicio.isoformat()).taxa_para(dc, du)
        fontes_taxa["est"] = "curva de cupom cambial · B3"
    r_d = opcoes_fx.r_d_continua(taxa_dom)
    r_f = opcoes_fx.r_f_continua(taxa_est, dc)

    quantidade = servicos.numero_do_form(form, "nocional", "nocional")   # em dólares

    smile = None
    usar_smile = form.get("fonte_vol") == "smile"
    if usar_smile:
        vols = _numeros(form.get("smile") or "", "smile por delta")
        if len(vols) != len(opcoes_fx.DELTAS_B3):
            raise servicos.ErroFormulario(
                "o smile precisa de {n} vols, de Δ1% a Δ99%", n=len(opcoes_fx.DELTAS_B3))
        smile = list(zip(opcoes_fx.DELTAS_B3, [v / 100.0 for v in vols]))
    vol_unica = None if usar_smile else servicos.taxa_do_form(form, "vol", "volatilidade")

    # a perna cujo strike vai ser calculado pode vir sem strike
    resolver = (form.get("resolver_strike") or "").strip()
    pernas, numeros, indice_resolver = [], [], None
    for i in range(1, MAX_PERNAS_OPCAO + 1):
        if not form.get(f"usar{i}"):
            continue
        vol_perna = vol_unica
        if (form.get(f"vol{i}") or "").strip():
            vol_perna = servicos.taxa_do_form(form, f"vol{i}", "volatilidade")
        if resolver == str(i):
            indice_resolver = len(pernas)
            strike = spot
        else:
            strike = servicos.numero_do_form(form, f"strike{i}", "strike")
        pernas.append(opcoes_fx.Perna(
            tipo=form.get(f"tipo{i}") or "call", lado=form.get(f"lado{i}") or "comprada",
            strike=strike, vol=vol_perna))
        numeros.append(i)
    if not pernas:
        raise servicos.ErroFormulario("marque pelo menos uma opção")
    if resolver and indice_resolver is None:
        raise servicos.ErroFormulario("a opção do strike a calcular não está marcada")

    strike_resolvido = None
    if indice_resolver is not None:
        alvo = (servicos.numero_do_form(form, "premio_alvo", "prêmio alvo", 0.0)
                if (form.get("premio_alvo") or "").strip() else 0.0)
        k = opcoes_fx.resolver_strike(pernas, indice_resolver, spot, r_d, r_f, t,
                                      quantidade, smile, alvo)
        velha = pernas[indice_resolver]
        pernas[indice_resolver] = opcoes_fx.Perna(velha.tipo, velha.lado, k, velha.vol)
        strike_resolvido = {"opcao": numeros[indice_resolver], "strike": k, "alvo": alvo}

    resultados = opcoes_fx.avaliar_pernas(pernas, spot, r_d, r_f, t, quantidade, smile)
    liquido = sum(r.premio_total for r in resultados)
    nocional_brl = quantidade * spot

    # Benefício de taxa: quanto o fee e o prêmio mexem no spread de um
    # empréstimo a CDI+ do mesmo prazo — a pergunta da planilha do collar.
    beneficio = None
    if (form.get("spread") or "").strip():
        spread = servicos.taxa_do_form(form, "spread", "spread")
        fee = servicos.taxa_do_form(form, "fee", "fee", 0.0) if (form.get("fee") or "").strip() else 0.0
        sem = opcoes_fx.taxa_all_in(spread, t, fee)
        com = opcoes_fx.taxa_all_in(spread, t, fee - liquido / nocional_brl)
        beneficio = {
            "spread": spread, "fee": fee, "sem": sem, "com": com, "diferenca": com - sem,
            "pct_sem": opcoes_fx.percentual_do_cdi(sem, taxa_dom),
            "pct_com": opcoes_fx.percentual_do_cdi(com, taxa_dom),
        }

    primeira = resultados[0].avaliacao
    return {
        "pernas": resultados, "liquido": liquido,
        "delta": sum(r.delta_posicao for r in resultados),
        "vega": sum(r.vega_posicao for r in resultados),
        "du": du, "dc": dc, "t": t, "spot": spot, "quantidade": quantidade,
        "nocional_brl": nocional_brl,
        "taxa_dom": taxa_dom, "taxa_est": taxa_est, "r_d": r_d, "r_f": r_f,
        "fontes_taxa": fontes_taxa, "forward": opcoes_fx.forward(spot, r_d, r_f, t),
        "paridade": opcoes_fx.paridade(spot, primeira.strike, r_d, r_f, t),
        "paridade_modelo": (
            opcoes_fx.avaliar("call", spot, primeira.strike, r_d, r_f, primeira.vol, t).premio
            - opcoes_fx.avaliar("put", spot, primeira.strike, r_d, r_f, primeira.vol, t).premio),
        "usar_smile": usar_smile, "beneficio": beneficio,
        "strike_resolvido": strike_resolvido, "numeros": numeros,
    }
