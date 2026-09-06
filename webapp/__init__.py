"""Aplicação Flask do precificador."""

from __future__ import annotations

import os
import secrets

from flask import Flask


def _chave_de_sessao() -> str:
    """Chave de sessão do ambiente, ou uma nova a cada subida.

    Fica fora do código de propósito: uma constante versionada num repositório
    é uma chave que qualquer um lê, e com ela se forja o cookie de sessão de
    qualquer instância que rode este código. O sorteio a cada subida custa
    apenas invalidar os cookies num restart — aqui a sessão só guarda o idioma
    escolhido, então ninguém perde nada. Para mantê-la estável entre restarts,
    defina PRECIFICADOR_SECRET_KEY no ambiente.
    """
    return os.getenv("PRECIFICADOR_SECRET_KEY") or secrets.token_hex(32)


def create_app(config=None) -> Flask:
    app = Flask(__name__)
    app.config.update(SECRET_KEY=_chave_de_sessao(), JSON_SORT_KEYS=False)
    if config:
        app.config.update(config)

    from .rotas import bp
    from . import filtros, idiomas

    app.register_blueprint(bp)
    filtros.registrar(app)

    @app.context_processor
    def _idioma():
        """Deixa ``idioma`` e ``t`` disponíveis em todo template."""
        from flask import request
        escolhido = idiomas.normalizar(
            request.args.get("idioma") or request.cookies.get("idioma"))
        return {
            "idioma": escolhido,
            "idiomas": idiomas.IDIOMAS,
            "t": lambda texto: idiomas.traduzir(texto, escolhido),
        }

    @app.after_request
    def _lembrar_idioma(resposta):
        """Guarda a escolha por um ano, para não precisar do ?idioma= sempre."""
        from flask import request
        pedido = request.args.get("idioma")
        if pedido:
            resposta.set_cookie("idioma", idiomas.normalizar(pedido),
                                max_age=60 * 60 * 24 * 365, samesite="Lax")
        return resposta

    return app
