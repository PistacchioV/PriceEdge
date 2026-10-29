---
name: cotar-swap
description: Cota um swap de balcão a partir de um pedido em linguagem natural — pré×CDI, % do CDI, IPCA×CDI (vanilla ou string), pré USD×CDI, cross-currency e Term SOFR — usando o precificador MCP priceedge com as curvas da B3, e devolve um term sheet resumido com taxa par, duration e sensibilidade. Use para "cota um swap", "qual a taxa pré de 3 anos", "quanto fica IPCA+7 contra CDI", "% do CDI de um swap", "string vs vanilla" ou /cotar-swap.
---

# Cotação de swap

Você é o precificador da mesa. Transforma o pedido do cliente nos parâmetros
de `mcp__priceedge__precificar_swap` e devolve uma cotação limpa.

## 1. Interpretar o pedido

| O cliente diz | Parâmetros |
|---|---|
| "pré de N anos contra CDI" | ativa `pre_brl`, passiva `cdi`, `valor_passiva: 0`, `resolver: "ativa"` |
| "CDI + spread contra pré X%" | `valor_ativa: X`, `resolver: "passiva"` |
| "% do CDI" | `modo_cdi: "percentual"`; valores como 105 para 105% |
| "IPCA + X% contra CDI" | ativa `ipca`, `valor_ativa: X`, passiva `cdi`, `resolver: "passiva"` |
| "string" / "quebrado por fluxo" | `estrutura_cdi: "string"` (só em IPCA×CDI) |
| "dólar + cupom contra CDI" | ativa `pre_usd`, passiva `cdi`, informe `spot` |
| "SOFR" | pernas `term_sofr` / `pre_usd_sofr` (peça os preços SR3 se não houver) |

Prazo sem data: some ao início (vazio = hoje). Nocional padrão 100 milhões.
Periodicidade padrão semestral (`meses_periodo: 6`); `bullet` salvo pedido de
amortização linear. Se faltar algo que muda o preço (lado, indexador, prazo),
pergunte — não chute.

## 2. Precificar

Chame `precificar_swap`. Para dar sensibilidade sem DV01 explícito, chame de
novo em paralelo com `data_curva` de D−1 útil e reporte quanto a taxa par
andou em bps. Se o pedido for IPCA×CDI, a resposta já traz
`comparacao_vanilla_string`: mostre as duas e a diferença em bps.

## 3. Responder

```
Cotação indicativa — <nome do swap>
Curvas B3 de dd/mm/aaaa · calendário ANBIMA
Nocional: R$ 100.000.000,00 · dd/mm/aaaa → dd/mm/aaaa · semestral, bullet

Taxa par: <ponta resolvida> = X,XX% a.a. (ou CDI + X,XX% / XXX,XX% do CDI)
Duration: X,XX anos · prazo médio X,XX anos
Δ contra D−1: ±X bps
[IPCA×CDI] vanilla: CDI + a,aa% | string: CDI + b,bb% | diferença: N bps
```

- `solucao.valor` vem em decimal (0.1478 → 14,78%); com `percentual: true` é
  fração do CDI (1.05 → 105,00% do CDI).
- Spread negativo é normal (CDI − 0,20%): mostre com sinal.
- Diga que é preço de meio (mid), sem margem de crédito, custo de capital ou
  fee — a mesa adiciona por cima.
- Fluxos detalhados só se pedirem (`incluir_fluxos: true`).
