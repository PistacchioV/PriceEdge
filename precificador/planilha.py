"""Leitura de planilha — ``.xlsx`` e ``.csv`` — sem dependência nenhuma.

Um ``.xlsx`` é um zip de XML, e ler os quatro pedaços que importam cabe em
pouco mais de cem linhas. A alternativa era o ``openpyxl``, que é excelente e
que **não** entrou aqui de propósito: no ambiente corporativo cada pacote novo
depende de política de instalação, e a subida deste app já tropeçou no pip
mais de uma vez. Uma dependência a menos é um motivo a menos para a tela não
abrir na estação.

O que a leitura resolve, e que é onde um leitor ingênuo erra:

**A célula guarda posição, não ordem.** O XML pula célula vazia — uma linha com
``A1`` e ``D1`` vem com dois elementos, não quatro. Quem lê em sequência
desalinha a planilha inteira a partir da primeira lacuna, e o erro não aparece:
a coluna P vira a N e os números continuam parecendo números. Aqui a referência
(``L12``) é convertida em índice, e a linha sai com o comprimento certo.

**Texto mora em outro arquivo.** A maioria das células de texto guarda um
índice para ``sharedStrings.xml``; sem resolvê-lo, a coluna de ticker viria
como ``0``, ``1``, ``2``.

**Data é número.** O Excel guarda data como dias desde 30/12/1899, e saber que
um número é data exige ler o formato em ``styles.xml``. Como quem chama sabe
qual coluna é a data, a conversão fica com ele — ``como_data`` faz as duas
leituras, o serial e o texto.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date, datetime, timedelta
from typing import List, Optional, Sequence
from xml.etree import ElementTree

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# o Excel conta os dias a partir de 30/12/1899 por causa do bug do ano 1900,
# que ele mantém de propósito para continuar compatível com o Lotus 1-2-3
_ORIGEM_EXCEL = date(1899, 12, 30)


class ErroPlanilha(ValueError):
    """Arquivo que não dá para ler, com o motivo por extenso."""


def _indice_da_coluna(referencia: str) -> int:
    """``'L12'`` → 11. Zero-based, que é como a lista é indexada."""
    letras = re.match(r"([A-Z]+)", referencia or "")
    if not letras:
        return 0
    indice = 0
    for letra in letras.group(1):
        indice = indice * 26 + (ord(letra) - ord("A") + 1)
    return indice - 1


def letra_da_coluna(indice: int) -> str:
    """0 → ``'A'``, 11 → ``'L'``. Para a mensagem de erro falar a língua da tela."""
    nome = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        nome = chr(ord("A") + resto) + nome
    return nome


def _textos_compartilhados(arquivo: zipfile.ZipFile) -> List[str]:
    try:
        bruto = arquivo.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    raiz = ElementTree.fromstring(bruto)
    textos = []
    for item in raiz.findall(f"{NS}si"):
        # o texto de uma célula pode vir partido em vários <t> quando tem
        # formatação no meio; juntar é o que devolve a string original
        textos.append("".join(t.text or "" for t in item.iter(f"{NS}t")))
    return textos


def _primeira_planilha(arquivo: zipfile.ZipFile) -> str:
    nomes = [n for n in arquivo.namelist()
             if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
    if not nomes:
        raise ErroPlanilha("o arquivo .xlsx não tem nenhuma planilha dentro")
    return sorted(nomes)[0]


def ler_xlsx(dados: bytes) -> List[List[str]]:
    """As células da primeira planilha, como texto, com as lacunas preservadas."""
    try:
        arquivo = zipfile.ZipFile(io.BytesIO(dados))
    except zipfile.BadZipFile:
        raise ErroPlanilha(
            "este arquivo não é um .xlsx. Se ele for .xls antigo, abra e salve "
            "como .xlsx ou como CSV.") from None

    with arquivo:
        compartilhados = _textos_compartilhados(arquivo)
        raiz = ElementTree.fromstring(arquivo.read(_primeira_planilha(arquivo)))

        linhas: List[List[str]] = []
        for linha in raiz.iter(f"{NS}row"):
            celulas: List[str] = []
            for celula in linha.findall(f"{NS}c"):
                posicao = _indice_da_coluna(celula.get("r") or "")
                # a lacuna é preenchida: sem isso a coluna P vira a N na
                # primeira célula vazia, e o número continua parecendo número
                while len(celulas) < posicao:
                    celulas.append("")

                tipo = celula.get("t")
                if tipo == "inlineStr":
                    valor = "".join(t.text or "" for t in celula.iter(f"{NS}t"))
                else:
                    no = celula.find(f"{NS}v")
                    valor = (no.text or "") if no is not None else ""
                    if tipo == "s":
                        try:
                            valor = compartilhados[int(valor)]
                        except (ValueError, IndexError):
                            valor = ""
                celulas.append(valor)
            linhas.append(celulas)
    return linhas


def ler_csv(dados: bytes) -> List[List[str]]:
    """As linhas de um CSV, com o separador e a codificação descobertos.

    A B3 exporta com ``;`` e cp1252; um arquivo salvo de outro lugar costuma
    vir com ``,`` e UTF-8. Adivinhar os dois é mais barato que pedir ao usuário
    que saiba qual é o dele.
    """
    texto = None
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = dados.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise ErroPlanilha("não foi possível ler o texto do arquivo")

    amostra = texto[:4096]
    separador = ";" if amostra.count(";") >= amostra.count(",") else ","
    return [linha for linha in csv.reader(io.StringIO(texto), delimiter=separador)]


def ler(nome: str, dados: bytes) -> List[List[str]]:
    """Lê pela extensão do nome: ``.xlsx`` ou ``.csv``."""
    if (nome or "").lower().endswith(".xlsx"):
        return ler_xlsx(dados)
    if (nome or "").lower().endswith((".csv", ".txt")):
        return ler_csv(dados)
    raise ErroPlanilha(
        f"não sei ler {nome!r}. Use .xlsx ou .csv — o .xls antigo precisa ser "
        "salvo de novo num dos dois.")


def celula(linha: Sequence[str], indice: int) -> str:
    """A célula da posição, ou vazio quando a linha é mais curta."""
    return (linha[indice] or "").strip() if indice < len(linha) else ""


def como_data(valor: str) -> Optional[date]:
    """Data de uma célula, venha ela como serial do Excel ou como texto.

    O serial é resolvido sem consultar o formato: quem chama sabe qual coluna é
    a data, e ler ``styles.xml`` só para confirmar seria trabalho para chegar à
    mesma resposta.

    A faixa aceita começa em 1954 e não em 1900, e o motivo é uma armadilha:
    uma taxa como ``3,74231`` é um serial válido no calendário do Excel e viraria
    02/01/1900 sem reclamar de nada. Nenhum dado de mercado tem data anterior a
    1954, e nenhuma taxa ou preço chega a 20.000 — o piso separa os dois sem
    precisar saber qual coluna veio.
    """
    texto = (valor or "").strip()
    if not texto:
        return None
    try:
        numero = float(texto.replace(",", "."))
    except ValueError:
        numero = None
    if numero is not None and 20000 <= numero <= 73050:  # 1954 a 2100
        return _ORIGEM_EXCEL + timedelta(days=int(numero))
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y",
                    "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    return None


def como_numero(valor: str) -> Optional[float]:
    """Número de uma célula, aceitando vírgula decimal e separador de milhar.

    ``'3,74231'`` e ``'3.74231'`` são o mesmo número: o primeiro é o que a
    planilha em português mostra, o segundo é o que o XML guarda.
    """
    texto = (valor or "").strip()
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None
