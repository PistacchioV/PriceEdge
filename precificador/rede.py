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
    PRECIFICADOR_SEM_PROXY=1        ignora o proxy do ambiente para hosts internos

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


class ErroRede(RuntimeError):
    """Falha de rede ou de autenticação numa chamada externa."""


def sso_ligado() -> bool:
    return os.getenv("PRECIFICADOR_SSO", "").strip().lower() in ("1", "true", "sim")


def sso_disponivel() -> bool:
    """True quando há como fazer o handshake Negotiate nesta máquina."""
    return requests is not None and (HttpNegotiateAuth is not None
                                     or HTTPKerberosAuth is not None)


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
            resposta.raise_for_status()
            return resposta.content
        except Exception as exc:         # requests tem sua própria árvore de erros
            raise ErroRede(f"falha na chamada autenticada a {url}: {exc}") from exc

    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=cabecalho), timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ErroRede(f"HTTP {exc.code} em {url}") from exc
    except OSError as exc:
        raise ErroRede(f"falha de conexão com {url}: {exc}") from exc


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
