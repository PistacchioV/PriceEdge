"""Glossário dos termos que aparecem na ferramenta.

Escrito para quem já opera mas não necessariamente conhece a convenção
brasileira — ou o contrário. Cada verbete diz o que o termo é *nesta*
ferramenta, não a definição de livro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Verbete:
    grupo: str
    termo: str
    definicao: str
    nota: str = ""


GLOSSARIO: List[Verbete] = [
    # ------------------------------------------------------------ contagem
    Verbete("Contagem de dias", "DU — dias úteis",
            "Dias em que há pregão, pelo calendário escolhido. Base 252 ao ano.",
            "Contados como NETWORKDAYS − 1: o dia inicial não entra."),
    Verbete("Contagem de dias", "DC — dias corridos",
            "Dias de calendário puros, fim de semana e feriado incluídos. Base 360 ou 365.",
            "O cupom cambial e o SOFR usam DC/360; o prazo médio usa DC/365."),
    Verbete("Contagem de dias", "Exponencial 252",
            "Capitalização (1 + i)^(DU/252). Convenção de tudo que é em reais: DI, IPCA, TR."),
    Verbete("Contagem de dias", "Linear 360",
            "Capitalização 1 + i · DC/360. Convenção do que é em dólar: cupom cambial, "
            "Term SOFR, pré em dólar."),
    Verbete("Contagem de dias", "Following / Modified following",
            "Regra para levar um vencimento que cai em dia não útil para um dia útil. "
            "Following empurra para frente; modified following também, salvo se isso "
            "virar o mês — aí volta para trás.",
            "Modified following é o padrão de mercado."),

    # -------------------------------------------------------------- curvas
    Verbete("Curvas", "Vértice",
            "Um prazo com taxa publicada pela B3. A curva é a interpolação entre eles."),
    Verbete("Curvas", "Taxa spot (zero)",
            "Taxa de hoje até o vencimento, sem pagamento no meio. É o que a curva publica."),
    Verbete("Curvas", "FRA — taxa a termo",
            "Taxa implícita entre dois vencimentos futuros. Sai da razão dos fatores de "
            "capitalização: ((1+i₂)^(DU₂/252) / (1+i₁)^(DU₁/252))^(252/(DU₂−DU₁)) − 1."),
    Verbete("Curvas", "Fator de desconto",
            "O inverso do fator de capitalização — quanto vale hoje R$ 1 pago no vencimento."),
    Verbete("Curvas", "Spline cúbica natural",
            "Interpolação suave que passa por todos os vértices, com a segunda derivada "
            "zerada nas pontas. É a UDF cubic_spline das planilhas."),
    Verbete("Curvas", "Flat-forward",
            "Interpolação que mantém a taxa a termo constante entre vértices. Alternativa "
            "à spline, garante forwards não-negativos."),
    Verbete("Curvas", "Eixo da curva",
            "Contra qual prazo a curva é interpolada — dias úteis ou dias corridos. "
            "Consultar no eixo errado devolve a taxa de outro prazo.",
            "Consultar no eixo errado é um erro silencioso: devolve um número plausível."),
    Verbete("Curvas", "DV01",
            "Variação do MtM para um deslocamento paralelo de 1 ponto-base na curva."),

    # --------------------------------------------------------- indexadores
    Verbete("Indexadores", "DI / CDI",
            "Taxa dos depósitos interfinanceiros de um dia. A curva DI × Pré da B3 é a "
            "estrutura a termo dela.",
            "DI é o futuro negociado; CDI é a taxa apurada. No swap, dão no mesmo."),
    Verbete("Indexadores", "CDI ± spread",
            "Remuneração multiplicativa: (1 + CDI)·(1 + spread) = (1 + pré). Somar o "
            "spread ao CDI é o erro que a planilha marca em vermelho."),
    Verbete("Indexadores", "% do CDI",
            "Percentual aplicado sobre a taxa **diária**, não sobre a anual: "
            "[1 + ((1+CDI)^(1/252) − 1)·p]^DU.",
            "A 14% ao ano, 110% do CDI dá 15,5031% — não os 15,40% do cálculo ingênuo."),
    Verbete("Indexadores", "Cupom cambial limpo (DOC)",
            "Juro em dólar dentro do Brasil, já sem o efeito do casado. É a curva que "
            "desconta fluxo em dólar num cross-currency."),
    Verbete("Indexadores", "Cupom cambial sujo (DDI)",
            "O mesmo juro, mas com a PTAX D−1 embutida. Difere do limpo pelo casado."),
    Verbete("Indexadores", "IPCA+ / juro real",
            "Taxa real contratada acima da inflação. A inflação implícita sai de "
            "(1 + DI)/(1 + DI×IPCA) − 1."),
    Verbete("Indexadores", "NI — número-índice",
            "O índice de preços acumulado que corrige o principal de um papel IPCA+.",
            "Entre os dias 15 é interpolado pro rata em dias úteis."),
    Verbete("Indexadores", "VNA / VNE",
            "Valor Nominal Atualizado é o VNE (valor de emissão) corrigido pelo NI."),
    Verbete("Indexadores", "SOFR",
            "Taxa overnight garantida em dólar, publicada pelo Fed de Nova York. "
            "Backward-looking: só fecha no fim do período."),
    Verbete("Indexadores", "Term SOFR",
            "Versão forward-looking do SOFR, cotada pela CME em 1, 3, 6 e 12 meses. "
            "É conhecida no início do período."),
    Verbete("Indexadores", "Lookback (lag)",
            "Observa a taxa de k dias úteis antes, mas pesa pelos dias do período de juros."),
    Verbete("Indexadores", "Observation shift",
            "Desloca a janela inteira k dias úteis para trás, pesos inclusive. "
            "É a convenção que fecha exatamente com o SOFR Index."),

    # ------------------------------------------------------------ produtos
    Verbete("Produtos", "Swap",
            "Troca de fluxos entre duas pontas. Aqui a ponta ativa é a que se recebe e "
            "a passiva a que se paga."),
    Verbete("Produtos", "MtM — marcação a mercado",
            "Diferença entre o valor presente das duas pontas. Zero é o swap justo."),
    Verbete("Produtos", "Taxa par",
            "A taxa que zera o MtM — o que o solver procura."),
    Verbete("Produtos", "Cross-currency swap",
            "Swap com as pontas em moedas diferentes. Cada fluxo desconta pela curva da "
            "sua moeda — nunca pela mesma."),
    Verbete("Produtos", "NDF",
            "Contrato a termo de moeda liquidado por diferença. O preço sai da paridade "
            "coberta de juros: spot · (1+DI)^(DU/252) / (1 + cupom·DC/360)."),
    Verbete("Produtos", "Pontos de NDF",
            "Diferença entre o termo e o spot, em pips: (NDF − spot) × 10.000."),
    Verbete("Produtos", "Casado",
            "Diferença entre o primeiro futuro de dólar e o spot."),
    Verbete("Produtos", "Rolagem",
            "Diferença entre o segundo e o primeiro futuro de dólar, em pips."),
    Verbete("Produtos", "Bullet",
            "Amortização única, no vencimento. Os juros podem ou não ter cupom no meio."),
    Verbete("Produtos", "Fee upfront",
            "Valor pago ou recebido à vista, na contratação, fora dos fluxos do swap. "
            "Entra direto no MtM: um fee de R$ 100 mil recebido melhora o resultado da "
            "ponta ativa em R$ 100 mil já no dia zero.",
            "É por isso que a taxa par muda quando há fee: o swap deixa de ser justo "
            "no zero e passa a ser justo no valor do fee."),
    Verbete("Produtos", "Prazo médio × duration",
            "Prazo médio pondera pelo principal amortizado; duration pondera pelo valor "
            "presente do fluxo inteiro. Num bullet com cupom, a duration é menor."),

    # ---------------------------------------------------------- renda fixa
    Verbete("Renda fixa", "Fator diário do DI",
            "(1 + DI)^(1/252). O padrão B3/CETIP arredonda na 8ª casa antes de acumular; "
            "aqui o padrão é não arredondar.",
            "Em cinco anos a diferença chega à casa dos reais por milhão."),
    Verbete("Renda fixa", "IR regressivo",
            "22,5% até 180 dias, 20% até 360, 17,5% até 720, 15% acima disso — sobre o "
            "rendimento, não sobre o principal."),
    Verbete("Renda fixa", "IOF",
            "Incide só em resgate com menos de 30 dias corridos, de 96% a 0% do rendimento."),
    Verbete("Renda fixa", "PU — preço unitário",
            "Valor presente de um título por unidade."),
]


def por_grupo() -> dict:
    grupos: dict = {}
    for verbete in GLOSSARIO:
        grupos.setdefault(verbete.grupo, []).append(verbete)
    return grupos
