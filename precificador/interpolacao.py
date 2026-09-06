"""Interpolação de curvas.

Porte direto das UDFs de VBA das planilhas:

* ``cubic_spline(input_column; output_column; x)`` — spline cúbica natural
  (Numerical Recipes: ``spline`` + ``splint``), com as segundas derivadas
  fixadas em zero nas pontas.
* ``Cubic_Spline(xp; rangeX; rangeY)`` do módulo de Garman-Kohlhagen — mesma
  spline, mas ordenando os pontos e travando a extrapolação (fora do domínio
  devolve o y da ponta).
* ``cubic_spline`` do módulo CubicSpline da planilha de NDF — a mesma spline
  na forma de Burden & Faires, que fora do domínio **extrapola pela reta
  tangente** ao spline no nó extremo.

As três só diferem no que fazem fora do intervalo dos vértices, e essa
diferença importa: a curva da B3 termina em ~10 anos e um swap mais longo cai
justamente nessa região.  Por isso ``extrapolar`` é um parâmetro explícito:

    "flat"      trava no y da ponta (padrão, defensivo)
    "tangente"  segue a reta tangente ao spline no nó extremo (planilha de NDF)
    "cubica"    prolonga o polinômio do trecho extremo (planilha de aula)
"""

from __future__ import annotations

import bisect
from typing import Sequence


class SplineNatural:
    """Spline cúbica natural pré-computada sobre (x, y)."""

    def __init__(self, x: Sequence[float], y: Sequence[float], ordenar: bool = True):
        pontos = [(float(a), float(b)) for a, b in zip(x, y)
                  if a is not None and b is not None]
        if ordenar:
            pontos.sort(key=lambda p: p[0])
        # colapsa x repetidos (a B3 às vezes publica o mesmo prazo duas vezes)
        limpos = []
        for px, py in pontos:
            if limpos and px == limpos[-1][0]:
                limpos[-1] = (px, py)
            else:
                limpos.append((px, py))
        if len(limpos) < 2:
            raise ValueError("a spline precisa de pelo menos 2 pontos distintos")
        self.x = [p[0] for p in limpos]
        self.y = [p[1] for p in limpos]
        self.y2 = self._segundas_derivadas(self.x, self.y)

    # ------------------------------------------------------------------ core

    @staticmethod
    def _segundas_derivadas(x, y):
        n = len(x)
        y2 = [0.0] * n
        u = [0.0] * n
        for i in range(1, n - 1):
            sig = (x[i] - x[i - 1]) / (x[i + 1] - x[i - 1])
            p = sig * y2[i - 1] + 2.0
            y2[i] = (sig - 1.0) / p
            ui = ((y[i + 1] - y[i]) / (x[i + 1] - x[i])
                  - (y[i] - y[i - 1]) / (x[i] - x[i - 1]))
            u[i] = (6.0 * ui / (x[i + 1] - x[i - 1]) - sig * u[i - 1]) / p
        y2[n - 1] = 0.0
        for k in range(n - 2, -1, -1):
            y2[k] = y2[k] * y2[k + 1] + u[k]
        return y2

    # -------------------------------------------------------- extrapolação

    def derivada_inicio(self) -> float:
        """Inclinação do spline no primeiro nó."""
        h = self.x[1] - self.x[0]
        return ((self.y[1] - self.y[0]) / h
                - (2.0 * self.y2[0] + self.y2[1]) * h / 6.0)

    def derivada_fim(self) -> float:
        """Inclinação do spline no último nó."""
        h = self.x[-1] - self.x[-2]
        return ((self.y[-1] - self.y[-2]) / h
                + (self.y2[-2] + 2.0 * self.y2[-1]) * h / 6.0)

    def __call__(self, xp: float, extrapolar: str = "flat") -> float:
        xp = float(xp)
        if xp <= self.x[0]:
            if extrapolar == "flat":
                return self.y[0]
            if extrapolar == "tangente":
                return self.y[0] + self.derivada_inicio() * (xp - self.x[0])
        if xp >= self.x[-1]:
            if extrapolar == "flat":
                return self.y[-1]
            if extrapolar == "tangente":
                return self.y[-1] + self.derivada_fim() * (xp - self.x[-1])

        klo = bisect.bisect_right(self.x, xp) - 1
        klo = min(max(klo, 0), len(self.x) - 2)
        khi = klo + 1

        h = self.x[khi] - self.x[klo]
        if h == 0:
            return self.y[klo]
        a = (self.x[khi] - xp) / h
        b = (xp - self.x[klo]) / h
        return (a * self.y[klo] + b * self.y[khi]
                + ((a ** 3 - a) * self.y2[klo] + (b ** 3 - b) * self.y2[khi]) * h * h / 6.0)


def cubic_spline(x: Sequence[float], y: Sequence[float], xp: float,
                 extrapolar: str = "flat") -> float:
    """Equivalente de uma célula ``=cubic_spline(colX; colY; x)``."""
    return SplineNatural(x, y)(xp, extrapolar=extrapolar)


def linear(x: Sequence[float], y: Sequence[float], xp: float,
           extrapolar: str = "flat") -> float:
    """Interpolação linear — é o que a B3 usa para publicar o cupom cambial."""
    pontos = sorted((float(a), float(b)) for a, b in zip(x, y))
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    if xp <= xs[0]:
        if extrapolar == "flat" or len(xs) < 2:
            return ys[0]
        i = 0
    elif xp >= xs[-1]:
        if extrapolar == "flat":
            return ys[-1]
        i = len(xs) - 2
    else:
        i = bisect.bisect_right(xs, xp) - 1
        i = min(max(i, 0), len(xs) - 2)
    dx = xs[i + 1] - xs[i]
    if dx == 0:
        return ys[i]
    return ys[i] + (ys[i + 1] - ys[i]) * (xp - xs[i]) / dx


def flat_forward(x: Sequence[float], y: Sequence[float], xp: float,
                 base: float = 252.0) -> float:
    """Interpolação exponencial (flat-forward) sobre o fator de capitalização.

    Interpola linearmente ``ln((1+i)^(t/base))`` — a convenção da ANBIMA para
    curvas de juros em dias úteis.  Alternativa à spline quando se quer
    garantir forwards não-negativos entre vértices.
    """
    pontos = sorted((float(a), float(b)) for a, b in zip(x, y))
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    if xp <= xs[0]:
        return ys[0]
    if xp >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, xp) - 1
    i = min(max(i, 0), len(xs) - 2)
    x0, x1 = xs[i], xs[i + 1]
    ln0 = (x0 / base) * _ln1p(ys[i])
    ln1 = (x1 / base) * _ln1p(ys[i + 1])
    ln = ln0 + (ln1 - ln0) * (xp - x0) / (x1 - x0)
    import math
    return math.exp(ln * base / xp) - 1.0


def _ln1p(taxa: float) -> float:
    import math
    return math.log1p(taxa)


METODOS = {
    "spline": cubic_spline,
    "linear": linear,
    "flat_forward": flat_forward,
}


def interpolar(x, y, xp, metodo: str = "spline", **kwargs) -> float:
    try:
        funcao = METODOS[metodo]
    except KeyError as exc:
        raise ValueError(f"método de interpolação desconhecido: {metodo}") from exc
    if funcao is flat_forward:
        return funcao(x, y, xp)
    return funcao(x, y, xp, **kwargs)
