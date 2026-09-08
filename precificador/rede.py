"""Saída HTTP — um ponto só, com SSO Kerberos quando o ambiente pede.

Todos os módulos que buscam dado de fora (``b3``, ``bcb``, ``sofr``, ``euribor``,
``cambio``) passam por aqui. Isso existe por um motivo prático: numa rede
corporativa a chamada não sai igual à de casa — há proxy, há CA interna, e há
autenticação integrada.

**Kerberos / SPNEGO.** No Windows corporativo a identidade já autenticada da
estação serve para o handshake Negotiate, sem pedir senha. O pacote que faz
isso é ``requests-negotiate-sspi`` (só Windows); fora dele, ``requests-kerberos``
com um ticket válido (``kinit``). Quando nenhum dos dois existe — que é o caso
numa máquina comum — tudo cai para ``urllib``, sem autenticação, e as fontes
públicas usadas aqui continuam funcionando.

**O que precisa estar ligado no ambiente JP.** Nada em código: as três variáveis
abaixo bastam.

    PRECIFICADOR_SSO=1              liga o Negotiate na sessão
    PRECIFICADOR_CA_BUNDLE=...pem   CA interna (o certifi não traz a raiz da casa)
    PRECIFICADOR_PROXY=http://...   proxy de saída, quando não há como descobrir
    PRECIFICADOR_SEM_PROXY=1        ignora o proxy do ambiente para hosts internos

**Saída bloqueada.** Numa rede corporativa a conexão direta com a internet
costuma não existir: o pedido morre em ``WinError 10060`` — "a tentativa de
conexão falhou porque o host não respondeu" —, que é timeout de TCP, não erro
de HTTP. Não adianta tentar de novo. O caminho é o proxy, e ele quase nunca
está numa variável de ambiente: vem de um arquivo PAC apontado pelo registro do
Windows, que nem o ``urllib`` nem o ``requests`` sabem interpretar.

Por isso ``PRECIFICADOR_PROXY`` existe, e por isso ``diagnostico()`` reporta o
que o Windows tem configurado — inclusive a URL do PAC, para quem precisa abrir
o arquivo e ler de lá o endereço do proxy.

Duas lições que vieram do OTC Tracker e que economizam horas de depuração:

* o ADFS só oferece o desafio Negotiate para User-Agents da lista dele. Com o
  UA padrão do ``requests`` ele devolve **a página HTML de login**, e o erro que
  chega é um "JSON inválido" que não menciona autenticação nenhuma. Por isso o
  UA de navegador Windows é forçado quando o SSO está ligado;
* host interno costuma recusar o proxy do ambiente enquanto o navegador vai
  direto. ``trust_env=False`` resolve, e é o que ``PRECIFICADOR_SEM_PROXY`` faz.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .erros import ErroDeFonte

try:                                    # Windows corporativo
    from requests_negotiate_sspi import HttpNegotiateAuth   # type: ignore
except ImportError:
    HttpNegotiateAuth = None

try:                                    # Linux/macOS com ticket Kerberos
    from requests_kerberos import HTTPKerberosAuth, OPTIONAL  # type: ignore
except ImportError:
    HTTPKerberosAuth = None
    OPTIONAL = None

try:
    import requests                     # type: ignore
except ImportError:
    requests = None

# UA de navegador Windows: o ADFS só negocia Kerberos com quem está na lista dele
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; rv:11.0) "
                "like Gecko")
UA_PADRAO = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

TIMEOUT = 40


class ErroRede(ErroDeFonte):
    """Falha de rede. ``status`` traz o código HTTP quando houve resposta.

    Sem ele, quem chama só tem a frase — e distinguir "a fonte recusou" de
    "a saída está bloqueada" viraria busca de substring numa mensagem que
    muda. Um 429 do Yahoo pede esperar; um 10060 pede olhar o proxy.
    """

    def __init__(self, mensagem: str, status: Optional[int] = None) -> None:
        super().__init__(mensagem)
        self.status = status


class _ErroDeRota(ErroRede):
    """Falha de REDE numa saída — vale tentar a próxima.

    Separada de propósito: um HTTP 404 da fonte não melhora trocando de proxy,
    e insistir gastaria as três tentativas para chegar à mesma resposta.
    """


def proxy_configurado() -> Optional[str]:
    """O proxy a usar: o da variável, ou o que o sistema já expõe."""
    escolhido = (os.getenv("PRECIFICADOR_PROXY") or "").strip()
    if escolhido:
        return escolhido
    for chave in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        valor = (os.getenv(chave) or "").strip()
        if valor:
            return valor
    return None


_rota_boa = {"nome": None}


def rotas_de_saida() -> list:
    """As saídas a tentar, em ordem, sem repetir endereço.

    Uma máquina que sai direto e outra que só sai por proxy usam o mesmo
    código: a diferença é qual delas responde primeiro. A ordem é

        1. o proxy configurado (``PRECIFICADOR_PROXY`` ou as variáveis padrão);
        2. o proxy do sistema (no Windows, as Opções de Internet);
        3. conexão direta.

    A primeira que responder fica memorizada no processo e passa a ser tentada
    antes das outras — sem isso, toda chamada pagaria de novo o timeout das
    rotas mortas que vêm antes dela.

    A rota 1 é exatamente o que a camada fazia antes de existir cadeia, então
    o comportamento de quem já funciona não muda: o que era falha final virou
    primeira tentativa.
    """
    rotas, vistos = [], set()

    def juntar(nome, proxies):
        chave = (proxies.get("http", ""), proxies.get("https", ""))
        if chave in vistos:
            return
        vistos.add(chave)
        rotas.append((nome, proxies))

    proxy = proxy_configurado()
    if proxy:
        juntar(f"proxy {proxy}", {"http": proxy, "https": proxy})
    try:
        sistema = urllib.request.getproxies()
    except Exception:                                    # noqa: BLE001
        sistema = {}
    alvo = sistema.get("https") or sistema.get("http")
    if alvo:
        juntar(f"proxy do sistema {alvo}",
               {"http": sistema.get("http") or alvo,
                "https": sistema.get("https") or alvo})
    juntar("conexão direta", {})

    escolhida = _rota_boa.get("nome")
    if escolhida:
        rotas.sort(key=lambda r: 0 if r[0] == escolhida else 1)
    return rotas


def proxy_do_windows() -> dict:
    """O que o Windows tem no registro: proxy fixo e/ou URL do arquivo PAC.

    Só leitura, e só para relatar. O PAC não é interpretado aqui — é um script
    JavaScript que escolhe o proxy por destino, e resolvê-lo exigiria um
    interpretador. Mas saber que ele existe já responde a pergunta que trava
    todo mundo: "o proxy não está em variável nenhuma, então onde está?".
    """
    try:
        import winreg                                    # só existe no Windows
    except ImportError:
        return {}
    caminho = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    achado = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, caminho) as chave:
            for nome in ("ProxyEnable", "ProxyServer", "AutoConfigURL"):
                try:
                    achado[nome] = winreg.QueryValueEx(chave, nome)[0]
                except OSError:
                    pass
    except OSError:
        return {}
    return achado


def sso_ligado() -> bool:
    return os.getenv("PRECIFICADOR_SSO", "").strip().lower() in ("1", "true", "sim")


def sso_disponivel() -> bool:
    """True quando há como fazer o handshake Negotiate nesta máquina."""
    return requests is not None and (HttpNegotiateAuth is not None
                                     or HTTPKerberosAuth is not None)


FONTES_PARA_TESTE = [
    ("B3", "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp"),
    ("Banco Central — SGS", "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados?formato=json&dataInicial=01/09/2026&dataFinal=02/09/2026"),
    ("Banco Central — PTAX", "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/Moedas?$format=json&$top=1"),
    ("Fed de Nova York", "https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json"),
    ("Banco da Finlândia", "https://www.suomenpankki.fi/en/"),
]


def testar_fontes(timeout: int = 8) -> list:
    """Bate em cada fonte e diz o que aconteceu, uma por uma.

    Existe porque "deu erro na api" não diz qual API, nem se o problema é a
    fonte, a saída da rede ou a autenticação. Com o resultado lado a lado a
    resposta aparece sozinha: todas falhando com timeout é bloqueio de saída;
    uma só falhando é a fonte.
    """
    saida = []
    for nome, url in FONTES_PARA_TESTE:
        try:
            obter(url, timeout=timeout)
            saida.append({"fonte": nome, "ok": True, "detalhe": "respondeu"})
        except ErroDeFonte as exc:
            saida.append({"fonte": nome, "ok": False, "detalhe": str(exc)[:280]})
        except Exception as exc:                  # nenhuma fonte derruba o teste
            saida.append({"fonte": nome, "ok": False,
                          "detalhe": f"{type(exc).__name__}: {exc}"[:280]})
    return saida


def diagnostico() -> dict:
    """O que está e o que não está disponível — para a tela de metodologia."""
    return {
        "sso_pedido": sso_ligado(),
        "sso_disponivel": sso_disponivel(),
        "requests": requests is not None,
        "negotiate_sspi": HttpNegotiateAuth is not None,
        "kerberos": HTTPKerberosAuth is not None,
        "ca_bundle": os.getenv("PRECIFICADOR_CA_BUNDLE") or None,
        "sem_proxy": os.getenv("PRECIFICADOR_SEM_PROXY", "").lower() in ("1", "true"),
        "proxy": proxy_configurado(),
        "proxy_do_windows": proxy_do_windows(),
        "no_proxy": os.getenv("NO_PROXY") or os.getenv("no_proxy") or None,
        "variaveis_de_proxy": {
            nome: os.getenv(nome) for nome in
            ("PRECIFICADOR_PROXY", "HTTPS_PROXY", "HTTP_PROXY",
             "https_proxy", "http_proxy") if os.getenv(nome)
        },
    }


def sessao(proxies: Optional[dict] = None):
    """Sessão ``requests`` com SSO, ou ``None`` quando o caminho é o urllib.

    ``proxies`` vem da cadeia de saídas. Passar ``None`` mantém o que a camada
    fazia antes: o proxy configurado, ou nenhum.
    """
    if not sso_ligado():
        return None
    if requests is None:
        raise ErroRede(
            "PRECIFICADOR_SSO está ligado mas o pacote 'requests' não está "
            "instalado. Instale-o (e o requests-negotiate-sspi no Windows) ou "
            "desligue a variável.")

    s = requests.Session()
    if os.getenv("PRECIFICADOR_SEM_PROXY", "").lower() in ("1", "true"):
        s.trust_env = False              # host interno costuma recusar o proxy
    ca = os.getenv("PRECIFICADOR_CA_BUNDLE")
    if ca:
        s.verify = ca                    # o certifi não traz a raiz interna
    if proxies is None:
        proxy = proxy_configurado()
        proxies = {"http": proxy, "https": proxy} if proxy else {}
    if proxies:
        # NO_PROXY tem que continuar valendo: com trust_env desligado o requests
        # ignora a variável, e um host interno que deveria ir direto passaria a
        # sair pelo proxy — que costuma recusá-lo.
        s.proxies = dict(proxies,
                         no_proxy=os.getenv("NO_PROXY") or os.getenv("no_proxy") or "")
    else:
        s.proxies = {}

    if HttpNegotiateAuth is not None:
        s.auth = HttpNegotiateAuth()
    elif HTTPKerberosAuth is not None:
        s.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
    else:
        raise ErroRede(
            "PRECIFICADOR_SSO está ligado e nenhum handler Negotiate foi "
            "encontrado. Sem ele a chamada sai sem autenticação e o ADFS "
            "responde 401. Instale requests-negotiate-sspi (Windows) ou "
            "requests-kerberos (Linux/macOS, com ticket via kinit).")
    return s


def obter(url: str, cabecalho: Optional[dict] = None, timeout: int = TIMEOUT) -> bytes:
    """GET que devolve bytes, tentando as saídas em ordem.

    Erro de **rede** tenta a próxima saída; erro **da fonte** para na hora,
    porque aí a rota funcionou e o problema é o outro lado. O 407 e os 502/504
    são a exceção: eles vêm do proxy, não da fonte, e por isso contam como rota
    ruim — parar neles esconderia a saída que funciona.
    """
    cabecalho = dict(cabecalho or {})
    cabecalho.setdefault("User-Agent", UA_NAVEGADOR if sso_ligado() else UA_PADRAO)
    cabecalho.setdefault("Accept", "*/*")

    tentativas = []
    for nome, proxies in rotas_de_saida():
        try:
            conteudo = _obter_por(url, cabecalho, timeout, proxies)
        except _ErroDeRota as exc:
            tentativas.append(f"{nome}: {exc}")
            continue
        if _rota_boa.get("nome") != nome:
            _rota_boa["nome"] = nome
        return conteudo

    # a rota memorizada caiu junto com as outras: esquece, para a próxima
    # chamada recomeçar pela ordem natural em vez de insistir na que morreu
    _rota_boa["nome"] = None
    detalhe = "; ".join(tentativas) or "nenhuma saída disponível"
    raise ErroRede(f"falha de conexão com {url}: {detalhe}{_pista_de_proxy(detalhe)}")


def _obter_por(url: str, cabecalho: dict, timeout: int, proxies: dict) -> bytes:
    """Uma tentativa por uma saída."""
    s = sessao(proxies)
    if s is not None:
        try:
            resposta = s.get(url, headers=cabecalho, timeout=timeout)
        except Exception as exc:         # requests tem sua própria árvore de erros
            raise _ErroDeRota(str(exc)) from exc
        codigo = resposta.status_code
        if codigo in (407, 502, 504):
            raise _ErroDeRota(f"o proxy respondeu HTTP {codigo}")
        if codigo >= 400:
            raise ErroRede(f"HTTP {codigo} em {url}", status=codigo)
        return resposta.content

    abridor = urllib.request.urlopen
    if proxies:
        abridor = urllib.request.build_opener(
            urllib.request.ProxyHandler(dict(proxies))).open

    try:
        with abridor(urllib.request.Request(url, headers=cabecalho),
                     timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (407, 502, 504):
            raise _ErroDeRota(f"o proxy respondeu HTTP {exc.code}") from exc
        raise ErroRede(f"HTTP {exc.code} em {url}", status=exc.code) from exc
    except OSError as exc:
        raise _ErroDeRota(str(exc)) from exc


def _pista_de_proxy(exc) -> str:
    """Explica o timeout de saída quando ele tem cara de bloqueio de rede.

    ``WinError 10060`` e ``timed out`` não são erro do servidor remoto: são a
    conexão nem chegando lá. Repetir não resolve, e a mensagem crua manda o
    usuário investigar o site errado.
    """
    texto = str(exc)
    bloqueio = ("10060" in texto or "timed out" in texto.lower()
                or "Network is unreachable" in texto)
    if not bloqueio or proxy_configurado():
        return ""

    dica = (". A conexão nem chegou ao servidor — numa rede corporativa isso é "
            "o bloqueio de saída direta. Informe o proxy em PRECIFICADOR_PROXY "
            "e suba de novo")
    janela = proxy_do_windows()
    if janela.get("ProxyServer"):
        dica += f". O Windows tem configurado: {janela['ProxyServer']}"
    elif janela.get("AutoConfigURL"):
        dica += (f". O Windows usa um arquivo PAC ({janela['AutoConfigURL']}), "
                 "que não diz o endereço direto: abra-o e leia de lá o proxy")
    return dica


class SessaoNavegada:
    """GET e POST com cookies, pela mesma porta autenticada do pacote.

    Existe porque uma fonte precisa de **sessão**: o visualizador do Banco da
    Finlândia é um formulário ASP.NET que só entrega o CSV depois de duas idas
    com cookie e viewstate. Enquanto ela montava o próprio ``build_opener``, ela
    era a única fonte fora do Kerberos e fora do proxy — no ambiente
    corporativo, a única que ia falhar sem que a mensagem dissesse por quê.

    A rota é escolhida na **primeira** chamada e fica: trocar de saída no meio
    de uma sessão jogaria fora o cookie e o viewstate, e o formulário voltaria
    ao começo sem dizer nada.
    """

    def __init__(self, timeout: int = TIMEOUT, cabecalho: Optional[dict] = None):
        self.timeout = timeout
        self.cabecalho = dict(cabecalho or {})
        self.cabecalho.setdefault(
            "User-Agent", UA_NAVEGADOR if sso_ligado() else UA_PADRAO)
        self._porta = None          # a rota escolhida, depois da 1ª chamada
        self._nome = None

    def _abrir(self, proxies: dict):
        """A porta de uma rota: sessão do requests com SSO, ou opener do urllib."""
        s = sessao(proxies)
        if s is not None:
            return s                # o requests já guarda cookie sozinho
        manipuladores = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
        if proxies:
            manipuladores.append(urllib.request.ProxyHandler(dict(proxies)))
        return urllib.request.build_opener(*manipuladores)

    def _uma(self, porta, url, dados, cabecalho):
        if hasattr(porta, "get"):                       # requests.Session
            try:
                if dados is None:
                    r = porta.get(url, headers=cabecalho, timeout=self.timeout)
                else:
                    r = porta.post(url, data=dados, headers=cabecalho,
                                   timeout=self.timeout)
            except Exception as exc:                    # noqa: BLE001
                raise _ErroDeRota(str(exc)) from exc
            if r.status_code in (407, 502, 504):
                raise _ErroDeRota(f"o proxy respondeu HTTP {r.status_code}")
            if r.status_code >= 400:
                raise ErroRede(f"HTTP {r.status_code} em {url}", status=r.status_code)
            return r.content

        corpo = urllib.parse.urlencode(dados).encode() if dados is not None else None
        pedido = urllib.request.Request(url, data=corpo, headers=cabecalho)
        try:
            with porta.open(pedido, timeout=self.timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (407, 502, 504):
                raise _ErroDeRota(f"o proxy respondeu HTTP {exc.code}") from exc
            raise ErroRede(f"HTTP {exc.code} em {url}", status=exc.code) from exc
        except OSError as exc:
            raise _ErroDeRota(str(exc)) from exc

    def _pedir(self, url: str, dados: Optional[dict], extra: Optional[dict]) -> bytes:
        cabecalho = dict(self.cabecalho)
        cabecalho.update(extra or {})
        if dados is not None:
            cabecalho.setdefault("Content-Type", "application/x-www-form-urlencoded")

        if self._porta is not None:
            return self._uma(self._porta, url, dados, cabecalho)

        tentativas = []
        for nome, proxies in rotas_de_saida():
            porta = self._abrir(proxies)
            try:
                conteudo = self._uma(porta, url, dados, cabecalho)
            except _ErroDeRota as exc:
                tentativas.append(f"{nome}: {exc}")
                continue
            self._porta, self._nome = porta, nome
            _rota_boa["nome"] = nome
            return conteudo
        detalhe = "; ".join(tentativas) or "nenhuma saída disponível"
        raise ErroRede(f"falha de conexão com {url}: {detalhe}{_pista_de_proxy(detalhe)}")

    def get(self, url: str, referer: Optional[str] = None) -> bytes:
        return self._pedir(url, None, {"Referer": referer} if referer else None)

    def post(self, url: str, dados: dict, referer: Optional[str] = None) -> bytes:
        return self._pedir(url, dados, {"Referer": referer} if referer else None)


def obter_json(url: str, cabecalho: Optional[dict] = None, timeout: int = TIMEOUT):
    bruto = obter(url, {**(cabecalho or {}), "Accept": "application/json"}, timeout)
    try:
        return json.loads(bruto.decode("utf-8"))
    except ValueError as exc:
        # sintoma clássico de SSO: o ADFS devolveu a página de login em vez do JSON
        pista = ""
        if b"<html" in bruto[:400].lower():
            pista = (" — a resposta veio em HTML, não JSON. Num ambiente com SSO "
                     "isso costuma ser a página de login do ADFS: confira "
                     "PRECIFICADOR_SSO e o pacote Negotiate.")
        raise ErroRede(f"resposta ilegível de {url}: {exc}{pista}") from exc
