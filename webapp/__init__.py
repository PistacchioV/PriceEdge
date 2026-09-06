"""Aplicação Flask do precificador."""

from __future__ import annotations

from flask import Flask


def create_app(config=None) -> Flask:
    app = Flask(__name__)
    app.config.update(SECRET_KEY="precificador-swap-local", JSON_SORT_KEYS=False)
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
