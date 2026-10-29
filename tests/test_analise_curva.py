"""Análise da curva DI e as telas que a usam, sem rede."""

from datetime import date

import pytest

from precificador import analise_curva, b3
from precificador.calendario import calendario_anbima
from precificador.curvas import EXP252, Curva, Vertice

BASE = date(2026, 10, 28)
GRADE = [(1, 1), (21, 30), (63, 91), (126, 182), (252, 365), (504, 730),
         (1260, 1826), (2520, 3652)]


def _curva(nivel=0.14, inclinacao=0.0):
    """Curva sintética: nível + inclinação por ano de prazo."""
    return Curva(nome="DI x Pré", data_referencia=BASE, convencao=EXP252,
                 metodo="spline",
                 vertices=[Vertice(du, dc, nivel + inclinacao * du / 252) for du, dc in GRADE])


def test_termo_de_curva_plana_e_a_propria_taxa():
    assert analise_curva.termo(0.14, 252, 0.14, 504) == pytest.approx(0.14)
    # 10% por um ano e 12% por dois: o segundo ano sai a ~14%
    assert analise_curva.termo(0.10, 252, 0.12, 504) == pytest.approx(1.12 ** 2 / 1.10 - 1)


def test_pontos_caem_em_dia_util_e_trazem_a_termo():
    pontos = analise_curva.pontos(_curva(inclinacao=0.005), BASE, calendario_anbima())
    assert [p.rotulo for p in pontos] == [r for r, _ in analise_curva.PRAZOS_PADRAO]
    assert all(calendario_anbima().eh_dia_util(p.data) for p in pontos)
    assert pontos[0].termo is None
    # curva positivamente inclinada: cada a termo fica acima da taxa à vista
    assert all(p.termo > p.taxa for p in pontos[1:])
    assert analise_curva.inclinacao_bps(pontos, "1A", "5A") == pytest.approx(200, abs=5)


@pytest.mark.parametrize("curto, longo, nome", [
    (0.3, -0.2, "Estável"), (10, 12, "Paralelo para cima"), (-10, -8, "Paralelo para baixo"),
    (5, 30, "Bear steepening"), (30, 5, "Bear flattening"),
    (-30, -5, "Bull steepening"), (-5, -30, "Bull flattening"),
])
def test_classificacao_do_movimento(curto, longo, nome):
    assert analise_curva.classificar(curto, longo) == nome


def test_variacoes_casam_pelo_prazo():
    cal = calendario_anbima()
    hoje = analise_curva.pontos(_curva(0.15), BASE, cal)
    antes = analise_curva.pontos(_curva(0.14), date(2026, 10, 21), cal)
    assert all(v.bps == pytest.approx(100) for v in analise_curva.variacoes(hoje, antes))
    assert all(v.bps is None for v in analise_curva.variacoes(hoje, None))


def test_copom_em_curva_plana_nao_precifica_movimento():
    resultado = analise_curva.copom(
        _curva(0.14), BASE, calendario_anbima(),
        [date(2026, 12, 9), date(2027, 1, 27), date(2026, 9, 1)])
    # a reunião de setembro já passou e fica de fora
    assert [r.decisao for r in resultado.reunioes] == [date(2026, 12, 9), date(2027, 1, 27)]
    assert resultado.reunioes[0].vigencia == date(2026, 12, 10)
    assert resultado.reunioes[0].fim == date(2027, 1, 28)
    for r in resultado.reunioes:
        assert r.cdi_implicito == pytest.approx(0.14)
        assert r.movimento_bps == pytest.approx(0, abs=1e-6)


def test_copom_sem_reuniao_futura_e_none():
    assert analise_curva.copom(_curva(), BASE, calendario_anbima(), [date(2026, 1, 28)]) is None


def test_ler_datas_aceita_separadores_e_formatos():
    assert analise_curva.ler_datas("09/12/2026; 2027-01-27\n17/03/2027") == [
        date(2026, 12, 9), date(2027, 1, 27), date(2027, 3, 17)]


@pytest.fixture
def b3_sintetica(monkeypatch):
    from webapp import servicos

    def vertices(codigo, data):
        nivel = 5.40 if codigo in ("PTX", "EUR", "JPY", "INP") else (
            0.14 if codigo == "PRE" else 0.05)
        return [b3.VerticeB3(du, dc, nivel + 0.001 * du / 252) for du, dc in GRADE]
    monkeypatch.setattr(servicos, "vertices", vertices)


def test_tela_da_curva_di_com_copom(b3_sintetica):
    from webapp import create_app
    resposta = create_app().test_client().get(
        "/curva-di?data=2026-10-28&copom=09/12/2026,27/01/2027")
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Copom implícito na curva" in html
    assert "Prazos de referência" in html
    # mesma curva nas duas datas: a curva não andou
    assert "Estável" in html


def test_tela_da_curva_di_em_ingles(b3_sintetica):
    from webapp import create_app
    html = create_app().test_client().get(
        "/curva-di?idioma=en&data=2026-10-28&copom=09/12/2026").get_data(as_text=True)
    assert "Copom priced into the curve" in html
    assert "1Y" in html and "Benchmark tenors" in html
