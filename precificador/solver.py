"""Busca de raiz — o equivalente do Atingir Meta (GoalSeek) das planilhas.

Todas as macros de swap dos arquivos originais fazem a mesma coisa:

    Range("C11").GoalSeek Goal:=0, ChangingCell:=Range("C10")

isto é, procuram a taxa que zera o MtM.  Aqui isso vira ``taxa_par``, com
bisseção + secante (Brent simplificado), sem dependência externa.
"""

from __future__ import annotations

from typing import Callable

from .erros import ErroTraduzido


class SemConvergencia(ErroTraduzido, RuntimeError):
    pass


def atingir_meta(f: Callable[[float], float], chute: float = 0.10,
                 alvo: float = 0.0, tol: float = 1e-12,
                 max_iter: int = 200) -> float:
    """Encontra x tal que f(x) = alvo, partindo de ``chute``.

    Expande um intervalo em torno do chute até trocar de sinal e então faz
    bisseção com passo de secante.  É o suficiente para MtM de swap, que é
    monotônico na taxa.
    """
    def g(x: float) -> float:
        return f(x) - alvo

    x0 = chute
    f0 = g(x0)
    if abs(f0) < tol:
        return x0

    passo = max(abs(chute) * 0.5, 0.01)
    a = b = x0
    fa = fb = f0
    for _ in range(80):
        a, b = a - passo, b + passo
        fa, fb = g(a), g(b)
        if fa * f0 < 0:
            b, fb = x0, f0
            break
        if fb * f0 < 0:
            a, fa = x0, f0
            break
        passo *= 1.6
    else:
        raise SemConvergencia("não foi possível encontrar um intervalo com troca de sinal")

    for _ in range(max_iter):
        if abs(fb - fa) > 1e-300:
            x = b - fb * (b - a) / (fb - fa)          # secante
        else:
            x = 0.5 * (a + b)
        if not (min(a, b) < x < max(a, b)):
            x = 0.5 * (a + b)                          # cai para bisseção
        fx = g(x)
        if abs(fx) < tol or abs(b - a) < 1e-14:
            return x
        if fa * fx < 0:
            b, fb = x, fx
        else:
            a, fa = x, fx
    raise SemConvergencia("sem convergência após {iteracoes} iterações",
                          iteracoes=max_iter)
