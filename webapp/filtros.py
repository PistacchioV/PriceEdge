"""Filtros Jinja de formatação — números em padrão brasileiro."""

from __future__ import annotations

from datetime import date, datetime


def moeda(valor, casas: int = 2) -> str:
    if valor is None:
        return "—"
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def percentual(valor, casas: int = 4) -> str:
    if valor is None:
        return "—"
    return moeda(float(valor) * 100.0, casas) + "%"


def bps(valor, casas: int = 1) -> str:
    if valor is None:
        return "—"
    return moeda(float(valor) * 10000.0, casas) + " bp"


def numero(valor, casas: int = 0) -> str:
    if valor is None:
        return "—"
    return moeda(valor, casas)


def data_br(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, str):
        try:
            valor = datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            return valor
    return valor.strftime("%d/%m/%Y")


def registrar(app) -> None:
    for funcao in (moeda, percentual, bps, numero, data_br):
        app.jinja_env.filters[funcao.__name__] = funcao
    app.jinja_env.globals["hoje"] = date.today
