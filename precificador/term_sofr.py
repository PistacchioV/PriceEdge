"""Term SOFR — a curva a termo da CME, importada da planilha da B3.

O Term SOFR *forward-looking* de 1, 3, 6 e 12 meses é administrado pela CME e
**licenciado**: não há fonte pública que permita redistribuí-lo, e por isso ele
nunca desceu de API neste pacote — entrava digitado, número por número, na tela
de precificação e na de liquidação.

Quem tem a licença tem o arquivo. A B3 exporta as cotações num relatório com
uma coluna de ticker e uma de valor, e este módulo lê esse arquivo e guarda o
que veio. A licença continua sendo de quem importa: o dado entra pela mão do
usuário, e não sai daqui para lugar nenhum.

    coluna L   ticker            TSFR1M, TSFR3M, TSFR6M, TSFR12M
    coluna O   data da cotação   serial do Excel ou dd/mm/aaaa
    coluna P   valor da cotação  3,74231

**O valor não é taxa.** A planilha traz ``3,74231``, que é o percentual escrito
como número — e o pacote inteiro trabalha em decimal, onde 3,74% é ``0,0374231``.
Guardar o que veio faria a taxa entrar cem vezes maior em toda conta que a
usasse, e o número continuaria parecendo plausível na tela até alguém conferir
um MtM. A divisão por 100 acontece na importação, uma vez, e o que fica na base
já é decimal.

As colunas são procuradas pelo **cabeçalho** e só caem na posição fixa se ele
não aparecer: um relatório que ganhe uma coluna no meio continua sendo lido.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import planilha
from .calendario import para_data
from .erros import ErroTraduzido

ARQUIVO = Path(__file__).resolve().parent / "dados" / "term_sofr_b3.json"

# ticker da B3 → (campo na base, rótulo, meses)
TICKERS = {
    "TSFR1M": ("m1", "Term SOFR 1 mês", 1),
    "TSFR3M": ("m3", "Term SOFR 3 meses", 3),
    "TSFR6M": ("m6", "Term SOFR 6 meses", 6),
    "TSFR12M": ("m12", "Term SOFR 12 meses", 12),
}
CAMPOS = [(campo, rotulo, meses) for campo, rotulo, meses in TICKERS.values()]
CAMPO_POR_MESES = {meses: campo for campo, _, meses in CAMPOS}

# posição das colunas no relatório da B3, quando o cabeçalho não é encontrado
COLUNA_TICKER = 11        # L
COLUNA_DATA = 14          # O
COLUNA_VALOR = 15         # P

_CABECALHOS = {
    "ticker": ("ticker",),
    "data": ("data da cotacao", "data da cotação", "data"),
    "valor": ("valor da cotacao", "valor da cotação", "valor", "taxa"),
}

_TRAVA = threading.Lock()          # a base é um arquivo só; escrita é serializada


class ErroTermSOFR(ErroTraduzido, ValueError):
    """Arquivo que não dá para importar, com o motivo por extenso."""


@dataclass
class Importacao:
    """O que a importação encontrou — para a tela dizer o que entrou."""
    linhas_lidas: int
    aproveitadas: int
    novas: int
    atualizadas: int
    datas: List[date]
    tickers: Dict[str, int]
    ignorados: Dict[str, int]

    @property
    def inicio(self) -> Optional[date]:
        return min(self.datas) if self.datas else None

    @property
    def fim(self) -> Optional[date]:
        return max(self.datas) if self.datas else None


def _sem_acento(texto: str) -> str:
    import unicodedata
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c)).strip().lower()


def _achar_colunas(linhas: List[List[str]]) -> Tuple[int, int, int, int]:
    """(linha do cabeçalho, coluna do ticker, da data, do valor).

    Procura o cabeçalho para aguentar um relatório que mude de forma. Sem ele,
    volta às posições L, O e P — que é o que o arquivo de hoje tem.
    """
    for numero, linha in enumerate(linhas):
        achado = {}
        for indice, celula in enumerate(linha):
            rotulo = _sem_acento(celula)
            for chave, aceitos in _CABECALHOS.items():
                if chave not in achado and rotulo in aceitos:
                    achado[chave] = indice
        if len(achado) == 3:
            return numero, achado["ticker"], achado["data"], achado["valor"]
    return -1, COLUNA_TICKER, COLUNA_DATA, COLUNA_VALOR


def carregar_base() -> Dict[str, dict]:
    if not ARQUIVO.exists():
        return {}
    try:
        with ARQUIVO.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def salvar_base(taxas: Dict[str, dict]) -> None:
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO.with_suffix(".json.tmp")
    with temporario.open("w", encoding="utf-8") as f:
        json.dump(taxas, f, ensure_ascii=False, indent=1, sort_keys=True)
    temporario.replace(ARQUIVO)        # troca atômica: nunca fica meio arquivo


def importar(nome: str, dados: bytes) -> Importacao:
    """Lê o relatório da B3 e junta o que veio à base local.

    O que já existe é **substituído** pelo que chega: o arquivo mais novo é a
    correção do anterior, e manter o valor antigo faria a base divergir da
    planilha sem nenhum sinal.
    """
    try:
        linhas = planilha.ler(nome, dados)
    except planilha.ErroPlanilha as exc:
        raise ErroTermSOFR.de(exc) from exc
    if not linhas:
        raise ErroTermSOFR("o arquivo está vazio")

    cabecalho, c_ticker, c_data, c_valor = _achar_colunas(linhas)

    encontrados: Dict[str, Dict[str, float]] = {}
    tickers: Dict[str, int] = {}
    ignorados: Dict[str, int] = {}
    aproveitadas = 0

    for numero, linha in enumerate(linhas):
        if numero <= cabecalho:
            continue
        ticker = planilha.celula(linha, c_ticker).upper().replace(" ", "")
        if not ticker:
            continue
        if ticker not in TICKERS:
            ignorados[ticker] = ignorados.get(ticker, 0) + 1
            continue

        dia = planilha.como_data(planilha.celula(linha, c_data))
        valor = planilha.como_numero(planilha.celula(linha, c_valor))
        if dia is None or valor is None:
            ignorados["sem data ou valor"] = ignorados.get("sem data ou valor", 0) + 1
            continue

        campo = TICKERS[ticker][0]
        # o percentual da planilha vira decimal aqui, uma vez só
        encontrados.setdefault(dia.isoformat(), {})[campo] = valor / 100.0
        tickers[ticker] = tickers.get(ticker, 0) + 1
        aproveitadas += 1

    if not encontrados:
        conhecidos = ", ".join(sorted(TICKERS))
        raise ErroTermSOFR(
            "nenhuma cotação de Term SOFR no arquivo. Procurei o ticker na coluna "
            "{ticker}, a data na {data} e o valor na {valor}, e esperava um de: "
            "{esperados}.",
            ticker=planilha.letra_da_coluna(c_ticker),
            data=planilha.letra_da_coluna(c_data),
            valor=planilha.letra_da_coluna(c_valor), esperados=conhecidos)

    with _TRAVA:
        base = carregar_base()
        novas = atualizadas = 0
        for dia, taxas in encontrados.items():
            if dia in base:
                atualizadas += 1
                base[dia].update(taxas)
            else:
                novas += 1
                base[dia] = taxas
        salvar_base(base)

    return Importacao(
        linhas_lidas=len(linhas), aproveitadas=aproveitadas,
        novas=novas, atualizadas=atualizadas,
        datas=[para_data(d) for d in encontrados], tickers=tickers,
        ignorados=ignorados)


@dataclass
class Historico:
    """A base local, por data e por prazo."""
    taxas: Dict[str, dict]

    @classmethod
    def da_base(cls) -> "Historico":
        return cls(carregar_base())

    @property
    def datas(self) -> List[date]:
        return [para_data(d) for d in sorted(self.taxas)]

    @property
    def campos(self) -> List[str]:
        presentes = {c for linha in self.taxas.values() for c in linha}
        return [campo for campo, _, _ in CAMPOS if campo in presentes]

    @property
    def inicio(self) -> Optional[date]:
        datas = self.datas
        return datas[0] if datas else None

    @property
    def fim(self) -> Optional[date]:
        datas = self.datas
        return datas[-1] if datas else None

    @property
    def vazio(self) -> bool:
        return not self.taxas

    def por_data(self) -> Dict[date, dict]:
        return {para_data(d): dict(linha) for d, linha in self.taxas.items()}

    def em(self, referencia) -> Tuple[Optional[date], dict]:
        """As taxas vigentes na data, ou a última publicação anterior.

        Fim de semana e feriado não têm cotação, e a taxa que valeria é a da
        última publicação — devolver vazio faria a tela dizer que não há dado
        quando há.
        """
        alvo = para_data(referencia).isoformat()
        candidatas = [d for d in sorted(self.taxas) if d <= alvo]
        if not candidatas:
            return None, {}
        escolhida = candidatas[-1]
        return para_data(escolhida), dict(self.taxas[escolhida])

    def taxa(self, meses: int, referencia) -> Optional[float]:
        """A taxa de um prazo na data, em decimal. ``None`` quando não há."""
        campo = CAMPO_POR_MESES.get(meses)
        if not campo:
            return None
        _, linha = self.em(referencia)
        return linha.get(campo)

    def janela(self, inicio, fim) -> "Historico":
        i, f = para_data(inicio).isoformat(), para_data(fim).isoformat()
        return Historico({d: v for d, v in self.taxas.items() if i <= d <= f})


def carregar() -> Historico:
    return Historico.da_base()
