"""Opções de câmbio europeias — modelo de Garman-Kohlhagen.

É o Black-Scholes com a moeda estrangeira no papel do dividendo: quem tem o
dólar recebe a taxa de juro dele, e isso desconta o spot.

    d1 = [ln(S/K) + (r_d − r_f + σ²/2)·T] / (σ·√T)
    d2 = d1 − σ·√T
    call = S·e^(−r_f·T)·N(d1) − K·e^(−r_d·T)·N(d2)
    put  = K·e^(−r_d·T)·N(−d2) − S·e^(−r_f·T)·N(−d1)

``r_d`` e ``r_f`` são **contínuas**. As taxas do mercado brasileiro não são, e
a conversão é a da planilha *Benefício de taxa com Collar - Garman Kohlhagen*:

    r_d = ln(1 + CDI)                         (CDI exponencial 252)
    r_f = ln(1 + cupom · DC/360) · 365/DC     (cupom cambial linear 360)
    T   = DU/252

O prêmio sai em reais por dólar; vezes o nocional em dólar dá o prêmio em
reais. A planilha recebe o nocional em reais e divide pelo spot.

**Smile.** A B3 publica a superfície de volatilidade do dólar por delta
(Δ1% a Δ99%), não por strike. Para achar a vol de um strike, a planilha
(``Implied_Vol_Smile``, VBA) parte da vol de Δ50%, calcula o delta do strike
com ela, lê a vol daquele delta no smile, e repete até a vol parar de mudar.
``vol_do_smile`` faz o mesmo, com o mesmo critério de parada.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .erros import ErroDeDado

CALL = "call"
PUT = "put"
COMPRADA = "comprada"
VENDIDA = "vendida"

# Deltas das colunas da superfície de volatilidade de dólar da B3
DELTAS_B3 = (0.01, 0.05, 0.10, 0.25, 0.37, 0.50, 0.63, 0.75, 0.90, 0.95, 0.99)


def N(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def n(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ------------------------------------------------------- convenções de taxa

def r_d_continua(taxa_252: float) -> float:
    """CDI/pré exponencial 252 → taxa contínua."""
    return math.log(1.0 + taxa_252)


def r_f_continua(cupom_360: float, dias_corridos: int) -> float:
    """Cupom cambial linear 360 → taxa contínua base 365."""
    if dias_corridos <= 0:
        raise ErroDeDado("o vencimento da opção tem que ser depois da data de início")
    return math.log(1.0 + cupom_360 * dias_corridos / 360.0) * 365.0 / dias_corridos


# ------------------------------------------------------------------- modelo

@dataclass(frozen=True)
class Gregas:
    delta: float            # ∂V/∂S — hedge em moeda estrangeira, por unidade
    delta_forward: float    # ∂V/∂F, sem o e^(−r_f·T)
    gamma: float            # ∂²V/∂S²
    vega: float             # por 1 ponto de vol (1%)
    theta: float            # por dia corrido (/365)
    rho: float              # taxa doméstica, por 1%
    psi: float              # taxa estrangeira, por 1%


@dataclass(frozen=True)
class Avaliacao:
    tipo: str
    spot: float
    strike: float
    r_d: float
    r_f: float
    vol: float
    t: float
    d1: float
    d2: float
    premio: float           # em moeda doméstica por unidade de estrangeira
    gregas: Gregas

    @property
    def nd1(self) -> float:
        return N(self.d1)

    @property
    def nd2(self) -> float:
        return N(self.d2)

    @property
    def forward(self) -> float:
        return forward(self.spot, self.r_d, self.r_f, self.t)

    @property
    def moneyness(self) -> float:
        return self.spot / self.strike

    @property
    def situacao(self) -> str:
        """Dentro, no ou fora do dinheiro — contra o forward, que é o que vale."""
        f = self.forward
        if abs(f / self.strike - 1.0) < 1e-4:
            return "ATM"
        dentro = f > self.strike if self.tipo == CALL else f < self.strike
        return "ITM" if dentro else "OTM"


def forward(spot: float, r_d: float, r_f: float, t: float) -> float:
    return spot * math.exp((r_d - r_f) * t)


def _validar(spot, strike, vol, t):
    if spot <= 0 or strike <= 0:
        raise ErroDeDado("spot e strike têm que ser positivos")
    if vol <= 0:
        raise ErroDeDado("a volatilidade tem que ser positiva")
    if t <= 0:
        raise ErroDeDado("o prazo da opção tem que ser positivo")


def d1_d2(spot: float, strike: float, r_d: float, r_f: float, vol: float,
          t: float) -> Tuple[float, float]:
    raiz = vol * math.sqrt(t)
    d1 = (math.log(spot / strike) + (r_d - r_f + 0.5 * vol * vol) * t) / raiz
    return d1, d1 - raiz


def avaliar(tipo: str, spot: float, strike: float, r_d: float, r_f: float,
            vol: float, t: float) -> Avaliacao:
    """Prêmio e gregas de uma opção europeia, por unidade de moeda estrangeira."""
    _validar(spot, strike, vol, t)
    if tipo not in (CALL, PUT):
        raise ErroDeDado("o tipo da opção é call ou put")
    d1, d2 = d1_d2(spot, strike, r_d, r_f, vol, t)
    df_d, df_f = math.exp(-r_d * t), math.exp(-r_f * t)
    raiz_t = math.sqrt(t)
    if tipo == CALL:
        premio = spot * df_f * N(d1) - strike * df_d * N(d2)
        delta_fwd = N(d1)
        theta = (-spot * df_f * n(d1) * vol / (2 * raiz_t)
                 + r_f * spot * df_f * N(d1) - r_d * strike * df_d * N(d2))
        rho = strike * t * df_d * N(d2)
        psi = -spot * t * df_f * N(d1)
    else:
        premio = strike * df_d * N(-d2) - spot * df_f * N(-d1)
        delta_fwd = N(d1) - 1.0
        theta = (-spot * df_f * n(d1) * vol / (2 * raiz_t)
                 - r_f * spot * df_f * N(-d1) + r_d * strike * df_d * N(-d2))
        rho = -strike * t * df_d * N(-d2)
        psi = spot * t * df_f * N(-d1)
    gregas = Gregas(
        delta=df_f * delta_fwd, delta_forward=delta_fwd,
        gamma=df_f * n(d1) / (spot * vol * raiz_t),
        vega=spot * df_f * n(d1) * raiz_t / 100.0,
        theta=theta / 365.0, rho=rho / 100.0, psi=psi / 100.0)
    return Avaliacao(tipo, spot, strike, r_d, r_f, vol, t, d1, d2, premio, gregas)


def paridade(spot: float, strike: float, r_d: float, r_f: float, t: float) -> float:
    """C − P = S·e^(−r_f·T) − K·e^(−r_d·T): o lado direito, para conferir."""
    return spot * math.exp(-r_f * t) - strike * math.exp(-r_d * t)


# -------------------------------------------------------------------- smile

def vol_por_delta(delta: float, smile: Sequence[Tuple[float, float]]) -> float:
    """Interpolação linear no smile por delta, chapada fora das pontas (VBA)."""
    pontos = sorted(smile)
    if delta <= pontos[0][0]:
        return pontos[0][1]
    if delta >= pontos[-1][0]:
        return pontos[-1][1]
    for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
        if x0 <= delta <= x1:
            return y0 + (y1 - y0) / (x1 - x0) * (delta - x0)
    return pontos[-1][1]


def vol_do_smile(smile: Sequence[Tuple[float, float]], spot: float, strike: float,
                 r_d: float, r_f: float, t: float,
                 tolerancia: float = 1e-6, max_iter: int = 200) -> float:
    """Vol do strike: ponto fixo entre o delta da call e o smile por delta.

    O delta usado é o da **call** com desconto estrangeiro, ``e^(−r_f·T)·N(d1)``,
    para qualquer tipo de opção — como na planilha. O smile da B3 é indexado
    assim: Δ1% é a call muito fora do dinheiro (strike alto), Δ99% a muito
    dentro.
    """
    if len(smile) < 2:
        raise ErroDeDado("o smile precisa de pelo menos dois pontos")
    _validar(spot, strike, 1.0, t)
    vol = vol_por_delta(0.5, smile)
    for _ in range(max_iter):
        d1, _ = d1_d2(spot, strike, r_d, r_f, vol, t)
        nova = vol_por_delta(abs(math.exp(-r_f * t) * N(d1)), smile)
        if abs(nova - vol) <= tolerancia:
            return nova
        vol = nova
    raise ErroDeDado("a vol do smile não convergiu para o strike {strike}",
                     strike=f"{strike:.4f}")


# ------------------------------------------------------------------ posição

@dataclass(frozen=True)
class Perna:
    tipo: str               # call ou put
    lado: str               # comprada ou vendida
    strike: float
    vol: Optional[float] = None     # None = ler do smile


@dataclass(frozen=True)
class ResultadoPerna:
    perna: Perna
    avaliacao: Avaliacao
    quantidade: float       # em moeda estrangeira

    @property
    def sinal(self) -> int:
        return 1 if self.perna.lado == COMPRADA else -1

    @property
    def premio_total(self) -> float:
        """Fluxo do prêmio em reais: positivo recebe (vendida), negativo paga."""
        return -self.sinal * self.avaliacao.premio * self.quantidade

    @property
    def delta_posicao(self) -> float:
        return self.sinal * self.avaliacao.gregas.delta * self.quantidade

    @property
    def vega_posicao(self) -> float:
        return self.sinal * self.avaliacao.gregas.vega * self.quantidade


def avaliar_pernas(pernas: List[Perna], spot: float, r_d: float, r_f: float, t: float,
                   quantidade: float,
                   smile: Optional[Sequence[Tuple[float, float]]] = None
                   ) -> List[ResultadoPerna]:
    saida = []
    for perna in pernas:
        vol = perna.vol
        if vol is None:
            if not smile:
                raise ErroDeDado("informe a volatilidade ou o smile por delta")
            vol = vol_do_smile(smile, spot, perna.strike, r_d, r_f, t)
        saida.append(ResultadoPerna(perna, avaliar(perna.tipo, spot, perna.strike,
                                                   r_d, r_f, vol, t), quantidade))
    return saida


def taxa_all_in(spread: float, t: float, custo_liquido: float) -> float:
    """Spread CDI+ equivalente depois de um custo (ou ganho) à vista.

    É o "Atingir Meta" da planilha (``CalculotaxasAllin``) em forma fechada.
    O empréstimo a CDI + s vale, a valor presente, ``N·(1+s)^T`` — o CDI se
    cancela com o desconto. Somar um fee pago à vista e subtrair o prêmio
    líquido recebido nas opções, ambos em fração do nocional, e achar o spread
    que dá o mesmo valor:

        (1 + all-in)^T = (1 + s)^T + custo_liquido
    """
    base = (1.0 + spread) ** t + custo_liquido
    if base <= 0:
        raise ErroDeDado("o prêmio recebido passa do valor do empréstimo")
    return base ** (1.0 / t) - 1.0


def percentual_do_cdi(spread: float, cdi: float) -> float:
    """CDI + spread expresso em % do CDI, pela taxa diária (fórmula da planilha)."""
    diaria = (1.0 + cdi) ** (1.0 / 252.0) - 1.0
    return (((1.0 + spread) * (1.0 + cdi)) ** (1.0 / 252.0) - 1.0) / diaria


def premio_liquido(resultados: List[ResultadoPerna]) -> float:
    return sum(r.premio_total for r in resultados)


def resolver_strike(pernas: List[Perna], indice: int, spot: float, r_d: float,
                    r_f: float, t: float, quantidade: float,
                    smile: Optional[Sequence[Tuple[float, float]]] = None,
                    alvo: float = 0.0) -> float:
    """Strike da perna ``indice`` que leva o prêmio líquido (R$) ao ``alvo``.

    Com alvo zero é a pergunta da mesa: "qual cap zera o custo do collar?".
    O prêmio de uma opção é monótono no strike — a call cai, a put sobe —, e
    o das outras pernas não muda, então basta varrer a faixa de 30% a 300% do
    spot atrás da troca de sinal e fechar por bisseção. Com o smile, a vol
    acompanha o strike a cada tentativa, como na planilha.
    """
    def f(k: float) -> float:
        teste = list(pernas)
        teste[indice] = Perna(pernas[indice].tipo, pernas[indice].lado, k, pernas[indice].vol)
        return premio_liquido(avaliar_pernas(teste, spot, r_d, r_f, t, quantidade, smile)) - alvo

    grade = [spot * (0.3 + 0.01 * i) for i in range(271)]
    anterior = (grade[0], f(grade[0]))
    for k in grade[1:]:
        atual = (k, f(k))
        if anterior[1] == 0:
            return anterior[0]
        if anterior[1] * atual[1] < 0:
            a, b, fa = anterior[0], atual[0], anterior[1]
            for _ in range(100):
                m = 0.5 * (a + b)
                fm = f(m)
                if abs(b - a) < 1e-10:
                    break
                if fa * fm <= 0:
                    b = m
                else:
                    a, fa = m, fm
            return 0.5 * (a + b)
        anterior = atual
    raise ErroDeDado("nenhum strike entre 30% e 300% do spot leva o prêmio líquido ao alvo")
