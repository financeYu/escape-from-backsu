# Subproject Inventory

## Status

This inventory was created during Step 3 directory/config/schema cleanup.

No child project logic was copied or merged during Step 3.
No legacy output was deleted or overwritten.

## Discovered Projects

| path | likely purpose | status | loaders | scores | rankings | backtests | financial data | reports | copied or merged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `master_mvp` | canonical workspace root and master governance | canonical | target boundary only | placeholders only | no | no | deferred | yes | not applicable |
| `master_mvp/chart_mvp` | runnable KOSPI200 scanner, cache, chart rendering, CLI/GUI | canonical | yes, under `src/stock_core/providers` and `src/stock_core/cache` | placeholder/runtime scorer files present | legacy outputs present | no dedicated backtest found | collector/inventory only; no cached financial sample found | yes | no Step 3 merge |
| `master_mvp/Quant_mvp` | quant score governance, config policy, technical/valuation review docs | canonical | no runtime loader found | design/review docs only | no generated ranking outputs found | no | valuation deferred | yes | no Step 3 merge |
| `master_mvp/reserch_mvp` | research-ingestion specification | canonical | no | no | no | no | no | specification only | no Step 3 merge |
| `master_mvp/review_mvp` | code-review tooling and final validation support | canonical | no | no | no | no | no | README/agent docs | no Step 3 merge |
| `C:/Users/jjaew/Project/stock_mvp` | older stock project with crawler, loader, scorer, report, backtest files | legacy | yes | yes | unknown output state | yes | unknown | README present | no |
| `C:/Users/jjaew/Project/review_mvp` | empty leftover after prior move into `master_mvp/review_mvp` | legacy | no | no | no | no | no | no | no |

## Notes

- `chart_mvp` remains the current runtime source for existing loader/provider behavior.
- `Quant_mvp` remains the domain-governance source for score definitions and valuation boundaries.
- `review_mvp` is for code-level review and final validation only.
- `stock_mvp` contains potentially useful historical code, but it is not canonical and must not be imported blindly.
- Financial data remains `valuation_deferred` and `inventory_only`.

