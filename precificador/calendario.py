"""Calendário de dias úteis.

Reproduz o comportamento das funções de planilha usadas nas macros originais:

    NETWORKDAYS(inicio; fim; feriados) - 1   ->  Calendario.dias_uteis
    WORKDAY(data; n; feriados)               ->  Calendario.workday
    IF(OR(WEEKDAY(d;2)>5; COUNTIF(...)); WORKDAY(d;1); d)  ->  Calendario.ajusta

A lista de feriados é a mesma ANBIMA embutida nas planilhas (2001-2099),
extraída para ``dados/feriados_anbima.json``.  O calendário ``US+BR`` (união
dos feriados americanos e brasileiros, 2020-2038) vem da planilha de Term
SOFR e é usado nas pernas em dólar.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

_DADOS = Path(__file__).resolve().parent / "dados"

# Convenções de dia útil (business day conventions)
FOLLOWING = "following"
MODIFIED_FOLLOWING = "modified_following"
PRECEDING = "preceding"
MODIFIED_PRECEDING = "modified_preceding"
UNADJUSTED = "unadjusted"

CONVENCOES_DIA_UTIL = [
    (FOLLOWING, "Following — próximo dia útil"),
    (MODIFIED_FOLLOWING, "Modified following — próximo dia útil, sem virar o mês"),
    (PRECEDING, "Preceding — dia útil anterior"),
    (MODIFIED_PRECEDING, "Modified preceding — dia útil anterior, sem virar o mês"),
    (UNADJUSTED, "Unadjusted — não ajusta"),
]


def para_data(valor) -> date:
    """Aceita ``date``, ``datetime`` ou string ISO / dd/mm/aaaa."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue
    raise ValueError(f"data inválida: {valor!r}")


class Calendario:
    """Conjunto de feriados + regra de fim de semana (sábado e domingo)."""

    def __init__(self, feriados: Iterable[date], nome: str = "") -> None:
        self.nome = nome
        self._feriados = frozenset(feriados)

    # ------------------------------------------------------------------ base

    @property
    def feriados(self) -> frozenset:
        return self._feriados

    def eh_dia_util(self, d) -> bool:
        d = para_data(d)
        return d.weekday() < 5 and d not in self._feriados

    def ajusta(self, d, seguinte: bool = True,
               convencao: Optional[str] = None) -> date:
        """Leva a data para um dia útil segundo a convenção de dia útil.

        ``following`` (padrão) é o que as planilhas fazem — o
        ``IF(OR(WEEKDAY(d;2)>5;COUNTIF(feriados;d));WORKDAY(d;1);d)`` da coluna
        "Ajuste Pgto DU".  As demais existem porque contrato de balcão as usa:

        ``following``            próximo dia útil
        ``modified_following``   próximo dia útil, **salvo** se ele cair no mês
                                 seguinte — aí volta para o dia útil anterior
        ``preceding``            dia útil anterior
        ``modified_preceding``   espelho do modified following
        ``unadjusted``           não mexe na data

        Modified following é a convenção de mercado da maioria dos swaps: ela
        impede que um vencimento de fim de mês pule para o mês seguinte e
        desalinhe o período de juros.
        """
        d = para_data(d)
        if convencao is None:
            convencao = FOLLOWING if seguinte else PRECEDING
        convencao = convencao.lower()

        if convencao == UNADJUSTED:
            return d
        if self.eh_dia_util(d):
            return d

        if convencao in (FOLLOWING, MODIFIED_FOLLOWING):
            ajustada = self._caminha(d, +1)
            if convencao == MODIFIED_FOLLOWING and ajustada.month != d.month:
                return self._caminha(d, -1)
            return ajustada

        if convencao in (PRECEDING, MODIFIED_PRECEDING):
            ajustada = self._caminha(d, -1)
            if convencao == MODIFIED_PRECEDING and ajustada.month != d.month:
                return self._caminha(d, +1)
            return ajustada

        raise ValueError(f"convenção de dia útil desconhecida: {convencao}")

    def _caminha(self, d: date, direcao: int) -> date:
        passo = timedelta(days=direcao)
        while not self.eh_dia_util(d):
            d += passo
        return d

    def workday(self, d, dias: int) -> date:
        """``WORKDAY(d; dias; feriados)`` — n dias úteis à frente/atrás."""
        d = para_data(d)
        if dias == 0:
            return d
        passo = timedelta(days=1 if dias > 0 else -1)
        restantes = abs(int(dias))
        while restantes:
            d += passo
            if self.eh_dia_util(d):
                restantes -= 1
        return d

    def networkdays(self, inicio, fim) -> int:
        """``NETWORKDAYS(inicio; fim; feriados)`` do Excel.

        Conta os dias úteis do intervalo **incluindo as duas pontas**.
        """
        inicio, fim = para_data(inicio), para_data(fim)
        if fim < inicio:
            return -self.networkdays(fim, inicio)
        total = 0
        d = inicio
        while d <= fim:
            if self.eh_dia_util(d):
                total += 1
            d += timedelta(days=1)
        return total

    def dias_uteis(self, inicio, fim) -> int:
        """``NETWORKDAYS(inicio; fim; feriados) - 1`` — a convenção das planilhas.

        Quando ``inicio`` é dia útil isso equivale a contar o intervalo aberto
        à esquerda, e ``dias_uteis(d, d) == 0``.  Quando ``inicio`` cai em fim
        de semana ou feriado, porém, o −1 corta um dia útil de verdade e o
        resultado fica uma unidade abaixo dessa contagem.

        Parece detalhe, mas não é: nas agendas de swap a data inicial é sempre
        ajustada para dia útil e os dois jeitos coincidem — já no NI pro-rata a
        data-base é o dia 15, que cai em fim de semana com frequência, e aí a
        planilha usa este valor.  Reproduzi-lo é o que faz o VNA bater.
        """
        return self.networkdays(inicio, fim) - 1

    @staticmethod
    def dias_corridos(inicio, fim) -> int:
        return (para_data(fim) - para_data(inicio)).days

    # ------------------------------------------------------- construção/util

    @classmethod
    def de_json(cls, caminho: Path, nome: str = "") -> "Calendario":
        """Lê uma lista de datas ISO ou de objetos com ``data``/``date``.

        Os arquivos vêm de origens diferentes — o da ANBIMA saiu da planilha, o
        do SOFR e o do EURIBOR vieram do OTC Tracker — e cada um nomeia o campo
        no seu idioma. Ler as duas formas evita normalizar os arquivos só por
        causa disso.
        """
        bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
        datas = []
        for item in bruto:
            if isinstance(item, dict):
                texto = item.get("data") or item.get("date")
                if not texto:
                    continue
            else:
                texto = item
            datas.append(para_data(texto))
        return cls(datas, nome=nome)


@lru_cache(maxsize=None)
def calendario_anbima() -> Calendario:
    """Feriados bancários brasileiros (ANBIMA), 2001-2099."""
    return Calendario.de_json(_DADOS / "feriados_anbima.json", nome="ANBIMA")


@lru_cache(maxsize=None)
def calendario_us_br() -> Calendario:
    """União de feriados EUA + Brasil, usada nas pernas em dólar."""
    return Calendario.de_json(_DADOS / "feriados_us_br.json", nome="US+BR")


@lru_cache(maxsize=None)
def calendario_sofr() -> Calendario:
    """Calendário do SOFR — feriados federais dos EUA mais a Sexta-feira Santa.

    Importado do OTC Tracker (``apps/static/data/sofr.json``), 645 datas de
    2023 a 2077.  É o calendário de dias bons do SOFR: os feriados do Federal
    Reserve mais a recomendação SIFMA de fechar na Sexta-feira Santa.
    """
    return Calendario.de_json(_DADOS / "feriados_sofr.json", nome="SOFR")


@lru_cache(maxsize=None)
def calendario_bce() -> Calendario:
    """Calendário EURIBOR/TARGET2 — os dias em que se publica taxa em euro.

    Vem do arquivo ``dados/feriados_euribor.json`` (2024-2099), que traz também
    os dias de fechamento antecipado que o TARGET observa na prática — 24 e 31
    de dezembro — e que a regra pura não pegaria.

    Fora do alcance do arquivo cai em ``calendario_target2``, a regra do BCE.
    """
    do_arquivo = Calendario.de_json(_DADOS / "feriados_euribor.json", nome="EURIBOR")
    regra = calendario_target2()
    anos = {d.year for d in do_arquivo.feriados}
    complemento = {d for d in regra.feriados if d.year not in anos}
    return Calendario(do_arquivo.feriados | complemento, nome="BCE (EURIBOR/TARGET2)")


@lru_cache(maxsize=None)
def calendario_target2(inicio: int = 1999, fim: int = 2099) -> Calendario:
    """TARGET2 pela regra: seis feriados por ano, dois deles móveis.

        1 de janeiro · Sexta-feira Santa · Segunda-feira de Páscoa
        1 de maio · 25 de dezembro · 26 de dezembro

    Diferente dos demais mercados, o TARGET **não** transfere feriado que cai
    no fim de semana para o dia útil seguinte.
    """
    feriados = []
    for ano in range(inicio, fim + 1):
        domingo = pascoa(ano)
        feriados.extend([
            date(ano, 1, 1),
            domingo - timedelta(days=2),      # Sexta-feira Santa
            domingo + timedelta(days=1),      # Segunda-feira de Páscoa
            date(ano, 5, 1),
            date(ano, 12, 25),
            date(ano, 12, 26),
        ])
    return Calendario(feriados, nome="TARGET2")


def pascoa(ano: int) -> date:
    """Domingo de Páscoa pelo algoritmo de Meeus/Gauss (calendário gregoriano).

    Mesmo cálculo do ``DomingoDePascoa`` do módulo CurvasB3 das planilhas.
    """
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


# nome exibido -> (função, descrição). A tela lê daqui, então não há como a
# lista da interface ficar defasada em relação ao que o pacote realmente tem.
CALENDARIOS_DISPONIVEIS = [
    ("ANBIMA", calendario_anbima, "Feriados bancários do Brasil (2001-2099)"),
    ("SOFR", calendario_sofr, "Feriados do Federal Reserve + Sexta-feira Santa"),
    ("EURIBOR", calendario_bce, "TARGET2 com os fechamentos de 24 e 31/12"),
    ("TARGET2", calendario_target2, "Regra do BCE: seis feriados por ano"),
    ("US+BR", calendario_us_br, "União de EUA e Brasil (2020-2038)"),
]

CALENDARIOS = {nome: funcao for nome, funcao, _ in CALENDARIOS_DISPONIVEIS}
CALENDARIOS["BCE"] = calendario_bce          # apelido histórico do EURIBOR


def obter_calendario(nome: str = "ANBIMA") -> Calendario:
    try:
        return CALENDARIOS[nome.upper()]()
    except KeyError as exc:
        raise ValueError(f"calendário desconhecido: {nome}") from exc


# --------------------------------------------------------------- cronogramas

def cronograma(inicio, fim, meses: int, calendario: Calendario | None = None) -> list:
    """Datas de pagamento de ``inicio`` até ``fim`` a cada ``meses`` meses.

    Devolve as datas *não ajustadas* (a data cheia do aniversário); o ajuste
    para dia útil é feito na precificação, como nas planilhas.
    """
    inicio, fim = para_data(inicio), para_data(fim)
    if meses <= 0:
        return [fim]
    datas, i = [], 1
    while True:
        d = soma_meses(inicio, meses * i)
        if d >= fim:
            datas.append(fim)
            break
        datas.append(d)
        i += 1
    return datas


def soma_meses(d, meses: int) -> date:
    """``EDATE`` — soma meses preservando o dia (ou o último dia do mês)."""
    d = para_data(d)
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, _ultimo_dia(ano, mes))
    return date(ano, mes, dia)


def _ultimo_dia(ano: int, mes: int) -> int:
    if mes == 12:
        return 31
    return (date(ano, mes + 1, 1) - timedelta(days=1)).day


def terceira_quarta(ano: int, mes: int) -> date:
    """Data IMM: terceira quarta-feira do mês (vencimento dos futuros SOFR)."""
    d = date(ano, mes, 1)
    # weekday(): segunda=0 ... quarta=2
    primeira = d + timedelta(days=(2 - d.weekday()) % 7)
    return primeira + timedelta(days=14)
