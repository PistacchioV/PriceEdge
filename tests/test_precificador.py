"""Testes de regressão contra os números das planilhas originais.

Os arquivos ``*_ref.json`` foram extraídos das próprias planilhas com openpyxl;
são a referência contra a qual o porte é conferido.
"""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from precificador import (BULLET, Curva, LINEAR, ParametrosSwap, calendario_anbima,
                          cubic_spline, spread_par_cdi, swap_pre_x_cdi)
from precificador.calendario import terceira_quarta
from precificador.curvas import EXP252, LIN360, CurvaTermSOFR
from precificador.instrumentos import agenda_periodica, pesos_amortizacao
from precificador.produtos import (NumeroIndice, pre_brl_par, swap_ipca_x_cdi,
                                   swap_pre_usd_x_pre_brl)

REF = Path(__file__).parent
CURVAS = json.loads((REF / "curvas_ref.json").read_text())
AGENDA = json.loads((REF / "agenda_ref.json").read_text())


# ------------------------------------------------------------- interpolação

def test_spline_reproduz_a_udf_do_vba():
    """A spline em Python bate com a ``cubic_spline`` do VBA em 1e-8.

    Os alvos são a coluna "CDI futuro interpolado" da planilha *Pré USD x Pré
    BRL*.  Os x usados ali são os **dias úteis** — ver ``test_eixo_da_curva``.
    """
    xs = [linha["J"] for linha in AGENDA]
    alvos = [alvo[1] for alvo in CURVAS["alvos"]]
    for x, alvo in zip(xs, alvos):
        obtido = cubic_spline(CURVAS["dias"], CURVAS["cdi"], x,
                              extrapolar="cubica") / 100.0
        # 1e-6 relativo: o primeiro ponto (x=0) cai fora do domínio da curva
        # e a extrapolação cúbica amplifica o arredondamento do valor gravado
        # na célula.  Nos dez pontos internos o casamento é melhor que 1e-9.
        assert obtido == pytest.approx(alvo, rel=1e-6)


def test_eixo_da_curva_e_dias_corridos():
    """O eixo da curva da B3 vai a 12.556 dias: é calendário, não útil.

    A planilha *Pré USD x Pré BRL* interpola essa curva num valor de dias
    úteis, o que devolve a taxa de um prazo mais curto.  O pacote interpola em
    dias corridos, como faz a planilha de IPCA — que traz a fórmula explícita
    ``cubic_spline(Curvas!A:A; Curvas!B:B; DC total)``.
    """
    assert max(CURVAS["dias"]) == 12556
    assert CURVAS["dias"] == CURVAS["dc"]


def test_spline_passa_pelos_vertices():
    for i in (0, 40, 150, len(CURVAS["dias"]) - 1):
        x, y = CURVAS["dias"][i], CURVAS["cdi"][i]
        assert cubic_spline(CURVAS["dias"], CURVAS["cdi"], x) == pytest.approx(y, abs=1e-9)


def test_extrapolacao_flat_trava_nas_pontas():
    ultimo = CURVAS["cdi"][-1]
    assert cubic_spline(CURVAS["dias"], CURVAS["cdi"], 99_999) == pytest.approx(ultimo)


# -------------------------------------------------------------- calendário

def test_agenda_bate_com_as_colunas_de_datas_da_planilha():
    periodos = agenda_periodica(date(2026, 4, 1), date(2031, 4, 1), 6)
    esperado = AGENDA[1:]                       # a linha 0 é a data de início
    assert len(periodos) == len(esperado)
    for periodo, linha in zip(periodos, esperado):
        assert periodo.data_pagamento.isoformat() == linha["F"]
        assert periodo.dc_total == linha["H"]
        assert periodo.dc_periodo == linha["I"]
        assert periodo.du_total == linha["J"]
        assert periodo.du_periodo == linha["K"]


def test_feriados_e_dias_uteis():
    cal = calendario_anbima()
    assert not cal.eh_dia_util(date(2026, 4, 3))       # Paixão de Cristo
    assert not cal.eh_dia_util(date(2026, 4, 4))       # sábado
    assert cal.eh_dia_util(date(2026, 4, 6))
    assert cal.ajusta(date(2028, 4, 1)) == date(2028, 4, 3)
    assert cal.workday(date(2026, 4, 1), 2) == date(2026, 4, 6)
    assert cal.dias_uteis(date(2026, 4, 1), date(2026, 4, 1)) == 0


def test_data_imm():
    assert terceira_quarta(2026, 6) == date(2026, 6, 17)
    assert terceira_quarta(2026, 12) == date(2026, 12, 16)
    assert terceira_quarta(2027, 3) == date(2027, 3, 17)


# ------------------------------------------------------------------ curvas

def curva_di():
    return Curva.de_listas(CURVAS["dias"], [t / 100 for t in CURVAS["cdi"]],
                           "DI x Pré", date(2026, 4, 1), convencao=EXP252)


def curva_cupom():
    return Curva.de_listas(CURVAS["dc"], [t / 100 for t in CURVAS["doc"]],
                           "Cupom Cambial", date(2026, 4, 1), convencao=LIN360,
                           metodo="linear")


def test_fra_encadeia_de_volta_no_spot():
    """Capitalizar os FRAs de volta reproduz o fator spot do prazo final."""
    curva = curva_di()
    periodos = agenda_periodica(date(2026, 4, 1), date(2031, 4, 1), 6)
    fator, dc_ant, du_ant = 1.0, 0, 0
    for p in periodos:
        fra = curva.forward(dc_ant, p.dc_total, du_ant, p.du_total)
        fator *= (1 + fra) ** (p.du_periodo / 252)
        dc_ant, du_ant = p.dc_total, p.du_total
    ultimo = periodos[-1]
    assert fator == pytest.approx(
        curva.fator_capitalizacao(ultimo.dc_total, ultimo.du_total), rel=1e-12)


def test_shift_paralelo():
    curva = curva_di()
    assert curva.deslocada(0.0001).taxa(365) == pytest.approx(curva.taxa(365) + 0.0001)


# ----------------------------------------------------------------- produtos

PARAMS = ParametrosSwap(inicio=date(2026, 4, 1), vencimento=date(2031, 4, 1),
                        nocional=100_000_000, meses_periodo=6, amortizacao=BULLET)


def test_amortizacao():
    assert pesos_amortizacao(4, BULLET) == [0, 0, 0, 1]
    assert sum(pesos_amortizacao(10, LINEAR)) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        pesos_amortizacao(3, "personalizada", [0.5, 0.4, 0.2])


def test_spread_par_zera_o_mtm():
    """É o Atingir Meta das macros: a taxa devolvida tem que zerar o MtM."""
    di = curva_di()
    spread = spread_par_cdi(PARAMS, 0.17, di)
    swap = swap_pre_x_cdi(PARAMS, 0.17, spread, di)
    assert swap.mtm == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < spread < 0.10


def test_cdi_com_spread_zero_replica_a_curva():
    """Sem cupom no meio, pré par == taxa da curva; com cupom, o par se afasta.

    Num swap de um período só (bullet, sem pagamento intermediário) a taxa pré
    que zera o MtM contra CDI puro é exatamente a taxa spot da curva.  Com
    cupom semestral aparece o efeito par-vs-zero, de ordem de 1 bp aqui — e
    ele é real, não erro numérico.
    """
    di = curva_di()
    from precificador.produtos import pre_par_cdi
    zero_cupom = ParametrosSwap(inicio=date(2026, 4, 1), vencimento=date(2031, 4, 1),
                                nocional=100_000_000, meses_periodo=120)
    ultimo = zero_cupom.agenda()[-1]
    assert pre_par_cdi(zero_cupom, 0.0, di) == pytest.approx(di.taxa(ultimo.dc_total),
                                                             abs=1e-9)
    com_cupom = pre_par_cdi(PARAMS, 0.0, di)
    assert com_cupom == pytest.approx(di.taxa(PARAMS.agenda()[-1].dc_total), abs=5e-4)


def test_spread_multiplicativo_nao_aditivo():
    """(1+CDI)(1+spread) ≠ CDI+spread — o aviso em vermelho da planilha."""
    di = curva_di()
    pre = 0.17
    spread = spread_par_cdi(PARAMS, pre, di)
    ultimo = PARAMS.agenda()[-1]
    cdi = di.taxa(ultimo.dc_total)
    assert abs((pre - cdi) - spread) > 3e-4          # a diferença é material
    assert (1 + cdi) * (1 + spread) == pytest.approx(1 + pre, abs=2e-3)


def test_cross_currency_desconta_cada_perna_na_sua_curva():
    di, cupom = curva_di(), curva_cupom()
    taxa_brl = pre_brl_par(PARAMS, 0.10, di, cupom, 5.15)
    swap = swap_pre_usd_x_pre_brl(PARAMS, 0.10, taxa_brl, di, cupom, 5.15)
    assert swap.mtm == pytest.approx(0.0, abs=1e-6)
    assert swap.ativa.moeda == "USD" and swap.passiva.moeda == "BRL"
    assert 0.05 < taxa_brl < 0.25


def test_prazo_medio_e_duration_de_um_bullet():
    di = curva_di()
    swap = swap_pre_x_cdi(PARAMS, 0.17, 0.02, di)
    prazo = swap.ativa.fluxos[-1].periodo.dc_total / 365
    assert swap.prazo_medio == pytest.approx(prazo, abs=1e-9)   # bullet: só uma amortização
    assert swap.duration < swap.prazo_medio                     # cupom semestral encurta


def test_ipca_precisa_das_duas_curvas():
    di = curva_di()
    ipca = Curva.de_listas(CURVAS["dias"], [0.07] * len(CURVAS["dias"]),
                           "DI x IPCA", date(2026, 4, 1))
    swap = swap_ipca_x_cdi(PARAMS, 0.07, 0.02, di, ipca)
    inflacao_implicita = (1 + di.taxa(1826)) / 1.07 - 1
    indice = swap.ativa.fluxos[-1].amortizacao / PARAMS.nocional
    assert indice == pytest.approx((1 + inflacao_implicita) ** (1249 / 252), rel=1e-3)


# --------------------------------------------------------------- Term SOFR

def test_bootstrap_term_sofr():
    """A curva é ancorada no spot: DF(spot) = 1, e cai daí em diante."""
    datas = [terceira_quarta(2026, m) for m in (6, 9, 12)] + [terceira_quarta(2027, 3)]
    spot = date(2026, 5, 1)
    curva = CurvaTermSOFR(spot, datas, [0.03655, 0.0362, 0.0358])
    assert curva.fator_desconto(spot) == pytest.approx(1.0)
    dfs = [p["df"] for p in curva.pontos]
    assert all(df < 1.0 for df in dfs)
    assert all(a > b for a, b in zip(dfs, dfs[1:]))    # DF sempre decrescente
    # o encadeamento entre datas IMM é o bootstrap dos futuros
    dc = (datas[1] - datas[0]).days
    assert dfs[1] == pytest.approx(dfs[0] / (1 + 0.03655 * dc / 360))


def test_term_sofr_usa_as_taxas_da_cme_no_trecho_curto():
    """As taxas Term SOFR de 1, 3, 6 e 12 meses montam a ponta curta da curva."""
    spot = date(2026, 5, 1)
    datas = [terceira_quarta(2026, m) for m in (6, 9, 12)]
    taxas = {1: 0.0364637, 3: 0.0365811, 6: 0.0367358, 12: 0.0373148}
    curva = CurvaTermSOFR(spot, datas, [0.03655, 0.0362], taxas_term=taxas)

    tres_meses = date(2026, 8, 1)
    dc = (tres_meses - spot).days
    assert curva.fator_desconto(tres_meses) == pytest.approx(
        1 / (1 + taxas[3] * dc / 360), rel=1e-12)

    # o Term SOFR a termo de 3 meses no próprio spot volta a taxa de 3 meses
    assert curva.term_forward(spot, 3) == pytest.approx(taxas[3], rel=1e-9)


def test_term_forward_por_tenor():
    """Cada tenor devolve a taxa linear 360 da sua própria janela."""
    spot = date(2026, 5, 1)
    datas = [terceira_quarta(2026, m) for m in (6, 9, 12)] + [terceira_quarta(2027, 3)]
    taxas = {1: 0.0364637, 3: 0.0365811, 6: 0.0367358, 12: 0.0373148}
    curva = CurvaTermSOFR(spot, datas, [0.03655, 0.0362, 0.0358], taxas_term=taxas)
    for meses in (1, 3, 6, 12):
        assert curva.term_forward(spot, meses) == pytest.approx(taxas[meses], rel=1e-9)
    # a termo, seis meses à frente, a taxa muda
    assert curva.term_forward(date(2026, 11, 1), 3) != pytest.approx(taxas[3], rel=1e-6)


# --------------------------------------------------------------------- IPCA

def test_ni_pro_rata():
    """Aba "Cálculo NI Pro-Rata", com os mesmos insumos da planilha.

    dup=19, dut=21 e NI=7591,937980031845 são os valores gravados nas células
    M6, M7 e M5.  Eles só batem porque ``dias_uteis`` reproduz o
    ``NETWORKDAYS − 1`` literal: a data-base 15/03/2026 é um domingo, e nesse
    caso o −1 do Excel come um dia útil de verdade.
    """
    cal = calendario_anbima()
    ni = NumeroIndice(ni_anterior=7545.53, projecao_mensal=0.0068,
                      data_referencia=date(2026, 4, 13))
    assert ni.data_base == date(2026, 3, 15)
    assert ni.proxima_base == date(2026, 4, 15)
    assert cal.dias_uteis(ni.data_base, ni.data_referencia) == 19
    assert cal.dias_uteis(ni.data_base, ni.proxima_base) == 21
    assert ni.ni_cheio == pytest.approx(7596.839603999999, abs=1e-9)
    assert ni.ni_pro_rata() == pytest.approx(7591.937980031845, abs=1e-9)
    assert ni.vna(1000, 7545.53) == pytest.approx(1000 * ni.ni_pro_rata() / 7545.53)


def test_networkdays_e_dias_uteis_sao_coisas_diferentes():
    """A distinção que faz o NI pro-rata bater com a planilha."""
    cal = calendario_anbima()
    domingo, segunda = date(2026, 3, 15), date(2026, 3, 16)
    assert cal.networkdays(domingo, date(2026, 4, 13)) == 20
    assert cal.dias_uteis(domingo, date(2026, 4, 13)) == 19
    # partindo de um dia útil, as duas contagens voltam a coincidir
    assert cal.dias_uteis(segunda, date(2026, 4, 13)) == cal.networkdays(segunda, date(2026, 4, 13)) - 1


def test_swap_sofr_desconta_a_partir_do_inicio():
    """O spread par tem que ser a diferença entre o pré e o forward médio.

    Se os DFs forem tomados da primeira data IMM em vez da data de início do
    swap, o primeiro forward sai inflado e o spread par erra por mais de 100 bp.
    """
    from precificador.produtos import spread_par_sofr, swap_pre_usd_x_term_sofr
    meses = [(6, 2026), (9, 2026), (12, 2026), (3, 2027), (6, 2027),
             (9, 2027), (12, 2027), (3, 2028), (6, 2028)]
    precos = [96.345, 96.38, 96.42, 96.46, 96.49, 96.51, 96.52, 96.53]
    curva = CurvaTermSOFR(date(2026, 5, 1), [terceira_quarta(a, m) for m, a in meses],
                          [(100 - p) / 100 for p in precos])
    params = ParametrosSwap(inicio=date(2026, 9, 8), vencimento=date(2029, 9, 10),
                            nocional=50_000_000, meses_periodo=3)
    spread = spread_par_sofr(params, 0.05, curva)
    assert swap_pre_usd_x_term_sofr(params, 0.05, spread, curva).mtm == pytest.approx(0, abs=1e-6)
    forward_medio = sum(curva.forwards) / len(curva.forwards)
    assert spread == pytest.approx(0.05 - forward_medio, abs=2e-3)


def test_df_entre_datas():
    """``fator_desconto_entre`` é o que a precificação usa; DF isolado é do spot."""
    spot = date(2026, 5, 1)
    datas = [terceira_quarta(2026, m) for m in (6, 9, 12)]
    curva = CurvaTermSOFR(spot, datas, [0.03655, 0.0362])
    assert curva.fator_desconto_entre(datas[0], datas[0]) == pytest.approx(1.0)
    assert curva.fator_desconto(spot) == pytest.approx(1.0)
    # descontar de uma data posterior ao spot dá um DF maior que o do spot
    assert (curva.fator_desconto_entre(datas[0], datas[1])
            > curva.fator_desconto(datas[1]))


# ------------------------------------------------------- leitura de formulário

def test_parser_aceita_os_dois_padroes_decimais():
    """Os campos voltam do navegador já formatados; o parser tem que ler isso.

    ``formatar-campos.js`` escreve ``100.000.000,00`` e ``2,50000000 %`` de
    volta no input, então o servidor precisa desfazer o separador de milhar sem
    quebrar quem digita ``5.15`` no padrão americano.
    """
    from webapp.servicos import _decimal, taxa_do_form
    assert _decimal("100.000.000,00", "nocional") == pytest.approx(100_000_000)
    assert _decimal("100.000.000", "nocional") == pytest.approx(100_000_000)
    assert _decimal("100000000", "nocional") == pytest.approx(100_000_000)
    assert _decimal("1.500,50", "x") == pytest.approx(1500.50)
    assert _decimal("1,500.50", "x") == pytest.approx(1500.50)
    assert _decimal("5.15", "spot") == pytest.approx(5.15)      # ponto decimal
    assert _decimal("5,15", "spot") == pytest.approx(5.15)      # vírgula decimal

    assert taxa_do_form({"s": "2,50000000 %"}, "s", "spread") == pytest.approx(0.025)
    assert taxa_do_form({"s": "0,50000000 %"}, "s", "spread") == pytest.approx(0.005)
    assert taxa_do_form({"s": "-0,25000000 %"}, "s", "spread") == pytest.approx(-0.0025)
    assert taxa_do_form({"s": "17"}, "s", "taxa") == pytest.approx(0.17)


def test_formulario_aceita_ida_e_volta_do_formato():
    """Enviar o formulário com os valores já formatados tem que funcionar."""
    from webapp import create_app
    cliente = create_app().test_client()
    resposta = cliente.post("/precificar", data={
        "produto": "pre_cdi", "inicio": "2026-09-04", "vencimento": "2031-09-04",
        "nocional": "100.000.000,00", "meses_periodo": "6", "amortizacao": "bullet",
        "fee": "0", "data_curva": "2026-09-04", "taxa_pre": "17",
        "spread": "2,50000000 %", "resolver": "pre",
    })
    assert resposta.status_code == 200
    assert "não é um número" not in resposta.data.decode()


# ------------------------------------------------- convenções de dia útil --

def test_convencoes_de_dia_util():
    """Modified following não deixa o pagamento virar o mês."""
    from precificador.calendario import (FOLLOWING, MODIFIED_FOLLOWING, PRECEDING,
                                         UNADJUSTED)
    cal = calendario_anbima()
    domingo = date(2026, 5, 31)          # último dia do mês, domingo
    assert cal.ajusta(domingo, convencao=FOLLOWING) == date(2026, 6, 1)
    assert cal.ajusta(domingo, convencao=MODIFIED_FOLLOWING) == date(2026, 5, 29)
    assert cal.ajusta(domingo, convencao=PRECEDING) == date(2026, 5, 29)
    assert cal.ajusta(domingo, convencao=UNADJUSTED) == domingo
    # em dia útil, nenhuma convenção mexe na data
    util = date(2026, 5, 29)
    for conv in (FOLLOWING, MODIFIED_FOLLOWING, PRECEDING, UNADJUSTED):
        assert cal.ajusta(util, convencao=conv) == util


def test_sem_fluxo_colapsa_a_agenda():
    from precificador.produtos import ParametrosSwap
    p = ParametrosSwap(inicio=date(2026, 9, 4), vencimento=date(2031, 9, 4),
                       nocional=1e8, meses_periodo=6, sem_fluxo=True)
    agenda = p.agenda()
    assert len(agenda) == 1
    assert agenda[0].data_pagamento >= date(2031, 9, 4)


def test_calendarios_sofr_e_bce():
    """SOFR vem do OTC Tracker; o TARGET2 do BCE é gerado pela regra."""
    from precificador.calendario import calendario_bce, calendario_sofr, pascoa
    assert pascoa(2026) == date(2026, 4, 5)
    sofr_cal = calendario_sofr()
    assert not sofr_cal.eh_dia_util(date(2026, 11, 26))       # Thanksgiving
    assert not sofr_cal.eh_dia_util(date(2026, 7, 3))         # 4 de julho observado
    bce = calendario_bce()
    for feriado in (date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 6),
                    date(2026, 5, 1), date(2026, 12, 25), date(2026, 12, 26)):
        assert not bce.eh_dia_util(feriado)
    assert bce.eh_dia_util(date(2026, 7, 14))    # feriado francês não é do TARGET


# ------------------------------------------------------------ % do CDI ----

def test_percentual_do_cdi_incide_na_taxa_diaria():
    """110% do CDI não é 1,10 × a taxa anual."""
    from precificador.instrumentos import perna_cdi_percentual
    di = Curva.de_listas([1, 20000], [0.14, 0.14], "DI plana", date(2026, 9, 4),
                         dias_uteis=[1, 14000])
    params = ParametrosSwap(inicio=date(2026, 9, 4), vencimento=date(2027, 9, 6),
                            nocional=1_000_000, sem_fluxo=True)
    periodos = params.agenda()
    perna = perna_cdi_percentual(1_000_000, 1.10, periodos, di, [1.0])
    du = periodos[0].du_periodo
    diaria = 1.14 ** (1 / 252) - 1
    esperado = (1 + diaria * 1.10) ** du - 1
    assert perna.fluxos[0].taxa_periodo == pytest.approx(esperado, rel=1e-12)
    # o cálculo ingênuo (percentual sobre a taxa anual) dá outro número
    ingenuo = (1 + 1.10 * 0.14) ** (du / 252) - 1
    assert abs(perna.fluxos[0].taxa_periodo - ingenuo) > 1e-4


# ------------------------------------------------------------------ NDF ---

def test_ndf_pela_paridade_coberta():
    from precificador.produtos import ndf_forward
    ndf = ndf_forward(spot=5.10, di=0.14, cupom=0.05, dias_corridos=365, dias_uteis=252)
    assert ndf == pytest.approx(5.10 * 1.14 / (1 + 0.05 * 365 / 360), rel=1e-12)
    # sem juros dos dois lados, o termo é o próprio spot
    assert ndf_forward(5.10, 0.0, 0.0, 180, 124) == pytest.approx(5.10)


def test_escada_de_datas_cai_no_ultimo_dia_util_do_mes():
    from precificador.produtos import escada_datas
    cal = calendario_anbima()
    datas = escada_datas(date(2026, 9, 4), "mensal", 4, cal)
    assert len(datas) == 4
    for d in datas:
        assert cal.eh_dia_util(d)
        seguinte = d + __import__("datetime").timedelta(days=1)
        # não há dia útil depois dele dentro do mesmo mês
        while seguinte.month == d.month:
            assert not cal.eh_dia_util(seguinte)
            seguinte += __import__("datetime").timedelta(days=1)


# ---------------------------------------------------------- renda fixa ----

def test_renda_fixa_ir_e_iof():
    from precificador import renda_fixa as rf
    assert rf.aliquota_ir(180) == 0.225
    assert rf.aliquota_ir(181) == 0.20
    assert rf.aliquota_ir(721) == 0.15
    assert rf.aliquota_iof(30) == 0.0
    assert rf.aliquota_iof(1) == 0.96

    curto = rf.calcular(100_000, date(2026, 9, 8), date(2026, 9, 25),
                        rf.PREFIXADO, 0.14)
    assert curto.iof > 0 and curto.aliquota_ir == 0.225

    isento = rf.calcular(100_000, date(2026, 9, 8), date(2031, 9, 8),
                         rf.IPCA_MAIS, 0.06, ipca_projetado=0.045, produto="cri")
    assert isento.ir == 0 and isento.isento


def test_di_sem_arredondamento_e_o_padrao():
    """O arredondamento na 8ª casa muda o fator — por isso ele é opcional."""
    from precificador import renda_fixa as rf
    cheio = rf.fator_di(0.14, 1250, percentual=1.10, arredondar=False)
    truncado = rf.fator_di(0.14, 1250, percentual=1.10, arredondar=True)
    assert cheio != truncado
    assert abs(cheio - truncado) < 1e-4          # pequeno, mas não zero
    diferenca = rf.diferenca_arredondamento(0.14, 1250, 1.10, valor=1_000_000)
    assert abs(diferenca["diferenca_reais"]) > 0.5


# --------------------------------------------------------------- montador --

def test_montador_valida_combinacoes():
    from precificador.montador import validar
    assert validar("cdi", "cdi") is not None
    assert validar("pre_usd", "pre_usd_sofr") is not None
    assert validar("pre_brl", "cdi") is None
    assert validar("ipca", "pre_brl") is None


def test_montador_reproduz_o_produto_pronto():
    """Montar Pré BRL × CDI à mão tem que dar o mesmo do produto de atalho."""
    from precificador.montador import Mercado, montar, resolver
    di = curva_di()
    mercado = Mercado(di=di)
    spread_montado = resolver(PARAMS, mercado, "pre_brl", 0.17, "cdi", 0.0, "passiva")
    spread_pronto = spread_par_cdi(PARAMS, 0.17, di)
    assert spread_montado == pytest.approx(spread_pronto, abs=1e-9)
    swap = montar(PARAMS, mercado, "pre_brl", 0.17, "cdi", spread_montado)
    assert swap.mtm == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------- CDI realizado ---

def test_acumulo_do_cdi_segue_a_convencao_da_b3():
    """Fator = Π(1 + ((1+DI)^(1/252) − 1)·p) sobre [início, fim).

    A calculadora da B3 dá 1,09550031 para 01/01/2026 a 06/09/2026 a 100%. O
    último DI que entra é o de 04/09 — a data final não conta, e é isso que a
    janela [início, fim) garante.
    """
    from precificador import cdi
    fixings = [cdi.FixingCDI(date(2026, 1, 2), 0.149),
               cdi.FixingCDI(date(2026, 1, 5), 0.149),
               cdi.FixingCDI(date(2026, 1, 6), 0.149)]
    r = cdi.acumular(fixings, date(2026, 1, 1), date(2026, 1, 6), valor=1000.0)
    # o fixing de 06/01 é o da data final: fica de fora
    assert r.dias_uteis == 2
    assert r.ultimo == date(2026, 1, 5)
    esperado = (1.149 ** (1 / 252)) ** 2
    assert r.fator == pytest.approx(esperado, rel=1e-12)
    assert r.valor_calculado == pytest.approx(1000.0 * esperado)


def test_acumulo_com_percentual_e_arredondamento():
    from precificador import cdi
    fixings = [cdi.FixingCDI(date(2026, 1, 2), 0.149),
               cdi.FixingCDI(date(2026, 1, 5), 0.149)]
    cheio = cdi.acumular(fixings, date(2026, 1, 2), date(2026, 1, 6), percentual=1.10)
    truncado = cdi.acumular(fixings, date(2026, 1, 2), date(2026, 1, 6),
                            percentual=1.10, arredondar=True)
    diaria = 1.149 ** (1 / 252) - 1
    assert cheio.fator == pytest.approx((1 + diaria * 1.10) ** 2, rel=1e-12)
    assert cheio.fator != truncado.fator          # o arredondamento muda o número


def test_acumulo_recusa_periodo_sem_publicacao():
    from precificador import cdi
    fixings = [cdi.FixingCDI(date(2026, 1, 2), 0.149)]
    with pytest.raises(cdi.ErroBCB):
        cdi.acumular(fixings, date(2027, 1, 1), date(2027, 2, 1))
    with pytest.raises(ValueError):
        cdi.acumular(fixings, date(2026, 1, 5), date(2026, 1, 5))


def test_calculadora_aceita_fator_pronto():
    """O CDI realizado entra como fator; IR e IOF seguem o mesmo caminho."""
    from precificador import renda_fixa as rf
    r = rf.calcular(1000, date(2026, 1, 1), date(2026, 9, 6), rf.CDI_REALIZADO,
                    taxa=1.0, fator_pronto=1.09550031, dias_uteis=170)
    assert r.valor_bruto == pytest.approx(1095.50031)
    assert r.aliquota_ir == 0.20                  # 248 dias corridos
    assert r.valor_liquido == pytest.approx(1095.50031 - 95.50031 * 0.20)
    assert rf.CDI_REALIZADO in rf.RETROATIVOS


# --------------------------------------------------------------- EURIBOR ---

CSV_EURIBOR = (
    "dundasChartControl1_DRG_DataRowGrouping1_label,"
    "dundasChartControl1_DRG_DataRowGrouping1_dundasChartControl1_DCG_Period1_label,"
    "dundasChartControl1_DRG_DataRowGrouping1_dundasChartControl1_DCG_Period1_Value_X,"
    "dundasChartControl1_DRG_DataRowGrouping1_dundasChartControl1_DCG_Period1_Value_Y\n"
    "1 week,September,09/03/2026 00:00:00,2.182\n"
    "1 week,September,09/04/2026 00:00:00,2.154\n"
    "3 month,September,09/03/2026 00:00:00,2.655\n"
    "3 month,September,09/04/2026 00:00:00,2.679\n"
    "12 month,September,09/04/2026 00:00:00,3.108\n"
    "Date,4 Sep 2026,12 month,3.108\n"          # bloco da tabela: tem de ser ignorado
)


def test_parse_do_csv_do_banco_da_finlandia():
    """A data vem em MM/DD/AAAA e o rodapé traz outro bloco, que sai fora."""
    from precificador import euribor
    fixings = euribor.parse_csv(CSV_EURIBOR)
    assert len(fixings) == 5
    assert fixings[0].data == date(2026, 9, 3)
    assert fixings[0].tenor == "1 week"
    assert fixings[0].taxa == pytest.approx(0.02182)
    assert all(f.tenor in euribor.TENOR_MESES for f in fixings)


def test_curva_euribor_organiza_por_data_e_prazo():
    from precificador import euribor
    curva = euribor.CurvaEuribor.de_fixings(euribor.parse_csv(CSV_EURIBOR))
    assert curva.inicio == date(2026, 9, 3)
    assert curva.fim == date(2026, 9, 4)
    assert curva.tenores == ["1 week", "3 month", "12 month"]      # ordem de prazo
    assert curva.ultima() == pytest.approx(
        {"1 week": 0.02154, "3 month": 0.02679, "12 month": 0.03108})
    prazos = [p["meses"] for p in curva.curva_do_dia(date(2026, 9, 4))]
    assert prazos == sorted(prazos)              # a curva sai em ordem de prazo


def test_curva_euribor_em_data_de_referencia():
    """Sem publicação no dia pedido, vale a última anterior — é a taxa vigente."""
    from precificador import euribor
    curva = euribor.CurvaEuribor.de_fixings(euribor.parse_csv(CSV_EURIBOR))
    vigente, taxas = curva.em(date(2026, 9, 6))       # domingo
    assert vigente == date(2026, 9, 4)
    assert taxas["1 week"] == pytest.approx(0.02154)
    vigente, taxas = curva.em(date(2026, 9, 3))
    assert vigente == date(2026, 9, 3)
    assert taxas["1 week"] == pytest.approx(0.02182)
    assert curva.em(date(2020, 1, 1)) == (None, {})   # antes da base


def test_base_euribor_so_acrescenta():
    """Mesclar nunca sobrescreve o que já está gravado."""
    from precificador import euribor
    base = {"2026-09-04": {"1 week": 0.02154}}
    novos = euribor.mesclar(base, [
        euribor.FixingEuribor(date(2026, 9, 4), "1 week", 0.99),     # ignorado
        euribor.FixingEuribor(date(2026, 9, 4), "3 month", 0.02679), # entra
        euribor.FixingEuribor(date(2026, 9, 7), "1 week", 0.02160),  # entra
    ])
    assert novos == 2
    assert base["2026-09-04"]["1 week"] == pytest.approx(0.02154)
    assert base["2026-09-04"]["3 month"] == pytest.approx(0.02679)
    assert "2026-09-07" in base


def test_url_de_exportacao():
    from precificador import euribor
    assert euribor.url_exportacao("csv").endswith("&output=CSV")
    assert "EXCELOPENXML" in euribor.url_exportacao("excel")
    with pytest.raises(ValueError):
        euribor.url_exportacao("parquet")


def test_calendario_euribor_do_arquivo():
    """O calendário salvo traz 24 e 31/12, que a regra pura do TARGET2 não tem."""
    from precificador.calendario import calendario_bce, calendario_target2
    bce, regra = calendario_bce(), calendario_target2()
    assert not bce.eh_dia_util(date(2026, 12, 24))
    assert not bce.eh_dia_util(date(2026, 12, 31))
    assert regra.eh_dia_util(date(2026, 12, 24))       # a regra não fecha nesse dia
    # os feriados clássicos aparecem nos dois
    for feriado in (date(2026, 1, 1), date(2026, 4, 3), date(2026, 5, 1), date(2026, 12, 25)):
        assert not bce.eh_dia_util(feriado)
        assert not regra.eh_dia_util(feriado)
    # fora do alcance do arquivo, a regra assume
    assert not bce.eh_dia_util(date(2010, 4, 2))       # Sexta-feira Santa de 2010


# ------------------------------------------------------ cobertura de idioma --

# Formulários que dão resultado — as telas onde a metade mais escorregadia do
# texto só aparece depois do POST. Ficam aqui fora porque os dois testes de
# idioma precisam dos mesmos: foi por a varredura de português só fazer GET que
# "nenhuma" e "último fixing publicado" chegaram à tela em inglês.
FORMULARIOS = {
    "/renda-fixa": dict(valor="1.000,00", inicio="2026-01-01",
                        vencimento="2026-09-06", produto="cdb",
                        indexador="cdi_realizado", taxa="100"),
    "/sofr": dict(inicio="2026-06-01", fim="2026-09-01", lookback="5", shift="2"),
    "/sofr-sem-defasagem": dict(inicio="2026-06-01", fim="2026-09-01",
                                lookback="0", shift="0"),
    "/ndf": dict(data_curva="2026-09-04", moeda="USD", spot="5,10",
                 progressao="mensal", quantidade="4", calendario="ANBIMA",
                 datas="", vencimento="", primeiro_futuro="5125",
                 segundo_futuro="5150"),
    "/ndf-euro": dict(data_curva="2026-09-04", moeda="EUR", spot="5,95",
                      progressao="mensal", quantidade="4", calendario="ANBIMA"),
    "/ndf-cross": dict(data_curva="2026-09-04", moeda="EURUSD", spot="1,1618",
                       progressao="mensal", quantidade="4", calendario="ANBIMA"),
    "/ndf-livre": dict(data_curva="2026-09-04", moeda="LIVRE", spot="6,93",
                       taxa_estrangeira="4,25", progressao="mensal",
                       quantidade="4", calendario="ANBIMA"),
    "/ni-pro-rata": dict(ni_anterior="7.545,53", projecao="0,68",
                         data="2026-04-13", vne="1.000,00", ni_partida="7.545,53"),
    "/liquidacao": dict(data_operacao="2025-09-08", inicio="2025-09-08",
                       fim="2026-09-04", nocional="50.000.000,00",
                       nocional_original="100.000.000,00", amortizacao="10",
                       base_amortizacao="original", calendario="ANBIMA",
                       reter_ir="1", ativa_indexador="pre", ativa_taxa="14",
                       ativa_convencao="du_252", ativa_regime="composto",
                       ativa_moeda="BRL", ativa_tenor="3 month",
                       ativa_lookback="0", ativa_shift="0",
                       passiva_indexador="cdi_percentual", passiva_taxa="100",
                       passiva_convencao="du_252", passiva_regime="composto",
                       passiva_moeda="BRL", passiva_tenor="3 month",
                       passiva_lookback="0", passiva_shift="0"),
    "/liquidacao-sofr": dict(data_operacao="2025-09-08", inicio="2025-09-08",
                       fim="2026-09-04", nocional="30.000.000,00",
                       calendario="ANBIMA", reter_ir="1",
                       ativa_indexador="sofr", ativa_taxa="1,5",
                       ativa_moeda="USD", ativa_ptax_inicial="5,4012",
                       ativa_ptax_final="5,3188", ativa_convencao="act_360",
                       ativa_regime="simples", ativa_lookback="5",
                       ativa_shift="2", ativa_tenor="3 month",
                       passiva_indexador="cdi_percentual", passiva_taxa="100",
                       passiva_convencao="du_252", passiva_regime="composto",
                       passiva_moeda="BRL", passiva_tenor="3 month",
                       passiva_lookback="0", passiva_shift="0"),
    "/liquidacao-moeda": dict(data_operacao="2025-09-08", inicio="2025-09-08",
                       fim="2026-09-04", nocional="30.000.000,00",
                       calendario="ANBIMA", reter_ir="1",
                       ativa_indexador="moeda", ativa_moeda="CNH",
                       ativa_ptax_inicial="0,7620", ativa_ptax_final="0,7845",
                       ativa_tenor="3 month", ativa_lookback="0", ativa_shift="0",
                       passiva_indexador="cdi_percentual", passiva_taxa="105",
                       passiva_convencao="du_252", passiva_regime="composto",
                       passiva_moeda="BRL", passiva_tenor="3 month",
                       passiva_lookback="0", passiva_shift="0"),
    "/liquidacao-equity": dict(data_operacao="2025-09-08", inicio="2025-09-08",
                       fim="2026-09-04", nocional="20.000.000,00",
                       calendario="ANBIMA", reter_ir="1",
                       ativa_indexador="equity", ativa_ativo="S&P 500",
                       ativa_preco_inicial="6400", ativa_preco_final="6980",
                       ativa_taxa="0", ativa_moeda="USD",
                       ativa_ptax_inicial="5,40", ativa_ptax_final="5,32",
                       ativa_convencao="act_360", ativa_regime="simples",
                       passiva_indexador="pre", passiva_taxa="14",
                       passiva_convencao="du_252", passiva_regime="composto",
                       passiva_moeda="BRL"),
    "/liquidacao-term-sofr": dict(data_operacao="2025-09-08", inicio="2025-09-08",
                       fim="2026-09-04", nocional="30.000.000,00",
                       calendario="ANBIMA", reter_ir="1",
                       ativa_indexador="term_sofr", ativa_taxa_indice="4,32",
                       ativa_taxa="1,5", ativa_tenor="12 month",
                       ativa_moeda="USD", ativa_ptax_inicial="5,40",
                       ativa_ptax_final="5,32", ativa_convencao="act_360",
                       ativa_regime="simples",
                       passiva_indexador="cdi_spread", passiva_taxa="2",
                       passiva_convencao="du_252", passiva_regime="composto",
                       passiva_moeda="BRL"),
    "/interpolar": dict(x="1\n365\n1826", y="14\n13,5\n13,8", alvos="180, 900",
                        metodo="spline", extrapolar="flat"),
}

# as chaves acima carregam um sufixo para poder repetir a mesma rota com outros
# dados; a rota de verdade é o que vem antes do primeiro traço depois de "/ndf"
def _rota_do_formulario(chave: str) -> str:
    for base in ("/ndf", "/sofr", "/liquidacao"):
        if chave.startswith(base + "-"):
            return base
    return chave


def _exercitar_aplicacao(app):
    """Passa por todas as telas e pelos formulários, para o audit ver tudo."""
    gets = ["/", "/curvas", "/precificar", "/ndf", "/sofr", "/term-sofr", "/euribor",
            "/renda-fixa", "/liquidacao", "/interpolar", "/ni-pro-rata",
            "/metodologia"]
    for rota in gets:
        app.test_client().get(rota + "?idioma=en")

    from precificador import b3
    from webapp.servicos import DERIVADAS
    for codigo, *_ in b3.CURVAS_COMPLETAS:
        app.test_client().get(f"/curvas?idioma=en&curva={codigo}&extrair=1")
    for codigo, *_ in DERIVADAS:
        app.test_client().get(f"/curvas?idioma=en&curva={codigo}&extrair=1")

    for chave, dados in FORMULARIOS.items():
        app.test_client().post(_rota_do_formulario(chave) + "?idioma=en", data=dados)

    from precificador.montador import TEMPLATES
    base = dict(inicio="2026-09-04", vencimento="2031-09-04",
                nocional="100.000.000,00", meses_periodo="6", amortizacao="bullet",
                fee="0", calendario="ANBIMA", convencao_dia_util="following",
                data_curva="2026-09-04", spot="5,15", resolver="passiva",
                modo_cdi="spread", valor_passiva="",
                sofr="96.345, 96.38, 96.42, 96.46",
                term_sofr="3,64637, 3,65811, 3,67358, 3,73148")
    for tpl in TEMPLATES:
        app.test_client().get(f"/precificar?idioma=en&template={tpl.id}")
        app.test_client().post("/precificar?idioma=en", data=dict(
            base, perna_ativa=tpl.ativa, perna_passiva=tpl.passiva,
            valor_ativa=tpl.valor_ativa or "10"))


def test_nenhuma_string_fica_sem_traducao():
    """Em inglês, nenhuma frase pode cair de volta no português.

    Sem esta trava a falta de tradução é silenciosa: ``t()`` devolve o original
    e a frase em português se perde no meio de uma tela em inglês. O audit
    registra cada falta e este teste as lista por nome, para não sobrar caça ao
    tesouro.
    """
    from webapp import create_app, idiomas
    idiomas.auditar(True)
    try:
        _exercitar_aplicacao(create_app())
        faltando = sorted(idiomas.faltando())
    finally:
        idiomas.auditar(False)

    assert not faltando, (
        f"{len(faltando)} frases sem tradução em webapp/idiomas.py:\n  "
        + "\n  ".join(repr(f) for f in faltando[:25]))


# palavras que denunciam português na tela em inglês. Termos de mercado que o
# inglês empresta do português ficam de fora de propósito — casado, Selic,
# Ibovespa e os nomes de curva da B3 não se traduzem.
_MARCADORES_PT = re.compile(
    r"\b(taxa|taxas|dias|corridos|úteis|anos|meses|prazo|prazos|valor|valores|juros|"
    r"vencimento|fluxo|fator|preço|preços|cupom|cambial|dólar|planilha|macro|"
    r"rendimento|líquido|alíquota|período|equivalente|zerado|após|acúmulo|série|"
    r"guardados|vigentes|publicação|anterior|defasagem|janela|não|são|com|para|uma|"
    r"pelo|pela|dos|das|que|mas|também)\b", re.IGNORECASE)

_PERMITIDO = {
    "casado", "selic", "ibovespa", "libor", "euribor", "sofr", "anbima", "b3",
    "cetip", "ptx", "ddi", "doc", "pré", "tbf", "igp-m", "ipca", "cdi", "di",
    "ndf", "imm", "target2", "bcb",
}


def _texto_visivel(html: str):
    corpo = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "",
                   html, flags=re.S)
    for bruto in re.findall(r">([^<>]+)<", corpo):
        texto = " ".join(bruto.split())
        if len(texto) > 3 and "http" not in texto:
            yield texto


def test_nenhum_texto_em_portugues_sobra_na_tela_em_ingles():
    """A outra metade da varredura: o que nunca passou por ``t()``.

    ``test_nenhuma_string_fica_sem_traducao`` pega a frase que foi embrulhada e
    não tinha tradução. Este pega a que nem chegou a ser embrulhada — literal
    solto no template, rótulo concatenado, dado vindo do Python. Juntos, os dois
    fecham o cerco: não há como uma frase em português chegar à tela em inglês.
    """
    from webapp import create_app
    app = create_app()
    suspeitas = []

    paginas = ["/", "/curvas?curva=DOC&extrair=1", "/curvas?curva=PTX&extrair=1",
               "/precificar", "/ndf", "/sofr", "/term-sofr", "/euribor",
               "/renda-fixa", "/liquidacao", "/interpolar", "/ni-pro-rata",
            "/metodologia"]
    def varrer(rotulo, html):
        for texto in _texto_visivel(html):
            achados = {p.lower() for p in _MARCADORES_PT.findall(texto)}
            if achados - _PERMITIDO:
                suspeitas.append(f"{rotulo}: {texto[:90]}")

    for rota in paginas:
        separador = "&" if "?" in rota else "?"
        varrer(rota, app.test_client().get(rota + separador + "idioma=en").data.decode())

    # metade do texto destas telas só existe depois do POST
    for chave, dados in FORMULARIOS.items():
        rota = _rota_do_formulario(chave)
        varrer(chave, app.test_client().post(rota + "?idioma=en", data=dados).data.decode())

    assert not suspeitas, (
        f"{len(suspeitas)} trechos em português na tela em inglês:\n  "
        + "\n  ".join(suspeitas[:20]))


# --------------------------------------------------- câmbio e base do SOFR --

def test_vencimentos_do_dol_caem_no_primeiro_dia_util_do_mes():
    from precificador import cambio
    cal = calendario_anbima()
    vencs = cambio.vencimentos_dol(date(2026, 9, 4), 3, cal)
    assert len(vencs) == 3
    for v in vencs:
        assert cal.eh_dia_util(v)
        anterior = v - __import__("datetime").timedelta(days=1)
        # não há dia útil antes dele dentro do mesmo mês
        while anterior.month == v.month:
            assert not cal.eh_dia_util(anterior)
            anterior -= __import__("datetime").timedelta(days=1)
    assert vencs == sorted(vencs)


def test_futuro_de_dolar_sai_da_curva_de_preco_em_pontos():
    """O DOL é cotado em milésimos: 5,16 na curva vira 5.160 pontos."""
    from precificador import cambio
    from precificador.curvas import PRECO
    plana = Curva.de_listas([1, 20000], [5.16, 5.16], "PTX plana", date(2026, 9, 4),
                            dias_uteis=[1, 14000], convencao=PRECO, metodo="linear")
    futuros = cambio.futuros_dol(date(2026, 9, 4), plana, 2)
    assert len(futuros) == 2
    assert futuros[0].preco == pytest.approx(5160.0)
    assert futuros[0].taxa == pytest.approx(5.16)
    assert futuros[0].dias_corridos > 0


def test_base_do_sofr_so_acrescenta():
    from precificador import sofr
    base = {"2026-09-04": {"overnight": 0.0366}}
    novos = sofr._mesclar(base, {
        "2026-09-04": {"overnight": 0.99, "media30": 0.0364},   # overnight ignorado
        "2026-09-08": {"overnight": 0.0367},
    })
    assert novos == 2
    assert base["2026-09-04"]["overnight"] == pytest.approx(0.0366)
    assert base["2026-09-04"]["media30"] == pytest.approx(0.0364)
    assert "2026-09-08" in base


def test_historico_do_sofr_em_data_de_referencia():
    from precificador import sofr
    h = sofr.HistoricoSOFR({
        "2026-09-03": {"overnight": 0.0365, "media30": 0.0364},
        "2026-09-04": {"overnight": 0.0366, "media30": 0.0365},
    })
    assert h.inicio == date(2026, 9, 3) and h.fim == date(2026, 9, 4)
    assert h.campos == ["overnight", "media30"]
    vigente, taxas = h.em(date(2026, 9, 6))       # domingo
    assert vigente == date(2026, 9, 4)
    assert taxas["overnight"] == pytest.approx(0.0366)
    assert h.em(date(2017, 1, 1)) == (None, {})


def test_camada_de_rede_cai_para_urllib_sem_sso():
    """Sem PRECIFICADOR_SSO a sessão é None e tudo vai por urllib."""
    import os
    from precificador import rede
    anterior = os.environ.pop("PRECIFICADOR_SSO", None)
    try:
        assert not rede.sso_ligado()
        assert rede.sessao() is None
        estado = rede.diagnostico()
        assert estado["sso_pedido"] is False
        assert set(estado) >= {"sso_pedido", "sso_disponivel", "requests",
                               "negotiate_sspi", "kerberos", "ca_bundle", "sem_proxy"}
    finally:
        if anterior is not None:
            os.environ["PRECIFICADOR_SSO"] = anterior


def test_camada_de_rede_exige_handler_quando_sso_ligado():
    """Ligar o SSO sem o pacote Negotiate tem que falar isso, não falhar calado."""
    import os
    from precificador import rede
    os.environ["PRECIFICADOR_SSO"] = "1"
    try:
        if rede.sso_disponivel():
            pytest.skip("esta máquina tem handler Negotiate instalado")
        with pytest.raises(rede.ErroRede) as erro:
            rede.sessao()
        assert "requests" in str(erro.value).lower()
    finally:
        os.environ.pop("PRECIFICADOR_SSO", None)


# ------------------------------------------------------- NDF multi-moeda ----

def _curva_plana(taxa, convencao, metodo="linear"):
    from precificador.curvas import Curva, Vertice
    return Curva(nome="teste", data_referencia=date(2026, 9, 4),
                 vertices=[Vertice(du, dc, taxa)
                           for du, dc in ((1, 1), (252, 365), (504, 730))],
                 convencao=convencao, metodo=metodo)


def test_moeda_com_cupom_publicado_usa_a_paridade_coberta():
    from precificador.b3 import EXP252, LIN360
    from precificador.produtos import curva_ndf, moeda_ndf, ndf_forward

    di = _curva_plana(0.1354, EXP252)
    cupom = _curva_plana(0.0557, LIN360)
    p = curva_ndf(date(2026, 9, 4), 5.13, di, cupom, [date(2027, 9, 1)],
                  moeda=moeda_ndf("USD"))[0]

    assert p.ndf == pytest.approx(
        ndf_forward(5.13, 0.1354, 0.0557, p.dias_corridos, p.dias_uteis))
    assert p.pontos == pytest.approx((p.ndf - 5.13) * 10_000.0)


def test_cupom_implicito_devolve_o_cupom_que_gerou_o_preco():
    """Ida e volta: o cupom implícito na curva de preço é o que a criou."""
    from precificador.produtos import cupom_implicito, ndf_forward

    spot, di, cupom, dc, du = 5.13, 0.1354, 0.0557, 362, 247
    termo = ndf_forward(spot, di, cupom, dc, du)
    assert cupom_implicito(spot, termo, di, dc, du) == pytest.approx(cupom)


def test_moeda_sem_curva_de_cupom_implica_o_cupom_no_preco():
    from precificador.b3 import EXP252, PRECO
    from precificador.produtos import curva_ndf, moeda_ndf

    di = _curva_plana(0.1354, EXP252)
    preco = _curva_plana(0.0345, PRECO)
    p = curva_ndf(date(2026, 9, 4), 0.0340, di, None, [date(2027, 9, 1)],
                  curva_preco=preco, moeda=moeda_ndf("JPY"))[0]

    # o termo volta a ser o preço lido na curva, e o iene conta em pips de 1e6
    assert p.ndf == pytest.approx(0.0345, abs=1e-9)
    assert p.pontos == pytest.approx((0.0345 - 0.0340) * 1_000_000.0)


def test_cross_de_precos_nao_passa_pelo_di():
    from precificador.b3 import PRECO
    from precificador.produtos import curva_ndf, moeda_ndf

    preco = _curva_plana(1.1782, PRECO)
    p = curva_ndf(date(2026, 9, 4), 1.1540, None, None, [date(2027, 9, 1)],
                  curva_preco=preco, moeda=moeda_ndf("EURUSD"))[0]

    assert p.di == 0.0
    assert p.ndf == pytest.approx(1.1782)


def test_moeda_livre_desconta_pela_taxa_digitada():
    from precificador.b3 import EXP252
    from precificador.produtos import curva_ndf, moeda_ndf, ndf_forward

    di = _curva_plana(0.1354, EXP252)
    p = curva_ndf(date(2026, 9, 4), 6.90, di, None, [date(2027, 9, 1)],
                  moeda=moeda_ndf("LIVRE"), taxa_estrangeira=0.0425)[0]

    assert p.cupom == pytest.approx(0.0425)
    assert p.ndf == pytest.approx(
        ndf_forward(6.90, 0.1354, 0.0425, p.dias_corridos, p.dias_uteis))


def test_cada_moeda_cobra_a_curva_que_o_seu_modo_exige():
    from precificador.produtos import curva_ndf, moeda_ndf

    datas = [date(2027, 9, 1)]
    with pytest.raises(ValueError):                       # cupom sem curva de cupom
        curva_ndf(date(2026, 9, 4), 5.13, _curva_plana(0.13, "EXP252"), None,
                  datas, moeda=moeda_ndf("USD"))
    with pytest.raises(ValueError):                       # implícito sem curva de preço
        curva_ndf(date(2026, 9, 4), 0.034, _curva_plana(0.13, "EXP252"), None,
                  datas, moeda=moeda_ndf("JPY"))
    with pytest.raises(ValueError):                       # cross sem curva de preço
        curva_ndf(date(2026, 9, 4), 1.15, None, None, datas,
                  moeda=moeda_ndf("EURUSD"))


def test_moeda_desconhecida_cai_no_dolar():
    from precificador.produtos import MOEDA_NDF_PADRAO, moeda_ndf
    assert moeda_ndf("XYZ") is MOEDA_NDF_PADRAO
    assert moeda_ndf(None) is MOEDA_NDF_PADRAO
    assert moeda_ndf("usd").codigo == "USD"


def test_escada_mensal_abre_no_mes_corrente():
    """O primeiro degrau é o fim do mês em que a data-base está, não do seguinte."""
    from precificador.produtos import escada_datas
    cal = calendario_anbima()

    datas = escada_datas(date(2026, 9, 4), "mensal", 5, cal)
    assert datas[0] == date(2026, 9, 30)
    assert datas[1] == date(2026, 10, 30)

    # trimestral também abre no mês corrente, e só então salta de três em três
    trimestral = escada_datas(date(2026, 9, 4), "trimestral", 3, cal)
    assert trimestral == [date(2026, 9, 30), date(2026, 12, 31), date(2027, 3, 31)]


def test_escada_pula_o_mes_corrente_quando_a_base_ja_o_alcancou():
    """Na virada do mês o degrau sai, mas a contagem de vencimentos não encolhe."""
    from precificador.produtos import escada_datas
    cal = calendario_anbima()

    datas = escada_datas(date(2026, 9, 30), "mensal", 5, cal)
    assert len(datas) == 5
    assert datas[0] == date(2026, 10, 30)
    assert all(d > date(2026, 9, 30) for d in datas)


# ------------------------------------------- falha de fonte nao vira 500 ----

def test_toda_excecao_de_fonte_herda_da_base():
    """Uma fonte nova so entra no sistema se a tela souber trata-la.

    A garantia e que nenhuma excecao do pacote escape do ``except`` das rotas.
    Elas capturam ``(ErroFormulario, ErroDeFonte, ValueError)``, entao ha dois
    jeitos legitimos de estar coberto: herdar de ``ErroDeFonte``, para falha de
    fonte externa, ou de ``ValueError``, para dado de entrada que nao fecha.
    O que nao pode e uma terceira via — dai o teste.
    """
    import pkgutil, importlib, inspect
    import precificador
    from precificador.erros import ErroDeFonte

    fora = []
    for m in pkgutil.iter_modules(precificador.__path__):
        modulo = importlib.import_module(f"precificador.{m.name}")
        for nome, classe in vars(modulo).items():
            if (inspect.isclass(classe) and classe.__module__ == modulo.__name__
                    and issubclass(classe, Exception) and nome.startswith("Erro")
                    and classe is not ErroDeFonte
                    and not issubclass(classe, (ErroDeFonte, ValueError))):
                fora.append(f"{modulo.__name__}.{nome}")
    assert not fora, ("estas excecoes nao herdam de ErroDeFonte nem de ValueError, "
                      f"entao escapam do except das telas: {fora}")


def test_rede_fora_do_ar_nao_derruba_nenhuma_tela():
    """Com a saida bloqueada, cada tela mostra aviso — nunca um traceback.

    Reproduz o WinError 10060 da rede corporativa: a conexao nem chega ao
    servidor. Foi assim que a calculadora de renda fixa devolveu um traceback
    do Flask, porque a rota nao listava ErroBCB na sua tupla de except.
    """
    from unittest.mock import patch
    from webapp import create_app
    from precificador import rede

    def bloqueado(*a, **k):
        raise rede.ErroRede(
            "falha de conexão com https://api.bcb.gov.br: [WinError 10060] "
            "A connection attempt failed")

    app = create_app()
    app.config["PROPAGATE_EXCEPTIONS"] = False
    cliente = app.test_client()

    with patch.object(rede, "obter", bloqueado), patch.object(rede, "obter_json", bloqueado):
        for chave, dados in FORMULARIOS.items():
            rota = _rota_do_formulario(chave)
            r = cliente.post(rota, data=dados)
            assert r.status_code == 200, (
                f"{rota} devolveu {r.status_code} com a rede bloqueada — "
                "a tela deveria mostrar o aviso, não estourar")
        for rota in ("/", "/curvas?curva=DOC&extrair=1", "/ndf", "/sofr",
                     "/term-sofr", "/euribor", "/metodologia", "/api/cambio",
                     "/api/ndf/spot"):
            r = cliente.get(rota)
            assert r.status_code in (200, 502), (
                f"{rota} devolveu {r.status_code} com a rede bloqueada")


def test_timeout_de_saida_explica_o_proxy():
    """A mensagem tem que apontar o proxy, não mandar investigar o servidor."""
    from precificador import rede
    pista = rede._pista_de_proxy(OSError("[WinError 10060] A connection attempt failed"))
    assert "proxy" in pista.lower() and "PRECIFICADOR_PROXY" in pista
    # erro de verdade do servidor não ganha a pista
    assert rede._pista_de_proxy(OSError("HTTP 404")) == ""


# ----------------------------------------------- contagem de dias e liquidação

def test_cada_convencao_conta_o_seu_proprio_numero_de_dias():
    """O mesmo período tem uma contagem diferente em cada convenção.

    É o motivo de a contagem ser campo de tela e não constante de código: quem
    liquida um swap contra uma confirmação de fora precisa reproduzir a régua da
    contraparte, não a nossa.
    """
    from precificador import contagem
    inicio, fim = date(2026, 1, 31), date(2026, 7, 31)
    cal = calendario_anbima()

    assert contagem.dias(contagem.ACT_360, inicio, fim) == 181
    assert contagem.dias(contagem.ACT_365, inicio, fim) == 181
    # na régua de 30 dias, seis meses são exatamente 180
    assert contagem.dias(contagem.T30_360, inicio, fim) == 180
    assert contagem.dias(contagem.T30E_360, inicio, fim) == 180
    assert contagem.dias(contagem.DU_252, inicio, fim, cal) < 181

    # e o τ segue o denominador de cada uma
    assert contagem.fracao(contagem.ACT_360, inicio, fim) == 181 / 360
    assert contagem.fracao(contagem.ACT_365, inicio, fim) == 181 / 365
    assert contagem.fracao(contagem.T30_360, inicio, fim) == 0.5


def test_30_360_e_30e_360_so_diferem_no_dia_final():
    """A única diferença entre as duas: quem trunca o dia 31 do fim."""
    from precificador import contagem
    # 30/360 não baixa o dia final porque o inicial (30) não veio de um 31
    assert contagem.dias(contagem.T30_360, date(2026, 2, 28), date(2026, 8, 31)) == 183
    assert contagem.dias(contagem.T30E_360, date(2026, 2, 28), date(2026, 8, 31)) == 182


def test_act_act_divide_cada_trecho_pelo_ano_dele():
    """Um ano cheio é 1,0 mesmo atravessando um bissexto."""
    from precificador import contagem
    assert contagem.fracao(contagem.ACT_ACT, date(2024, 1, 1), date(2025, 1, 1)) == 1.0
    assert contagem.fracao(contagem.ACT_ACT, date(2026, 1, 1), date(2027, 1, 1)) == 1.0
    # um ano que atravessa um bissexto passa um pouco de 1,0: 184 dias sobre 365
    # em 2023 mais 182 sobre 366 em 2024. É a convenção funcionando, não erro.
    meio = contagem.fracao(contagem.ACT_ACT, date(2023, 7, 1), date(2024, 7, 1))
    assert abs(meio - (184 / 365 + 182 / 366)) < 1e-12
    assert 1.0 < meio < 1.002


def test_regime_simples_e_composto_dao_numeros_diferentes():
    from precificador import contagem
    inicio, fim = date(2026, 1, 2), date(2027, 1, 2)
    simples = contagem.fator(0.10, contagem.ACT_360, contagem.SIMPLES, inicio, fim)
    composto = contagem.fator(0.10, contagem.ACT_360, contagem.COMPOSTO, inicio, fim)
    # num ano civil ACT/360 dá τ = 365/360 > 1, e aí o composto passa o simples:
    # ele capitaliza o próprio juro na fração de ano que sobra
    assert composto > simples
    assert abs(simples - (1 + 0.10 * 365 / 360)) < 1e-12
    assert abs(composto - 1.10 ** (365 / 360)) < 1e-12


def test_liquidacao_aplica_o_saldo_remanescente_e_nao_o_original():
    """A base das duas pontas é o que sobrou, não o valor de registro.

    Este é o erro que o módulo existe para não deixar acontecer: num swap já
    amortizado pela metade, usar o notional de registro dobra o ajuste.
    """
    from precificador import liquidacao as L
    comum = dict(data_operacao="2025-09-08", inicio="2025-09-08", fim="2026-09-04",
                 ponta_ativa=L.Ponta(L.PRE, 0.14),
                 ponta_passiva=L.Ponta(L.FATOR, fator_manual=1.10),
                 reter_ir=False)
    metade = L.liquidar(nocional=50e6, nocional_original=100e6, **comum)
    inteiro = L.liquidar(nocional=100e6, nocional_original=100e6, **comum)
    assert abs(inteiro.ajuste_bruto - 2 * metade.ajuste_bruto) < 1e-6
    assert metade.nocional == 50e6


def test_amortizacao_muda_de_valor_conforme_a_base():
    """Os mesmos 10% valem coisas diferentes sobre original e sobre remanescente."""
    from precificador import liquidacao as L
    assert L.amortizar(100e6, 60e6, 0.10, L.SOBRE_ORIGINAL) == 10e6
    assert L.amortizar(100e6, 60e6, 0.10, L.SOBRE_REMANESCENTE) == 6e6
    # e nunca amortiza mais do que existe de saldo
    assert L.amortizar(100e6, 5e6, 0.10, L.SOBRE_ORIGINAL) == 5e6


def test_amortizacao_nao_entra_no_fator_do_proprio_fluxo():
    """Ela define o saldo do fluxo seguinte, não a base deste."""
    from precificador import liquidacao as L
    comum = dict(data_operacao="2025-09-08", inicio="2025-09-08", fim="2026-09-04",
                 nocional=50e6, nocional_original=100e6, reter_ir=False,
                 ponta_ativa=L.Ponta(L.PRE, 0.14),
                 ponta_passiva=L.Ponta(L.FATOR, fator_manual=1.10))
    sem = L.liquidar(percentual_amortizacao=0.0, **comum)
    com = L.liquidar(percentual_amortizacao=0.10, **comum)
    assert sem.ajuste_bruto == com.ajuste_bruto
    assert com.saldo_seguinte == 40e6 and sem.saldo_seguinte == 50e6


def test_ponta_em_moeda_separa_o_indice_do_cambio():
    """As duas metades do fator ficam guardadas separadas.

    Uma ponta cambial que rende 3,25% de cupom com o dólar caindo 1,5% não
    rendeu 3,25% em reais, e o resultado tem que deixar ver qual das duas
    explicou o número.
    """
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 20e6,
                   L.Ponta(L.CAMBIO, taxa=0.0325, moeda="USD",
                           ptax_inicial=5.40, ptax_final=5.32,
                           convencao="act_360", regime="simples"),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    a = r.ativa
    assert abs(a.fator_do_indice - (1 + 0.0325 * a.dias_corridos / 360)) < 1e-12
    assert abs(a.fator_cambial - 5.32 / 5.40) < 1e-12
    assert abs(a.fator - a.fator_do_indice * a.fator_cambial) < 1e-12


def test_fluxo_em_reais_nao_converte():
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 10e6,
                   L.Ponta(L.CAMBIO, taxa=0.0325, moeda=L.SEM_CONVERSAO,
                           convencao="act_360", regime="simples"),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    assert r.ativa.fator_cambial == 1.0
    assert abs(r.ativa.fator - r.ativa.fator_do_indice) < 1e-12


def test_equity_e_quanto_e_ignora_a_variacao_cambial():
    """Ação e índice liquidam em reais sem passar pelo câmbio.

    Um swap de S&P entrega o S&P, não o S&P mais dólar. Se o fator cambial
    entrasse, um índice que subiu 9,06% com o dólar caindo 1,53% viraria 7,45%
    em reais — e o cliente que comprou o índice receberia outra coisa.

    O teste enche os campos de fixing de propósito: mesmo preenchidos, eles não
    podem mudar o número.
    """
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 20e6,
                   L.Ponta(L.EQUITY, ativo="S&P 500", preco_inicial=6400,
                           preco_final=6980, moeda="USD",
                           ptax_inicial=5.4012, ptax_final=5.3188),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    a = r.ativa
    assert a.quanto is True and a.moeda == "USD"
    assert a.fator_cambial == 1.0
    assert abs(a.fator - 6980 / 6400) < 1e-12          # o retorno puro do índice
    assert a.ptax_inicial is None and a.ptax_final is None
    assert L.EQUITY not in L.COM_MOEDA


def test_equity_em_reais_tambem_rende_so_o_indice():
    """Um índice local não tem moeda para declarar, e a conta é a mesma."""
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 10e6,
                   L.Ponta(L.EQUITY, ativo="IBOV", preco_inicial=140000,
                           preco_final=152000, moeda=L.SEM_CONVERSAO),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    assert r.ativa.quanto is False              # em reais não há o que "quantizar"
    assert abs(r.ativa.fator - 152000 / 140000) < 1e-12


def test_fixing_de_taxa_a_termo_cai_em_d_menos_2_uteis():
    """EURIBOR e Term SOFR são fixados antes de o fluxo começar."""
    from precificador import liquidacao as L
    cal = calendario_anbima()
    # 2026-09-04 é uma sexta-feira; D-2 úteis é a quarta anterior
    assert L.data_de_fixing(date(2026, 9, 4), cal) == date(2026, 9, 2)
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 10e6,
                   L.Ponta(L.TERM_SOFR, taxa=0.015, taxa_indice=0.0432,
                           moeda=L.SEM_CONVERSAO),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    assert r.ativa.data_fixing == L.data_de_fixing(date(2025, 9, 8), cal)


def test_term_sofr_sem_taxa_digitada_explica_a_licenca():
    """A taxa da CME não pode ser redistribuída — o erro tem que dizer isso."""
    from precificador import liquidacao as L
    with pytest.raises(L.ErroLiquidacao) as exc:
        L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 10e6,
                   L.Ponta(L.TERM_SOFR, taxa=0.015), L.Ponta(L.PRE, 0.14))
    assert "licenciado" in str(exc.value)


def test_liquidacao_recusa_indice_realizado_no_futuro():
    """CDI e PTAX são o que aconteceu; não há fixing de amanhã."""
    from precificador import liquidacao as L
    amanha = date.today() + __import__("datetime").timedelta(days=30)
    with pytest.raises(L.ErroLiquidacao) as exc:
        L.liquidar("2025-01-02", "2025-01-02", amanha, 10e6,
                   L.Ponta(L.CDI_PERCENTUAL, 1.0), L.Ponta(L.PRE, 0.14))
    assert "realizado" in str(exc.value)


def test_ir_sai_da_tabela_regressiva_contada_da_operacao():
    """O prazo do IR conta da contratação, não do início do fluxo."""
    from precificador import liquidacao as L
    ativa, passiva = L.Ponta(L.PRE, 0.20), L.Ponta(L.FATOR, fator_manual=1.0)
    # 2 anos e meio de operação: 15%
    longo = L.liquidar("2024-01-02", "2026-01-02", "2026-09-04", 10e6, ativa, passiva)
    assert longo.aliquota_ir == 0.15
    # o mesmo fluxo, contratado junto: 8 meses, 20%
    curto = L.liquidar("2026-01-02", "2026-01-02", "2026-09-04", 10e6, ativa, passiva)
    assert curto.aliquota_ir == 0.20
    assert abs(curto.ajuste_liquido - curto.ajuste_bruto * 0.80) < 1e-6


def test_resultado_negativo_nao_retem_ir():
    """Não se retém imposto sobre prejuízo."""
    from precificador import liquidacao as L
    r = L.liquidar("2026-01-02", "2026-01-02", "2026-09-04", 10e6,
                   L.Ponta(L.FATOR, fator_manual=1.0), L.Ponta(L.PRE, 0.20))
    assert r.ajuste_bruto < 0 and r.ir == 0.0 and r.quem_recebe == L.PASSIVA


def test_nenhum_select_da_aplicacao_chega_vazio_a_tela():
    """Um ``<select>`` sem opção é uma variável de contexto que faltou.

    O Jinja itera um nome indefinido em silêncio: o ``for`` não roda, o select
    sai vazio e a página continua devolvendo 200. Foi assim que o campo de
    calendário da tela de liquidação chegou à tela sem nenhuma opção — nada no
    log, nada no teste de rota, só um campo em branco. Este teste varre o HTML
    de cada tela e falha no select que não tem nem uma ``<option>``.
    """
    from webapp import create_app
    app = create_app()
    vazios = []

    def varrer(rotulo, html):
        for atributos, miolo in re.findall(r"<select([^>]*)>(.*?)</select>", html, re.S):
            if "<option" not in miolo:
                nome = re.search(r'name="([^"]+)"', atributos)
                vazios.append(f"{rotulo}: {nome.group(1) if nome else atributos.strip()}")

    paginas = ["/", "/curvas", "/precificar", "/ndf", "/sofr", "/term-sofr",
               "/euribor", "/renda-fixa", "/liquidacao", "/interpolar",
               "/ni-pro-rata", "/metodologia"]
    for rota in paginas:
        varrer(rota, app.test_client().get(rota).data.decode())
    for chave, dados in FORMULARIOS.items():
        rota = _rota_do_formulario(chave)
        varrer(chave, app.test_client().post(rota, data=dados).data.decode())

    assert not vazios, ("estes select chegaram à tela sem nenhuma opção — falta a "
                        f"variável no contexto da rota: {vazios}")


def test_sofr_composto_acumula_os_fixings_do_proprio_periodo():
    """A ponta de SOFR composto olha para trás — sem data de fixação.

    Ela é o contraponto do Term SOFR: uma acumula o que aconteceu dia a dia, a
    outra usa uma taxa fixada antes de o período começar. O fator da primeira
    tem que sair do produto dos fixings, e não de uma taxa só.
    """
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.SOFR, taxa=0.015, moeda=L.SEM_CONVERSAO,
                           convencao="act_360", regime="simples"),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    a = r.ativa
    assert len(a.fixings) > 200                 # um fixing por dia útil do ano
    assert 0.02 < a.taxa_do_fixing < 0.08       # SOFR realizado, não uma taxa digitada
    # ``taxa_do_fixing`` é o SOFR composto **anualizado**: para virar fator ele
    # volta a passar pela mesma ACT/360 de onde saiu. Depois entra o spread.
    composto = 1 + a.taxa_do_fixing * a.dias_corridos / 360
    esperado = composto * (1 + 0.015 * a.dias_corridos / 360)
    assert abs(a.fator_do_indice - esperado) < 1e-9
    assert a.data_fixing is None                # não há data de fixação aqui


def test_moeda_pura_rende_so_a_variacao_cambial():
    """Uma ponta de moeda não tem cupom, nem índice, nem contagem de dias.

    É o desenho mais simples que existe: o notional segue a moeda e mais nada.
    Como não há taxa, não há o que capitalizar — e o resultado precisa deixar
    isso explícito em vez de devolver uma convenção que não pesou no número.
    """
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.MOEDA, moeda="CNH",
                           ptax_inicial=0.7620, ptax_final=0.7845),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    a = r.ativa
    assert a.fator_do_indice == 1.0                     # não há índice
    assert abs(a.fator - 0.7845 / 0.7620) < 1e-12       # só a moeda
    assert a.convencao is None and a.fracao_de_ano is None
    assert L.MOEDA in L.SEM_TAXA


def test_moeda_fora_do_boletim_do_bcb_exige_os_fixings():
    """O BCB boletina dez moedas. Fora delas não há PTAX para buscar.

    Sem esta trava a ponta de yuan iria bater na fonte e voltar com um erro de
    rede, que manda procurar o problema no lugar errado.
    """
    from precificador import liquidacao as L
    assert "CNH" not in L.MOEDAS_AUTOMATICAS and "USD" in L.MOEDAS_AUTOMATICAS
    with pytest.raises(L.ErroLiquidacao) as exc:
        L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.MOEDA, moeda="CNH"), L.Ponta(L.PRE, 0.14))
    assert "não boletina CNH" in str(exc.value)


def test_lista_de_moedas_automaticas_e_a_do_boletim_do_bcb():
    """As dez do boletim, conferidas contra o endpoint de moedas do Olinda."""
    from precificador import liquidacao as L
    assert L.MOEDAS_AUTOMATICAS == {
        L.SEM_CONVERSAO, "USD", "EUR", "GBP", "JPY", "CHF",
        "CAD", "AUD", "DKK", "NOK", "SEK"}


def test_moeda_pura_em_reais_nao_faz_sentido():
    from precificador import liquidacao as L
    with pytest.raises(L.ErroLiquidacao) as exc:
        L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.MOEDA, moeda=L.SEM_CONVERSAO), L.Ponta(L.PRE, 0.14))
    assert "moeda estrangeira" in str(exc.value)


def test_resultado_serializa_para_quem_chama_de_fora():
    """O motor serve sem a tela — o OTC tracker chama ``liquidar`` direto.

    ``para_dict`` tem que sair em tipos que o ``json`` aceita, com as datas em
    ISO e a descrição de cada ponta já montada em vez do par (molde, valores),
    que só a tela bilíngue usa.
    """
    import json
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.MOEDA, moeda="CNH",
                           ptax_inicial=0.7620, ptax_final=0.7845),
                   L.Ponta(L.CDI_PERCENTUAL, 1.05))
    d = r.para_dict()
    texto = json.dumps(d, ensure_ascii=False)      # falha se sobrar date ou objeto
    assert d["fim"] == "2026-09-04"
    assert d["ativa"]["descricao"] == "variação de 2,9528%, sem cupom"
    assert isinstance(d["passiva"]["fixings"], int)    # a contagem, não a lista
    assert d["ativa"]["convencao"] is None             # ponta sem taxa
    assert '"quem_recebe"' in texto


def test_lookback_e_shift_mudam_o_sofr_da_liquidacao():
    """As duas defasagens entram na conta — e não são a mesma coisa.

    ``lookback`` desloca só a leitura da taxa; ``shift`` desloca a janela
    inteira, datas e pesos. Se os campos existirem na tela mas não chegarem ao
    motor, os quatro números abaixo saem iguais e ninguém percebe.
    """
    from precificador import liquidacao as L
    comum = dict(data_operacao="2025-09-08", inicio="2025-09-08", fim="2026-09-04",
                 nocional=30e6, ponta_passiva=L.Ponta(L.PRE, 0.14), reter_ir=False)

    def sofr(lookback, shift):
        r = L.liquidar(ponta_ativa=L.Ponta(L.SOFR, taxa=0.015, moeda=L.SEM_CONVERSAO,
                                           convencao="act_360", regime="simples",
                                           lookback=lookback, shift=shift), **comum)
        return r.ativa

    puro, com_lb, com_sh, com_ambos = sofr(0, 0), sofr(5, 0), sofr(0, 2), sofr(5, 2)
    taxas = {p.taxa_do_fixing for p in (puro, com_lb, com_sh, com_ambos)}
    assert len(taxas) == 4, "as defasagens não chegaram ao cálculo"

    # o shift move a janela; o lookback não
    assert com_sh.obs_inicio < puro.obs_inicio and com_sh.obs_fim < puro.obs_fim
    assert com_lb.obs_inicio == puro.obs_inicio and com_lb.obs_fim == puro.obs_fim
    # e é o lookback que faz a taxa vir de outro dia
    assert any(d.defasado for d in com_lb.fixings)
    assert not any(d.defasado for d in com_sh.fixings)


def test_sofr_com_defasagem_busca_os_fixings_anteriores_ao_fluxo():
    """A janela de observação começa antes do fluxo, e a série tem que cobri-la.

    Buscar só o período deixava a composição sem os fixings que ela ia ler, e o
    erro estourava lá na fonte — mandando procurar o problema no NY Fed quando
    o problema era o intervalo pedido.
    """
    from precificador import liquidacao as L
    r = L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                   L.Ponta(L.SOFR, taxa=0.015, moeda=L.SEM_CONVERSAO,
                           convencao="act_360", regime="simples",
                           lookback=10, shift=5),
                   L.Ponta(L.PRE, 0.14), reter_ir=False)
    a = r.ativa
    assert a.obs_inicio < date(2025, 9, 8)          # a janela recuou
    assert min(d.data_observacao for d in a.fixings) < date(2025, 9, 8)


def test_defasagem_do_sofr_tem_teto():
    from precificador import liquidacao as L
    for campo in ("lookback", "shift"):
        with pytest.raises(L.ErroLiquidacao) as exc:
            L.liquidar("2025-09-08", "2025-09-08", "2026-09-04", 30e6,
                       L.Ponta(L.SOFR, taxa=0.015, moeda=L.SEM_CONVERSAO,
                               **{campo: L.LIMITE_DEFASAGEM + 1}),
                       L.Ponta(L.PRE, 0.14))
        assert "dias úteis" in str(exc.value)


def test_fixings_das_duas_fontes_chegam_na_mesma_forma():
    """CDI e SOFR têm formatos próprios; a tela recebe um só.

    Enquanto a tela leu o objeto cru, uma ponta de SOFR derrubava a página
    inteira: a tabela pedia ``.data`` num ``DiaComposicao``, que tem
    ``data_juros``. Um 500 em vez de um resultado.
    """
    from precificador import liquidacao as L
    comum = dict(data_operacao="2025-09-08", inicio="2025-09-08", fim="2026-09-04",
                 nocional=30e6, ponta_passiva=L.Ponta(L.PRE, 0.14), reter_ir=False)
    de_cdi = L.liquidar(ponta_ativa=L.Ponta(L.CDI_PERCENTUAL, 1.0), **comum).ativa
    de_sofr = L.liquidar(ponta_ativa=L.Ponta(L.SOFR, taxa=0.0, moeda=L.SEM_CONVERSAO,
                                             convencao="act_360", regime="simples",
                                             lookback=5), **comum).ativa
    for ponta in (de_cdi, de_sofr):
        assert ponta.fixings and all(isinstance(d, L.DiaDoFator) for d in ponta.fixings)
        primeiro = ponta.fixings[0]
        assert isinstance(primeiro.data, date)
        assert primeiro.fator_dia > 0 and primeiro.fator_acumulado > 0
    assert de_cdi.fixings[0].data_observacao is None      # o CDI não tem defasagem
    assert de_sofr.fixings[0].data_observacao is not None


def test_casado_entra_no_preco_com_o_sinal_do_fluxo():
    """Saída de moeda estrangeira soma o casado; entrada desconta.

    O casado é a distância entre o à vista e o futuro. Ele não é uma estatística
    de tela: entra no spot que precifica a curva, e o sinal vem da direção do
    fluxo. Sem isso, uma exportação e uma importação sairiam pelo mesmo preço.
    """
    from precificador.produtos import (ENTRADA, SAIDA, casado, sinal_do_casado,
                                       spot_com_casado)
    spot, primeiro = 5.4012, 5425.0
    pips = casado(primeiro, spot)
    assert abs(pips - 23.8) < 1e-9

    saida = spot_com_casado(spot, pips, SAIDA)
    entrada = spot_com_casado(spot, pips, ENTRADA)
    assert saida > spot > entrada
    assert abs((saida - spot) - (spot - entrada)) < 1e-12   # mesma distância

    # a identidade: numa saída o spot ajustado é o próprio 1º futuro em reais
    assert abs(saida - primeiro / 1000.0) < 1e-12
    assert sinal_do_casado(SAIDA) == 1 and sinal_do_casado(ENTRADA) == -1


def test_sem_casado_o_spot_passa_direto():
    """As moedas sem futuro na B3 não têm o que ajustar."""
    from precificador.produtos import ENTRADA, SAIDA, spot_com_casado
    for direcao in (SAIDA, ENTRADA):
        assert spot_com_casado(5.95, None, direcao) == 5.95
        assert spot_com_casado(5.95, 0.0, direcao) == 5.95


def test_direcao_do_fluxo_muda_a_curva_de_ndf_inteira():
    """O ajuste é no spot, então ele atravessa todos os vencimentos."""
    from webapp import create_app
    app = create_app()
    base = dict(data_curva="2026-09-04", moeda="USD", spot="5,4012",
                progressao="mensal", quantidade="4", calendario="ANBIMA",
                primeiro_futuro="5425", segundo_futuro="5450")
    telas = {}
    for direcao in ("saida", "entrada"):
        html = app.test_client().post("/ndf", data=dict(base, direcao=direcao)).data.decode()
        telas[direcao] = re.findall(r'tabular-nums">([\d.,\-]+)</p>', html)

    # o spot que precificou e o casado saem com sinais opostos
    assert telas["saida"][0] == "5,4250"      # = 1º futuro / 1.000
    assert telas["entrada"][0] == "5,3774"
    assert telas["saida"][1] == "23,80" and telas["entrada"][1] == "-23,80"
    assert telas["saida"] != telas["entrada"]


def test_toda_cor_usada_nos_templates_tem_regra_no_tema_claro():
    """Cor sem regra no tema claro é texto que some no fundo branco.

    A paleta é escrita para o escuro: ``text-cyan-100`` é quase branco, e no
    claro ele precisa virar um tom escuro. O arquivo de tema faz isso classe por
    classe, e por isso uma classe nova passa despercebida — foi o que aconteceu
    com as variantes de opacidade (``text-cyan-100/80``), dez trechos em cinco
    telas, todos ilegíveis no claro até alguém abrir a tela e olhar.

    Este teste varre os templates e cobra uma regra para cada cor clara usada.
    """
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent / "webapp"
    css = (raiz / "static" / "css" / "tema-claro.css").read_text(encoding="utf-8")

    # tons claros da paleta: no fundo branco eles não têm contraste nenhum
    claros = re.compile(r"text-(cyan|amber|emerald|rose|sky|violet)-(50|100|200)"
                        r"(/\d+)?")
    sem_regra = set()
    for template in sorted((raiz / "templates").glob("*.html")):
        for cor, tom, opacidade in claros.findall(template.read_text(encoding="utf-8")):
            classe = f"text-{cor}-{tom}"
            if opacidade:
                # a variante com opacidade é coberta pelo seletor de atributo
                coberta = f'[class*="{classe}/"]' in css
            else:
                coberta = f".{classe}" in css
            if not coberta:
                sem_regra.add(classe + (opacidade or ""))

    assert not sem_regra, ("estas cores não têm regra em tema-claro.css e somem "
                           f"no fundo branco: {sorted(sem_regra)}")
