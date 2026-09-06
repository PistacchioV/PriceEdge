"""Fontes de dados de mercado usadas (ou úteis) na precificação.

Só o que a ferramenta consome automaticamente está marcado como
``automatizado``; o resto é referência para conferência manual e para os
insumos que ainda entram digitados (Term SOFR, projeção de IPCA, VNA).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Fonte:
    grupo: str
    descricao: str
    url: str
    automatizado: bool = False
    nota: str = ""


FONTES: List[Fonte] = [
    # ------------------------------------------------------------ calendário
    Fonte("Calendário", "Lista com todos os feriados da ANBIMA",
          "https://www.anbima.com.br/feriados/feriados.asp", True,
          "Já embutida no pacote em dados/feriados_anbima.json (2001-2099)."),

    # ------------------------------------------------------- curvas em reais
    Fonte("Curvas B3", "Taxas Referenciais — modelo novo (fonte da extração automática)",
          "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/"
          "consultas/mercado-de-derivativos/precos-referenciais/taxas-referenciais-bm-fbovespa/",
          True,
          "A página é ruim de raspar, mas o endpoint GetDownloadFile por trás dela "
          "devolve o CSV do dia. É o que a aba Curvas usa."),
    Fonte("Curvas B3", "Taxas Referenciais — modelo antigo (melhor para extrair, porém instável)",
          "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/txref1.asp", False,
          "URL citada na aba Curvas da planilha de Pré USD × Pré BRL. Aceita "
          "?Data=dd/mm/aaaa&slcTaxa=PRE|DOC|DIC. Cai com frequência."),
    Fonte("Curvas B3", "ANBIMA — estrutura a termo de CDI, juro real e inflação implícita",
          "https://www.anbima.com.br/informacoes/est-termo/CZ.asp", False,
          "Curvas já prontas, boas para conferir a inflação implícita calculada "
          "a partir de PRE e DIC."),

    # -------------------------------------------------------------- inflação
    Fonte("Inflação", "Projeção de inflação da ANBIMA (IPCA-15 / IGP-M)",
          "https://www.anbima.com.br/pt_br/informar/estatisticas/precos-e-indices/"
          "projecao-de-inflacao-gp-m.htm", False,
          "É a projeção mensal que entra no NI pro-rata."),
    Fonte("Inflação", "Número-índice do IPCA (IBGE, tabela 1737)",
          "https://sidra.ibge.gov.br/tabela/1737", False,
          "NIk-1: o último número-índice publicado."),
    Fonte("Inflação", "VNA de títulos públicos (ANBIMA Data)",
          "https://data.anbima.com.br/titulos-publicos/valor-nominal-atualizado", False,
          "Para conferir o VNA calculado na tela de NI pro-rata."),

    # ------------------------------------------------------------ dólar/SOFR
    Fonte("Dólar e SOFR", "Term SOFR e SOFR (CME Group)",
          "https://www.cmegroup.com/market-data/cme-group-benchmark-administration/term-sofr.html",
          False, "Fonte da aba Dados CME."),
    Fonte("Dólar e SOFR", "Curva Term SOFR atualizada diariamente (Pensford)",
          "https://www.pensford.com/forward-curve", False,
          "Curva forward pronta e gratuita."),
    Fonte("Dólar e SOFR", "Futuro de SOFR 3 meses em tabela, com delay (Barchart)",
          "https://www.barchart.com/futures/quotes/SQ*0/futures-prices", False,
          "Os preços SR3 que alimentam o bootstrap da curva Term SOFR."),
    Fonte("Dólar e SOFR", "Futuro de SOFR 3 meses direto da CME",
          "https://www.cmegroup.com/markets/interest-rates/stirs/"
          "three-month-sofr.quotes.html", False, "Mesma informação, mais difícil de extrair."),
    Fonte("Dólar e SOFR", "SOFR — New York Fed",
          "https://www.newyorkfed.org/markets/reference-rates/sofr", False,
          "Taxa realizada, para o fixing."),

    # ----------------------------------------------------------- conferência
    Fonte("Conferência", "Histórico de preços e taxas dos títulos (Tesouro Direto)",
          "https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/"
          "historico-de-precos-e-taxas", False, "Confere o PU par da NTN-B."),
    Fonte("Conferência", "Calculadora de renda fixa da B3",
          "https://calculadorarendafixa.com.br/#/navbar/calculadora", False,
          "Bate o cálculo de um papel isolado."),
    Fonte("Conferência", "Estatísticas do Banco Central",
          "https://www.bcb.gov.br/estatisticas", False,
          "Séries de CDI, Selic e PTAX."),
    Fonte("Conferência", "ANBIMA Data — diretório de dados",
          "https://data.anbima.com.br/", False, ""),
]


def por_grupo() -> dict:
    grupos: dict = {}
    for fonte in FONTES:
        grupos.setdefault(fonte.grupo, []).append(fonte)
    return grupos
