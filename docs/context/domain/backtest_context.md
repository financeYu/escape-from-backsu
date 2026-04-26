# Backtest Context

Canonical references:

- `Quant_mvp/backtest_mvp/AGENTS.md`
- `Quant_mvp/backtest_mvp/README.md`
- `docs/step17_conservative_backtest_core.md`
- `docs/step17_backtest_guardrails.md`
- `docs/architecture/step17_backtest_boundary.md`

Boundary summary:

- Step 17 backtests are evaluation-only.
- `Quant_mvp/backtest_mvp` is the canonical Quant-owned module.
- `src.backtest` is a compatibility facade only.
- Realized/evaluation returns belong only in Step 17 output context.
- Backtest results must not feed upstream score, ranking, or report construction.
