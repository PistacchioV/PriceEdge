#!/usr/bin/env python3
"""Sobe o servidor local do PriceEdge.

    python run.py            -> http://127.0.0.1:5001
    python run.py 8080       -> outra porta

O ambiente manda quando as variáveis estão definidas — é assim que os .bat de
UAT e produção escolhem porta, interface e modo sem editar este arquivo:

    PRECIFICADOR_PORTA=5051
    PRECIFICADOR_HOST=0.0.0.0
    PRECIFICADOR_DEBUG=0
"""

import os
import sys

from webapp import create_app

app = create_app()


def _porta() -> int:
    do_ambiente = os.getenv("PRECIFICADOR_PORTA")
    if do_ambiente:
        return int(do_ambiente)
    return int(sys.argv[1]) if len(sys.argv) > 1 else 5001


if __name__ == "__main__":
    debug = os.getenv("PRECIFICADOR_DEBUG", "1").strip().lower() not in ("0", "false", "nao", "não")
    app.run(host=os.getenv("PRECIFICADOR_HOST", "127.0.0.1"),
            port=_porta(), debug=debug)
