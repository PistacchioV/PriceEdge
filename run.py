#!/usr/bin/env python3
"""Sobe o servidor local do precificador.

    python run.py            -> http://127.0.0.1:5001
    python run.py 8080       -> outra porta
"""

import sys

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    app.run(host="127.0.0.1", port=porta, debug=True)
