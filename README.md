# precificador

Porte das planilhas VBA de *Precificação Swap* para um pacote Python, com uma
aplicação Flask por cima.

O que era macro virou módulo: a UDF `cubic_spline` virou `precificador.interpolacao`,
o extrator de curvas da B3 virou `precificador.b3`, as colunas de datas viraram
`precificador.calendario`, as colunas de fluxo viraram `precificador.instrumentos`
e o `GoalSeek` que as macros chamavam virou `precificador.solver`.

---

## Como rodar

```bash
cd "precificador-app"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

Abre em <http://127.0.0.1:5001>. Precisa de internet para as curvas da B3 e para
os fixings do NY Fed.

```bash
.venv/bin/python -m pytest tests -q
```

---

## Telas

| Rota | O que faz |
|---|---|
| `/` | painel com as estruturas e as curvas disponíveis |
| `/curvas` | extração da curva do dia, gráfico, tabela de vértices, download CSV |
| `/precificar` | os cinco swaps prontos: MtM, taxa par e os dois fluxos de caixa |
| `/montar` | swap personalizado — escolha a ponta ativa e a passiva |
| `/ndf` | curva de dólar a termo, casado, rolagem, pontos |
| `/sofr` | SOFR composto do NY Fed, com lookback e observation shift |
| `/euribor` | EURIBOR diário desde 2006, base local que só cresce |
| `/renda-fixa` | CDB, LCI, debênture: bruto, IR, IOF e líquido, com CDI **realizado** do BCB |
| `/interpolar` | a spline isolada — compare métodos e extrapolações |
| `/ni-pro-rata` | número-índice pro-rata e VNA de papel IPCA+ |
| `/metodologia` | convenções, decisões do porte, fontes de dados e glossário |

API JSON: `/api/curvas/<código>?data=AAAA-MM-DD` e
`/api/interpolar/<código>?dc=1826&metodo=spline`.

**Idioma e tema.** O botão EN/PT no cabeçalho troca o idioma (524 verbetes, com
nomenclatura de mercado) e fica salvo em cookie; o botão ao lado alterna claro e
escuro, salvo em `localStorage`. Sem preferência, o tema segue o sistema.

---

## Estrutura

```
precificador/            o pacote — não depende de Flask nem de nada externo
  calendario.py          feriados ANBIMA/SOFR/BCE, WORKDAY, NETWORKDAYS−1,
                         convenções de dia útil, cronogramas, datas IMM
  interpolacao.py        spline cúbica natural, linear, flat-forward
  b3.py                  extração das Taxas Referenciais da B3
  sofr.py                fixings do NY Fed e composição com lookback/shift
  cdi.py                 série 4389 do BCB e acúmulo diário do CDI realizado
  euribor.py             EURIBOR do Banco da Finlândia + base histórica local
  curvas.py              Curva (spot, desconto, FRA) e CurvaTermSOFR
  instrumentos.py        agenda, amortização, pernas, Swap, prazo médio, duration
  produtos.py            os cinco swaps prontos, NDF e NI pro-rata
  montador.py            pontas soltas para montar swap personalizado
  renda_fixa.py          CDB/LCI/debênture com IR e IOF
  solver.py              o Atingir Meta (bisseção + secante)
  fontes.py              catálogo das fontes de dados de mercado
  glossario.py           39 verbetes, definições operacionais
  dados/                 feriados ANBIMA, US+BR, SOFR e EURIBOR
                         euribor_historico.json — 5.310 dias desde 2006

webapp/                  a aplicação Flask
  rotas.py               páginas e API JSON
  servicos.py            cache de curvas, leitura de formulário, gráficos SVG
  filtros.py             formatação numérica em padrão brasileiro
  idiomas.py             dicionário PT/EN
  templates/             Jinja, sobre o design system Pulsedesk
  static/                CSS de formulários, tema claro, JS de formatação e tema
  static/vendor/         Tailwind, Iconify, fontes e JS copiados do design system
```

O pacote é usável sozinho:

```python
from datetime import date
from precificador import ParametrosSwap, Curva, spread_par_cdi
from precificador.b3 import extrair_curva

di = Curva.de_b3(extrair_curva("PRE", date(2026, 9, 4)), "DI x Pré", date(2026, 9, 4))
params = ParametrosSwap(inicio=date(2026, 9, 4), vencimento=date(2031, 9, 4),
                        nocional=100_000_000, meses_periodo=6)
print(spread_par_cdi(params, taxa_pre=0.17, curva_di=di))   # 0.025577...
```

---

## Convenções

| | |
|---|---|
| Juros em reais | exponencial 252 — `(1+i)^(DU/252)` |
| Juros em dólar | linear 360 — `1 + i·DC/360` |
| Spread sobre CDI | **multiplicativo** — `(1+CDI)·(1+spread) = (1+pré)` |
| % do CDI | incide sobre a taxa **diária** — `[1 + ((1+CDI)^(1/252)−1)·p]^DU` |
| Spread sobre SOFR | aditivo |
| Interpolação | spline cúbica natural |
| Contagem de DU | `NETWORKDAYS(a; b) − 1` literal, como no Excel |
| Dia útil | following, modified following, preceding, modified preceding ou unadjusted |
| Feriados | ANBIMA (BR), SOFR (Fed + Sexta-feira Santa), EURIBOR/TARGET2, US+BR |

Num cross-currency, o fluxo em reais desconta pela curva DI e o fluxo em dólar
pela curva de cupom cambial. Isso está fixado em código, não numa fórmula que dá
para arrastar errado.

**% do CDI não é o spread com outro nome.** Com CDI a 14% ao ano, 110% do CDI dá
15,5031% — e não os 15,40% de multiplicar a taxa anual por 1,10. O percentual
incide sobre a taxa diária, e a capitalização não é linear.

**`NETWORKDAYS − 1`.** Quando a data inicial é dia útil, isso equivale a contar o
intervalo aberto à esquerda. Quando ela cai em fim de semana, o `−1` corta um dia
útil de verdade. Nas agendas de swap a data inicial é sempre ajustada e os dois
jeitos coincidem; no NI pro-rata a data-base é o dia 15, e é esse valor que faz o
VNA bater com a planilha (`dup=19`, `dut=21`, `NI=7591,937980031845`).

---

## Onde o código não copia a planilha

**1. A curva é interpolada em dias corridos.**
A planilha *Pré USD × Pré BRL* interpola a curva num valor de **dias úteis**
(126 em vez de 183), mas o eixo dessa mesma aba vai até 12.556 — é calendário. A
planilha de NDF faz o inverso com o cupom cambial: passa dias corridos num eixo
de dias úteis. A planilha de IPCA traz a fórmula consistente, e é a que o pacote
segue. O eixo é configurável em `Curva.eixo`, e `taxa_para(dc, du)` escolhe o
certo sozinho.

**2. Fora do domínio, a curva trava na ponta.**
As três UDFs das planilhas divergem: uma extrapola o polinômio cúbico, outra
trava, a do NDF segue a reta tangente. As três estão implementadas
(`extrapolar="cubica" | "flat" | "tangente"`); o padrão é `flat`.

**3. O endpoint `GetReferenceRates` saiu.**
A planilha do collar busca `DI1` e `DDI` em
`referenceRatesProxy/api/pt-br/GetReferenceRates/`. Esse endereço responde 404
hoje (verificado). Só o `GetDownloadFile` continua de pé. O `Search/GetList`
também ficou de fora: ignora o parâmetro de data e devolve sempre a curva mais
recente, disfarçada de histórico.

**4. O fator diário do DI não é arredondado.**
O padrão B3/CETIP trunca na 8ª casa antes de acumular. Aqui o padrão é precisão
plena — em cinco anos a 14% com 110% do CDI a diferença é de R$ 3,87 por milhão.
A tela de renda fixa mostra os dois lado a lado e tem o interruptor.

---

## Validação

35 testes contra números tirados das próprias planilhas e das fontes oficiais:

* a spline bate com a UDF do VBA em **1e-9** nos pontos internos;
* a agenda reproduz as colunas de datas (DC, DU, ajuste de dia útil) linha a linha;
* o NI pro-rata dá **7591,937980031845** — os 16 dígitos da célula M5;
* o SOFR composto bate com o **SOFR Index oficial do NY Fed** em 0,0001 bp;
* o montador reproduz exatamente o resultado dos produtos de atalho;
* o acúmulo do CDI segue a convenção da calculadora da B3 — janela
  `[início, fim)`, o DI da data final não entra.

---

## Limites conhecidos

- **Histórico da B3**: a API pública cobre aproximadamente o último mês útil.
- **Term SOFR e futuros SR3 entram digitados** — não há raspagem da CME/Barchart.
- **O BCB publica o CDI com um dia de defasagem.** Um acúmulo que termine hoje
  pode ficar um dia útil atrás da calculadora da B3 até a série ser atualizada;
  a tela mostra a janela efetivamente usada.
- **Projeção de IPCA e NIk−1 entram digitados**, da ANBIMA e do SIDRA.
- **EURIBOR fica guardado localmente.** A fonte mostra seis meses por vez e a
  escolha da janela é um postback ASP.NET. O módulo faz o postback, pega o
  `ReportSession` que a resposta devolve e exporta por ali — assim alcança as 250
  janelas do seletor, de janeiro de 2006 até hoje. Tudo vai para
  `dados/euribor_historico.json`, que só cresce: a cada carregamento da tela a
  janela corrente é rebuscada, datas novas entram e nada gravado é sobrescrito.
  Para refazer a carga completa: `POST /euribor/sincronizar` (~50 requisições).
- **Calendários** ANBIMA (planilha), SOFR e EURIBOR (arquivos), TARGET2 (regra do
  BCE, usada fora do alcance do arquivo do EURIBOR).
- **Sem opções.** Garman-Kohlhagen e a superfície de volatilidade da planilha do
  collar não foram portados; só a spline que ela compartilha.
- O cupom cambial usa a curva **DOC** (limpo). A distinção limpo × sujo não está
  na ferramenta.
- A correção do IPCA na calculadora de renda fixa usa o acumulado do período, não
  a interpolação entre aniversários — para isso use a tela de NI pro-rata.

---

## Design

A interface segue o design system em `../pulsedesk-saas.aura.build`: mesmo
Tailwind (runtime), mesmas fontes (Geist e Plus Jakarta Sans), ícones Solar,
paleta escura com acento ciano, painéis de vidro e o mesmo scroll-reveal.

Três acréscimos, porque a landing original não tinha formulário, tabela nem tema
claro: `static/css/app.css` (controles e tabelas na mesma linguagem visual),
`static/css/tema-claro.css` (remapeia sob `html[data-tema="claro"]` exatamente o
conjunto de utilitários usado nos templates) e `static/js/reveal-fallback.js`,
que garante que o scroll-reveal nunca deixe um resultado invisível — o script
original zera a opacidade de todo parágrafo e conta com o `IntersectionObserver`,
o que numa ferramenta de trabalho é frágil demais.
