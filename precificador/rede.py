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

import json
import os
import urllib.error
import urllib.request
from .erros import ErroDeFonte
from typing import Optional

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
    """Falha de rede ou de autenticação numa chamada externa."""


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


def sessao():
    """Sessão ``requests`` com SSO, ou ``None`` quando o caminho é o urllib."""
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
    proxy = proxy_configurado()
    if proxy:
        # NO_PROXY tem que continuar valendo: com trust_env desligado o requests
        # ignora a variável, e um host interno que deveria ir direto passaria a
        # sair pelo proxy — que costuma recusá-lo.
        s.proxies = {"http": proxy, "https": proxy,
                     "no_proxy": os.getenv("NO_PROXY") or os.getenv("no_proxy") or ""}

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
    """GET que devolve bytes, pelo caminho de SSO ou pelo urllib."""
    cabecalho = dict(cabecalho or {})
    cabecalho.setdefault("User-Agent", UA_NAVEGADOR if sso_ligado() else UA_PADRAO)
    cabecalho.setdefault("Accept", "*/*")

    s = sessao()
    if s is not None:
        try:
            resposta = s.get(url, headers=cabecalho, timeout=timeout)
            codigo = resposta.status_code
            resposta.raise_for_status()
            return resposta.content
        except Exception as exc:         # requests tem sua própria árvore de erros
            codigo = locals().get("codigo")
            raise ErroRede(f"falha na chamada autenticada a {url}: {exc}",
                           status=codigo if codigo and codigo >= 400 else None) from exc

    abridor = urllib.request.urlopen
    proxy = proxy_configurado()
    if proxy:
        abridor = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})).open

    try:
        with abridor(urllib.request.Request(url, headers=cabecalho),
                     timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ErroRede(f"HTTP {exc.code} em {url}", status=exc.code) from exc
    except OSError as exc:
        raise ErroRede(f"falha de conexão com {url}: {exc}{_pista_de_proxy(exc)}") from exc


def _pista_de_proxy(exc: Exception) -> str:
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
