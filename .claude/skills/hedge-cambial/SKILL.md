---
name: hedge-cambial
description: Compara alternativas de hedge cambial USD/BRL para importador ou exportador — NDF, call/put comprada, collar custo zero, call spread, three-way — com o NDF e o Garman-Kohlhagen do servidor MCP priceedge (curvas DI e cupom da B3), mostrando prêmio, strikes, proteção e o que fica descoberto. Use para "hedge de dólar", "collar custo zero", "NDF ou opção", "proteger importação/exportação", "three-way" ou /hedge-cambial.
---

# Hedge cambial: NDF × opções

Você estrutura hedge de dólar para clientes corporativos. Os números vêm de
`mcp__priceedge__curva_ndf` e `mcp__priceedge__precificar_opcao_fx`.

## 1. Entender a exposição

Precisa de: lado (importador = vendido em dólar, teme alta → compra proteção
de call; exportador = comprado em dólar, teme queda → proteção de put),
nocional em USD, vencimento, e vol (ou smile da B3). Sem vol, pergunte; não
invente. Spot: use o informado, ou o da curva (`curva_ndf` sem `spot`).

## 2. Montar as alternativas (chamadas em paralelo)

Importador (para exportador, espelhe: put comprada / call vendida):

| Alternativa | Pernas | Observação |
|---|---|---|
| NDF | `curva_ndf` com `vencimento` | trava o termo, custo zero, sem ganho na queda |
| Call comprada | call comprada no forward ou ATM | paga prêmio, proteção total |
| Call spread | call comprada K1, call vendida K2 > K1 | prêmio menor, proteção até K2 |
| Collar custo zero | call comprada K, put vendida (strike a resolver) | `resolver_strike` na put, `premio_alvo: 0` |
| Three-way | collar + call vendida K3 > K | prêmio baixo/zero, proteção limitada acima de K3 |

Use o `forward` devolvido pela opção como referência de strike "ATM forward".

## 3. Comparar

Tabela: alternativa | prêmio líquido (R$ e % do nocional em R$) | strikes |
taxa efetiva de compra do dólar em 3 cenários (spot no vencimento 15% abaixo,
igual ao forward, 15% acima) | risco que sobra.

Taxa efetiva do importador num cenário S_T: 
- NDF: forward.
- Opções: S_T ajustado pelo payoff das pernas no vencimento + prêmio pago
  levado a valor futuro pela taxa doméstica (prêmio/nocional USD × (1+DI)^(du/252)).

## 4. Responder

Mostre a tabela, os strikes com 4 casas, o prêmio com sinal (o tool usa
positivo = recebido) e o delta da estrutura. Explique em 3–4 linhas o
trade-off de cada uma (custo × proteção × participação). Diga as fontes: curvas
B3 da data, vol informada pelo usuário. Feche com: "Simulação indicativa por
Garman-Kohlhagen — não é oferta nem recomendação; preço executável depende de
crédito, margem e liquidez."
