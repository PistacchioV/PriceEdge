#!/usr/bin/env python3
"""Sobe o servidor MCP do PriceEdge em stdio, de qualquer pasta.

    .venv/bin/python run_mcp.py

Diferente de ``python -m mcp_priceedge``, funciona com o caminho absoluto a
partir de outro diretório — é o que o ``claude mcp add`` em escopo de usuário
precisa, já que o cliente não sobe o processo dentro do repositório.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_priceedge import criar_servidor  # noqa: E402

if __name__ == "__main__":
    criar_servidor().rodar()
