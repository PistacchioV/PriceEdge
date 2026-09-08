"""Português e inglês.

O dicionário é indexado pela própria frase em português — sem chaves
inventadas. Isso tem duas vantagens: o template continua legível quando você
lê o código, e uma frase sem tradução cai de volta no português em vez de
mostrar uma chave crua na tela.

Fórmulas, siglas e rótulos que já são iguais nos dois idiomas (DI, DU, DC,
NDF, SOFR, VNA) ficam de fora de propósito.
"""

from __future__ import annotations

from typing import Dict

IDIOMAS = [("pt", "Português"), ("en", "English")]
PADRAO = "pt"

TRADUCOES: Dict[str, str] = {
    # ------------------------------------------------------------ navegação
    "Painel": "Dashboard",
    "Interpolação": "Interpolation",
    "NI pro-rata": "Pro-rata index",
    "Metodologia": "Methodology",
    "Ferramentas": "Tools",
    "Novo swap": "New swap",
    "Referência": "Reference",
    "Convenções": "Conventions",
    "Precificar swap": "Price a swap",
    "Taxas referenciais B3": "B3 reference rates",
    "API JSON": "JSON API",
    "Design system Pulsedesk": "Pulsedesk design system",
    "Trocar idioma": "Switch language",
    "Trocar tema": "Switch theme",
    "Porte das planilhas de precificação de swaps para Python: calendário ANBIMA, "
    "spline cúbica, curvas da B3 e as quatro estruturas do curso.":
        "The swap pricing spreadsheets ported to Python: ANBIMA calendar, cubic "
        "spline, B3 curves and the course's swap structures.",
    "Dados públicos da B3. Ferramenta de estudo — confira contra a sua fonte oficial "
    "antes de operar.":
        "Public B3 data. A study tool — check against your official source before "
        "trading on it.",
    "DI · exponencial 252": "DI · exponential 252",
    "Cupom cambial · linear 360": "Onshore USD rate · linear 360",
    "Feriados · ANBIMA": "Holidays · ANBIMA",

    # --------------------------------------------------------------- painel
    "Swaps de balcão, ponta a ponta.": "OTC swaps, leg by leg.",
    "Curvas da B3 · calendário ANBIMA · spline cúbica natural":
        "B3 curves · ANBIMA calendar · natural cubic spline",
    "As macros VBA de interpolação e extração de curvas viraram um pacote Python. "
    "Extraia a curva do dia direto da B3, interpole o prazo que precisar e precifique "
    "as quatro estruturas do curso — com o MtM e a taxa par calculados na hora.":
        "The VBA macros for interpolation and curve extraction are now a Python "
        "package. Pull today's curve straight from B3, interpolate any tenor and "
        "price the course's structures — with MtM and par rate computed on the spot.",
    "Precificar um swap": "Price a swap",
    "Extrair curva da B3": "Pull a B3 curve",
    "Taxas Referenciais B3": "B3 reference rates",
    "Endpoint ativo": "Endpoint live",
    "Histórico limitado": "Limited history",
    "A B3 mantém arquivo público de aproximadamente o último mês útil. Datas mais "
    "antigas não têm dado nessa API.":
        "B3 keeps roughly the last month of public files. Older dates have no data "
        "in this API.",
    "01 · Estruturas": "01 · Structures",
    "Quatro swaps, cada um com a sua armadilha.":
        "Five swaps, each with its own trap.",
    "São as mesmas estruturas das planilhas de aula. O que muda é que aqui a curva de "
    "desconto de cada perna está fixada em código, não numa fórmula que dá para "
    "arrastar errado.":
        "The same structures as the course spreadsheets. What changes is that each "
        "leg's discount curve is fixed in code here, not in a formula you can drag "
        "into the wrong column.",
    "futuros SR3": "SR3 futures",

    # --------------------------------------------------------------- curvas
    "Taxas Referenciais": "Reference rates",
    "Extrair curva da B3.": "Pull a curve from B3.",
    "Mesmo endpoint do link “Histórico de arquivos” da página oficial. O arquivo "
    "público cobre aproximadamente o último mês útil — datas anteriores não existem "
    "nessa API.":
        "The same endpoint behind the “File history” link on B3's own page. The "
        "public file covers roughly the last month — earlier dates do not exist in "
        "this API.",
    "Curva": "Curve",
    "Data (dia útil)": "Date (business day)",
    "Vértices publicados": "Published curve pillars",
    "Convenção": "Convention",
    "Dias úteis (252)": "Business days (252)",
    "Dias corridos (360)": "Calendar days (360)",
    "Taxa (% a.a.)": "Rate (% p.a.)",
    "linhas": "rows",

    # ---------------------------------------------------------- precificação
    "Precificação": "Pricing",
    "Contrato": "Contract",
    "Nocional": "Notional",
    "anos": "years",
    "SOFR, estrutura a termo realizada.": "SOFR, the realized term structure.",
    "Overnight e médias compostas de 30, 90 e 180 dias, do Fed de Nova York, guardadas "
    "numa base local desde a criação do SOFR em 2018.":
        "Overnight and 30, 90 and 180-day compounded averages from the New York Fed, "
        "kept in a local database since SOFR began in 2018.",
    "SOFR overnight": "SOFR overnight",
    "Média composta 30 dias": "30-day compounded average",
    "Média composta 90 dias": "90-day compounded average",
    "Média composta 180 dias": "180-day compounded average",
    "SOFR Index": "SOFR Index",
    "índice acumulado": "accumulated index",
    "SOFR — valores diários": "SOFR — daily values",
    "Sobre o Term SOFR da CME": "About CME Term SOFR",
    "O Term SOFR forward-looking de 1, 3, 6 e 12 meses é administrado pela CME e "
    "licenciado — não há fonte pública que permita redistribuí-lo, então ele continua "
    "entrando digitado na tela de precificação. O que está aqui é a estrutura a termo "
    "realizada, que o Fed de Nova York publica aberta: o overnight e as médias "
    "compostas.":
        "The forward-looking 1, 3, 6 and 12-month Term SOFR is administered by CME and "
        "licensed — no public source allows redistributing it, so it stays a manual "
        "input on the pricing screen. What is here is the realized term structure, which "
        "the New York Fed publishes openly: the overnight rate and the compounded "
        "averages.",
    "SOFR composto": "Compounded SOFR",
    "04 · Rede e autenticação": "04 · Network and authentication",
    "05 · Glossário": "05 · Glossary",
    "Como as chamadas externas saem daqui.": "How outbound calls leave this app.",
    "Toda busca externa passa por um ponto só. Fora de rede corporativa vai por urllib, "
    "sem autenticação — as fontes usadas são públicas. Num ambiente com SSO, três "
    "variáveis ligam o Negotiate sem mexer em código.":
        "Every outbound fetch goes through a single point. Outside a corporate network "
        "it uses urllib with no authentication — the sources are public. In an SSO "
        "environment, three variables turn Negotiate on without touching code.",
    "SSO pedido": "SSO requested",
    "SSO disponível": "SSO available",
    "requests": "requests",
    "Negotiate SSPI": "Negotiate SSPI",
    "Kerberos": "Kerberos",
    "Proxy ignorado": "Proxy bypassed",
    "ativo": "on", "inativo": "off",
    "Variáveis de ambiente": "Environment variables",
    "O ADFS só oferece o desafio Negotiate a User-Agents da lista dele: com o padrão do "
    "requests ele devolve a página de login, e o erro que chega fala de JSON inválido "
    "sem mencionar autenticação. Por isso o User-Agent de navegador é forçado quando o "
    "SSO está ligado.":
        "ADFS only offers the Negotiate challenge to User-Agents on its allow-list: with "
        "the requests default it returns the login page, and the error that surfaces "
        "talks about invalid JSON without mentioning authentication. That is why a "
        "browser User-Agent is forced when SSO is on.",
    "Precificação de swaps": "Swap pricing",
    "Buscar cotações": "Fetch quotes",
    "PTAX de": "PTAX of",
    "futuros implícitos na curva PTX da B3": "futures implied by B3's PTX curve",
    "não foi possível buscar as cotações": "could not fetch the quotes",
    "(1 + i) ^ (DU / 252)": "(1 + i) ^ (BD / 252)",
    "1 + i · DC / 360": "1 + i · CD / 360",
    "(1+CDI) · (1+spread) = (1+pré)": "(1+CDI) · (1+spread) = (1+fixed)",
    "SOFR + spread": "SOFR + spread",
    "A linha é a curva interpolada": "The line is the interpolated curve",
    "os pontos são os vértices publicados.": "the dots are the published pillars.",
    "taxa": "rate",
    "fator": "factor",
    "taxa = f(dias corridos)": "rate = f(calendar days)",
    "Templates": "Templates",
    "Livre": "Blank",
    "Precificar": "Price a swap",
    "Preço": "Price",
    "Preço a termo": "Forward price",
    "preço a termo por dias corridos": "forward price by calendar days",
    "taxa (% a.a.) por dias corridos": "rate (% p.a.) by calendar days",
    "Juros em real — exponencial 252": "BRL rates — compounded 252",
    "Cupom e spread — linear 360": "Coupons and spreads — linear 360",
    "Preço a termo — não é taxa": "Forward price — not a rate",
    "O que cada módulo resolve.": "What each module solves.",
    "02 · Módulos": "02 · Modules",
    "Customized Swap": "Customized Swap",
    "Janela do gráfico": "Chart window",
    "1 mês": "1 month", "3 meses": "3 months", "6 meses": "6 months",
    "1 ano": "1 year", "5 anos": "5 years", "Tudo": "All",
    "Ver": "View",
    "Base local": "Local database",
    "dias guardados": "days stored",
    "Taxas vigentes em": "Rates in force on",
    "não houve publicação em": "no publication on",
    "vale a última anterior": "the previous one applies",
    "Série do Banco da Finlândia, os cinco prazos cotados, guardada numa base local que "
    "só cresce — a fonte publica seis meses por vez e o histórico some com facilidade.":
        "The Bank of Finland series, all five quoted tenors, kept in a local database "
        "that only grows — the source publishes six months at a time and the history "
        "disappears easily.",
    "Banco da Finlândia, relatório de EURIBOR diário. A fonte mostra seis meses por vez, "
    "mas o seletor de data inicial vai até janeiro de 2006 — a base local percorre todas "
    "as janelas e guarda tudo. A cada carregamento a janela corrente é buscada de novo; "
    "datas que ainda não estão na base entram, e nada do que já foi gravado se perde.":
        "Bank of Finland, daily EURIBOR report. The source shows six months at a time, "
        "but the start-date selector goes back to January 2006 — the local database "
        "walks every window and keeps it all. On each load the current window is "
        "fetched again; dates not yet in the database are added, and nothing already "
        "stored is lost.",
    "Valor pago ou recebido à vista, na contratação, fora dos fluxos do swap. Entra "
    "direto no MtM: um fee de R$ 100 mil recebido melhora o resultado da ponta ativa em "
    "R$ 100 mil já no dia zero.":
        "An amount paid or received in cash at inception, outside the swap's cash "
        "flows. It goes straight into the mark-to-market: a R$ 100k fee received "
        "improves the receive leg's result by R$ 100k on day zero.",
    "É por isso que a taxa par muda quando há fee: o swap deixa de ser justo no zero e "
    "passa a ser justo no valor do fee.":
        "That is why the par rate moves when there is a fee: the swap is no longer fair "
        "at zero, it is fair at the fee amount.",
    "Lookback (dias úteis)": "Lookback (business days)",
    "Observation shift (dias úteis)": "Observation shift (business days)",
    "O shift desloca a janela inteira — datas e pesos. O lookback desloca só a leitura "
    "da taxa dentro dela. Zerados, o cálculo observa o próprio período; iguais, é o "
    "lookback com observation shift. Valores usuais: 2 a 5 dias úteis.":
        "The shift moves the whole window — dates and weights. The lookback moves only "
        "the rate reading inside it. Both at zero, the calculation observes the period "
        "itself; equal, it is lookback with observation shift. Usual values: 2 to 5 "
        "business days.",
    "janela observada": "observed window",
    "nenhuma": "none",
    "Juros em euro": "Euro rates",
    "EURIBOR, valores diários.": "EURIBOR, daily values.",
    "Série do Banco da Finlândia, os cinco prazos cotados. A fonte publica uma janela "
    "de seis meses por vez — é o que vem aqui.":
        "The Bank of Finland series, all five quoted tenors. The source publishes a "
        "six-month window at a time — that is what arrives here.",
    "EURIBOR — valores diários": "EURIBOR — daily values",
    "dias publicados": "published days",
    "Valores publicados": "Published values",
    "dias": "days",
    "Fonte e limite": "Source and limit",
    "Banco da Finlândia, relatório de EURIBOR diário. O seletor de data inicial do site "
    "é um postback e não passa pela URL, então daqui sai sempre a janela padrão — os "
    "últimos seis meses. Para histórico mais antigo, escolha outra data inicial no "
    "próprio site e exporte.":
        "Bank of Finland, daily EURIBOR report. The site's start-date selector is an "
        "ASP.NET postback and does not travel in the URL, so what comes through here is "
        "always the default window — the last six months. For older history, pick "
        "another start date on the site itself and export from there.",
    "Taxas e curvas": "Rates and curves",
    "Data de início": "Start date",
    "Vencimento": "Maturity",
    "Periodicidade": "Payment frequency",
    "Amortização": "Amortization",
    "Fee upfront": "Upfront fee",
    "Convenção de dia útil": "Business day convention",
    "Sem fluxo de caixa — só o pagamento final":
        "Zero coupon — single payment at maturity",
    "Principal e juros liquidam de uma vez no vencimento. A periodicidade é ignorada.":
        "Principal and interest settle in one go at maturity. Frequency is ignored.",
    "Pesos por período, em % (separados por vírgula, somando 100)":
        "Weight per period, in % (comma separated, adding to 100)",
    "Data das curvas da B3": "B3 curve date",
    "Remuneração da ponta CDI": "CDI leg convention",
    "O spread é multiplicativo sobre a taxa anual; o percentual incide sobre a taxa":
        "The spread is multiplicative on the annual rate; the percentage applies to "
        "the",
    ". Não dá na mesma.": " rate. They are not the same thing.",
    "diária": "daily",
    "Spread sobre o CDI (% a.a.)": "Spread over CDI (% p.a.)",
    "Percentual do CDI (%)": "Percentage of CDI (%)",
    "deixe vazio para calcular": "leave empty to solve for it",
    "O que resolver": "What to solve for",
    "A ponta CDI, dada a taxa pré": "The CDI leg, given the fixed rate",
    "A ponta CDI, dada a taxa em dólar": "The CDI leg, given the dollar rate",
    "Taxa pré par, dada a ponta CDI": "Par fixed rate, given the CDI leg",
    "Taxa pré USD par, dada a ponta CDI": "Par USD fixed rate, given the CDI leg",
    "Taxa pré BRL (% a.a. 252)": "BRL fixed rate (% p.a. 252)",
    "Taxa pré BRL (% a.a. exp 252)": "BRL fixed rate (% p.a. exp 252)",
    "Taxa pré USD (% a.a. lin 360)": "USD fixed rate (% p.a. lin 360)",
    "Taxa real da emissão — IPCA+ (% a.a. 252)":
        "Real rate of the issue — IPCA+ (% p.a. 252)",
    "Dólar de partida": "Initial FX rate",
    "Taxa pré BRL par": "Par BRL fixed rate",
    "Taxa pré USD par": "Par USD fixed rate",
    "Tenor do Term SOFR": "Term SOFR tenor",
    "Term SOFR CME — 1M, 3M, 6M, 12M (%)": "CME Term SOFR — 1M, 3M, 6M, 12M (%)",
    "Define o reset e a periodicidade da perna flutuante.":
        "Sets the reset and the frequency of the floating leg.",
    "Monta o trecho curto da curva.": "Builds the short end of the curve.",
    "Preços dos futuros SR3 (SOFR 3 meses), do mais curto ao mais longo":
        "SR3 futures prices (3-month SOFR), shortest to longest",
    "Cotação em preço (100 − taxa). Cada preço vira o forward entre duas datas IMM "
    "(terceira quarta-feira do mês de vencimento). Fonte: Barchart ou CME.":
        "Quoted as price (100 − rate). Each price becomes the forward between two IMM "
        "dates (third Wednesday of the delivery month). Source: Barchart or CME.",
    "A ponta CDI par é sempre calculada. A inflação implícita vem das curvas PRE e DIC "
    "do mesmo arquivo da B3, então as duas pontas ficam consistentes.":
        "The par CDI leg is always solved. Break-even inflation comes from the PRE and "
        "DIC curves of the same B3 file, so both legs stay consistent.",
    "Preencha o contrato e clique em Calcular.":
        "Fill in the contract and hit Calculate.",
    "As curvas são baixadas da B3 na hora e ficam em cache por data. Se a data não "
    "tiver arquivo publicado, o erro aparece aqui.":
        "Curves are pulled from B3 on demand and cached by date. If no file was "
        "published for that date, the error shows up here.",
    "par": "par",
    "Ponta ativa": "Receive leg",
    "Ponta passiva": "Pay leg",
    "Pagamento": "Payment date",
    "Saldo": "Outstanding notional",
    "Taxa período": "Accrual rate",
    "Juros": "Interest accrued",
    "Valor futuro": "Future value",
    "Valor presente": "Present value",

    # ------------------------------------------------------------------ NDF
    "Câmbio a termo": "Currency forwards",
    "NDF · curva de dólar.": "NDF · dollar curve.",
    "Paridade coberta de juros com as duas curvas da B3: DI exponencial em dias úteis "
    "no numerador, cupom cambial linear em dias corridos no denominador.":
        "Covered interest parity with both B3 curves: DI compounded on business days "
        "in the numerator, FX coupon linear on calendar days in the denominator.",
    "Data-base das curvas": "Curve base date",
    "Spot D+2": "Spot D+2",
    "1º futuro DOL": "1st DOL future",
    "2º futuro DOL": "2nd DOL future",
    "Vencimentos": "Maturities",
    "Vencimento do NDF": "NDF maturity",
    "Preenchido, a curva é montada só para esta data — é o NDF de um contrato "
    "específico. Vazio, vale a escada abaixo.":
        "If filled in, the curve is built for this date alone — the NDF of one specific "
        "contract. Left empty, the ladder below applies.",
    "Progressão": "Ladder",
    "Quantidade": "Count",
    "Ou datas específicas (opcional)": "Or specific dates (optional)",
    "Preenchido, ignora a progressão. As demais datas seguem o último dia útil do mês "
    "de vencimento, como na planilha.":
        "If filled in, the ladder is ignored. Otherwise dates fall on the last "
        "business day of the delivery month, as in the spreadsheet.",
    "Dólar a termo": "Forward dollar",
    "a linha tracejada é o spot": "the dashed line is spot",
    "Curva de dólar a termo": "Forward dollar curve",
    "Carry": "Carry",
    "Pontos": "Points",
    "Cupom cambial": "Onshore USD rate",
    "Informe o spot e monte a escada de vencimentos.":
        "Enter the spot and build the maturity ladder.",
    "As curvas DI x Pré e Cupom Cambial Limpo são baixadas da B3 para a data-base.":
        "The DI x Pré and Clean FX Coupon curves are pulled from B3 for the base date.",
    "Fórmula aplicada": "Formula applied",
    "vencimentos": "maturities",

    # ----------------------------------------------------------------- SOFR
    "Taxa realizada": "Realized rate",
    "SOFR composto, direto do Fed.": "Compounded SOFR, straight from the Fed.",
    "Fixings diários do Federal Reserve de Nova York, compostos dia a dia. O Term SOFR "
    "é cotado de antemão; este é o que fecha no fim do período.":
        "Daily fixings from the New York Fed, compounded day by day. Term SOFR is "
        "quoted upfront; this one only settles at the end of the period.",
    "Período de juros": "Accrual period",
    "Início": "Start date",
    "Fim": "End date",
    "Convenção de observação": "Observation method",
    "Defasagem (dias úteis)": "Lookback (business days)",
    "Ignorada quando a convenção é “sem defasagem”. Valores usuais: 2 a 5 dias úteis.":
        "Ignored when the convention is “no lag”. Usual values: 2 to 5 business days.",
    "Fórmula": "Formula",
    "são os dias corridos até o próximo dia útil — o fixing de sexta remunera três dias.":
        "are the calendar days to the next business day — Friday's fixing pays for "
        "three days.",
    "SOFR composto no período": "Compounded SOFR over the period",
    "Fator": "Compounded factor",
    "Composição dia a dia": "Daily compounding schedule",
    "Dia de juros": "Accrual date",
    "Observação": "Observation date",
    "Fator do dia": "Daily accrual factor",
    "Acumulado": "Compounded factor",
    "Escolha o período e a convenção.": "Pick the period and the convention.",
    "Os fixings vêm da API pública do NY Fed e o resultado é conferido contra o SOFR "
    "Index oficial.":
        "Fixings come from the NY Fed public API and the result is checked against the "
        "official SOFR Index.",

    # ----------------------------------------------------------- renda fixa
    "Calculadora": "Calculator",
    "Renda fixa, bruto e líquido.": "Fixed income, gross and net.",
    "Prefixado, % do CDI, CDI + spread e IPCA+, com IR regressivo e IOF. O fator do DI "
    "roda em precisão plena — sem o arredondamento na 8ª casa.":
        "Fixed rate, % of CDI, CDI + spread and IPCA+, with the regressive income tax "
        "and IOF. The DI factor runs at full precision — no rounding at the 8th "
        "decimal.",
    "Aplicação": "Trade",
    "Valor aplicado (R$)": "Principal invested (R$)",
    "Data da aplicação": "Trade date",
    "Produto": "Product",
    "Indexador": "Index / benchmark",
    "Taxa contratada": "Contract rate",
    "110 para 110% do CDI · 2 para CDI+2% · 14 para 14% a.a. prefixado · 6 para IPCA+6%":
        "110 for 110% of CDI · 2 for CDI+2% · 14 for 14% p.a. fixed · 6 for IPCA+6%",
    "CDI projetado (% a.a.)": "Projected CDI (% p.a.)",
    "IPCA projetado (% a.a.)": "Projected IPCA (% p.a.)",
    "Arredondar o fator diário do DI na 8ª casa":
        "Round the daily DI factor at the 8th decimal",
    "Padrão B3/CETIP. Desligado, o fator roda em precisão plena — que é o padrão aqui.":
        "The B3/CETIP standard. Left off, the factor runs at full precision — which is "
        "the default here.",
    "Valor líquido no vencimento": "Net proceeds at maturity",
    "isento de IR": "income tax exempt",
    "Valor bruto": "Gross proceeds",
    "O que o arredondamento na 8ª casa muda":
        "What rounding at the 8th decimal changes",
    "Precisão plena": "Full precision",
    "Arredondado na 8ª casa": "Rounded at the 8th decimal",
    "Bruto no vencimento": "Gross proceeds at maturity",
    "Valor": "Value",
    "Tabela regressiva do IR": "Regressive income tax table",
    "até 180 dias 22,5% · 181 a 360 dias 20% · 361 a 720 dias 17,5% · acima de 720 dias "
    "15%. IOF regressivo em resgate com menos de 30 dias corridos.":
        "up to 180 days 22.5% · 181 to 360 days 20% · 361 to 720 days 17.5% · beyond "
        "720 days 15%. Regressive IOF on redemptions inside 30 calendar days.",
    "Informe o valor, o prazo e a taxa contratada.":
        "Enter the amount, the term and the contracted rate.",

    # --------------------------------------------------------- interpolação
    "Interpolação de curvas.": "Curve interpolation.",
    "Mesma spline cúbica natural das planilhas — segunda derivada zero nas pontas, "
    "busca binária pelo intervalo. Aqui dá para comparar com a linear e com a "
    "flat-forward, e ver o que cada uma faz fora do domínio dos vértices.":
        "The same natural cubic spline as the spreadsheets — second derivative zero at "
        "the ends, binary search for the interval. Here you can compare it against "
        "linear and flat-forward, and see what each does outside the vertex range.",
    "Pontos conhecidos": "Market pillars",
    "Carregar da B3": "Load from B3",
    "Eixo x — prazos (dias corridos)": "x axis — tenor (calendar days)",
    "Eixo y — taxas (% a.a.)": "y axis — rate (% p.a.)",
    "Método": "Method",
    "Fora do domínio": "Outside the pillar range",
    "Travar na ponta (recomendado)": "Flat beyond the last pillar (recommended)",
    "Extrapolar o polinômio":
        "Extrapolate the polynomial (as the VBA does)",
    "Prazos a interpolar": "Tenors to interpolate",
    "Resultado": "Result",
    "Prazo (dc)": "Tenor (calendar days)",
    "Taxa interpolada": "Interpolated rate",
    "Situação": "Status",
    "extrapolado": "extrapolated",
    "dentro do domínio": "inside the range",
    "Cole os vértices ou carregue uma curva da B3.":
        "Paste the vertices or load a curve from B3.",
    "Um valor por linha, nas duas colunas. Vírgula ou ponto decimal, tanto faz.":
        "One value per line in each column. Comma or dot as the decimal separator, "
        "either works.",

    # ------------------------------------------------------------ NI pro-rata
    "Número-índice pro-rata e VNA.": "Pro-rata index number and adjusted face value.",
    "A aba “Cálculo NI Pro-Rata” das planilhas de IPCA. Interpola o número-índice entre "
    "o dia 15 de um mês e o do seguinte, em dias úteis, com a projeção da ANBIMA.":
        "The “Pro-rata index” tab of the IPCA spreadsheets. Interpolates the index "
        "number between the 15th of one month and the next, on business days, using "
        "ANBIMA's projection.",
    "Insumos": "Inputs",
    "Data de referência": "Reference date",
    "NIk−1 (IBGE)": "NIk−1 (IBGE)",
    "Projeção mensal ANBIMA (%)": "ANBIMA monthly projection (%)",
    "NI de partida": "Base index number",
    "NIk−1 vem da tabela 1737 do SIDRA; a projeção mensal, da página de projeção de "
    "inflação da ANBIMA. Ambos os links estão em Metodologia → fontes.":
        "NIk−1 comes from SIDRA table 1737; the monthly projection from ANBIMA's "
        "inflation projection page. Both links are under Methodology → sources.",
    "Informe o número-índice e a projeção do mês.":
        "Enter the index number and this month's projection.",

    # --------------------------------------------------------- metodologia
    "Convenções, fontes e critérios de cálculo.":
        "Conventions, sources and calculation choices.",
    "Tudo que o pacote decide por você está listado aqui. Onde o porte discorda de "
    "alguma planilha original, o motivo está escrito.":
        "Everything the package decides on your behalf is listed here. Where the port "
        "disagrees with an original spreadsheet, the reason is written down.",
    "01 · Critérios de cálculo": "01 · Porting decisions",
    "Três escolhas de cálculo que valem explicação.":
        "Three places where the code does not copy the spreadsheet.",
    "02 · Curvas disponíveis": "02 · Available curves",
    "Sete curvas, com o código que a B3 usa no arquivo.":
        "Seven curves, with the code B3 uses in the file.",
    "Nome": "Name",
    "Código": "Code",
    "Uso": "Use",
    "03 · Fontes de dados": "03 · Data sources",
    "Onde cada número nasce.": "Where each number comes from.",
    "As marcadas como automáticas a ferramenta busca sozinha. O resto entra digitado — "
    "e é aí que compensa conferir na fonte.":
        "The ones marked automatic the tool fetches on its own. The rest is typed in — "
        "and that is where checking the source pays off.",
    "automático": "automatic",
    "04 · Glossário": "04 · Glossary",
    "O que cada termo quer dizer aqui.": "What each term means here.",
    "Definições operacionais, não de livro: o que o termo significa dentro desta "
    "ferramenta e onde ele costuma ser confundido.":
        "Working definitions, not textbook ones: what the term means inside this tool "
        "and where it usually gets confused.",
    "05 · Origem": "05 · Origin",
    "De qual arquivo veio cada coisa.": "Which file each piece came from.",

    # ------------------------------------- catálogo de curvas e textos de tela
    "Ajuste Pré": "Ajuste Pré (adjustment curve)",
    "Selic x Pré": "Selic x Pré",
    "DI x IGP-M": "DI x IGP-M",
    "TR x Pré": "TR x Pré",
    "TBF x Pré": "TBF x Pré",
    "Cupom Cambial Sujo (DI x dólar)": "Dirty FX coupon (DI x USD)",
    "Cupom Cambial OC1": "FX coupon OC1",
    "Cupom de Euro (DI x euro)": "Euro coupon (DI x EUR)",
    "Libor": "Libor",
    "Spread Libor Euro x Dólar": "Libor EUR vs USD spread",
    "Dólar a Termo (Real x dólar)": "Forward USD (BRL/USD)",
    "Euro a Termo (Real x euro)": "Forward EUR (BRL/EUR)",
    "Iene a Termo (Real x iene)": "Forward JPY (BRL/JPY)",
    "Ibovespa a Termo": "Forward Ibovespa",
    "EUR/USD a Termo (derivado)": "Forward EUR/USD (derived)",
    "EURIBOR": "EURIBOR",

    "Juros nominais em reais. É a curva de desconto de tudo que é em real.":
        "Nominal BRL rates. It is the discount curve for everything in reais.",
    "Mesma curva do PRE, publicada para ajuste de posições.":
        "The same curve as PRE, published for position adjustment.",
    "Estrutura a termo da Selic. Na prática acompanha o DI.":
        "Term structure of the Selic rate. In practice it tracks DI.",
    "Juro real. Contra a curva PRE dá a inflação implícita.":
        "Real rate. Against the PRE curve it gives break-even inflation.",
    "Juro real contra o IGP-M, para papéis indexados a esse índice.":
        "Real rate against IGP-M, for instruments indexed to it.",
    "Juros descontada a TR.": "Rates net of the TR.",
    "A TR projetada pela curva.": "The TR implied by the curve.",
    "A TBF projetada pela curva.": "The TBF implied by the curve.",
    "Cupom cambial sem o efeito do casado. Desconta fluxo em dólar.":
        "Onshore USD rate stripped of the casado. It discounts dollar flows.",
    "O DDI, com a PTAX D−1 embutida. Difere do limpo pelo casado.":
        "The DDI, with the D−1 PTAX embedded. It differs from the clean one by the casado.",
    "Cupom cambial do primeiro vencimento em aberto.":
        "Onshore USD rate of the first open contract month.",
    "O cupom cambial do euro — o equivalente do DOC para a moeda europeia.":
        "The euro coupon — the DOC equivalent for the European currency.",
    "Curva de Libor publicada pela B3.": "Libor curve as published by B3.",
    "A base entre euro e dólar. É o que mais perto chega de uma curva EUR/USD.":
        "The euro-dollar basis. It is the closest thing to an EUR/USD curve here.",
    "Preço do dólar a termo, não taxa: 5,13 hoje, 56,99 em 34 anos.":
        "Forward dollar price, not a rate: 5.13 today, 56.99 in 34 years.",
    "Preço do euro a termo. Dividido pelo PTX dá o EUR/USD a termo.":
        "Forward euro price. Divided by PTX it gives the forward EUR/USD.",
    "Preço do iene a termo.": "Forward yen price.",
    "Ibovespa a termo, em pontos.": "Forward Ibovespa, in index points.",
    "Não existe curva EUR/USD na B3, mas as duas pontas existem: o euro a termo "
    "dividido pelo dólar a termo dá o EUR/USD a termo.":
        "B3 publishes no EUR/USD curve, but both legs exist: the forward euro divided "
        "by the forward dollar gives the forward EUR/USD.",

    "Extraia a curva do dia direto da B3, interpole o prazo que precisar e monte o swap "
    "ponta a ponta — com o MtM e a taxa par calculados na hora.":
        "Pull today's curve straight from B3, interpolate any tenor and build the swap "
        "leg by leg — with MtM and par rate computed on the spot.",
    "A curva de desconto de cada perna está fixada em código: fluxo em real desconta no "
    "DI, fluxo em dólar no cupom cambial. Não há fórmula para arrastar errado.":
        "Each leg's discount curve is fixed in code: BRL flows discount on DI, USD flows "
        "on the onshore USD curve. There is no formula to drag into the wrong column.",
    "Precificação de swaps de balcão: calendário ANBIMA, spline cúbica, curvas da B3 e "
    "as estruturas de mercado.":
        "OTC swap pricing: ANBIMA calendar, cubic spline, B3 curves and the market "
        "structures.",
    "Feriados ANBIMA, SOFR e EURIBOR; WORKDAY, NETWORKDAYS e convenções de dia útil":
        "ANBIMA, SOFR and EURIBOR holidays; WORKDAY, NETWORKDAYS and business day "
        "conventions",
    "Spline cúbica natural, linear e flat-forward, com três regras de extrapolação":
        "Natural cubic spline, linear and flat-forward, with three extrapolation rules",
    "Extração das 18 curvas de Taxas Referenciais da B3":
        "Extraction of all 18 B3 reference rate curves",
    "Busca da taxa par que zera o MtM": "Search for the par rate that zeroes the MtM",
    "Spline cúbica natural — segunda derivada zero nas pontas, busca binária pelo "
    "intervalo. Dá para comparar com a linear e com a flat-forward, e ver o que cada uma "
    "faz fora do domínio dos vértices.":
        "Natural cubic spline — second derivative zero at the ends, binary search for the "
        "interval. Compare it against linear and flat-forward, and see what each does "
        "outside the pillar range.",
    "Interpola o número-índice entre o dia 15 de um mês e o do seguinte, em dias úteis, "
    "com a projeção da ANBIMA.":
        "Interpolates the index number between the 15th of one month and the next, on "
        "business days, using ANBIMA's projection.",
    "Preenchido, ignora a progressão. As demais datas caem no último dia útil do mês de "
    "vencimento.":
        "If filled in, the ladder is ignored. Otherwise dates fall on the last business "
        "day of the delivery month.",
    "Tudo que a ferramenta decide por você está listado aqui, com o motivo de cada "
    "escolha.":
        "Everything the tool decides on your behalf is listed here, with the reason for "
        "each choice.",
    "O eixo publicado pela B3 vai até 12.556 — são dias corridos. Consultar essa curva "
    "num valor de dias úteis (126 em vez de 183) devolve a taxa de um prazo mais curto, "
    "e a diferença chega a 15 bp no vértice de seis meses. Por isso o eixo é explícito "
    "em Curva.eixo e taxa_para(dc, du) escolhe o certo sozinha.":
        "The axis B3 publishes runs to 12,556 — those are calendar days. Querying that "
        "curve at a business-day value (126 instead of 183) returns the rate for a "
        "shorter tenor, and the gap reaches 15 bp at the six-month pillar. That is why "
        "the axis is explicit in Curva.eixo and taxa_para(dc, du) picks the right one.",
    "Prolongar o polinômio cúbico além do último vértice pode devolver qualquer coisa. O "
    "padrão aqui é travar no último valor publicado; a extrapolação cúbica e a tangente "
    "continuam disponíveis na tela de interpolação, para conferir contra outra fonte.":
        "Extending the cubic polynomial beyond the last pillar can return anything. The "
        "default here is to hold the last published value; cubic and tangent "
        "extrapolation remain available on the interpolation screen, to cross-check "
        "against another source.",
    "O endereço referenceRatesProxy/api/pt-br/GetReferenceRates/ responde 404 hoje. Só o "
    "GetDownloadFile, do link “Histórico de arquivos”, continua de pé — e é o único "
    "usado aqui. O Search/GetList também foi descartado: ignora o parâmetro de data e "
    "devolve sempre a curva mais recente, disfarçada de histórico.":
        "The referenceRatesProxy/api/pt-br/GetReferenceRates/ address returns 404 today. "
        "Only GetDownloadFile, behind the “File history” link, is still up — and it is "
        "the only one used here. Search/GetList was dropped too: it ignores the date "
        "parameter and always returns the most recent curve, disguised as history.",


    # ------------------------------------- fragmentos de resultado (concatenados)
    "rendimento líquido de": "net return of",
    "a.a. equivalente": "p.a. equivalent",
    "alíquota ": "rate ",
    "produto isento": "tax-exempt product",
    "zerado após 30 dias": "zero after 30 days",
    "Dias corridos": "Calendar days",
    "no período": "over the period",
    "O padrão B3/CETIP trunca o fator diário do DI na 8ª casa decimal antes de acumular. Em":
        "The B3/CETIP standard truncates the daily DI factor at the 8th decimal before "
        "compounding. Over",
    "dias úteis isso dá uma diferença de": "business days that is a difference of",
    "sobre os": "on the",
    "aplicados": "invested",
    "Curvas disponíveis para": "Curves available for",


    # ------------------------------------------------------- CDI realizado
    "% do CDI — acumulado realizado (BCB)": "% of CDI — realized accrual (BCB)",
    "% do CDI — projetado": "% of CDI — projected",
    "CDI + spread — projetado": "CDI + spread — projected",
    "O CDI vem da série 4389 do Banco Central e o acúmulo é diário, sobre o que de "
    "fato aconteceu. Não há projeção, então o vencimento não passa de hoje.":
        "The CDI comes from the Central Bank's series 4389 and accrues daily, on what "
        "actually happened. There is no projection, so maturity cannot go past today.",
    "Acúmulo do CDI, dia a dia": "CDI accrual, day by day",
    "série 4389 do BCB": "BCB series 4389",
    "a": "to",
    "dias úteis": "business days",
    "Taxa no período": "Period return",
    "do CDI": "of CDI",
    "Valor base": "Base amount",
    "antes do acúmulo": "before accrual",
    "Valor calculado": "Accrued amount",
    "bruto, antes dos impostos": "gross, before tax",
    "O BCB publica o CDI com um dia de defasagem. Se a calculadora da B3 mostrar um "
    "fator um pouco maior, é porque ela já tem o fixing do último dia útil e a série "
    "ainda não.":
        "The Central Bank publishes CDI with a one-day lag. If B3's calculator shows a "
        "slightly larger factor, it is because it already has the last business day's "
        "fixing and the series does not.",
    "Data": "Date",
    "CDI (% a.a.)": "CDI (% p.a.)",
    "Hoje": "Today",
    "Limpar": "Clear",
    "Fechar": "Close",
    "Mês anterior": "Previous month",
    "Próximo mês": "Next month",
    "Abrir calendário": "Open calendar",


    # -------------------------------------------------------------- montador
    "Montar": "Build",
    "Montar swap": "Build a swap",
    "Estruturação": "Structuring",
    "Monte o swap ponta a ponta.": "Build the swap leg by leg.",
    "Escolha o que se recebe e o que se paga. As curvas necessárias são carregadas "
    "conforme a combinação, e cada perna desconta pela curva da sua própria moeda.":
        "Pick what you receive and what you pay. The curves you need are loaded to "
        "match the combination, and each leg discounts on its own currency's curve.",
    "Pontas": "Legs",
    "Ponta ativa (recebe)": "Receive leg",
    "Ponta passiva (paga)": "Pay leg",
    "Recebe": "Receive",
    "Paga": "Pay",
    "A ponta passiva, dada a ativa": "The pay leg, given the receive leg",
    "A ponta ativa, dada a passiva": "The receive leg, given the pay leg",
    "Montar e precificar": "Build and price",
    "taxa que zera o MtM": "the rate that zeroes the mark-to-market",
    "Escolha as duas pontas e monte a estrutura.":
        "Pick both legs and build the structure.",
    "Combinações que não fazem sentido — mesmo indexador dos dois lados, curvas de "
    "desconto incompatíveis — são recusadas com o motivo.":
        "Combinations that make no sense — same benchmark on both sides, incompatible "
        "discount curves — are rejected with the reason.",
    "Pré BRL": "BRL fixed",
    "CDI (± spread ou % do CDI)": "CDI (± spread or % of CDI)",
    "IPCA+ capitalizado": "Compounded IPCA+",
    "Pré USD + variação cambial": "USD fixed + FX variation",
    "Pré USD (desconto SOFR)": "USD fixed (SOFR discounting)",
    "Term SOFR ± spread": "Term SOFR ± spread",
    "Taxa pré (% a.a. 252)": "Fixed rate (% p.a. 252)",
    "Spread ou percentual": "Spread or percentage",
    "Taxa real (% a.a. 252)": "Real rate (% p.a. 252)",
    "Taxa pré USD (% a.a. 360)": "USD fixed rate (% p.a. 360)",
    "Spread (% a.a. 360)": "Spread (% p.a. 360)",
    "Taxa fixa em reais, exponencial 252, descontada pelo DI.":
        "Fixed BRL rate, compounded 252, discounted on the DI curve.",
    "Flutuante em reais. O spread é multiplicativo; o percentual incide sobre a taxa diária.":
        "Floating in BRL. The spread is multiplicative; the percentage applies to the "
        "daily rate.",
    "Principal e juros corrigidos pela inflação implícita das curvas.":
        "Principal and interest indexed by the break-even inflation from the curves.",
    "Taxa fixa em dólar, linear 360, descontada pelo cupom cambial.":
        "Fixed USD rate, linear 360, discounted on the onshore USD curve.",
    "Taxa fixa em dólar descontada pela própria curva SOFR.":
        "Fixed USD rate discounted on the SOFR curve itself.",
    "Flutuante em dólar sobre o Term SOFR. Spread aditivo.":
        "Floating in USD over Term SOFR. Additive spread.",
    "as duas pontas são iguais — um swap precisa de dois indexadores diferentes":
        "both legs are the same — a swap needs two different benchmarks",
    "as duas pontas são pré em dólar; muda só a curva de desconto, não o indexador":
        "both legs are USD fixed; only the discount curve differs, not the benchmark",
    "misturar cupom cambial e Term SOFR na mesma moeda desconta as pernas em curvas incompatíveis":
        "mixing the onshore USD rate and Term SOFR in the same currency discounts the "
        "legs on incompatible curves",
    "Mercado": "Market",


    # ------------------------------------------------------ fontes de dados
    "Lista com todos os feriados da ANBIMA": "Full list of ANBIMA holidays",
    "Já embutida no pacote em dados/feriados_anbima.json (2001-2099).":
        "Already embedded in the package at dados/feriados_anbima.json (2001-2099).",
    "Taxas Referenciais — modelo novo (fonte da extração automática)":
        "Reference rates — new site (source of the automatic extraction)",
    "A página é ruim de raspar, mas o endpoint GetDownloadFile por trás dela devolve o "
    "CSV do dia. É o que a aba Curvas usa.":
        "The page is painful to scrape, but the GetDownloadFile endpoint behind it "
        "returns the day's CSV. It is what the Curvas tab uses.",
    "Taxas Referenciais — modelo antigo (melhor para extrair, porém instável)":
        "Reference rates — legacy site (easier to scrape, but flaky)",
    "URL citada na aba Curvas da planilha de Pré USD × Pré BRL. Aceita "
    "?Data=dd/mm/aaaa&slcTaxa=PRE|DOC|DIC. Cai com frequência.":
        "URL cited in the Curvas tab of the USD fixed × BRL fixed spreadsheet. Accepts "
        "?Data=dd/mm/yyyy&slcTaxa=PRE|DOC|DIC. Goes down often.",
    "ANBIMA — estrutura a termo de CDI, juro real e inflação implícita":
        "ANBIMA — term structure of CDI, real rates and break-even inflation",
    "Curvas já prontas, boas para conferir a inflação implícita calculada a partir de PRE e DIC.":
        "Ready-made curves, useful to check the break-even inflation computed from PRE and DIC.",
    "Projeção de inflação da ANBIMA (IPCA-15 / IGP-M)":
        "ANBIMA inflation projection (IPCA-15 / IGP-M)",
    "É a projeção mensal que entra no NI pro-rata.":
        "It is the monthly projection that feeds the pro-rata index.",
    "Número-índice do IPCA (IBGE, tabela 1737)": "IPCA index number (IBGE, table 1737)",
    "NIk-1: o último número-índice publicado.": "NIk−1: the last published index number.",
    "VNA de títulos públicos (ANBIMA Data)":
        "Adjusted face value of government bonds (ANBIMA Data)",
    "Para conferir o VNA calculado na tela de NI pro-rata.":
        "To check the adjusted face value computed on the pro-rata index screen.",
    "Term SOFR e SOFR (CME Group)": "Term SOFR and SOFR (CME Group)",
    "Fonte da aba Dados CME.": "Source of the Dados CME tab.",
    "Curva Term SOFR atualizada diariamente (Pensford)":
        "Term SOFR curve updated daily (Pensford)",
    "Curva forward pronta e gratuita.": "A ready-made forward curve, free of charge.",
    "Futuro de SOFR 3 meses em tabela, com delay (Barchart)":
        "3-month SOFR futures in table form, delayed (Barchart)",
    "Os preços SR3 que alimentam o bootstrap da curva Term SOFR.":
        "The SR3 prices that feed the Term SOFR bootstrap.",
    "Futuro de SOFR 3 meses direto da CME": "3-month SOFR futures straight from CME",
    "Mesma informação, mais difícil de extrair.": "Same information, harder to extract.",
    "SOFR — New York Fed": "SOFR — New York Fed",
    "Taxa realizada, para o fixing.": "The realized rate, for the fixing.",
    "Histórico de preços e taxas dos títulos (Tesouro Direto)":
        "Historical bond prices and yields (Tesouro Direto)",
    "Confere o PU par da NTN-B.": "Cross-checks the par unit price of an NTN-B.",
    "Calculadora de renda fixa da B3": "B3 fixed income calculator",
    "Bate o cálculo de um papel isolado.": "Ties out the calculation of a single security.",
    "Estatísticas do Banco Central": "Central Bank statistics",
    "Séries de CDI, Selic e PTAX.": "CDI, Selic and PTAX series.",
    "ANBIMA Data — diretório de dados": "ANBIMA Data — data directory",


    # ---------------------------------- painel: módulos e decisões do porte
    "Feriados ANBIMA 2001-2099, WORKDAY e NETWORKDAYS−1":
        "ANBIMA holidays 2001-2099, WORKDAY and NETWORKDAYS−1",
    "Colunas de datas das planilhas": "The date columns of the spreadsheets",
    "Spline cúbica natural — a UDF cubic_spline, com o mesmo algoritmo do Numerical Recipes":
        "Natural cubic spline — the cubic_spline UDF, same algorithm as Numerical Recipes",
    "Aula - Interpolação de Dados": "Aula - Interpolação de Dados",
    "Download das Taxas Referenciais, base64 + CSV em Windows-1252":
        "Downloads the reference rates: base64 + CSV in Windows-1252",
    "Extrair Curvas da B3": "Extrair Curvas da B3",
    "Taxa spot, fator de desconto e FRA nas duas convenções":
        "Spot rate, discount factor and forward rate in both conventions",
    "Abas Curvas / Curva DI / Curva DAP": "Curvas / Curva DI / Curva DAP tabs",
    "Agenda, amortização, juros, valor futuro e valor presente":
        "Schedule, amortization, interest, future value and present value",
    "Colunas 3 a 7 das abas de swap": "Columns 3 to 7 of the swap tabs",
    "O Atingir Meta que as macros chamavam para achar a taxa par":
        "The Goal Seek the macros called to find the par rate",
    "GoalSeek dos módulos VBA": "GoalSeek in the VBA modules",

    "A curva é interpolada em dias corridos": "The curve is interpolated on calendar days",
    "A planilha de Pré USD × Pré BRL interpola a curva num valor de dias úteis, mas o "
    "eixo dessa curva vai até 12.556 — é calendário. Interpolar 126 em vez de 183 "
    "devolve a taxa de um prazo mais curto. A planilha de IPCA traz a fórmula certa, "
    "cubic_spline(Curvas!A:A; Curvas!B:B; DC total), e é essa que o pacote segue. A "
    "diferença chega a 15 bp no vértice de seis meses.":
        "The USD fixed × BRL fixed spreadsheet interpolates the curve at a business-day "
        "value, but that curve's axis runs to 12,556 — those are calendar days. "
        "Interpolating 126 instead of 183 returns the rate for a shorter tenor. The IPCA "
        "spreadsheet has the right formula, cubic_spline(Curvas!A:A; Curvas!B:B; total "
        "calendar days), and that is the one the package follows. The gap reaches 15 bp "
        "at the six-month pillar.",
    "Fora do domínio, a curva trava na ponta":
        "Beyond the pillars, the curve goes flat",
    "A UDF do VBA extrapola o polinômio cúbico, o que num prazo além do último vértice "
    "pode devolver qualquer coisa. O padrão aqui é travar no último valor publicado; a "
    "extrapolação cúbica continua disponível na tela de interpolação, para reproduzir "
    "número de planilha.":
        "The VBA UDF extrapolates the cubic polynomial, which beyond the last pillar can "
        "return anything at all. The default here is to hold the last published value; "
        "cubic extrapolation is still available on the interpolation screen, to "
        "reproduce a spreadsheet number.",
    "O endpoint GetReferenceRates saiu": "The GetReferenceRates endpoint is gone",
    "A planilha do collar Garman-Kohlhagen busca DI1 e DDI em "
    "referenceRatesProxy/api/pt-br/GetReferenceRates/. Esse endereço responde 404 hoje. "
    "Só o GetDownloadFile, do link “Histórico de arquivos”, continua de pé — e é o único "
    "usado aqui. O Search/GetList também foi descartado: ele ignora o parâmetro de data "
    "e devolve sempre a curva mais recente.":
        "The Garman-Kohlhagen collar spreadsheet fetches DI1 and DDI from "
        "referenceRatesProxy/api/pt-br/GetReferenceRates/. That address returns 404 "
        "today. Only GetDownloadFile, behind the “File history” link, is still up — and "
        "it is the only one used here. Search/GetList was dropped too: it ignores the "
        "date parameter and always returns the most recent curve.",

    "módulo CurvasB3 — endpoint, base64, CSV em Windows-1252, calendário de feriados por "
    "cálculo de Páscoa":
        "the CurvasB3 module — endpoint, base64, Windows-1252 CSV, holiday calendar "
        "derived from the Easter calculation",
    "UDF cubic_spline, spline natural do Numerical Recipes":
        "the cubic_spline UDF, the Numerical Recipes natural spline",
    "cross-currency e Pré BRL × CDI ± spread; feriados ANBIMA 2001-2099":
        "cross-currency and BRL fixed × CDI ± spread; ANBIMA holidays 2001-2099",
    "inflação implícita, FRA de DAP, NI pro-rata, VNA":
        "break-even inflation, DAP forward rates, pro-rata index, adjusted face value",
    "bootstrap de futuros SR3 em datas IMM, calendário US+BR":
        "SR3 futures bootstrap on IMM dates, US+BR calendar",
    "segunda implementação da spline e os endpoints DI1/DDI hoje fora do ar":
        "a second spline implementation and the DI1/DDI endpoints that are now down",


    # ------------------------------------------------------------ glossário
    "DU — dias úteis": "BD — business days",
    "Dias em que há pregão, pelo calendário escolhido. Base 252 ao ano.":
        "Days the market is open, on the chosen calendar. 252 basis per year.",
    "Contados como NETWORKDAYS − 1: o dia inicial não entra.":
        "Counted as NETWORKDAYS − 1: the start date does not count.",
    "DC — dias corridos": "CD — calendar days",
    "Dias de calendário puros, fim de semana e feriado incluídos. Base 360 ou 365.":
        "Plain calendar days, weekends and holidays included. 360 or 365 basis.",
    "O cupom cambial e o SOFR usam DC/360; o prazo médio usa DC/365.":
        "The onshore USD rate and SOFR use CD/360; weighted average life uses CD/365.",
    "Capitalização (1 + i)^(DU/252). Convenção de tudo que é em reais: DI, IPCA, TR.":
        "Compounding as (1 + i)^(BD/252). The convention for everything in reais: DI, IPCA, TR.",
    "Linear 360": "Linear 360",
    "Capitalização 1 + i · DC/360. Convenção do que é em dólar: cupom cambial, Term SOFR, pré em dólar.":
        "Accrual as 1 + i · CD/360. The convention for dollar instruments: onshore USD "
        "rate, Term SOFR, USD fixed.",
    "Following / Modified following": "Following / Modified following",
    "Regra para levar um vencimento que cai em dia não útil para um dia útil. Following "
    "empurra para frente; modified following também, salvo se isso virar o mês — aí "
    "volta para trás.":
        "The rule that moves a payment date falling on a non-business day. Following "
        "rolls forward; modified following also rolls forward unless that crosses into "
        "the next month, in which case it rolls back.",
    "Modified following é o padrão de mercado.":
        "Modified following is the market standard.",
    "Vértice": "Pillar",
    "Um prazo com taxa publicada pela B3. A curva é a interpolação entre eles.":
        "A tenor with a rate published by B3. The curve is the interpolation between them.",
    "Taxa spot (zero)": "Spot (zero) rate",
    "Taxa de hoje até o vencimento, sem pagamento no meio. É o que a curva publica.":
        "The rate from today to maturity with no intermediate payment. It is what the "
        "curve publishes.",
    "FRA — taxa a termo": "FRA — forward rate",
    "Taxa implícita entre dois vencimentos futuros. Sai da razão dos fatores de "
    "capitalização: ((1+i₂)^(DU₂/252) / (1+i₁)^(DU₁/252))^(252/(DU₂−DU₁)) − 1.":
        "The rate implied between two future dates. It comes from the ratio of "
        "compounding factors: ((1+i₂)^(BD₂/252) / (1+i₁)^(BD₁/252))^(252/(BD₂−BD₁)) − 1.",
    "Fator de desconto": "Discount factor",
    "O inverso do fator de capitalização — quanto vale hoje R$ 1 pago no vencimento.":
        "The inverse of the compounding factor — what R$ 1 paid at maturity is worth today.",
    "Spline cúbica natural": "Natural cubic spline",
    "Interpolação suave que passa por todos os vértices, com a segunda derivada zerada "
    "nas pontas. É a UDF cubic_spline das planilhas.":
        "A smooth interpolation through every pillar, with the second derivative set to "
        "zero at both ends. ",
    "Flat-forward": "Flat forward",
    "Interpolação que mantém a taxa a termo constante entre vértices. Alternativa à "
    "spline, garante forwards não-negativos.":
        "Interpolation that holds the forward rate constant between pillars. An "
        "alternative to the spline; it guarantees non-negative forwards.",
    "Contra qual prazo a curva é interpolada — dias úteis ou dias corridos. Consultar "
    "no eixo errado devolve a taxa de outro prazo.":
        "Which tenor the curve is interpolated against — business or calendar days. "
        "Querying on the wrong axis returns the rate for a different tenor.",
    "Consultar no eixo errado é um erro silencioso: devolve um número plausível.":
        "Querying on the wrong axis fails silently: it returns a plausible number.",
    "DV01": "DV01",
    "Variação do MtM para um deslocamento paralelo de 1 ponto-base na curva.":
        "The change in mark-to-market for a 1 basis point parallel shift of the curve.",
    "DI / CDI": "DI / CDI",
    "Taxa dos depósitos interfinanceiros de um dia. A curva DI × Pré da B3 é a estrutura "
    "a termo dela.":
        "The overnight interbank deposit rate. B3's DI × Pré curve is its term structure.",
    "DI é o futuro negociado; CDI é a taxa apurada. No swap, dão no mesmo.":
        "DI is the traded future; CDI is the published fixing. In a swap they amount to "
        "the same thing.",
    "CDI ± spread": "CDI ± spread",
    "Remuneração multiplicativa: (1 + CDI)·(1 + spread) = (1 + pré). Somar o spread ao "
    "CDI é o erro que a planilha marca em vermelho.":
        "Multiplicative remuneration: (1 + CDI)·(1 + spread) = (1 + fixed). Adding the "
        "spread to CDI is the mistake the spreadsheet flags in red.",
    "Percentual aplicado sobre a taxa **diária**, não sobre a anual: [1 + ((1+CDI)^(1/252) − 1)·p]^DU.":
        "A percentage applied to the **daily** rate, not the annual one: "
        "[1 + ((1+CDI)^(1/252) − 1)·p]^BD.",
    "A 14% ao ano, 110% do CDI dá 15,5031% — não os 15,40% do cálculo ingênuo.":
        "At 14% a year, 110% of CDI gives 15.5031% — not the 15.40% of the naive "
        "calculation.",
    "Cupom cambial limpo (DOC)": "Clean FX coupon (DOC)",
    "Juro em dólar dentro do Brasil, já sem o efeito do casado. É a curva que desconta "
    "fluxo em dólar num cross-currency.":
        "The onshore dollar rate in Brazil, already stripped of the casado. It is the "
        "curve that discounts dollar flows in a cross-currency swap.",
    "Cupom cambial sujo (DDI)": "Dirty FX coupon (DDI)",
    "O mesmo juro, mas com a PTAX D−1 embutida. Difere do limpo pelo casado.":
        "The same rate, but with the D−1 PTAX embedded. It differs from the clean one "
        "by the casado.",
    "IPCA+ / juro real": "IPCA+ / real rate",
    "Taxa real contratada acima da inflação. A inflação implícita sai de (1 + DI)/(1 + DI×IPCA) − 1.":
        "The real rate contracted above inflation. Break-even inflation comes from "
        "(1 + DI)/(1 + DI×IPCA) − 1.",
    "NI — número-índice": "NI — index number",
    "O índice de preços acumulado que corrige o principal de um papel IPCA+.":
        "The accumulated price index that adjusts the principal of an IPCA+ instrument.",
    "Entre os dias 15 é interpolado pro rata em dias úteis.":
        "Between the 15th of each month it is interpolated pro rata on business days.",
    "VNA / VNE": "VNA / VNE",
    "Valor Nominal Atualizado é o VNE (valor de emissão) corrigido pelo NI.":
        "The adjusted face value is the issue face value indexed by the NI.",
    "SOFR": "SOFR",
    "Taxa overnight garantida em dólar, publicada pelo Fed de Nova York. "
    "Backward-looking: só fecha no fim do período.":
        "The secured overnight dollar rate published by the New York Fed. "
        "Backward-looking: it only settles at the end of the period.",
    "Term SOFR": "Term SOFR",
    "Versão forward-looking do SOFR, cotada pela CME em 1, 3, 6 e 12 meses. É conhecida "
    "no início do período.":
        "The forward-looking version of SOFR, quoted by CME at 1, 3, 6 and 12 months. "
        "It is known at the start of the period.",
    "Lookback (lag)": "Lookback (lag)",
    "Observa a taxa de k dias úteis antes, mas pesa pelos dias do período de juros.":
        "Observes the rate from k business days earlier, but weights by the days of the "
        "accrual period.",
    "Observation shift": "Observation shift",
    "Desloca a janela inteira k dias úteis para trás, pesos inclusive. É a convenção que "
    "fecha exatamente com o SOFR Index.":
        "Shifts the whole window back k business days, weights included. It is the "
        "convention that ties out exactly with the SOFR Index.",
    "Swap": "Swap",
    "Troca de fluxos entre duas pontas. Aqui a ponta ativa é a que se recebe e a passiva "
    "a que se paga.":
        "An exchange of cash flows between two legs. Here the active leg is the one you "
        "receive and the passive leg the one you pay.",
    "MtM — marcação a mercado": "MtM — mark-to-market",
    "Diferença entre o valor presente das duas pontas. Zero é o swap justo.":
        "The difference between the present value of the two legs. Zero is a fair swap.",
    "Taxa par": "Par rate",
    "A taxa que zera o MtM — o que o solver procura.":
        "The rate that zeroes the mark-to-market. It is what Goal Seek looked for in the "
        "spreadsheets.",
    "Cross-currency swap": "Cross-currency swap",
    "Swap com as pontas em moedas diferentes. Cada fluxo desconta pela curva da sua "
    "moeda — nunca pela mesma.":
        "A swap with legs in different currencies. Each flow discounts on its own "
        "currency's curve — never on the same one.",
    "NDF": "NDF",
    "Contrato a termo de moeda liquidado por diferença. O preço sai da paridade coberta "
    "de juros: spot · (1+DI)^(DU/252) / (1 + cupom·DC/360).":
        "A non-deliverable currency forward settled by difference. The price comes from "
        "covered interest parity: spot · (1+DI)^(BD/252) / (1 + coupon·CD/360).",
    "Pontos de NDF": "Forward points",
    "Diferença entre o termo e o spot, em pips: (NDF − spot) × 10.000.":
        "The difference between forward and spot, in pips: (NDF − spot) × 10,000.",
    "Casado": "Casado (spot vs. 1st future)",
    "Diferença entre o primeiro futuro de dólar e o spot.":
        "The difference between the first dollar future and spot.",
    "Rolagem": "Roll (future-to-future)",
    "Diferença entre o segundo e o primeiro futuro de dólar, em pips.":
        "The difference between the second and the first dollar future, in pips.",
    "Bullet": "Bullet",
    "Amortização única, no vencimento. Os juros podem ou não ter cupom no meio.":
        "A single principal repayment at maturity. Interest may or may not pay coupons "
        "along the way.",
    "Prazo médio × duration": "Weighted average life vs. duration",
    "Prazo médio pondera pelo principal amortizado; duration pondera pelo valor presente "
    "do fluxo inteiro. Num bullet com cupom, a duration é menor.":
        "Weighted average life weights by principal repaid; duration weights by the "
        "present value of the whole flow. On a bullet with coupons, duration is shorter.",
    "Fator diário do DI": "Daily DI factor",
    "(1 + DI)^(1/252). O padrão B3/CETIP arredonda na 8ª casa antes de acumular; aqui o "
    "padrão é não arredondar.":
        "(1 + DI)^(1/252). The B3/CETIP standard rounds it at the 8th decimal before "
        "compounding; here the default is not to round.",
    "Em cinco anos a diferença chega à casa dos reais por milhão.":
        "Over five years the difference reaches a few reais per million.",
    "IR regressivo": "Regressive withholding tax",
    "22,5% até 180 dias, 20% até 360, 17,5% até 720, 15% acima disso — sobre o "
    "rendimento, não sobre o principal.":
        "22.5% up to 180 days, 20% to 360, 17.5% to 720, 15% beyond that — on the "
        "return, not on the principal.",
    "Incide só em resgate com menos de 30 dias corridos, de 96% a 0% do rendimento.":
        "Applies only to redemptions inside 30 calendar days, from 96% down to 0% of the "
        "return.",
    "PU — preço unitário": "PU — unit price",
    "Valor presente de um título por unidade.":
        "The present value of one unit of a security.",


    # ------------------------------------------------- curvas e produtos B3
    "DI x Pré": "DI x Pré (BRL nominal)",
    "Cupom Cambial Limpo": "Clean FX coupon (onshore USD)",
    "DI x IPCA": "DI x IPCA (real rate)",
    "DI x TR": "DI x TR",
    "Real x Dólar": "BRL/USD",
    "Real x Euro": "BRL/EUR",
    "Real x Iene": "BRL/JPY",
    "Juros nominais em reais, exponencial 252":
        "Nominal BRL rates, compounded on 252 business days",
    "Cupom cambial limpo (DOC), linear 360":
        "Clean FX coupon (DOC), linear 360 — the onshore USD rate",
    "Juro real, exponencial 252": "Real rate, compounded on 252 business days",
    "Exponencial 252": "Compounded on 252 business days",
    "Cupom de dólar": "USD coupon",
    "Cupom de euro": "EUR coupon",
    "Cupom de iene": "JPY coupon",

    "Pré BRL × CDI ± spread": "BRL fixed × CDI ± spread",
    "Pré USD × Pré BRL": "USD fixed × BRL fixed (cross-currency)",
    "Pré USD × CDI ± spread": "USD fixed × CDI ± spread",
    "IPCA capitalizado × CDI ± spread": "Compounded IPCA × CDI ± spread",
    "Pré USD × Term SOFR ± spread": "USD fixed × Term SOFR ± spread",
    "Uma curva só. O spread é multiplicativo: (1+CDI)·(1+spread) = (1+pré).":
        "A single curve. The spread is multiplicative: (1+CDI)·(1+spread) = (1+fixed).",
    "Cross-currency. Fluxo em reais desconta no DI, fluxo em dólar no cupom cambial.":
        "Cross-currency. BRL flows discount on DI, USD flows on the onshore USD rate.",
    "Cross-currency com a ponta em reais flutuante. Duas curvas de desconto, spread multiplicativo.":
        "Cross-currency with a floating BRL leg. Two discount curves, multiplicative spread.",
    "Inflação implícita de (1+DI)/(1+DI×IPCA)−1, capitalizada por período.":
        "Break-even inflation from (1+DI)/(1+DI×IPCA)−1, compounded per period.",
    "Bootstrap dos futuros SR3 em datas IMM. Spread aditivo, linear 360.":
        "Bootstrapped from SR3 futures on IMM dates. Additive spread, linear 360.",

    # ---------------------------------------------------- opções de formulário
    "Mensal": "Monthly", "Trimestral": "Quarterly", "Semestral": "Semi-annual",
    "Anual": "Annual", "Diária": "Daily", "Semanal": "Weekly",
    "Sem cupom (zero cupom)": "No coupon (zero coupon)",
    "Bullet — principal no vencimento": "Bullet — principal at maturity",
    "Linear — amortização constante": "Straight line — equal principal",
    "Personalizada (% por período)": "Custom (% per period)",
    "Following — próximo dia útil": "Following — next business day",
    "Modified following — próximo dia útil, sem virar o mês":
        "Modified following — next business day, without rolling into the next month",
    "Preceding — dia útil anterior": "Preceding — previous business day",
    "Modified preceding — dia útil anterior, sem virar o mês":
        "Modified preceding — previous business day, without rolling back a month",
    "Unadjusted — não ajusta": "Unadjusted — no roll",
    "Sem defasagem — observa o próprio período":
        "No lookback — observes the accrual period itself",
    "Lookback (lag) — taxa defasada, peso do período de juros":
        "Lookback — lagged rate, weighted by the accrual period",
    "Observation shift — janela inteira deslocada":
        "Observation shift — the whole window is shifted back",
    "Prefixado (% a.a. 252)": "Fixed rate (% p.a. 252)",
    "% do CDI": "% of CDI",
    "CDI + spread": "CDI + spread",
    "IPCA + taxa real": "IPCA + real rate",
    "CDB / RDB": "CDB / RDB (bank deposit)",
    "LCI / LCA": "LCI / LCA (real estate / agri note)",
    "CRI / CRA": "CRI / CRA (securitised receivable)",
    "Debênture comum": "Corporate debenture",
    "Debênture incentivada": "Tax-exempt infrastructure debenture",
    "Tesouro Direto": "Brazilian government bond",
    "LIG": "LIG (covered bond)",
    "isento": "tax exempt",
    "vértices": "pillars",

    # --------------------------------------------- metodologia: convenções
    "Juros em reais": "BRL interest",
    "Juros em dólar": "USD interest",
    "exponencial 252": "compounded 252",
    "linear 360": "linear 360",
    "Spread sobre CDI": "Spread over CDI",
    "multiplicativo": "multiplicative",
    "Spread sobre SOFR": "Spread over SOFR",
    "aditivo": "additive",
    "spline cúbica natural": "natural cubic spline",
    "Eixo da curva": "Curve axis",
    "segunda derivada = 0 nas pontas": "second derivative = 0 at both ends",
    "DI, IPCA e TR. DU pelo calendário ANBIMA, contando NETWORKDAYS − 1.":
        "DI, IPCA and TR. Business days on the ANBIMA calendar, counted as NETWORKDAYS − 1.",
    "Cupom cambial, pré USD e Term SOFR. DC é dia de calendário puro.":
        "Onshore USD rate, USD fixed and Term SOFR. Calendar days, plain and simple.",
    "Somar o spread ao CDI é erro.":
        "Adding the spread to CDI is simply wrong.",
    "Praxe do mercado de dólar. Diferente do CDI de propósito.":
        "Standard in the dollar market. Deliberately unlike CDI.",
    "Cupom cambial usa linear, como a B3 publica.":
        "A port of the cubic_spline UDF. The FX coupon uses linear, as B3 publishes it.",
    "O desconto, porém, é em dias úteis. São eixos diferentes de propósito.":
        "Discounting, however, runs on business days. Two different axes, on purpose.",
    "taxa = f(DC)": "rate = f(calendar days)",

    # ---------------------------------------------------- glossário: grupos
    "Contagem de dias": "Day count",
    "Curvas": "Curves",
    "Indexadores": "Benchmarks",
    "Produtos": "Products",
    "Renda fixa": "Fixed income",
    "Calendário": "Calendar",
    "Curvas B3": "B3 curves",
    "Inflação": "Inflation",
    "Dólar e SOFR": "Dollar and SOFR",
    "Conferência": "Cross-checking",


    # -------------------------------------- rótulos de estatística e sufixos
    "Vértices": "Curve pillars",
    "Prazo máximo": "Longest pillar",
    "Ponta longa": "Long end",
    "Extrair": "Pull",
    "Baixar CSV": "Download CSV",
    "MtM (diferença de VPs)": "Mark-to-market (PV difference)",
    "Prazo médio": "Weighted average life",
    "ponderado pela amortização": "weighted by principal repaid",
    "Duration": "Macaulay duration",
    "Macaulay, sobre o VP": "on present value",
    "VP ponta ativa": "PV — receive leg",
    "VP ponta passiva": "PV — pay leg",
    "Períodos": "Periods",
    "pagamentos no cronograma": "payments in the schedule",
    "Data-base": "Base date",
    "D−1": "D−1",
    "1º futuro − spot×1.000": "1st future − spot×1,000",
    "(2º − 1º futuro) × 10": "(2nd − 1st future) × 10",
    "Fator acumulado": "Compounded factor",
    "produto dos fatores diários": "product of the daily factors",
    "Média simples ponderada": "Weighted simple average (non-compounded)",
    "sem capitalização": "without compounding",
    "Dias úteis observados": "Business days observed",
    "fixings usados": "fixings used",
    "Defasagem": "Lookback",
    "Dias úteis": "Business days",
    "dias corridos": "calendar days",
    "Taxa bruta equivalente": "Equivalent gross yield",
    "ao ano, base 252": "per year, 252 basis",
    "IR": "Withholding tax (IR)",
    "IOF": "IOF (transaction tax)",
    "NI atual (pro-rata)": "Current index (pro-rata)",
    "interpolado em dias úteis": "interpolated on business days",
    "NI cheio (projetado)": "Full index (projected)",
    "NIk−1 × (1 + projeção)": "NIk−1 × (1 + projection)",
    "Próxima base": "Next base",
    "dia 15 de referência": "reference 15th",
    "dia 15 do mês seguinte": "15th of the next month",
    "dup": "dup",
    "dut": "dut",
    "dias úteis decorridos": "business days elapsed",
    "dias úteis do período": "business days in the period",
    "pontos na curva": "points on the curve",
    "Domínio": "Range",
    "Interpolar": "Interpolate",
    "Compor": "Compound",
    "Calcular": "Calculate",
    "Montar curva": "Build the curve",
    "calendário ": "calendar ",
    "data-base ": "base date ",
    "interpolação: ": "interpolation: ",
    "em ": "at ",
    "rendimento de ": "return of ",
    "rendimento de R$ ": "return of R$ ",
    "linhas no arquivo da B3": "rows in the B3 file",
    'Moeda': 'Currency',
    'Dólar': 'US dollar',
    'Euro': 'Euro',
    'Iene': 'Japanese yen',
    'Euro contra dólar': 'Euro against dollar',
    'Outra moeda': 'Other currency',
    'Non Deliverable Forward.': 'Non deliverable forward.',
    'NDF fx curve': 'NDF fx curve',
    'Juro da moeda': 'Currency rate',
    'juro da moeda': 'currency rate',
    'Juro da moeda estrangeira (% a.a., linear 360)': 'Foreign currency rate (% p.a., act/360)',
    'Escolha a moeda, informe o spot e monte a escada de vencimentos.': 'Pick the currency, enter the spot and build the maturity ladder.',
    'As curvas da moeda escolhida são baixadas da B3 para a data-base.': 'The curves for the chosen currency are downloaded from B3 for the base date.',
    'Paridade coberta de juros com as curvas da B3: DI exponencial em dias úteis no numerador, o juro da moeda escolhida linear em dias corridos no denominador. Trocar a moeda troca a curva e a convenção que descontam a ponta estrangeira.': "Covered interest parity on the B3 curves: DI compounded over business days in the numerator, the chosen currency's rate linear over calendar days in the denominator. Each currency brings its own grid of tenors.",
    'A B3 publica o iene a termo com duas casas decimais — a curva inteira sai em R$ 0,03 por iene. O cupom implícito que vem dela é indicativo, não preço; para fechar contrato, digite a taxa em iene no modo de moeda livre.': 'B3 publishes the yen forward to two decimal places — the whole curve prints at R$ 0.03 per yen. The coupon implied from it is indicative, not a price; to strike a trade, type the yen rate under the free-currency mode.',
    'Cross derivado das duas curvas de preço da B3: euro a termo dividido por dólar a termo. Não passa pelo DI — as duas pontas já estão em reais e o real cancela.': "A cross derived from B3's two price curves: euro forward divided by dollar forward. The DI never enters — both legs are already in reais and the real cancels out.",
    'Libra, franco, peso, dólar canadense: a B3 não publica cupom para nenhuma delas. O DI entra da curva e o juro da moeda estrangeira entra digitado, linear em 360 dias.': 'Sterling, franc, peso, Canadian dollar: B3 publishes no coupon curve for any of them. The DI comes off the curve and the foreign rate is typed in, linear over 360 days.',
    'euro a termo': 'euro forward',
    'dólar a termo': 'dollar forward',
    "SOFR Index, composto direto do Fed.": "SOFR Index, compounded straight from the Fed.",
    "SOFR Index": "SOFR Index",
    "nenhuma": "none",
    "Sem defasagem": "No lag",
    "Lookback de {lookback} dias úteis": "{lookback}-business-day lookback",
    "Observation shift de {shift} dias úteis": "{shift}-business-day observation shift",
    "Lookback {lookback} du com observation shift {shift} du": "{lookback}-day lookback with {shift}-day observation shift",
    "último fixing publicado": "last published fixing",
    "Conferência pelo SOFR Index oficial": "Checked against the official SOFR Index",
    "diferença de": "a difference of",
    'PTAX de fechamento': 'Closing PTAX',
    'Vem da âncora curta da curva de preço da B3, que é o ponto de onde ela constrói o termo — arredondada em duas casas. O spot D+2 interbancário não tem fonte pública: sobrescreva com a cotação de tela quando tiver.': "Taken from the short anchor of B3's price curve — the point it builds the forward from — rounded to two decimals. The interbank D+2 spot has no public feed: overwrite it with your screen quote when you have one.",
    'A média que o Banco Central apura em quatro janelas e publica às 13h. É contra ela que o NDF liquida no vencimento — não é o spot com que ele é precificado.': 'The average the central bank samples across four windows and publishes at 1pm. It is what the NDF settles against at maturity — not the spot it is priced off.',
    'Proxy de saída': 'Outbound proxy',
    'O que o Windows tem configurado': 'What Windows has configured',
    'A saída é resolvida por um arquivo PAC, que é um script e escolhe o proxy por destino — nem o urllib nem o requests sabem interpretá-lo. Abra a URL acima, leia o endereço do proxy e informe-o em PRECIFICADOR_PROXY.': 'Egress is resolved by a PAC file, which is a script that picks the proxy per destination — neither urllib nor requests can interpret it. Open the URL above, read the proxy address and set it in PRECIFICADOR_PROXY.',
    'Testar as fontes': 'Test the sources',
    'Bate em cada fonte e diz o que aconteceu. Todas falhando com timeout é bloqueio de saída; uma só falhando é a fonte.': 'Hits each source and reports what happened. All of them timing out means egress is blocked; a single one failing means that source.',
    'Proxy visto por este processo': 'Proxy seen by this process',
    'Nenhuma variável de proxy neste processo': 'No proxy variable in this process',
    'A estação pode ter o proxy configurado e este processo não enxergá-lo: variável definida no perfil de um terminal não chega ao cmd que o .bat abre. Defina antes de subir, ou grave de vez com setx.': "The workstation may have a proxy configured that this process cannot see: a variable set in one terminal's profile never reaches the cmd the .bat opens. Set it before starting, or make it permanent with setx.",

    # ----------------------------------------------------- liquidação de swap
    "Liquidação": "Settlement",
    "Liquidação de swap": "Swap settlement",
    "O ajuste que muda de mãos.": "The payment that changes hands.",
    "Índice realizado, não projeção: o CDI vem dia a dia do Banco Central e a "
    "variação cambial vem da PTAX publicada. As duas pontas rendem sobre o notional "
    "remanescente e só a diferença liquida.":
        "Realised indices, not forecasts: CDI comes day by day from the central bank "
        "and the currency move comes from published PTAX. Both legs accrue on the "
        "outstanding notional and only the difference settles.",
    "Calcular a liquidação": "Settle",
    "Informe as datas, o saldo remanescente e o indexador de cada ponta.":
        "Enter the dates, the outstanding balance and each leg's index.",

    "A operação": "The trade",
    "Data da operação": "Trade date",
    "Início do fluxo": "Flow start",
    "Fim do fluxo": "Flow end",
    "A data da operação conta o prazo do IR; o fluxo é onde os índices acumulam.":
        "The trade date sets the withholding-tax horizon; the flow is where the "
        "indices accrue.",

    "O principal": "The principal",
    "Notional remanescente (R$)": "Outstanding notional (BRL)",
    "Notional original (R$)": "Original notional (BRL)",
    "Notional remanescente": "Outstanding notional",
    "Notional original": "Original notional",
    "A base que rende — é este valor que multiplica o fator das duas pontas.":
        "The base that accrues — this is the figure both legs' factors multiply.",
    "O valor de registro, só para calcular a amortização sobre ele.":
        "The registered amount, used only to size the amortisation against it.",
    "Amortização no fim do fluxo (%)": "Amortisation at flow end (%)",
    "Amortização incide sobre": "Amortisation applies to",
    "Sobre o valor original — parcela constante":
        "The original amount — constant instalment",
    "Sobre o saldo remanescente — parcela decrescente":
        "The outstanding balance — declining instalment",
    "sobre o valor original": "of the original amount",
    "sobre o saldo remanescente": "of the outstanding balance",
    "O caminho do principal": "How the principal moves",
    "A amortização acontece no fim do fluxo: ela não entra no fator deste período, "
    "que rendeu sobre o saldo de abertura. Ela define o saldo do fluxo seguinte.":
        "Amortisation happens at flow end: it does not enter this period's factor, "
        "which accrued on the opening balance. It sets the next flow's balance.",
    "Etapa": "Stage",
    "registro": "registered",
    "abertura do fluxo": "flow opening",
    "abertura do próximo fluxo": "next flow's opening",
    "Saldo seguinte": "Next balance",
    "Saldo após a amortização": "Balance after amortisation",
    "amortiza R$ ": "amortises BRL ",
    "sem amortização neste fluxo": "no amortisation in this flow",
    "base das duas pontas": "base of both legs",

    "As duas pontas": "The two legs",
    "Ponta ativa — quem recebe o índice": "Receiving leg — receives the index",
    "Ponta passiva — quem paga o índice": "Paying leg — pays the index",
    "Taxa contratada ou spread": "Contracted rate or spread",
    "Pré — taxa fixa ao ano": "Fixed — rate per annum",
    "CDI — % do CDI realizado": "CDI — % of realised CDI",
    "CDI + spread realizado": "Realised CDI + spread",
    "Variação cambial + cupom": "Currency move + coupon",
    "SOFR composto realizado + spread": "Realised compounded SOFR + spread",
    "Term SOFR do fixing + spread": "Term SOFR fixing + spread",
    "EURIBOR do fixing + spread": "EURIBOR fixing + spread",
    "IPCA por número-índice + cupom real": "IPCA by index number + real coupon",
    "Equity — ação ou índice, por variação de preço":
        "Equity — a stock or index, by price move",
    "Fator acumulado digitado": "Accrued factor, typed in",
    "O fator que veio na confirmação, sem recalcular nada.":
        "The factor as it came on the confirmation, with nothing recalculated.",

    "Moeda do fluxo": "Flow currency",
    "Fixing inicial da moeda": "Opening currency fixing",
    "Fixing final da moeda": "Closing currency fixing",
    "PTAX, busca sozinha": "PTAX, fetched automatically",
    "Em branco, os dois vêm da PTAX de fechamento do dia útil anterior a cada data. "
    "Em reais, não há conversão.":
        "Left blank, both come from the closing PTAX of the business day before each "
        "date. In reais there is no conversion.",
    "Real — fluxo já em reais, sem conversão":
        "Real — flow already in reais, no conversion",
    "Dólar dos Estados Unidos": "US dollar",
    "Dólar canadense": "Canadian dollar",
    "Dólar australiano": "Australian dollar",
    "Coroa dinamarquesa": "Danish krone",
    "Coroa norueguesa": "Norwegian krone",
    "Coroa sueca": "Swedish krona",
    "Yuan offshore": "Offshore yuan",
    "Yuan onshore": "Onshore yuan",
    "fixing digitado": "fixing typed in",
    "Moeda — só a variação cambial": "Currency — the currency move alone",
    "Acúmulo do SOFR, dia a dia": "SOFR accrual, day by day",
    "SOFR do Fed de Nova York": "SOFR from the New York Fed",
    "SOFR (% a.a.)": "SOFR (% p.a.)",
    "janela de observação": "observation window",
    "Observação": "Observation",
    "variação de {variacao}%, sem cupom": "a {variacao}% currency move, no coupon",
    "Só a variação da moeda entre as duas datas, sem cupom e sem índice. Não há taxa "
    "para capitalizar, então contagem de dias e regime não se aplicam.":
        "Just the currency move between the two dates, with no coupon and no index. "
        "There is no rate to compound, so day count and regime do not apply.",
    "O Banco Central boletina dez moedas; nas de fora dela — o yuan, por exemplo — os "
    "dois fixings entram digitados.":
        "The central bank publishes ten currencies; outside that list — the yuan, for "
        "one — both fixings are typed in.",
    "Libra esterlina": "Pound sterling",
    "Franco suíço": "Swiss franc",

    "Prazo do fixing": "Fixing tenor",
    "Data do fixing": "Fixing date",
    "Taxa do fixing (% a.a.)": "Fixing rate (% p.a.)",
    "Taxa a termo: fixada antes de o fluxo começar. Em branco, a data do fixing é "
    "D-2 dias úteis do início.":
        "A forward-looking rate, set before the flow starts. Left blank, the fixing "
        "date is two business days before the start.",
    "O Term SOFR é administrado pela CME e licenciado — não há fonte pública que "
    "permita redistribuí-lo, então a taxa do fixing entra digitada.":
        "Term SOFR is administered by CME and licensed — no public source allows "
        "redistributing it, so the fixing rate is typed in.",
    "Lookback (dias úteis)": "Lookback (business days)",
    "Observation shift (dias úteis)": "Observation shift (business days)",
    "O SOFR composto olha para trás: ele acumula os fixings do próprio período, sem "
    "data de fixação.":
        "Compounded SOFR looks backwards: it accrues the period's own fixings, with "
        "no fixing date.",

    "Número-índice inicial": "Opening index number",
    "Número-índice final": "Closing index number",
    "Ação ou índice": "Stock or index",
    "Preço inicial": "Opening price",
    "Preço final": "Closing price",
    "Preço": "Price",
    "Moeda de cotação": "Quotation currency",
    "Quanto — sem conversão cambial": "Quanto — no currency conversion",
    "A ponta rende a variação de preço no período e liquida em reais como número "
    "puro. A moeda acima diz em que régua o preço está cotado; ela não entra na "
    "conta. Quem quer a variação cambial usa a ponta cambial ao lado.":
        "The leg earns the price move over the period and settles in reais as a plain "
        "number. The currency above says which ruler the price is quoted against; it "
        "never enters the arithmetic. For the currency move, use the currency leg.",
    "Cotação em": "Quoted in",
    "quanto · câmbio não entra": "quanto · no currency effect",
    "{ativo} variou {retorno}% mais spread de {taxa}%, sem conversão cambial":
        "{ativo} moved {retorno}% plus a {taxa}% spread, with no currency conversion",

    "Contagem de dias": "Day count",
    "Capitalização": "Compounding",
    "Composto — (1 + i) ^ τ": "Compound — (1 + i) ^ τ",
    "Simples — 1 + i · τ": "Simple — 1 + i · τ",
    "DU/252 — dias úteis": "BD/252 — business days",
    "ACT/360 — dias corridos": "ACT/360 — calendar days",
    "ACT/365 — dias corridos": "ACT/365 — calendar days",
    "30/360 — bond basis": "30/360 — bond basis",
    "30E/360 — eurobond": "30E/360 — eurobond",
    "ACT/ACT — ISDA": "ACT/ACT — ISDA",
    "O mesmo período em cada contagem": "The same period under each day count",
    "Convenção": "Convention",
    "Contagem": "Day count",
    "Dias": "Days",
    "Base": "Base",
    "ano real": "actual year",

    "Ajuste líquido em": "Net payment on",
    "Ajuste bruto": "Gross payment",
    "A ponta passiva paga à ponta ativa.": "The paying leg pays the receiving leg.",
    "A ponta ativa paga à ponta passiva.": "The receiving leg pays the paying leg.",
    "diferença de fator de ": "factor difference of ",
    "IR retido": "Tax withheld",
    "sem retenção": "nothing withheld",
    "dias de operação": "days since the trade",
    "Reter o IR na fonte": "Withhold tax at source",
    "Tabela regressiva sobre o resultado positivo, pelo prazo contado da data da "
    "operação.":
        "The regressive table on a positive result, over the horizon counted from the "
        "trade date.",
    "Juros do período": "Interest for the period",
    "Variação da moeda": "Currency move",
    "não há retenção quando a ponta ativa ganha":
        "nothing is withheld when the receiving leg wins",
    "Tabela regressiva pelo prazo contado da data da operação. Só incide quando a "
    "ponta ativa perde — a retenção é da fonte pagadora, e é aí que ela paga.":
        "The regressive table over the horizon counted from the trade date. It "
        "only applies when the receiving leg loses — withholding is the paying "
        "source's job, and that is when it pays.",
    "Fixing": "Fixing",
    "Fixing de": "Fixing for",
    "Índice · câmbio": "Index · currency",
    "em": "on",
    "Como a conta é feita": "How the number is built",
    "O principal do swap é nocional: não troca de mãos. Liquida só a diferença entre "
    "o valor futuro das duas pontas, e quem tem o resultado negativo paga. O IR segue "
    "a tabela regressiva — até 180 dias 22,5% · 181 a 360 dias 20% · 361 a 720 dias "
    "17,5% · acima de 720 dias 15%.":
        "A swap's principal is notional: it never changes hands. Only the difference "
        "between the two legs' future values settles, and whoever ends up negative "
        "pays. Withholding follows the regressive table — up to 180 days 22.5% · 181 "
        "to 360 days 20% · 361 to 720 days 17.5% · beyond 720 days 15%.",
    "O produto diário do CDI é sempre 252 — a contagem escolhida capitaliza o spread.":
        "The CDI daily product is always 252 — the chosen day count compounds the spread.",
    "14 para 14% a.a. · 100 para 100% do CDI · 2 para CDI+2% · 3,25 para um cupom de "
    "3,25%":
        "14 for 14% p.a. · 100 for 100% of CDI · 2 for CDI+2% · 3.25 for a 3.25% coupon",

    # moldes de descrição de cada ponta
    "{taxa}% a.a. sobre τ = {tau}": "{taxa}% p.a. over τ = {tau}",
    "{taxa}% do CDI em {du} dias úteis publicados":
        "{taxa}% of CDI over {du} published business days",
    "CDI + {taxa}% em {du} dias úteis publicados":
        "CDI + {taxa}% over {du} published business days",
    "variação de {variacao}% mais cupom de {taxa}% sobre τ = {tau}":
        "a {variacao}% currency move plus a {taxa}% coupon over τ = {tau}",
    "SOFR composto de {sofr}% mais spread de {taxa}% em {dc} dias corridos":
        "compounded SOFR of {sofr}% plus a {taxa}% spread over {dc} calendar days",
    "{nome} {tenor} de {indice}% mais spread de {taxa}%, fixado em {quando}":
        "{nome} {tenor} at {indice}% plus a {taxa}% spread, fixed on {quando}",
    "correção de {correcao}% mais cupom real de {taxa}% a.a.":
        "a {correcao}% inflation adjustment plus a {taxa}% p.a. real coupon",
    "{ativo} variou {retorno}% mais spread de {taxa}%":
        "{ativo} moved {retorno}% plus a {taxa}% spread",
    "fator digitado": "factor typed in",


    # ------------------------------------------ NDF: direção do fluxo e casado
    "Direção do fluxo": "Flow direction",
    "Saída de moeda estrangeira — soma o casado":
        "Foreign currency going out — adds the casado",
    "Entrada de moeda estrangeira — desconta o casado":
        "Foreign currency coming in — subtracts the casado",
    "Saída de moeda estrangeira": "Foreign currency going out",
    "Entrada de moeda estrangeira": "Foreign currency coming in",
    "O casado entra no preço com o sinal do fluxo: saída soma, entrada desconta. É o "
    "spot já ajustado que precifica a curva.":
        "The casado enters the price with the flow's sign: outgoing adds, incoming "
        "subtracts. It is the adjusted spot that prices the curve, not the one typed.",
    "Spot que precificou": "Spot used for pricing",
    "É este o spot que entrou na curva, e não o digitado.":
        "This is the spot that went into the curve, not the one typed.",
    "Numa saída ele coincide com o 1º futuro dividido por 1.000 — precificar pelo "
    "casado é precificar pelo futuro, que é o que o casado significa.":
        "On an outflow it equals the 1st future divided by 1,000 — pricing off the "
        "casado is pricing off the future, which is what the casado means.",
    "Spot": "Spot",
    "spot ": "spot ",
    "casado": "casado",
    "casado de": "casado of",
    "pips": "pips",
    "saída · soma": "outflow · adds",
    "entrada · desconta": "inflow · subtracts",


    # -------------------------------------------------------------- cotações
    "Cotações": "Quotes",
    "Histórico de mercado": "Market history",
    "O que fechou, dia a dia.": "What closed, day by day.",
    "PTAX do Banco Central, ações e commodities. Da PTAX vem só o boletim de "
    "fechamento — é o que a mesa usa, e trazer os intermediários poria quatro linhas "
    "no mesmo dia.":
        "Central bank PTAX, equities and commodities. From PTAX only the closing "
        "bulletin — that is what the desk uses, and pulling the intraday ones would "
        "put four rows on the same day.",
    "PTAX — Banco Central": "PTAX — Central Bank",
    "Ações e índices": "Equities and indices",
    "Commodities": "Commodities",
    "Boletim de fechamento por moeda.": "Closing bulletin per currency.",
    "Fechamento diário do Yahoo Finance.": "Daily close from Yahoo Finance.",
    "Futuros e contratos contínuos, pelo de-para da B3.":
        "Futures and continuous contracts, through the B3 mapping.",
    "Tipo": "Kind",
    "Instrumento": "Instrument",
    "De": "From",
    "Até": "To",
    "Buscar": "Search",
    "O símbolo cadastrado aparece ao lado do código. Em commodities, o código do "
    "vencimento é resolvido pelo padrão mesmo fora da lista.":
        "The registered symbol shows next to the code. In commodities, a contract "
        "code is resolved by the pattern even when it is not in the list.",
    "Símbolo consultado": "Symbol queried",
    "na fonte": "at the source",
    "o código é o símbolo": "the code is the symbol",
    "Linhas": "Rows",
    "Última publicação": "Latest publication",
    "a tabela abre pela mais recente": "the table opens with the most recent",
    "Banco Central · boletim de fechamento": "Central bank · closing bulletin",
    "Yahoo Finance · fechamento diário": "Yahoo Finance · daily close",
    "A fonte respondeu, mas não há publicação no período escolhido.":
        "The source answered, but there is no publication in the chosen period.",
    "Sobre a tabela": "About the table",
    "Célula vazia não é zero: a fonte não publicou aquele valor naquele dia — no "
    "Yahoo, o papel não teve pregão. Um zero ali afirmaria um preço que não existiu.":
        "An empty cell is not a zero: the source published no value that day — on "
        "Yahoo, the instrument did not trade. A zero there would assert a price that "
        "never existed.",
    "Compra CCY/BRL": "CCY/BRL bid",
    "Venda CCY/BRL": "CCY/BRL ask",
    "Compra CCY/USD": "CCY/USD bid",
    "Venda CCY/USD": "CCY/USD ask",
    "Fechamento ajustado": "Adjusted close",
    "Fechamento": "Close",
    "Máxima": "High",
    "Mínima": "Low",
    "Abertura": "Open",
    "Volume": "Volume",


    # ------------------------------------- Term SOFR importado da planilha B3
    "Curva a termo": "Forward curve",
    "Term SOFR de 1, 3, 6 e 12 meses": "Term SOFR at 1, 3, 6 and 12 months",
    "Administrada pela CME e licenciada: não há fonte pública que permita "
    "redistribuí-la. Quem tem a licença tem o arquivo — arraste o relatório da B3 "
    "aqui e as cotações ficam guardadas nesta máquina.":
        "Administered by CME and licensed: no public source allows redistributing "
        "it. Whoever holds the licence holds the file — drop the B3 report here and "
        "the quotes are kept on this machine.",
    "Arraste o relatório da B3 aqui, ou clique para escolher":
        "Drop the B3 report here, or click to choose one",
    "Ticker na coluna L, data na O e valor na P — .xlsx, .csv ou .tsv. O valor vem "
    "como número (3,74231) e é convertido para taxa na importação.":
        "Ticker in column L, date in O and value in P — .xlsx, .csv or .tsv. The "
        "value arrives as a plain number (3.74231) and is converted to a rate on "
        "import.",
    "dias na base": "days on file",
    "Term SOFR 1 mês": "Term SOFR 1 month",
    "Term SOFR 3 meses": "Term SOFR 3 months",
    "Term SOFR 6 meses": "Term SOFR 6 months",
    "Term SOFR 12 meses": "Term SOFR 12 months",
    "O que está nesta seção é a estrutura a termo realizada, que o Fed de Nova York "
    "publica aberta: o overnight e as médias compostas. A curva forward-looking da "
    "CME é licenciada e vem do arquivo que você importa acima — as duas convivem na "
    "mesma tela porque respondem a perguntas diferentes.":
        "This section holds the realised term structure, which the New York Fed "
        "publishes openly: the overnight rate and the compounded averages. CME's "
        "forward-looking curve is licensed and comes from the file you import "
        "above — the two live on the same screen because they answer different "
        "questions.",


    # ---------------------------------------- o que liquida num fluxo de swap
    "Vencimento do swap": "Swap maturity",
    "O que liquida": "What settles",
    "Pelas datas — juros no fluxo intermediário, valor futuro no vencimento":
        "By the dates — interest on an interim flow, future value at maturity",
    "Só os juros — fluxo intermediário, o principal segue":
        "Interest only — interim flow, the principal carries on",
    "Valor futuro das duas pontas — liquidação final":
        "Future value of both legs — final settlement",
    "Fluxo intermediário — liquida só o diferencial de juros":
        "Interim flow — only the interest differential settles",
    "Liquidação final — liquida o valor futuro das duas pontas":
        "Final settlement — the future value of both legs settles",
    "A data da operação conta o prazo do IR; o fluxo é onde os índices acumulam. Um "
    "fluxo que termina antes do vencimento é intermediário: nele só o diferencial de "
    "juros muda de mãos, e o principal segue para o período seguinte.":
        "The trade date sets the withholding-tax horizon; the flow is where the "
        "indices accrue. A flow ending before maturity is an interim one: only the "
        "interest differential changes hands there, and the principal carries on to "
        "the next period.",
    "As duas liquidações, lado a lado": "Both settlements, side by side",
    "O que separa as duas é a variação cambial sobre o principal. Num fluxo "
    "intermediário ela não muda de mãos, porque o principal não liquida ali — ele "
    "segue de pé para o período seguinte.":
        "What separates them is the currency move on the principal. On an interim "
        "flow it does not change hands, because the principal does not settle "
        "there — it stays standing for the next period.",
    "Só os juros": "Interest only",
    "Valor futuro": "Future value",
    "Conta": "Arithmetic",
    "Diferença": "Difference",
    "juros da ativa − juros da passiva":
        "receiving-leg interest − paying-leg interest",
    "VF da ativa − VF da passiva": "receiving-leg FV − paying-leg FV",
    "câmbio sobre o principal": "currency move on the principal",


    # ------------------------------------------- mensagens de erro do motor
    # Elas viram frase pela chave do MOLDE: os números entram depois, então uma
    # entrada aqui vale para todas as datas, moedas e curvas que a preencherem.
    "{data} não é dia útil (fim de semana ou feriado)":
        "{data} is not a business day (weekend or holiday)",
    "não foi possível obter {curva} em {data}: {motivo}":
        "could not fetch {curva} for {data}: {motivo}",
    "resposta da B3 ilegível para {curva}: {motivo}":
        "B3 returned something unreadable for {curva}: {motivo}",
    "a B3 não publicou a curva {curva} para {data}. O histórico público cobre "
    "aproximadamente o último mês útil.":
        "B3 published no {curva} curve for {data}. The public archive covers "
        "roughly the last business month.",
    "as curvas {a} e {b} não têm prazos em comum":
        "curves {a} and {b} share no tenors",
    "data inválida: {valor}": "invalid date: {valor}",
    "convenção de dia útil desconhecida: {convencao}":
        "unknown business-day convention: {convencao}",
    "calendário desconhecido: {nome}": "unknown calendar: {nome}",
    "o Banco Central não publicou PTAX entre {inicio} e {fim}. A cotação sai por "
    "volta das 13h do dia útil.":
        "the central bank published no PTAX between {inicio} and {fim}. The rate "
        "comes out around 1pm on a business day.",
    "o Banco Central não publicou boletim de {moeda} entre {inicio} e {fim}. O "
    "fechamento sai por volta das 13h do dia útil.":
        "the central bank published no {moeda} bulletin between {inicio} and "
        "{fim}. The close comes out around 1pm on a business day.",
    "não foi possível obter a cotação: {motivo}":
        "could not fetch the quote: {motivo}",
    "a data final não pode ser anterior à inicial":
        "the end date cannot precede the start date",
    "a data final tem que ser posterior à inicial":
        "the end date must come after the start date",
    "a data final é anterior à inicial": "the end date precedes the start date",
    "o Banco Central não publicou CDI entre {inicio} e {fim}. A série tem um dia "
    "de defasagem e não cobre datas futuras.":
        "the central bank published no CDI between {inicio} and {fim}. The series "
        "runs a day behind and does not cover future dates.",
    "não foi possível obter a série {codigo} do BCB: {motivo}":
        "could not fetch central bank series {codigo}: {motivo}",
    "{campo} inválida: {valor}. Use dd/mm/aaaa.":
        "invalid {campo}: {valor}. Use dd/mm/yyyy.",
    "{moeda} não é publicada no boletim PTAX do BCB":
        "{moeda} is not published in the central bank PTAX bulletin",
    "nenhum símbolo de mercado informado": "no market symbol given",
    "o Yahoo Finance recusou {simbolo}: {motivo}":
        "Yahoo Finance refused {simbolo}: {motivo}",
    "não há dado para {simbolo} no período":
        "no data for {simbolo} in the period",
    "tipo de cotação desconhecido: {tipo}": "unknown quote kind: {tipo}",
    "{instrumento} não tem símbolo de mercado no cadastro de {cadastro}":
        "{instrumento} has no market symbol registered under {cadastro}",
    "{fonte}: {motivo}": "{fonte}: {motivo}",
    "{fonte} recusou por excesso de consultas (HTTP 429). O limite é por endereço "
    "de rede e passa sozinho — tente de novo em alguns minutos.":
        "{fonte} refused for too many requests (HTTP 429). The limit is per network "
        "address and lifts on its own — try again in a few minutes.",
    "curva {curva} sem vértices": "curve {curva} has no vertices",
    "{curva} é uma curva de preço a termo, não de taxa — não há fator de "
    "capitalização. Use taxa_para() para o preço.":
        "{curva} is a forward-price curve, not a rate curve — there is no "
        "compounding factor. Use taxa_para() for the price.",
    "a curva {curva} é interpolada em dias úteis; informe dias_uteis":
        "curve {curva} is interpolated on business days; pass dias_uteis",
    "convenção EXP252 exige dias úteis": "the EXP252 convention needs business days",
    "FRA exponencial exige dias úteis": "an exponential FRA needs business days",
    "formato não suportado: {formato}": "unsupported format: {formato}",
    "o visualizador não devolveu uma sessão de relatório — a página pode ter mudado":
        "the report viewer returned no session — the page may have changed",
    "não foi possível obter o relatório: {motivo}":
        "could not fetch the report: {motivo}",
    "Banco da Finlândia: {motivo}": "Bank of Finland: {motivo}",
    "amortização personalizada precisa de um peso por período":
        "a custom amortisation needs one weight per period",
    "os pesos de amortização somam {total}, deveriam somar 1":
        "the amortisation weights add up to {total}, they should add up to 1",
    "a spline precisa de pelo menos 2 pontos distintos":
        "the spline needs at least 2 distinct points",
    "método de interpolação desconhecido: {metodo}":
        "unknown interpolation method: {metodo}",
    "indexador desconhecido: {indexador}": "unknown index: {indexador}",
    "não há fixing de EURIBOR {tenor} publicado até {data}":
        "no EURIBOR {tenor} fixing published up to {data}",
    "o fixing inicial da moeda não pode ser zero":
        "the opening currency fixing cannot be zero",
    "o fim do fluxo tem que ser posterior ao início":
        "the flow must end after it starts",
    "o fluxo não pode começar ({inicio}) antes da operação ({operacao})":
        "the flow cannot start ({inicio}) before the trade ({operacao})",
    "o notional remanescente tem que ser positivo":
        "the outstanding notional must be positive",
    "a liquidação usa índice realizado, não projeção — o fim do fluxo não pode "
    "passar de hoje ({hoje})":
        "settlement uses realised indices, not forecasts — the flow cannot end "
        "after today ({hoje})",
    "o notional remanescente não pode ser maior que o valor original":
        "the outstanding notional cannot exceed the original amount",
    "os dois fixings de moeda estão preenchidos, mas a moeda do fluxo está em "
    "Real, que não converte. Escolha a moeda estrangeira para a variação cambial "
    "entrar na conta, ou apague os fixings.":
        "both currency fixings are filled in, but the flow currency is Real, which "
        "does not convert. Pick the foreign currency for the currency move to "
        "count, or clear the fixings.",
    "o Banco Central não boletina {moeda}: informe o fixing {qual} da moeda. Os "
    "dois entram digitados.":
        "the central bank does not publish {moeda}: enter the {qual} currency "
        "fixing. Both are typed in.",
    "uma ponta de moeda pura precisa de uma moeda estrangeira — em reais ela não "
    "renderia nada":
        "a pure currency leg needs a foreign currency — in reais it would earn "
        "nothing",
    "a ponta de equity precisa do preço inicial e do preço final":
        "the equity leg needs an opening and a closing price",
    "a ponta de IPCA precisa do número-índice inicial e do final":
        "the IPCA leg needs an opening and a closing index number",
    "informe o fator acumulado da ponta": "enter the leg's accrued factor",
    "o {defasagem} tem que ficar entre 0 e {teto} dias úteis":
        "the {defasagem} must be between 0 and {teto} business days",
    "o Term SOFR é licenciado pela CME e não tem fonte pública. Informe a taxa do "
    "fixing, ou importe o relatório da B3 na tela de Term SOFR.":
        "Term SOFR is licensed by CME and has no public source. Enter the fixing "
        "rate, or import the B3 report on the Term SOFR screen.",
    "esta ponta precisa da curva {curva}, que não foi carregada":
        "this leg needs the {curva} curve, which was not loaded",
    "não sei ler {arquivo}. Use .xlsx, .csv ou .tsv — o .xls antigo precisa ser "
    "salvo de novo num desses.":
        "I cannot read {arquivo}. Use .xlsx, .csv or .tsv — an old .xls has to be "
        "saved again as one of those.",
    "o arquivo .xlsx não tem nenhuma planilha dentro":
        "the .xlsx file has no worksheet inside",
    "não foi possível ler o texto do arquivo": "could not read the file's text",
    "este arquivo não é um .xlsx. Se ele for .xls antigo, abra e salve como .xlsx "
    "ou como CSV.":
        "this file is not an .xlsx. If it is an old .xls, open it and save as "
        ".xlsx or as CSV.",
    "{par} precisa da curva de preço a termo": "{par} needs the forward-price curve",
    "{par} precisa da curva de preço para implicar o cupom":
        "{par} needs the price curve to imply the coupon",
    "{par} precisa da curva de cupom": "{par} needs the coupon curve",
    "a curva de DI é obrigatória fora do modo de cross":
        "the DI curve is required outside cross mode",
    "o vencimento tem que ser posterior ao início":
        "maturity must come after the start",
    "o vencimento tem que ser posterior à aplicação":
        "maturity must come after the investment date",
    "falha de conexão com {url}: {detalhe}{pista}":
        "connection to {url} failed: {detalhe}{pista}",
    "resposta ilegível de {url}: {motivo}{pista}":
        "unreadable response from {url}: {motivo}{pista}",
    "PRECIFICADOR_SSO está ligado mas o pacote 'requests' não está instalado. "
    "Instale-o (e o requests-negotiate-sspi no Windows) ou desligue a variável.":
        "PRECIFICADOR_SSO is on but the 'requests' package is not installed. "
        "Install it (and requests-negotiate-sspi on Windows) or turn the variable "
        "off.",
    "PRECIFICADOR_SSO está ligado e nenhum handler Negotiate foi encontrado. Sem "
    "ele a chamada sai sem autenticação e o ADFS responde 401. Instale "
    "requests-negotiate-sspi (Windows) ou requests-kerberos (Linux/macOS, com "
    "ticket via kinit).":
        "PRECIFICADOR_SSO is on and no Negotiate handler was found. Without it the "
        "call goes out unauthenticated and ADFS answers 401. Install "
        "requests-negotiate-sspi (Windows) or requests-kerberos (Linux/macOS, with "
        "a ticket from kinit).",
    "o proxy respondeu HTTP {codigo}": "the proxy answered HTTP {codigo}",
    "HTTP {codigo} em {url}": "HTTP {codigo} at {url}",
    "o fim do período tem que ser posterior ao início":
        "the period must end after it starts",
    "lookback e shift não podem ser negativos":
        "lookback and shift cannot be negative",
    "período sem dias corridos": "the period has no calendar days",
    "não há fixing de SOFR publicado para {data} nem antes dessa data — amplie o "
    "intervalo consultado":
        "no SOFR fixing published for {data} or before it — widen the range you "
        "are asking for",
    "o SOFR Index não tem publicação para {data}":
        "the SOFR Index has no publication for {data}",
    "não foi possível obter a série do NY Fed: {motivo}":
        "could not fetch the NY Fed series: {motivo}",
    "sem convergência após {iteracoes} iterações":
        "no convergence after {iteracoes} iterations",
    "não foi possível encontrar um intervalo com troca de sinal":
        "could not find a bracket where the sign changes",
    "o arquivo está vazio": "the file is empty",
    "nenhuma cotação de Term SOFR no arquivo. Procurei o ticker na coluna "
    "{ticker}, a data na {data} e o valor na {valor}, e esperava um de: "
    "{esperados}.":
        "no Term SOFR quote in the file. I looked for the ticker in column "
        "{ticker}, the date in {data} and the value in {valor}, and expected one "
        "of: {esperados}.",
    "informe as datas de início e vencimento":
        "enter the start and maturity dates",
    "preencha o campo {campo}": "fill in the {campo} field",
    "{campo}: “{texto}” não é um número": "{campo}: “{texto}” is not a number",
    "pesos de amortização inválidos": "invalid amortisation weights",
    "modo de moeda desconhecido: {modo}": "unknown currency mode: {modo}",


    # Rótulos de campo que entram nos moldes de erro. São valores, não frases —
    # "preencha o campo {campo}" precisa deles traduzidos para não sair meia
    # frase em cada idioma. Os que a ponta monta na hora ("taxa da ponta ativa")
    # entram logo abaixo, pelo mesmo motivo.
    "spot D+2": "D+2 spot",
    "notional remanescente": "outstanding notional",
    "notional original": "original notional",
    "valor aplicado": "amount invested",
    "juro da moeda estrangeira": "foreign currency rate",
    "1º futuro": "1st future",
    "2º futuro": "2nd future",
    "CDI projetado": "forecast CDI",
    "IPCA projetado": "forecast IPCA",
    "projeção mensal": "monthly forecast",
    "NI de partida": "starting index number",
    "amortização": "amortisation",
    "quantidade": "quantity",
    "taxa da ponta ativa": "receiving-leg rate",
    "taxa da ponta passiva": "paying-leg rate",
    "fixing inicial da ponta ativa": "receiving-leg opening fixing",
    "fixing inicial da ponta passiva": "paying-leg opening fixing",
    "fixing final da ponta ativa": "receiving-leg closing fixing",
    "fixing final da ponta passiva": "paying-leg closing fixing",
    "número-índice inicial da ponta ativa": "receiving-leg opening index number",
    "número-índice inicial da ponta passiva": "paying-leg opening index number",
    "número-índice final da ponta ativa": "receiving-leg closing index number",
    "número-índice final da ponta passiva": "paying-leg closing index number",
    "fator da ponta ativa": "receiving-leg factor",
    "fator da ponta passiva": "paying-leg factor",
    "preço inicial da ponta ativa": "receiving-leg opening price",
    "preço inicial da ponta passiva": "paying-leg opening price",
    "preço final da ponta ativa": "receiving-leg closing price",
    "preço final da ponta passiva": "paying-leg closing price",
    "taxa do fixing da ponta ativa": "receiving-leg fixing rate",
    "taxa do fixing da ponta passiva": "paying-leg fixing rate",
    "data inicial": "start date",
    "data final": "end date",

}


# Auditoria de tradução.
#
# Uma frase sem tradução cai de volta no português — o que é a degradação certa
# em produção e um problema em desenvolvimento, porque some no meio da tela.
# Ligando a auditoria, toda falta é registrada; o teste
# ``test_nenhuma_string_fica_sem_traducao`` renderiza a aplicação inteira em
# inglês e falha se este conjunto não vier vazio.
_FALTANDO: set = set()
_AUDITANDO = False


def auditar(ligado: bool = True) -> None:
    global _AUDITANDO
    _AUDITANDO = ligado
    if ligado:
        _FALTANDO.clear()


def faltando() -> set:
    """As frases que pediram tradução e não tinham."""
    return set(_FALTANDO)


def traduzir(texto: str, idioma: str = PADRAO) -> str:
    """Traduz uma frase; sem tradução, devolve o original."""
    if idioma == PADRAO:
        return texto
    traduzido = TRADUCOES.get(texto)
    if traduzido is None:
        if _AUDITANDO and texto and texto.strip():
            _FALTANDO.add(texto)
        return texto
    return traduzido


def do_pedido() -> str:
    """O idioma da tela atual — o mesmo que o ``t`` dos templates usa."""
    try:
        from flask import request
        return normalizar(request.args.get("idioma")
                          or request.cookies.get("idioma"))
    except Exception:                                    # noqa: BLE001
        return PADRAO                                    # fora de um pedido


def mensagem(exc, idioma=None) -> str:
    """A frase de um erro no idioma da tela.

    Os erros do pacote guardam o molde separado dos valores (ver
    ``precificador.erros.ErroTraduzido``), e é isso que permite traduzi-los: a
    chave é o molde, e os números entram depois. Um erro que não passou por lá
    cai de volta no português, que é o que acontecia com todos eles.

    Se a tradução tiver um campo que os valores não têm — um molde editado de um
    lado só —, a frase original é usada. Um erro de formatação escondendo o erro
    de verdade seria o pior desfecho possível para esta função.
    """
    from precificador.erros import montar, partes
    escolhido = idioma if idioma is not None else do_pedido()
    molde, valores = partes(exc)
    # o rótulo que entra no molde é texto, e texto também se traduz: "preencha o
    # campo {campo}" com campo="notional remanescente" daria meia frase em cada
    # idioma. Número e data passam direto, porque não estão no dicionário.
    valores = {chave: traduzir(valor, escolhido) if isinstance(valor, str) else valor
               for chave, valor in valores.items()}
    traduzido = traduzir(molde, escolhido)
    if not valores:
        return traduzido
    try:
        return traduzido.format(**valores)
    except (KeyError, IndexError, ValueError):
        # tradução com um campo que os valores não têm: melhor a frase original
        # inteira do que a traduzida com um {campo} cru no meio
        return montar(molde, valores)


def normalizar(idioma) -> str:
    codigo = (idioma or "").strip().lower()[:2]
    return codigo if codigo in dict(IDIOMAS) else PADRAO
