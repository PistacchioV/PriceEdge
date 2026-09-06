"""EURIBOR — taxas diárias do Banco da Finlândia, com base histórica local.

O Suomen Pankki publica o EURIBOR de 1 semana, 1, 3, 6 e 12 meses num relatório
SSRS que exporta CSV, Excel, XML e PDF. É a fonte pública mais limpa da série
diária — e some da internet com facilidade, daí a base local.

**Como a fonte funciona.** O relatório mostra seis meses por vez, a partir de
uma data inicial escolhida num seletor. O seletor é um postback ASP.NET: a
escolha não passa pela URL, então pedir o CSV direto devolve sempre a janela
padrão (os últimos seis meses). Para alcançar o resto:

1. GET na página do visualizador, guardando o ``__VIEWSTATE`` e os cookies;
2. POST com o índice da janela e o botão "View Report";
3. a resposta traz um ``ReportSession`` e um ``ControlID``;
4. GET em ``Reserved.ReportViewerWebControl.axd`` com esses dois e ``Format=CSV``.

São 250 janelas disponíveis, de janeiro de 2006 até o mês corrente. Como cada
uma cobre seis meses e elas andam de mês em mês, uma a cada cinco já cobre tudo
com folga.

**A base local.** ``dados/euribor_historico.json`` guarda tudo que já foi visto,
no formato ``{"AAAA-MM-DD": {"1 week": 0.02154, ...}}``. A sincronização só
acrescenta: uma data que já está lá nunca é sobrescrita por engano, e o que a
fonte deixar de publicar continua aqui.
"""

from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from . import rede

RELATORIO = "/tilastot/markkina-_ja_hallinnolliset_korot/euriborkorot_pv_chrt_en"
RAIZ = "https://reports.suomenpankki.fi"
VISUALIZADOR = f"{RAIZ}/WebForms/ReportViewerPage.aspx?report={RELATORIO}&output="
EXPORTACAO_DIRETA = f"{RAIZ}/WebForms/ReportViewerPage.aspx?report={RELATORIO}&output=CSV"
HANDLER = f"{RAIZ}/Reserved.ReportViewerWebControl.axd"
PAGINA = ("https://www.suomenpankki.fi/en/statistics/data-and-charts/interest-rates/"
          "charts/korot_kuviot_en/euriborkorot_pv_chrt_en/")

ARQUIVO = Path(__file__).resolve().parent / "dados" / "euribor_historico.json"

FORMATOS = {"csv": "CSV", "excel": "EXCELOPENXML", "xml": "XML",
            "pdf": "PDF", "word": "WORDOPENXML"}

CAMPO_SELETOR = "ReportViewer1$ctl04$ctl03$ddValue"
CAMPO_BOTAO = "ReportViewer1$ctl04$ctl00"

TENORES = ["1 week", "1 month", "3 month", "6 month", "12 month"]
TENOR_MESES = {"1 week": 0.25, "1 month": 1, "3 month": 3, "6 month": 6, "12 month": 12}

CABECALHO = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "*/*",
}

_TRAVA = threading.Lock()          # a base é um arquivo só; escrita é serializada


class ErroEuribor(RuntimeError):
    """Falha ao obter ou interpretar o relatório do Banco da Finlândia."""


@dataclass(frozen=True)
class FixingEuribor:
    data: date
    tenor: str
    taxa: float          # decimal ao ano (0.02154 = 2,154%)


# ----------------------------------------------------------------- sessão --

class Sessao:
    """Uma sessão do visualizador SSRS, com cookies e viewstate."""

    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self._jar = http.cookiejar.CookieJar()
        self._op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar))
        self._campos: Dict[str, str] = {}
        self._html = ""

    def abrir(self) -> "Sessao":
        self._html = self._get(VISUALIZADOR).decode("utf-8", "replace")
        self._campos = self._ler_campos(self._html)
        return self

    def _get(self, url: str, referer: Optional[str] = None) -> bytes:
        cabecalho = dict(CABECALHO)
        if referer:
            cabecalho["Referer"] = referer
        try:
            return self._op.open(urllib.request.Request(url, headers=cabecalho),
                                 timeout=self.timeout).read()
        except urllib.error.HTTPError as exc:
            raise ErroEuribor(f"o Banco da Finlândia respondeu HTTP {exc.code}") from exc
        except OSError as exc:
            raise ErroEuribor(f"falha de conexão com o Banco da Finlândia: {exc}") from exc

    def _post(self, url: str, dados: dict) -> str:
        cabecalho = dict(CABECALHO)
        cabecalho["Content-Type"] = "application/x-www-form-urlencoded"
        cabecalho["Referer"] = VISUALIZADOR
        corpo = urllib.parse.urlencode(dados).encode()
        try:
            return self._op.open(
                urllib.request.Request(url, data=corpo, headers=cabecalho),
                timeout=self.timeout).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise ErroEuribor(f"o Banco da Finlândia respondeu HTTP {exc.code}") from exc
        except OSError as exc:
            raise ErroEuribor(f"falha de conexão com o Banco da Finlândia: {exc}") from exc

    @staticmethod
    def _ler_campos(html: str) -> Dict[str, str]:
        return dict(re.findall(
            r'<input type="hidden" name="([^"]+)"[^>]*value="([^"]*)"', html))

    def janelas(self) -> List[Tuple[str, date]]:
        """As janelas oferecidas pelo seletor: (índice, data inicial)."""
        if not self._html:
            self.abrir()
        saida = []
        for indice, rotulo in re.findall(r'<option[^>]*value="(\d+)">([^<]+)</option>',
                                         self._html):
            limpo = rotulo.replace("&nbsp;", " ").strip()
            try:
                saida.append((indice, datetime.strptime(limpo, "%d %b %Y").date()))
            except ValueError:
                continue                       # a opção "<Select a Value>"
        return saida

    def csv_da_janela(self, indice: str) -> str:
        """Seleciona a janela pelo postback e baixa o CSV daquela sessão."""
        if not self._campos:
            self.abrir()
        dados = dict(self._campos)
        dados.update({
            "__EVENTTARGET": "", "__EVENTARGUMENT": "",
            CAMPO_SELETOR: indice, CAMPO_BOTAO: "View Report",
            "ReportViewer1$ctl05$ctl00$CurrentPage": "1",
        })
        resposta = self._post(VISUALIZADOR, dados)

        sessao = re.search(r"ReportSession=([a-z0-9]+)", resposta)
        controle = re.search(r"ControlID=([a-f0-9]+)", resposta)
        if not (sessao and controle):
            raise ErroEuribor("o visualizador não devolveu uma sessão de relatório — "
                              "a página pode ter mudado")

        # o viewstate roda a cada postback; sem atualizar, o próximo falha
        novos = self._ler_campos(resposta)
        if novos:
            self._campos = novos

        url = (f"{HANDLER}?ReportSession={sessao.group(1)}"
               "&Culture=1033&CultureOverrides=True&UICulture=1033"
               "&UICultureOverrides=True&ReportStack=1"
               f"&ControlID={controle.group(1)}&OpType=Export"
               "&FileName=euribor&ContentDisposition=OnlyHtmlInline&Format=CSV")
        return self._get(url, referer=VISUALIZADOR).decode("utf-8-sig", "replace")


# ------------------------------------------------------------------ leitura

def url_exportacao(formato: str = "csv") -> str:
    """URL de exportação da janela padrão, no formato pedido."""
    saida = FORMATOS.get(formato.lower())
    if not saida:
        raise ValueError(f"formato não suportado: {formato}")
    return f"{RAIZ}/WebForms/ReportViewerPage.aspx?report={RELATORIO}&output={saida}"


def parse_csv(conteudo: str) -> List[FixingEuribor]:
    """Lê o CSV do gráfico e devolve os fixings, descartando o bloco da tabela."""
    leitor = csv.reader(io.StringIO(conteudo))
    try:
        next(leitor)
    except StopIteration:
        return []

    fixings: List[FixingEuribor] = []
    for linha in leitor:
        if len(linha) < 4:
            continue
        tenor, bruto_data, bruto_taxa = linha[0], linha[2], linha[3]
        if tenor not in TENOR_MESES:                  # bloco da tabela no rodapé
            continue
        try:
            d = datetime.strptime(bruto_data.strip()[:10], "%m/%d/%Y").date()
            taxa = float(bruto_taxa.strip()) / 100.0
        except (ValueError, IndexError):
            continue
        fixings.append(FixingEuribor(d, tenor, taxa))
    return sorted(fixings, key=lambda f: (f.data, TENORES.index(f.tenor)))


def janela_atual(timeout: int = 60) -> List[FixingEuribor]:
    """A janela padrão (últimos ~6 meses), sem precisar de sessão."""
    try:
        bruto = rede.obter(EXPORTACAO_DIRETA, CABECALHO, timeout).decode("utf-8-sig", "replace")
    except rede.ErroRede as exc:
        raise ErroEuribor(f"não foi possível obter o relatório: {exc}") from exc
    return parse_csv(bruto)


# -------------------------------------------------------- base histórica --

def carregar_base() -> Dict[str, Dict[str, float]]:
    """A base local, ``{data ISO: {tenor: taxa}}``. Vazia se ainda não existe."""
    if not ARQUIVO.exists():
        return {}
    try:
        conteudo = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return conteudo.get("taxas", conteudo) if isinstance(conteudo, dict) else {}


def salvar_base(taxas: Dict[str, Dict[str, float]]) -> None:
    """Grava a base ordenada por data, com um resumo no topo."""
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ordenado = {d: {t: taxas[d][t] for t in TENORES if t in taxas[d]}
                for d in sorted(taxas)}
    documento = {
        "fonte": PAGINA,
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inicio": next(iter(ordenado), None),
        "fim": next(reversed(list(ordenado)), None) if ordenado else None,
        "dias": len(ordenado),
        "tenores": TENORES,
        "taxas": ordenado,
    }
    temporario = ARQUIVO.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(documento, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    temporario.replace(ARQUIVO)                 # troca atômica: nunca fica pela metade


def mesclar(base: Dict[str, Dict[str, float]],
            fixings: Iterable[FixingEuribor]) -> int:
    """Acrescenta à base o que ainda não está lá. Devolve quantos valores entraram.

    Só acrescenta: um valor já gravado não é substituído. A fonte às vezes
    republica uma janela com arredondamento diferente, e o primeiro valor visto
    é o que estava publicado no dia.
    """
    novos = 0
    for f in fixings:
        chave = f.data.isoformat()
        linha = base.setdefault(chave, {})
        if f.tenor not in linha:
            linha[f.tenor] = f.taxa
            novos += 1
    return novos


def sincronizar(profundo: bool = False, passo: int = 5,
                limite: Optional[int] = None) -> dict:
    """Atualiza a base com o que a fonte tem de novo.

    ``profundo=False`` (o padrão, usado a cada carregamento da tela) busca só a
    janela corrente — é uma requisição e pega o que saiu desde a última vez.

    ``profundo=True`` percorre o seletor inteiro para semear a base, uma janela
    a cada ``passo`` (as janelas cobrem seis meses e andam de mês em mês, então
    ``passo=5`` cobre tudo com um mês de sobreposição).
    """
    with _TRAVA:
        base = carregar_base()
        antes = len(base)
        relatorio = {"novos": 0, "janelas": 0, "erros": []}

        if not profundo:
            try:
                relatorio["novos"] = mesclar(base, janela_atual())
                relatorio["janelas"] = 1
            except ErroEuribor as exc:
                relatorio["erros"].append(str(exc))
        else:
            sessao = Sessao().abrir()
            janelas = sessao.janelas()
            escolhidas = janelas[::passo]
            if janelas and janelas[-1] not in escolhidas:
                escolhidas.append(janelas[-1])      # garante a ponta mais antiga
            if limite:
                escolhidas = escolhidas[:limite]
            for indice, inicio in escolhidas:
                try:
                    novos = mesclar(base, parse_csv(sessao.csv_da_janela(indice)))
                    relatorio["novos"] += novos
                    relatorio["janelas"] += 1
                    # grava a cada janela: uma carga de 50 requisições não pode
                    # perder tudo por causa de uma queda no meio
                    if novos:
                        salvar_base(base)
                except ErroEuribor as exc:
                    relatorio["erros"].append(f"{inicio:%b/%Y}: {exc}")

        if relatorio["novos"] or antes == 0:
            salvar_base(base)
        relatorio.update({"dias_antes": antes, "dias_depois": len(base)})
        return relatorio


# ------------------------------------------------------------------ curva --

@dataclass
class CurvaEuribor:
    """A base histórica, organizada por data e por prazo."""
    taxas: Dict[str, Dict[str, float]]

    @classmethod
    def da_base(cls) -> "CurvaEuribor":
        return cls(carregar_base())

    @classmethod
    def de_fixings(cls, fixings: Iterable[FixingEuribor]) -> "CurvaEuribor":
        """Monta a curva a partir de uma leitura solta, sem passar pela base."""
        taxas: Dict[str, Dict[str, float]] = {}
        for f in fixings:
            taxas.setdefault(f.data.isoformat(), {})[f.tenor] = f.taxa
        return cls(taxas)

    @property
    def datas(self) -> List[date]:
        return [datetime.strptime(d, "%Y-%m-%d").date() for d in sorted(self.taxas)]

    @property
    def tenores(self) -> List[str]:
        presentes = {t for linha in self.taxas.values() for t in linha}
        return [t for t in TENORES if t in presentes]

    @property
    def inicio(self) -> Optional[date]:
        datas = self.datas
        return datas[0] if datas else None

    @property
    def fim(self) -> Optional[date]:
        datas = self.datas
        return datas[-1] if datas else None

    def por_data(self) -> Dict[date, Dict[str, float]]:
        return {datetime.strptime(d, "%Y-%m-%d").date(): linha
                for d, linha in self.taxas.items()}

    def ultima(self) -> Dict[str, float]:
        """As taxas da última data publicada na base."""
        fim = self.fim
        return dict(self.taxas[fim.isoformat()]) if fim else {}

    def em(self, referencia: date) -> Tuple[Optional[date], Dict[str, float]]:
        """As taxas vigentes na data de referência.

        Se não houver publicação nesse dia — fim de semana, feriado, ou uma data
        futura — devolve a última anterior, que é a taxa que estaria valendo.
        """
        alvo = referencia.isoformat()
        candidatas = [d for d in sorted(self.taxas) if d <= alvo]
        if not candidatas:
            return None, {}
        escolhida = candidatas[-1]
        return datetime.strptime(escolhida, "%Y-%m-%d").date(), dict(self.taxas[escolhida])

    def curva_do_dia(self, referencia: Optional[date] = None) -> List[dict]:
        """A curva de um dia, em ordem de prazo — pronta para plotar."""
        _, linha = self.em(referencia or date.today())
        return [{"tenor": t, "meses": TENOR_MESES[t], "taxa": linha[t]}
                for t in TENORES if t in linha]

    def janela(self, inicio: date, fim: date) -> "CurvaEuribor":
        """Um recorte da base, para gráfico e tabela."""
        i, f = inicio.isoformat(), fim.isoformat()
        return CurvaEuribor({d: linha for d, linha in self.taxas.items() if i <= d <= f})


def carregar(sincroniza: bool = True) -> CurvaEuribor:
    """A base local, atualizada com a janela corrente da fonte.

    Falha de rede não derruba a tela: se a fonte estiver fora, fica o que já
    está gravado — que é justamente o motivo de existir a base.
    """
    if sincroniza:
        try:
            sincronizar(profundo=False)
        except ErroEuribor:
            pass
    return CurvaEuribor.da_base()
