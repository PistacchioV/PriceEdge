"""O lado de transporte do MCP: JSON-RPC 2.0 em stdio, uma mensagem por linha.

O SDK oficial do MCP pede Python 3.10+, e o ambiente do banco roda 3.9 — por
isso o protocolo é escrito aqui, com a biblioteca padrão. Só a parte que um
servidor de ferramentas usa: ``initialize``, ``ping``, ``tools/list`` e
``tools/call``. Prompts e recursos ficam de fora; as skills fazem esse papel.

O stdout é do protocolo e de mais ninguém: um ``print`` perdido no meio de uma
precificação corromperia a conversa com o cliente. Enquanto uma ferramenta
roda, o stdout aponta para o stderr.
"""

from __future__ import annotations

import contextlib
import json
import sys
from typing import Callable, Dict, Optional, TextIO

VERSOES = ("2025-06-18", "2025-03-26", "2024-11-05")

PARSE_ERROR, METODO_INEXISTENTE, PARAMETRO_INVALIDO = -32700, -32601, -32602


class Servidor:
    def __init__(self, nome: str, versao: str, ferramentas: Dict[str, dict],
                 executar: Callable[[str, dict], dict], instrucoes: str = ""):
        self.nome, self.versao, self.instrucoes = nome, versao, instrucoes
        self.ferramentas = ferramentas
        self.executar = executar

    # ----------------------------------------------------------- mensagens

    def responder(self, mensagem: dict) -> Optional[dict]:
        """A resposta de uma mensagem, ou None quando ela é uma notificação."""
        metodo, ident = mensagem.get("method"), mensagem.get("id")
        if ident is None:
            return None                      # notificações não têm resposta
        try:
            resultado = self._despachar(metodo, mensagem.get("params") or {})
        except _ErroRPC as exc:
            return {"jsonrpc": "2.0", "id": ident,
                    "error": {"code": exc.codigo, "message": exc.mensagem}}
        return {"jsonrpc": "2.0", "id": ident, "result": resultado}

    def _despachar(self, metodo: str, params: dict) -> dict:
        if metodo == "initialize":
            pedida = params.get("protocolVersion")
            resposta = {
                "protocolVersion": pedida if pedida in VERSOES else VERSOES[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.nome, "version": self.versao},
            }
            if self.instrucoes:
                resposta["instructions"] = self.instrucoes
            return resposta
        if metodo == "ping":
            return {}
        if metodo == "tools/list":
            return {"tools": [{"name": nome, **spec}
                              for nome, spec in self.ferramentas.items()]}
        if metodo == "tools/call":
            nome = params.get("name")
            if nome not in self.ferramentas:
                raise _ErroRPC(PARAMETRO_INVALIDO, f"ferramenta desconhecida: {nome}")
            return self._chamar(nome, params.get("arguments") or {})
        raise _ErroRPC(METODO_INEXISTENTE, f"método não suportado: {metodo}")

    def _chamar(self, nome: str, argumentos: dict) -> dict:
        # erro de negócio (curva não publicada, strike sem solução) volta como
        # resultado com isError — é o modelo que precisa lê-lo, não o cliente
        try:
            with contextlib.redirect_stdout(sys.stderr):
                conteudo = self.executar(nome, argumentos)
            erro = False
        except Exception as exc:                    # noqa: BLE001 — vira texto
            conteudo, erro = {"erro": _frase(exc)}, True
        texto = json.dumps(conteudo, ensure_ascii=False, indent=1)
        return {"content": [{"type": "text", "text": texto}], "isError": erro}

    # ------------------------------------------------------------- laço

    def rodar(self, entrada: TextIO = sys.stdin, saida: TextIO = sys.stdout) -> None:
        for linha in entrada:
            linha = linha.strip()
            if not linha:
                continue
            try:
                mensagem = json.loads(linha)
            except json.JSONDecodeError:
                resposta = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": PARSE_ERROR, "message": "JSON inválido"}}
            else:
                lote = mensagem if isinstance(mensagem, list) else [mensagem]
                respostas = [r for r in map(self.responder, lote) if r is not None]
                if not respostas:
                    continue
                resposta = respostas if isinstance(mensagem, list) else respostas[0]
            saida.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            saida.flush()


class _ErroRPC(Exception):
    def __init__(self, codigo: int, mensagem: str):
        super().__init__(mensagem)
        self.codigo, self.mensagem = codigo, mensagem


def _frase(exc: Exception) -> str:
    """A mensagem do erro, com os valores já no molde (ver ``ErroTraduzido``)."""
    from webapp import idiomas
    try:
        return idiomas.mensagem(exc, "pt")
    except Exception:                               # noqa: BLE001
        return str(exc) or type(exc).__name__
