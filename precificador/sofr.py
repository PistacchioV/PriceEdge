"""SOFR realizado — taxas do Federal Reserve de Nova York e juros compostos.

O Term SOFR é uma taxa *forward-looking*, cotada de antemão; o SOFR puro é
*backward-looking* e só fecha no fim do período, capitalizando o overnight dia
a dia.  Este módulo cuida do segundo caso: busca a série do NY Fed e compõe o
período conforme a convenção do contrato.

Fonte: https://markets.newyorkfed.org/api/rates/secured/sofr/search.json
       https://markets.newyorkfed.org/api/rates/secured/sofrai/search.json  (índice)

As duas defasagens que aparecem em contrato são independentes e podem conviver:

**Lookback (lag)** — no dia ``d`` usa-se a taxa observada ``k`` dias úteis
antes, mas o peso continua sendo o do próprio dia. É a convenção mais comum em
empréstimo bilateral.

**Observation shift** — desloca-se a janela inteira ``k`` dias úteis para trás,
taxas **e** pesos. É a do mercado de derivativos (ISDA) e a que fecha
exatamente com o SOFR Index.

Por isso são dois campos, não um seletor: ``shift`` move a janela (datas e
pesos) e ``lookback`` move só a leitura da taxa dentro dela. Zerando os dois,
o cálculo observa o próprio período. Igualando-os, o efeito é o de um lookback
com observation shift.

A diferença entre eles é pequena, mas existe: com lookback puro os pesos e as
taxas vêm de janelas diferentes, o que descasa feriado e fim de semana.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence

from . import rede
from .erros import ErroDeFonte
from .calendario import Calendario, calendario_sofr, para_data

API = "https://markets.newyorkfed.org/api/rates/secured"

def convencao(lookback: int, shift: int) -> tuple:
    """Como o mercado chamaria essa combinação, em (molde, números).

    Devolve o molde separado dos números porque a tela é bilíngue: uma frase já
    montada com o "3" dentro não tem como ser chave de tradução, e foi assim que
    "Sem defasagem" chegou à tela em inglês.
    """
    if not lookback and not shift:
        return ("Sem defasagem", {})
    if lookback and not shift:
        return ("Lookback de {lookback} dias úteis", {"lookback": lookback})
    if shift and not lookback:
        return ("Observation shift de {shift} dias úteis", {"shift": shift})
    return ("Lookback {lookback} du com observation shift {shift} du",
            {"lookback": lookback, "shift": shift})


def nome_da_convencao(lookback: int, shift: int) -> str:
    """A convenção já montada em português — para log e uso programático."""
    molde, valores = convencao(lookback, shift)
    return molde.format(**valores)


class ErroFed(ErroDeFonte):
    """Falha ao obter a série do NY Fed."""


@dataclass(frozen=True)
class FixingSOFR:
    data: date
    taxa: float            # decimal (0.0366), não percentual
    volume: Optional[float] = None


def _buscar(url: str, timeout: int = 30):
    try:
        return rede.obter_json(url, timeout=timeout)
    except rede.ErroRede as exc:
        raise ErroFed(f"não foi possível obter a série do NY Fed: {exc}") from exc


def serie_sofr(inicio, fim) -> List[FixingSOFR]:
    """Fixings diários do SOFR no intervalo, em ordem crescente de data."""
    d0, d1 = para_data(inicio), para_data(fim)
    dados = _buscar(f"{API}/sofr/search.json?startDate={d0:%Y-%m-%d}&endDate={d1:%Y-%m-%d}")
    linhas = dados.get("refRates", []) if isinstance(dados, dict) else dados
    fixings = [
        FixingSOFR(para_data(linha["effectiveDate"]),
                   float(linha["percentRate"]) / 100.0,
                   linha.get("volumeInBillions"))
        for linha in linhas
        if linha.get("type") == "SOFR" and linha.get("percentRate") is not None
    ]
    return sorted(fixings, key=lambda f: f.data)


def serie_indice(inicio, fim) -> Dict[date, float]:
    """SOFR Index publicado pelo NY Fed, por data."""
    d0, d1 = para_data(inicio), para_data(fim)
    dados = _buscar(f"{API}/sofrai/search.json?startDate={d0:%Y-%m-%d}&endDate={d1:%Y-%m-%d}")
    linhas = dados.get("refRates", []) if isinstance(dados, dict) else dados
    return {para_data(l["effectiveDate"]): float(l["index"])
            for l in linhas if l.get("index") is not None}


# --------------------------------------------------------------- composição

@dataclass
class DiaComposicao:
    """Uma linha do cálculo — o que a planilha mostraria dia a dia."""
    data_juros: date          # dia do período de juros
    data_observacao: date     # dia de onde a taxa veio
    taxa: float
    dias: int                 # dias corridos que a taxa remunera
    fator_dia: float          # 1 + taxa · dias/360
    fator_acumulado: float


@dataclass
class ResultadoSOFR:
    inicio: date
    fim: date
    lookback: int
    shift: int
    obs_inicio: date
    obs_fim: date
    dias_corridos: int
    fator: float
    taxa_composta: float
    taxa_media_simples: float
    dias: List[DiaComposicao]

    def para_dict(self) -> dict:
        return {
            "inicio": self.inicio.isoformat(), "fim": self.fim.isoformat(),
            "lookback": self.lookback, "shift": self.shift,
            "obs_inicio": self.obs_inicio.isoformat(),
            "obs_fim": self.obs_fim.isoformat(),
            "dias_corridos": self.dias_corridos, "fator": self.fator,
            "taxa_composta": self.taxa_composta,
            "taxa_media_simples": self.taxa_media_simples,
            "dias": [d.__dict__ for d in self.dias],
        }


def compor(fixings: Sequence[FixingSOFR], inicio, fim,
           lookback: int = 0, shift: int = 0,
           calendario: Optional[Calendario] = None,
           base: float = 360.0) -> ResultadoSOFR:
    """Compõe o SOFR do período com as defasagens pedidas.

        fator = Π [1 + r_i · n_i / 360]
        taxa  = (fator − 1) · 360 / D

    ``n_i`` é o número de dias corridos até o próximo dia útil — é assim que
    fim de semana e feriado entram: o fixing de sexta remunera três dias.

    ``shift`` desloca a janela inteira (datas e pesos) ``k`` dias úteis para
    trás; ``lookback`` desloca só a leitura da taxa, dentro da janela já
    deslocada. Os dois são independentes e podem ser usados juntos.
    """
    cal = calendario or calendario_sofr()
    d0, d1 = para_data(inicio), para_data(fim)
    if d1 <= d0:
        raise ValueError("o fim do período tem que ser posterior ao início")
    if lookback < 0 or shift < 0:
        raise ValueError("lookback e shift não podem ser negativos")

    por_data = {f.data: f.taxa for f in fixings}

    # a janela de pesos: o período de juros deslocado por `shift`
    obs_inicio = cal.workday(d0, -shift) if shift else d0
    obs_fim = cal.workday(d1, -shift) if shift else d1

    dias_da_janela = _dias_uteis_entre(cal, obs_inicio, obs_fim)
    sequencia = dias_da_janela + [obs_fim]

    linhas: List[DiaComposicao] = []
    fator = 1.0
    soma_ponderada = 0.0

    for i, dia in enumerate(dias_da_janela):
        n = (sequencia[i + 1] - dia).days
        observacao = cal.workday(dia, -lookback) if lookback else dia
        taxa = _taxa_do_dia(por_data, observacao, cal)
        fator *= 1.0 + taxa * n / base
        soma_ponderada += taxa * n
        linhas.append(DiaComposicao(dia, observacao, taxa, n,
                                    1.0 + taxa * n / base, fator))

    dias_corridos = (obs_fim - obs_inicio).days
    if dias_corridos <= 0:
        raise ValueError("período sem dias corridos")

    return ResultadoSOFR(
        inicio=d0, fim=d1, lookback=lookback, shift=shift,
        obs_inicio=obs_inicio, obs_fim=obs_fim,
        dias_corridos=dias_corridos,
        fator=fator,
        taxa_composta=(fator - 1.0) * base / dias_corridos,
        taxa_media_simples=soma_ponderada / dias_corridos,
        dias=linhas,
    )


def _dias_uteis_entre(cal: Calendario, inicio: date, fim: date) -> List[date]:
    """Dias úteis de ``inicio`` (inclusive) até ``fim`` (exclusive)."""
    dias, d = [], inicio
    while d < fim:
        if cal.eh_dia_util(d):
            dias.append(d)
        d += timedelta(days=1)
    return dias


def _taxa_do_dia(por_data: Dict[date, float], dia: date, cal: Calendario) -> float:
    """Fixing do dia; se faltar, repete o último publicado antes dele.

    Buraco na série acontece — feriado que o calendário não previu, revisão
    ainda não publicada.  Repetir o anterior é o que a convenção manda e o que
    o próprio NY Fed faz no cálculo do índice.
    """
    if dia in por_data:
        return por_data[dia]
    anteriores = [d for d in por_data if d < dia]
    if not anteriores:
        raise ErroFed(f"não há fixing de SOFR publicado para {dia:%d/%m/%Y} "
                      "nem antes dessa data — amplie o intervalo consultado")
    return por_data[max(anteriores)]


def compor_por_indice(indice: Dict[date, float], inicio, fim,
                      base: float = 360.0) -> float:
    """Taxa composta a partir do SOFR Index — o atalho oficial do NY Fed.

        taxa = (Index_fim / Index_início − 1) · 360 / D

    Bate exatamente com a composição diária na convenção *observation shift*,
    e serve de conferência para ela.
    """
    d0, d1 = para_data(inicio), para_data(fim)
    if d0 not in indice or d1 not in indice:
        faltando = d0 if d0 not in indice else d1
        raise ErroFed(f"o SOFR Index não tem publicação para {faltando:%d/%m/%Y}")
    dias = (d1 - d0).days
    if dias <= 0:
        raise ValueError("período sem dias corridos")
    return (indice[d1] / indice[d0] - 1.0) * base / dias


# ------------------------------------------------------- base histórica ----
#
# O Term SOFR *forward-looking* de 1, 3, 6 e 12 meses é da CME e é licenciado —
# não há fonte pública que permita redistribuí-lo, e por isso ele continua
# entrando digitado na tela de precificação. O que o NY Fed publica aberto, e o
# que fica guardado aqui, é a estrutura a termo *realizada*: o overnight e as
# médias compostas de 30, 90 e 180 dias, mais o SOFR Index.
#
# Mesmo desenho da base de EURIBOR: um JSON que só cresce, sincronizado a cada
# carregamento da tela, para o histórico não depender da API continuar de pé.

import json as _json
import threading as _threading
from pathlib import Path as _Path

ARQUIVO = _Path(__file__).resolve().parent / "dados" / "sofr_historico.json"
INICIO_DA_SERIE = date(2018, 4, 2)          # primeiro fixing publicado do SOFR

CAMPOS = [
    ("overnight", "SOFR overnight"),
    ("media30", "Média composta 30 dias"),
    ("media90", "Média composta 90 dias"),
    ("media180", "Média composta 180 dias"),
]

_TRAVA_BASE = _threading.Lock()


def carregar_base() -> Dict[str, dict]:
    if not ARQUIVO.exists():
        return {}
    try:
        conteudo = _json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return conteudo.get("taxas", {}) if isinstance(conteudo, dict) else {}


def salvar_base(taxas: Dict[str, dict]) -> None:
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ordenado = {d: taxas[d] for d in sorted(taxas)}
    documento = {
        "fonte": "https://markets.newyorkfed.org/api/rates/secured",
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inicio": next(iter(ordenado), None),
        "fim": next(reversed(list(ordenado)), None) if ordenado else None,
        "dias": len(ordenado),
        "campos": [c for c, _ in CAMPOS] + ["indice"],
        "taxas": ordenado,
    }
    temporario = ARQUIVO.with_suffix(".json.tmp")
    temporario.write_text(_json.dumps(documento, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    temporario.replace(ARQUIVO)


def _mesclar(base: Dict[str, dict], linhas: dict) -> int:
    """Acrescenta o que falta; nunca sobrescreve valor já gravado."""
    novos = 0
    for chave, valores in linhas.items():
        linha = base.setdefault(chave, {})
        for campo, valor in valores.items():
            if valor is not None and campo not in linha:
                linha[campo] = valor
                novos += 1
    return novos


def _janela(inicio: date, fim: date) -> dict:
    """Overnight, médias e índice do intervalo, num dicionário por data."""
    coletado: dict = {}
    for f in serie_sofr(inicio, fim):
        coletado.setdefault(f.data.isoformat(), {})["overnight"] = f.taxa

    dados = _buscar(f"{API}/sofrai/search.json"
                    f"?startDate={inicio:%Y-%m-%d}&endDate={fim:%Y-%m-%d}")
    linhas = dados.get("refRates", []) if isinstance(dados, dict) else dados
    for linha in linhas:
        if linha.get("type") != "SOFRAI":
            continue
        chave = para_data(linha["effectiveDate"]).isoformat()
        alvo = coletado.setdefault(chave, {})
        for campo, origem in (("media30", "average30day"), ("media90", "average90day"),
                              ("media180", "average180day")):
            if linha.get(origem) is not None:
                alvo[campo] = float(linha[origem]) / 100.0
        if linha.get("index") is not None:
            alvo["indice"] = float(linha["index"])
    return coletado


def sincronizar(profundo: bool = False, dias_recentes: int = 45) -> dict:
    """Atualiza a base local com o que o NY Fed publicou.

    ``profundo=True`` varre desde 02/04/2018, ano a ano — a API recusa
    intervalos muito longos numa requisição só.
    """
    with _TRAVA_BASE:
        base = carregar_base()
        antes = len(base)
        relatorio = {"novos": 0, "janelas": 0, "erros": []}
        hoje = date.today()

        if profundo:
            intervalos = []
            inicio = INICIO_DA_SERIE
            while inicio < hoje:
                fim = min(date(inicio.year + 1, inicio.month, inicio.day), hoje)
                intervalos.append((inicio, fim))
                inicio = fim
        else:
            intervalos = [(hoje - timedelta(days=dias_recentes), hoje)]

        for inicio, fim in intervalos:
            try:
                novos = _mesclar(base, _janela(inicio, fim))
                relatorio["novos"] += novos
                relatorio["janelas"] += 1
                if novos:
                    salvar_base(base)          # grava a cada janela
            except ErroFed as exc:
                relatorio["erros"].append(f"{inicio:%Y}: {exc}")

        if relatorio["novos"] or antes == 0:
            salvar_base(base)
        relatorio.update({"dias_antes": antes, "dias_depois": len(base)})
        return relatorio


@dataclass
class HistoricoSOFR:
    """A base histórica, por data e por prazo."""
    taxas: Dict[str, dict]

    @classmethod
    def da_base(cls) -> "HistoricoSOFR":
        return cls(carregar_base())

    @property
    def datas(self) -> List[date]:
        return [para_data(d) for d in sorted(self.taxas)]

    @property
    def campos(self) -> List[str]:
        presentes = {c for linha in self.taxas.values() for c in linha}
        return [c for c, _ in CAMPOS if c in presentes]

    @property
    def inicio(self) -> Optional[date]:
        datas = self.datas
        return datas[0] if datas else None

    @property
    def fim(self) -> Optional[date]:
        datas = self.datas
        return datas[-1] if datas else None

    def por_data(self) -> Dict[date, dict]:
        return {para_data(d): linha for d, linha in self.taxas.items()}

    def em(self, referencia: date):
        """As taxas vigentes na data (ou a última publicação anterior)."""
        alvo = referencia.isoformat()
        candidatas = [d for d in sorted(self.taxas) if d <= alvo]
        if not candidatas:
            return None, {}
        escolhida = candidatas[-1]
        return para_data(escolhida), dict(self.taxas[escolhida])

    def janela(self, inicio: date, fim: date) -> "HistoricoSOFR":
        i, f = inicio.isoformat(), fim.isoformat()
        return HistoricoSOFR({d: v for d, v in self.taxas.items() if i <= d <= f})


def carregar_historico(sincroniza: bool = True) -> HistoricoSOFR:
    """A base local, atualizada com os últimos dias. Falha de rede não derruba."""
    if sincroniza:
        try:
            sincronizar(profundo=False)
        except ErroFed:
            pass
    return HistoricoSOFR.da_base()
