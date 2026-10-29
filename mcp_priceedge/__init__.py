"""Servidor MCP do PriceEdge: as curvas e os precificadores como ferramentas.

Rode com ``python -m mcp_priceedge`` — o Claude Code sobe sozinho a partir do
``.mcp.json`` na raiz do repositório.
"""

from __future__ import annotations

from .ferramentas import CATALOGO, executar
from .protocolo import Servidor

INSTRUCOES = (
    "Ferramentas de precificação do PriceEdge sobre dados oficiais: curvas "
    "referenciais da B3, boletim da ANBIMA, PTAX e CDI do BCB. Taxas de entrada "
    "em % a.a.; taxas de saída em decimal. Cite sempre a data das curvas usadas. "
    "Não é recomendação de investimento."
)


def criar_servidor() -> Servidor:
    return Servidor("priceedge", "1.0.0", CATALOGO, executar, INSTRUCOES)
