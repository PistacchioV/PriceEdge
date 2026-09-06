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


def normalizar(idioma) -> str:
    codigo = (idioma or "").strip().lower()[:2]
    return codigo if codigo in dict(IDIOMAS) else PADRAO
