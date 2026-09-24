"""IPCA — o número-índice mensal do IBGE, para a ponta de IPCA da liquidação.

A ponta de IPCA corrige o notional por ``NI_final / NI_inicial``. Até aqui os
dois números entravam **digitados**: a mesa os copiava do SIDRA para dentro da
tela, e um dígito trocado ali é um erro que não aparece — a correção sai
plausível e o ajuste fecha com o número errado.

De qual mês é cada número, quem diz é o contrato, pela defasagem do fixing:

    M-1   o mês anterior à data do fluxo
    M-2   o segundo mês anterior

A mesma defasagem vale nas duas pontas do fluxo: o número inicial é o do mês
M-n contado do **início**, o final é o do mês M-n contado do **fim**. Um fluxo
de 11/03/2026 a 11/09/2026 com M-1 corrige de fevereiro a agosto de 2026 —
agosto é o último IPCA publicado antes de setembro; com M-2, de janeiro a
julho.

A fonte é a API de agregados do IBGE (SIDRA): tabela 1737, variável 2266
(*IPCA — Número-índice, base dezembro de 1993 = 100*), localidade Brasil. É a
mesma URL da macro da mesa, com uma diferença que vale o comentário: a
variável entra **fixada** em vez de "a primeira que vier". Sem ela a resposta
traz seis variáveis, e a primeira é a variação mensal — um número na casa de
0,4 onde se espera um na casa de 7.000, que quebra alto em vez de corrigir
errado, mas só depois de assustar quem lê.

**Mês ainda não publicado não vem na série** — a chave simplesmente falta,
nunca chega como zero. Aqui isso vira erro que diz *qual* mês: o IPCA sai por
volta do dia 10 do mês seguinte, e um fluxo que liquida no dia 5 com M-1 pede
um número que ainda não existe. Um zero ali zeraria a correção.

O que já foi publicado não muda, então o memo guarda cada mês que a API
devolveu e só o que falta volta a ser pedido.
"""

from __future__ import annotations

import threading
from typing import Dict, Iterable, List, Tuple

from . import rede
from .calendario import para_data
from .erros import ErroDeDado, ErroDeFonte

API = ("https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/{de}-{ate}"
       "/variaveis/2266?localidades=BR")

DIGITADO = ""
M1 = "m1"
M2 = "m2"
DEFASAGEM = {M1: 1, M2: 2}

# o que a tela oferece; o primeiro é o comportamento de sempre
FIXINGS = [
    (DIGITADO, "Números digitados"),
    (M1, "M-1 — o mês anterior ao fluxo"),
    (M2, "M-2 — dois meses antes do fluxo"),
]

TIMEOUT = 40

_memo: Dict[str, float] = {}
_trava = threading.Lock()


class ErroIBGE(ErroDeFonte):
    """Falha ao obter o número-índice do IBGE — ou mês ainda não publicado."""


def mes_do_fixing(referencia, fixing: str) -> Tuple[int, int]:
    """O ``(ano, mês)`` do IPCA que um fixing M-1/M-2 pede para uma data.

    A conta é em meses absolutos para não tropeçar na virada do ano: janeiro
    com M-2 é novembro do ano anterior.
    """
    if fixing not in DEFASAGEM:
        raise ErroDeDado("fixing de IPCA desconhecido: {fixing}", fixing=fixing)
    d = para_data(referencia)
    n = d.year * 12 + (d.month - 1) - DEFASAGEM[fixing]
    return n // 12, n % 12 + 1


def chave(ano: int, mes: int) -> str:
    return f"{ano:04d}{mes:02d}"


def rotulo(ano: int, mes: int) -> str:
    """``08/2026`` — como a tela escreve mês."""
    return f"{mes:02d}/{ano:04d}"


def serie(de: Tuple[int, int], ate: Tuple[int, int], timeout: int = TIMEOUT) -> Dict[str, float]:
    """Os números-índice publicados entre dois meses, como ``{'AAAAMM': float}``.

    Mês sem publicação simplesmente não vem — a ausência é a informação.
    """
    if (ate[0], ate[1]) < (de[0], de[1]):
        de, ate = ate, de
    url = API.format(de=chave(*de), ate=chave(*ate))
    try:
        bruto = rede.obter_json(url, timeout=timeout)
    except rede.ErroRede as exc:
        raise ErroIBGE("não foi possível obter o número-índice do IPCA no IBGE: "
                       "{motivo}", motivo=str(exc)) from exc

    valores: Dict[str, float] = {}
    try:
        for variavel in bruto or []:
            for resultado in variavel.get("resultados") or []:
                for s in resultado.get("series") or []:
                    for k, v in (s.get("serie") or {}).items():
                        try:
                            valores[str(k)] = float(v)
                        except (TypeError, ValueError):
                            continue          # '...' e '-' são "sem dado"
    except AttributeError as exc:
        raise ErroIBGE("resposta inesperada do IBGE: {motivo}",
                       motivo=str(exc)) from exc

    with _trava:
        _memo.update(valores)
    return valores


def numeros_indice(meses: Iterable[Tuple[int, int]],
                   timeout: int = TIMEOUT) -> Dict[Tuple[int, int], float]:
    """O número-índice de cada ``(ano, mês)`` pedido.

    Uma ida só à API para tudo o que o memo não tem — dois meses distantes
    cabem no mesmo intervalo, e a série no meio é de graça.
    """
    pedidos: List[Tuple[int, int]] = sorted({(int(a), int(m)) for a, m in meses})
    if not pedidos:
        return {}

    with _trava:
        faltam = [am for am in pedidos if chave(*am) not in _memo]
    if faltam:
        serie(faltam[0], faltam[-1], timeout=timeout)

    saida: Dict[Tuple[int, int], float] = {}
    with _trava:
        for am in pedidos:
            valor = _memo.get(chave(*am))
            if valor is None:
                raise ErroIBGE(
                    "o número-índice do IPCA de {mes} ainda não foi publicado "
                    "(IBGE, tabela 1737)", mes=rotulo(*am))
            saida[am] = valor
    return saida


def correcao(inicio, fim, fixing: str, timeout: int = TIMEOUT) -> "CorrecaoIPCA":
    """A correção do fluxo pelo IPCA, com os dois meses que a formaram.

    Devolver os meses junto do fator não é enfeite: é o que deixa conferir a
    leitura contra o SIDRA sem ter de acreditar nela.
    """
    mes_inicial = mes_do_fixing(inicio, fixing)
    mes_final = mes_do_fixing(fim, fixing)
    indices = numeros_indice((mes_inicial, mes_final), timeout=timeout)
    ni_inicial, ni_final = indices[mes_inicial], indices[mes_final]
    if not ni_inicial:
        raise ErroIBGE("o número-índice do IPCA de {mes} veio zerado",
                       mes=rotulo(*mes_inicial))
    return CorrecaoIPCA(fator=ni_final / ni_inicial,
                        ni_inicial=ni_inicial, ni_final=ni_final,
                        mes_inicial=mes_inicial, mes_final=mes_final)


class CorrecaoIPCA:
    """O fator e de onde ele veio — os dois números e os dois meses."""

    __slots__ = ("fator", "ni_inicial", "ni_final", "mes_inicial", "mes_final")

    def __init__(self, fator, ni_inicial, ni_final, mes_inicial, mes_final):
        self.fator = fator
        self.ni_inicial = ni_inicial
        self.ni_final = ni_final
        self.mes_inicial = mes_inicial
        self.mes_final = mes_final

    @property
    def rotulo_inicial(self) -> str:
        return rotulo(*self.mes_inicial)

    @property
    def rotulo_final(self) -> str:
        return rotulo(*self.mes_final)
