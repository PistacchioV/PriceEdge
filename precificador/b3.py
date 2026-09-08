"""Cliente das Taxas Referenciais da B3.

Porte do módulo ``CurvasB3`` da planilha *Extrair Curvas da B3.xlsm*.

O endpoint é o mesmo que o link "Histórico de arquivos" da página oficial usa:

    https://sistemaswebb3-derivativos.b3.com.br/referenceRatesProxy/Search/GetDownloadFile/<base64>
    payload: {"language":"pt-br","date":"AAAA-MM-DD","id":"<código>"}

A resposta é um CSV em base64, codificado em Windows-1252, com as colunas
``Descrição da Taxa;Dias Úteis;Dias Corridos;Preço/Taxa``.

Duas armadilhas herdadas do VBA, mantidas registradas aqui:

* **Não usar** ``Search/GetList`` para datas passadas — ele ignora o parâmetro
  ``date`` e devolve sempre a curva mais recente, o que faz história antiga
  voltar com os números de hoje.
* O endpoint ``api/pt-br/GetReferenceRates/<DI1|DDI>``, usado na planilha do
  collar, hoje responde 404.  Foi mantido fora daqui de propósito.

A B3 só mantém arquivo público de aproximadamente o último mês útil; datas
mais antigas não têm dado nessa API.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from . import rede
from .erros import ErroDeFonte
from .calendario import calendario_anbima, para_data

BASE_URL = ("https://sistemaswebb3-derivativos.b3.com.br"
            "/referenceRatesProxy/Search/GetDownloadFile/")

# Convenções: EXP252 (juros em reais, base 252), LIN360 (cupom em moeda
# estrangeira, base 360) e PRECO — as três últimas famílias não são taxa, são
# a moeda ou o índice **a termo**, e por isso não têm fator de desconto.
EXP252, LIN360, PRECO = "EXP252", "LIN360", "PRECO"

# (código, nome, convenção, descrição)
CURVAS_COMPLETAS = [
    ("PRE", "DI x Pré", EXP252,
     "Juros nominais em reais. É a curva de desconto de tudo que é em real."),
    ("APR", "Ajuste Pré", EXP252,
     "Mesma curva do PRE, publicada para ajuste de posições."),
    ("SLP", "Selic x Pré", EXP252,
     "Estrutura a termo da Selic. Na prática acompanha o DI."),
    ("DIC", "DI x IPCA", EXP252,
     "Juro real. Contra a curva PRE dá a inflação implícita."),
    ("DIM", "DI x IGP-M", EXP252,
     "Juro real contra o IGP-M, para papéis indexados a esse índice."),
    ("TR", "DI x TR", EXP252, "Juros descontada a TR."),
    ("TP", "TR x Pré", EXP252, "A TR projetada pela curva."),
    ("TFP", "TBF x Pré", EXP252, "A TBF projetada pela curva."),

    ("DOC", "Cupom Cambial Limpo", LIN360,
     "Cupom cambial sem o efeito do casado. Desconta fluxo em dólar."),
    ("DOL", "Cupom Cambial Sujo (DI x dólar)", LIN360,
     "O DDI, com a PTAX D−1 embutida. Difere do limpo pelo casado."),
    ("DCO", "Cupom Cambial OC1", LIN360,
     "Cupom cambial do primeiro vencimento em aberto."),
    ("EUC", "Cupom de Euro (DI x euro)", LIN360,
     "O cupom cambial do euro — o equivalente do DOC para a moeda europeia."),
    ("LIB", "Libor", LIN360, "Curva de Libor publicada pela B3."),
    ("SDE", "Spread Libor Euro x Dólar", LIN360,
     "A base entre euro e dólar. É o que mais perto chega de uma curva EUR/USD."),

    ("PTX", "Dólar a Termo (Real x dólar)", PRECO,
     "Preço do dólar a termo, não taxa: 5,13 hoje, 56,99 em 34 anos."),
    ("EUR", "Euro a Termo (Real x euro)", PRECO,
     "Preço do euro a termo. Dividido pelo PTX dá o EUR/USD a termo."),
    ("JPY", "Iene a Termo (Real x iene)", PRECO, "Preço do iene a termo."),
    ("INP", "Ibovespa a Termo", PRECO, "Ibovespa a termo, em pontos."),
]

# a lista antiga (código, nome, descrição), que o resto do código já consome
CURVAS = [(cod, nome, desc) for cod, nome, _, desc in CURVAS_COMPLETAS]

CONVENCAO_POR_CODIGO = {cod: conv for cod, _, conv, _ in CURVAS_COMPLETAS}
CODIGO_POR_NOME = {nome.lower(): cod for cod, nome, _, _ in CURVAS_COMPLETAS}
NOME_POR_CODIGO = {cod: nome for cod, nome, _, _ in CURVAS_COMPLETAS}

# curvas de preço não são taxa: não descontam nada e não entram em swap
CODIGOS_DE_PRECO = {cod for cod, _, conv, _ in CURVAS_COMPLETAS if conv == PRECO}


class ErroB3(ErroDeFonte):
    """Falha ao obter ou interpretar o arquivo da B3."""


@dataclass(frozen=True)
class VerticeB3:
    dias_uteis: int
    dias_corridos: int
    taxa: float          # em % ao ano, como a B3 publica


def codigo_curva(nome_ou_codigo: str) -> str:
    texto = (nome_ou_codigo or "").strip()
    return CODIGO_POR_NOME.get(texto.lower(), texto.upper())


def _parse_br(texto: str) -> float:
    texto = texto.strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def baixar_csv(codigo: str, data, timeout: int = 30) -> str:
    """Devolve o CSV cru da B3 para a curva e a data pedidas."""
    d = para_data(data)
    payload = json.dumps(
        {"language": "pt-br", "date": d.strftime("%Y-%m-%d"), "id": codigo},
        separators=(",", ":"),
    )
    url = BASE_URL + base64.b64encode(payload.encode("ascii")).decode("ascii")
    try:
        corpo = rede.obter(url, {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://sistemaswebb3-derivativos.b3.com.br/",
        }, timeout=timeout)
    except rede.ErroRede as exc:
        raise ErroB3("não foi possível obter {curva} em {data}: {motivo}",
                     curva=codigo, data=f"{d:%d/%m/%Y}", motivo=str(exc)) from exc

    if not corpo.strip():
        return ""
    try:
        return base64.b64decode(corpo).decode("cp1252")
    except Exception as exc:  # resposta fora do formato esperado
        raise ErroB3("resposta da B3 ilegível para {curva}: {motivo}",
                     curva=codigo, motivo=str(exc)) from exc


def parse_csv(conteudo: str) -> List[VerticeB3]:
    vertices: List[VerticeB3] = []
    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split(";")
        if len(partes) < 4:
            continue
        try:                      # a linha de cabeçalho cai aqui e é descartada
            du = int(partes[1].strip())
            dc = int(partes[2].strip())
        except ValueError:
            continue
        vertices.append(VerticeB3(du, dc, _parse_br(partes[3])))
    return vertices


def extrair_curva(nome_ou_codigo: str, data) -> List[VerticeB3]:
    """Busca uma curva e devolve seus vértices (lista vazia se não houver arquivo)."""
    d = para_data(data)
    if not calendario_anbima().eh_dia_util(d):
        raise ErroB3("{data} não é dia útil (fim de semana ou feriado)",
                     data=f"{d:%d/%m/%Y}")
    conteudo = baixar_csv(codigo_curva(nome_ou_codigo), d)
    return parse_csv(conteudo)


def extrair_todas(data) -> dict:
    """Todas as curvas da lista para uma data. Falhas individuais viram lista vazia."""
    resultado = {}
    for codigo, nome, _ in CURVAS:
        try:
            resultado[codigo] = extrair_curva(codigo, data)
        except ErroB3:
            resultado[codigo] = []
    return resultado


def ultimo_dia_util(referencia=None) -> date:
    """Dia útil anterior à referência (a B3 publica a curva no fim do pregão)."""
    d = para_data(referencia) if referencia else date.today()
    cal = calendario_anbima()
    d = d - timedelta(days=1)
    return cal.ajusta(d, seguinte=False)
