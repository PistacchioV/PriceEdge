"""Servidor MCP: o protocolo e as ferramentas que não dependem de rede."""

import io
import json

import pytest

from mcp_priceedge import criar_servidor
from mcp_priceedge.ferramentas import CATALOGO, EXECUTORES, executar
from webapp import rotas
from werkzeug.datastructures import MultiDict


def _conversa(*mensagens):
    entrada = io.StringIO("".join(json.dumps(m) + "\n" for m in mensagens))
    saida = io.StringIO()
    criar_servidor().rodar(entrada, saida)
    return [json.loads(linha) for linha in saida.getvalue().splitlines()]


def _chamar(nome, argumentos):
    resposta, = _conversa({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": nome, "arguments": argumentos}})
    resultado = resposta["result"]
    return resultado["isError"], json.loads(resultado["content"][0]["text"])


def test_handshake_e_lista_de_ferramentas():
    init, lista = _conversa(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "teste", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert init["result"]["protocolVersion"] == "2025-06-18"
    assert init["result"]["serverInfo"]["name"] == "priceedge"
    nomes = [t["name"] for t in lista["result"]["tools"]]
    assert nomes == list(CATALOGO)
    for ferramenta in lista["result"]["tools"]:
        assert ferramenta["inputSchema"]["type"] == "object"
        assert ferramenta["description"]


def test_todo_item_do_catalogo_tem_executor():
    assert set(CATALOGO) == set(EXECUTORES)


def test_metodo_desconhecido_e_ferramenta_desconhecida_sao_erro_rpc():
    metodo, ferramenta = _conversa(
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "nao_existe", "arguments": {}}},
    )
    assert metodo["error"]["code"] == -32601
    assert ferramenta["error"]["code"] == -32602


def test_erro_de_negocio_volta_como_resultado_com_isError():
    erro, corpo = _chamar("precificar_opcao_fx", {
        "spot": 5.15, "vencimento": "2027-01-04", "inicio": "2026-01-02",
        "pernas": [{"tipo": "call", "lado": "comprada", "strike": 5.2}]})
    assert erro
    assert "vol" in corpo["erro"]


def test_dias_uteis_no_calendario_anbima():
    erro, corpo = _chamar("dias_uteis", {"inicio": "2026-01-02", "fim": "2027-01-04"})
    assert not erro
    assert corpo["dias_corridos"] == 367
    assert corpo["dias_uteis"] > 245


def test_opcao_fx_e_o_mesmo_numero_da_tela():
    """A ferramenta monta o formulário e chama a rota: os prêmios têm de bater."""
    argumentos = {
        "spot": 5.15, "inicio": "2026-01-02", "vencimento": "2027-01-04",
        "nocional": 20e6, "vol": 15, "taxa_dom": 14.5, "taxa_est": 5.5,
        "pernas": [{"tipo": "put", "lado": "vendida", "strike": 4.9},
                   {"tipo": "call", "lado": "comprada", "strike": 5.6}],
    }
    erro, corpo = _chamar("precificar_opcao_fx", argumentos)
    assert not erro
    tela = rotas._precificar_opcao(MultiDict({
        "inicio": "2026-01-02", "vencimento": "2027-01-04", "spot": "5,15",
        "nocional": "20.000.000,00", "moeda_nocional": "USD", "fonte_vol": "unica",
        "vol": "15,00", "taxa_dom": "14,50", "taxa_est": "5,50",
        "usar1": "1", "tipo1": "put", "lado1": "vendida", "strike1": "4,90",
        "usar2": "1", "tipo2": "call", "lado2": "comprada", "strike2": "5,60",
    }))
    assert corpo["premio_liquido_brl"] == pytest.approx(tela["liquido"], abs=1e-6)
    assert corpo["taxa_dom"] == pytest.approx(0.145)
    assert corpo["fontes_taxa"] == {"dom": "informada", "est": "informada"}


def test_collar_custo_zero_resolve_o_strike():
    corpo = executar("precificar_opcao_fx", {
        "spot": 5.15, "inicio": "2026-01-02", "vencimento": "2027-01-04",
        "vol": 15, "taxa_dom": 14.5, "taxa_est": 5.5, "resolver_strike": 2,
        "pernas": [{"tipo": "call", "lado": "comprada", "strike": 5.6},
                   {"tipo": "put", "lado": "vendida"}],
    })
    assert corpo["premio_liquido_brl"] == pytest.approx(0.0, abs=1e-2)
    strike = corpo["strike_resolvido"]["strike"]
    assert corpo["pernas"][1]["strike"] == pytest.approx(strike)
    assert strike < corpo["forward"] < 5.6
