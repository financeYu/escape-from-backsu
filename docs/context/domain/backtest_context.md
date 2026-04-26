# Backtest Context

Canonical references:

- `docs/step17_conservative_backtest_core.md`
- `docs/step17_backtest_guardrails.md`
- `docs/architecture/step17_backtest_boundary.md`
- `reports/backtest/README.md`

Boundary summary:

- Step 17 backtests are evaluation-only.
- Realized/evaluation returns belong only in Step 17 output context.
- Backtest results must not feed upstream score, ranking, or report construction.
- This Pre-Step19 task changes no backtest logic.
