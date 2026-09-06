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


def _fora_do_reloader() -> list:
    """Pastas que o auto-reload não deve vigiar.

    Sem virtualenv, a biblioteca padrão fica dentro da própria instalação do
    Python e entra no ``sys.path`` — e o watchdog do Werkzeug passa a vigiar
    ela junto com o código da aplicação. O efeito aparece no log assim:

        Detected change in '...\\python3.12\\latest\\Lib\\_strptime.py', reloading

    Não houve mudança nenhuma: ``_strptime`` é importado tarde, na primeira
    chamada a ``strptime``, e o watchdog lê o import de um arquivo novo como
    alteração. O servidor reinicia sozinho no meio do primeiro request, perde o
    cache de curvas e faz tudo de novo. Tirando a instalação do Python da
    vigilância, sobra o que interessa: o código daqui.
    """
    pastas = {sys.prefix, sys.base_prefix, sys.exec_prefix}
    daqui = os.path.dirname(os.path.abspath(__file__))
    return [os.path.join(p, "**") for p in pastas if p and not daqui.startswith(p)]


if __name__ == "__main__":
    debug = os.getenv("PRECIFICADOR_DEBUG", "1").strip().lower() not in (
        "0", "false", "nao", "não")
    app.run(host=os.getenv("PRECIFICADOR_HOST", "127.0.0.1"),
            port=_porta(), debug=debug,
            exclude_patterns=_fora_do_reloader() if debug else None)
