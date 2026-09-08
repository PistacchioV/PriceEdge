"""Cotações — PTAX do Banco Central, ações e commodities.

Porte da tela *Quotes* do OTC Tracker. São três buscas de histórico por período,
e a diferença entre elas é a fonte e o de-para:

    PTAX          BCB Olinda        Data · Moeda · CCY/BRL compra e venda
                                    · CCY/USD compra e venda
    Ações         Yahoo Finance     Data · fechamento ajustado · fechamento
                                    · máxima · mínima · abertura · volume
    Commodities   Yahoo Finance     idem

Três decisões que vieram de lá e continuam valendo aqui:

**Só o boletim de fechamento.** O BCB publica vários boletins por dia — abertura
e intermediários — e a cotação que a mesa usa é a de fechamento. Trazer todos
poria quatro linhas do mesmo dia na tabela, com valores diferentes e nenhuma
indicação de qual vale.

**Vazio não é zero.** O Yahoo devolve ``null`` no dia sem pregão daquele papel.
Um ``0,00`` ali afirmaria um preço que não existiu, então a célula fica vazia.

**O de-para aceita padrão, não só código fechado.** Um contrato futuro é a mesma
mercadoria em cada vencimento, e cadastrar linha por linha seriam dezenas de
linhas por mercadoria — mais uma a cada vencimento que a B3 abre, para sempre.
A notação ``"MY"`` (letra do mês + ano) resolve a família inteira numa linha:

    BO"MY"  →  ZL"MY".CBT        BOK6   → ZLK26.CBT
    C_"MY"  →  ZC"MY".CBT        'C K6' → ZCK26.CBT

Duas assimetrias que o padrão resolve e que obrigariam ao de-para literal se
ficassem de fora: o **ano** tem larguras diferentes dos dois lados — a B3
escreve um dígito (``BOK6``) ou dois (``AULZ29``), o símbolo de mercado escreve
sempre dois —, e o ``"MY"`` do símbolo fica no **meio** (``ZL"MY".CBT``), porque
o sufixo de bolsa vem depois do vencimento.

Linha **sem** ``"MY"`` continua sendo de-para literal, e ela vence o padrão: é o
que permite cadastrar a exceção de um vencimento só sem desmontar a regra da
mercadoria inteira. Ações não têm vencimento e são todas literais — o mesmo
motor serve os dois cadastros sem nenhum ramo por tipo.

O que **não** veio junto: a sessão Kerberos da Athena, que é de host interno do
OTC Tracker e não existe aqui. Quem sai à internet é o ``rede`` deste pacote,
que já sabe do proxy corporativo.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

from . import rede
from .erros import ErroDeFonte

PASTA = Path(__file__).resolve().parent / "dados"

PTAX = "ptax"
ACOES = "acoes"
COMMODITIES = "commodities"

# As moedas que o BCB publica na PTAX. Não é cadastro: é o domínio do endpoint —
# pedir uma moeda fora desta lista devolve vazio, não erro.
MOEDAS_PTAX = ("AUD", "CAD", "CHF", "DKK", "EUR", "GBP", "JPY", "NOK", "SEK", "USD")

TIPOS = [
    (PTAX, "PTAX — Banco Central", "Boletim de fechamento por moeda."),
    (ACOES, "Ações e índices", "Fechamento diário do Yahoo Finance."),
    (COMMODITIES, "Commodities", "Futuros e contratos contínuos, pelo de-para da B3."),
]
TIPO_POR_CODIGO = {codigo: (nome, texto) for codigo, nome, texto in TIPOS}

CADASTROS = {ACOES: "cotacoes_acoes.json", COMMODITIES: "cotacoes_commodities.json"}

COLUNAS_PTAX = ("Data", "Moeda", "Compra CCY/BRL", "Venda CCY/BRL",
                "Compra CCY/USD", "Venda CCY/USD")
COLUNAS_OHLC = ("Data", "Fechamento ajustado", "Fechamento", "Máxima",
                "Mínima", "Abertura", "Volume")

URL_PTAX = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
            "dataFinalCotacao=@dataFinalCotacao)")
URL_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"


class ErroCotacao(ErroDeFonte):
    """Falha que a tela mostra — sempre com o motivo por extenso."""


# ------------------------------------------------------------------ período

def _data(valor, rotulo: str) -> date:
    """``AAAA-MM-DD`` ou ``dd/mm/aaaa`` → data.

    As duas porque a tela manda ISO e quem chama de fora costuma mandar o
    formato que se lê na tela.
    """
    texto = str(valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    raise ErroCotacao(f"{rotulo} inválida: {valor!r}. Use dd/mm/aaaa.")


def periodo(inicio, fim) -> Tuple[date, date]:
    """As duas datas validadas.

    Fim antes do início é erro de quem digitou, e dizer isso é melhor do que
    devolver uma tabela vazia — que parece fonte sem dado.
    """
    d1, d2 = _data(inicio, "data inicial"), _data(fim, "data final")
    if d2 < d1:
        raise ErroCotacao("a data final é anterior à inicial")
    return d1, d2


def _numero(valor, casas: int) -> str:
    """Número já formatado, ou vazio quando a fonte não trouxe.

    Vazio não é zero: o Yahoo devolve ``null`` no dia sem pregão daquele papel,
    e um ``0,00`` ali afirmaria um preço que não existiu.
    """
    if valor is None:
        return ""
    try:
        texto = f"{float(valor):,.{casas}f}"
    except (TypeError, ValueError):
        return ""
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def _chave_de_data(linha: Sequence) -> datetime:
    """Ordena pela 1ª coluna (dd/mm/aaaa).

    A tabela abre do mais recente para o mais antigo, e como texto 01/12
    viria antes de 02/01.
    """
    try:
        return datetime.strptime(linha[0], "%d/%m/%Y")
    except (ValueError, IndexError, TypeError):
        return datetime.min


def _buscar(url: str, parametros: dict, fonte: str) -> dict:
    """GET com JSON de volta, pela camada de rede do pacote.

    O 429 ganha frase própria porque ele não é defeito nem bloqueio: é a fonte
    limitando por IP, e a ação é esperar — diferente de um timeout, que manda
    olhar a saída da rede. O Yahoo faz isso com endereço de datacenter e com
    rede que sai por NAT compartilhado.
    """
    try:
        return rede.obter_json(f"{url}?{urlencode(parametros)}", timeout=30)
    except rede.ErroRede as exc:
        if getattr(exc, "status", None) == 429:
            raise ErroCotacao(
                f"{fonte} recusou por excesso de consultas (HTTP 429). O limite "
                "é por endereço de rede e passa sozinho — tente de novo em "
                "alguns minutos.") from exc
        raise ErroCotacao(f"{fonte}: {exc}") from exc


# --------------------------------------------------------------------- PTAX

def historico_ptax(moeda: str, inicio, fim) -> Tuple[List[str], List[list]]:
    """Histórico da PTAX de uma moeda: (colunas, linhas).

    Só o boletim de **fechamento** — ver o cabeçalho do módulo.
    """
    codigo = str(moeda or "").strip().upper()
    if codigo not in MOEDAS_PTAX:
        raise ErroCotacao(f"{moeda!r} não é publicada no boletim PTAX do BCB")
    d1, d2 = periodo(inicio, fim)

    dados = _buscar(URL_PTAX, {
        "@moeda": f"'{codigo}'",
        # o Olinda espera mm-dd-aaaa neste endpoint
        "@dataInicial": f"'{d1:%m-%d-%Y}'",
        "@dataFinalCotacao": f"'{d2:%m-%d-%Y}'",
        "$format": "json",
        "$select": ("paridadeCompra,paridadeVenda,cotacaoCompra,cotacaoVenda,"
                    "dataHoraCotacao,tipoBoletim"),
    }, "PTAX (BCB)")

    linhas = []
    for item in dados.get("value") or []:
        if str(item.get("tipoBoletim", "")).strip().lower() != "fechamento":
            continue
        carimbo = str(item.get("dataHoraCotacao") or "")
        try:
            dia = datetime.strptime(carimbo[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            dia = carimbo
        linhas.append([
            dia, codigo,
            _numero(item.get("cotacaoCompra"), 4), _numero(item.get("cotacaoVenda"), 4),
            _numero(item.get("paridadeCompra"), 4), _numero(item.get("paridadeVenda"), 4),
        ])
    linhas.sort(key=_chave_de_data, reverse=True)
    return list(COLUNAS_PTAX), linhas


# ------------------------------------------------------- ações e commodities

def historico_ohlc(simbolo: str, inicio, fim) -> Tuple[List[str], List[list]]:
    """Histórico diário de um símbolo do Yahoo: (colunas, linhas).

    O ``period2`` leva um dia a mais porque o endpoint trata o fim como
    **exclusivo** — sem isso o último dia do período pedido some da tabela.
    """
    codigo = str(simbolo or "").strip()
    if not codigo:
        raise ErroCotacao("nenhum símbolo de mercado informado")
    d1, d2 = periodo(inicio, fim)

    dados = _buscar(URL_YAHOO.format(codigo), {
        "period1": int(datetime(d1.year, d1.month, d1.day).timestamp()),
        "period2": int((datetime(d2.year, d2.month, d2.day)
                        + timedelta(days=1)).timestamp()),
        "interval": "1d", "events": "div,split",
    }, "Yahoo Finance")

    grafico = dados.get("chart") or {}
    if grafico.get("error"):
        erro = grafico["error"] or {}
        raise ErroCotacao(f"o Yahoo Finance recusou {codigo}: "
                          f"{erro.get('description') or erro}")
    resultado = (grafico.get("result") or [None])[0]
    if not resultado:
        raise ErroCotacao(f"não há dado para {codigo} no período")

    carimbos = resultado.get("timestamp") or []
    indicadores = resultado.get("indicators") or {}
    cotacao = (indicadores.get("quote") or [{}])[0]
    ajustado = (indicadores.get("adjclose") or [{}])[0].get("adjclose") or []

    def em(sequencia, i):
        return sequencia[i] if i < len(sequencia) else None

    linhas = []
    for i, carimbo in enumerate(carimbos):
        linhas.append([
            datetime.fromtimestamp(carimbo).strftime("%d/%m/%Y"),
            _numero(em(ajustado, i), 6),
            _numero(em(cotacao.get("close") or [], i), 6),
            _numero(em(cotacao.get("high") or [], i), 6),
            _numero(em(cotacao.get("low") or [], i), 6),
            _numero(em(cotacao.get("open") or [], i), 6),
            _numero(em(cotacao.get("volume") or [], i), 0),
        ])
    linhas.sort(key=_chave_de_data, reverse=True)
    return list(COLUNAS_OHLC), linhas


# --------------------------------------------------------- de-para de símbolo

_LETRAS_DE_MES = "FGHJKMNQUVXZ"
_CONTRATO = re.compile(r"^([" + _LETRAS_DE_MES + r"])([0-9]{1,2})$")
_MARCADOR = re.compile(r'"MY"')


def tem_padrao(texto) -> bool:
    """O texto traz o marcador ``"MY"`` — isto é, é padrão e não literal?"""
    return bool(_MARCADOR.search("" if texto is None else str(texto)))


def partir_padrao(texto) -> Tuple[str, str]:
    """``'ZL"MY".CBT'`` → ``('ZL', '.CBT')``. O ``_`` vira espaço nas duas partes."""
    s = "" if texto is None else str(texto)
    m = _MARCADOR.search(s)
    cabeca, cauda = (s[:m.start()], s[m.end():]) if m else (s, "")
    return cabeca.replace("_", " "), cauda.replace("_", " ")


def _sem_espaco(valor) -> str:
    """Caixa alta e sem espaço nenhum — a forma em que os dois lados casam.

    O milho é ``'C K6'`` na B3 e ``C_"MY"`` no cadastro, cujo prefixo é ``'C '``.
    Comparar contando o espaço obrigaria a acertar quantos vieram da fonte.
    """
    return re.sub(r"\s+", "", str(valor or "")).upper()


def _chave_de_rotulo(valor) -> str:
    return re.sub(r"\s+", " ", str(valor or "")).strip().upper()


def ano_de_dois_digitos(digitos: str, hoje: Optional[date] = None) -> str:
    """Ano do contrato em dois dígitos, que é como o símbolo de mercado escreve.

    Dois dígitos passam direto. O dígito único da B3 é ambíguo por dez anos, e a
    desambiguação é a do mercado futuro: a década corrente, virando para a
    seguinte quando o ano cairia mais de um ano atrás. A folga de um ano é de
    propósito — o vencimento recém-liquidado ainda é consultado. Em 2026, ``5``
    é 2025, nunca 2015.
    """
    if len(digitos) >= 2:
        return digitos[-2:]
    ano_hoje = (hoje or date.today()).year
    ano = ano_hoje - ano_hoje % 10 + int(digitos)
    if ano < ano_hoje - 1:
        ano += 10
    return "%02d" % (ano % 100)


def carregar_cadastro(tipo: str) -> List[dict]:
    """As linhas do de-para de um tipo. Tipo sem cadastro devolve vazio."""
    arquivo = CADASTROS.get(tipo)
    if not arquivo:
        return []
    caminho = PASTA / arquivo
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as f:
        return json.load(f)


def busca_de_simbolo(linhas: Sequence[dict]) -> Callable[[str], str]:
    """Devolve ``f(código) → símbolo`` para o cadastro dado.

    É uma **função** e não um dicionário porque o cadastro tem duas naturezas: a
    linha literal vira índice, a linha com ``"MY"`` continua sendo regra e só se
    resolve contra um código concreto. Entregá-la pronta é o que deixa a tela
    resolver a lista inteira lendo o cadastro uma vez só.
    """
    exatos: Dict[str, str] = {}
    padroes = []
    for linha in linhas or []:
        rotulo = str(linha.get("LABEL") or "")
        simbolo = str(linha.get("SYMBOL") or "").strip()
        if not simbolo:
            continue
        if tem_padrao(rotulo):
            # símbolo sem marcador é literal de propósito: a mercadoria inteira
            # respondendo por um contínuo (ZC=F) é cadastro válido, e aplicar
            # mês/ano nele produziria um ticker que não existe
            alvo = partir_padrao(simbolo) if tem_padrao(simbolo) else None
            cabeca, cauda = partir_padrao(rotulo)
            padroes.append((_sem_espaco(cabeca), _sem_espaco(cauda), simbolo, alvo))
        else:
            exatos[_chave_de_rotulo(rotulo)] = simbolo

    # prefixo mais longo primeiro: CO"MY" tem de ganhar de C_"MY" em COZ6,
    # senão quem responde pelo código seria a ordem do arquivo
    padroes.sort(key=lambda p: len(p[0]), reverse=True)

    def procurar(rotulo: str) -> str:
        achado = exatos.get(_chave_de_rotulo(rotulo))
        if achado:
            return achado
        codigo = _sem_espaco(rotulo)
        for cabeca, cauda, simbolo, alvo in padroes:
            if not (codigo.startswith(cabeca) and codigo.endswith(cauda)):
                continue
            meio = (codigo[len(cabeca):len(codigo) - len(cauda)] if cauda
                    else codigo[len(cabeca):])
            # o miolo TEM de ser mês+ano de contrato. Sem essa exigência o
            # prefixo C do milho casaria com CCZ6 (cacau) e com CLZ6 (WTI),
            # devolvendo o símbolo da mercadoria errada em silêncio
            m = _CONTRATO.match(meio)
            if m:
                if alvo is None:
                    return simbolo
                return alvo[0] + m.group(1) + ano_de_dois_digitos(m.group(2)) + alvo[1]
        return ""

    return procurar


def simbolo_de(tipo: str, rotulo: str) -> str:
    """Símbolo de mercado do instrumento escolhido, ou vazio."""
    return busca_de_simbolo(carregar_cadastro(tipo))(rotulo)


def instrumentos(tipo: str) -> List[List[str]]:
    """``[[código, símbolo]]`` de um tipo, em ordem alfabética.

    O símbolo vai junto porque a tela mostra ``AAPL34 → AAPL34.SA``: sem ele,
    quem escolhe não distingue o que está cadastrado do que ainda vai falhar
    pedindo cadastro.

    Linha de **padrão** fica de fora da lista: ela é regra, não instrumento —
    listada, viraria uma opção que a busca literal não resolve. Ela continua
    valendo para quem digitar o código do vencimento.
    """
    if tipo == PTAX:
        return [[m, m] for m in MOEDAS_PTAX]      # na PTAX o código é o símbolo
    linhas = carregar_cadastro(tipo)
    simbolo = busca_de_simbolo(linhas)
    vistos: Dict[str, str] = {}
    for linha in linhas or []:
        rotulo = " ".join(str(linha.get("LABEL") or "").split())
        if not rotulo or not str(linha.get("SYMBOL") or "").strip():
            continue
        if tem_padrao(rotulo):
            continue
        vistos.setdefault(rotulo.upper(), rotulo)
    return [[codigo, simbolo(codigo)] for _, codigo in sorted(vistos.items())]


def historico(tipo: str, instrumento: str, inicio, fim) -> dict:
    """A busca de qualquer um dos três tipos, pela mesma porta.

    Ações e commodities são o mesmo caminho — a diferença entre elas é só o
    cadastro de onde o símbolo sai. Duas funções seriam duas cópias.
    """
    if tipo == PTAX:
        colunas, linhas = historico_ptax(instrumento, inicio, fim)
        return {"colunas": colunas, "linhas": linhas, "simbolo": instrumento}

    if tipo not in CADASTROS:
        raise ErroCotacao(f"tipo de cotação desconhecido: {tipo!r}")

    rotulo = str(instrumento or "").strip()
    simbolo = simbolo_de(tipo, rotulo)
    if not simbolo:
        # pede cadastro em vez de tentar o código como símbolo: 'AAPL34' e
        # 'AA UN' não são tickers de mercado, e a resposta seria um 404 obscuro
        # da fonte em vez de "falta cadastrar"
        raise ErroCotacao(
            f"{rotulo or '(vazio)'} não tem símbolo de mercado no cadastro de "
            f"{TIPO_POR_CODIGO.get(tipo, (tipo,))[0].lower()}")
    colunas, linhas = historico_ohlc(simbolo, inicio, fim)
    return {"colunas": colunas, "linhas": linhas, "simbolo": simbolo}
