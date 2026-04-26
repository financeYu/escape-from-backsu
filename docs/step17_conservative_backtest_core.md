# Step 17 Conservative Backtest Core

> Historical Step document. Not current authority; use
> `docs/roadmap_status.md` and `docs/context/ARCHIVE_INDEX.md` for current
> routing.

## Purpose

Step 17 adds an evaluation-only conservative backtest core. It consumes
already-generated Step 15 latest-ranking-compatible rows or Step 16
detail-report-compatible context as read-only upstream input.

Canonical implementation ownership now lives under the Quant-dependent
subproject `Quant_mvp/backtest_mvp`. Legacy imports through `src.backtest`
remain compatibility facades only.

The core does not redefine score formulas, normalized score formulas,
`technical_composite_score`, `final_composite_score`, adoption states, or
ranking logic. It does not write generated reports by itself.

## Boundary

Allowed direction:

```text
Step 15/16 technical snapshot input
-> Step 17 conservative evaluation
-> Step 17 result objects only
```

Forbidden reverse direction:

```text
Step 17 result metrics
-> score formula edits
-> normalization edits
-> adoption-state edits
-> Step 15 ranking edits
-> Step 16 report edits
```

Backtest output is not a trading recommendation. It is a constrained
historical evaluation artifact with explicit assumptions, price-history
limitations, and data-boundary warnings.

## Input Contracts

Ranking snapshot input must include:

- `ticker`
- one date field: `ranking_date`, `decision_date`, or Step 15 `date`
- one upstream rank field: `rank` or `latest_rank`

If upstream technical score fields such as `technical_composite_score` or
`final_composite_score` are present, Step 17 treats them as read-only context.
The engine never recomputes or changes those fields.

Price input must include daily OHLCV fields:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

Ticker values must be six-digit strings. This preserves Korean stock codes with
leading zeros and rejects integer ticker loading.

## Selection And Execution

Selection is deterministic:

- exclude rows explicitly blocked by upstream guardrails
- skip and report rows with missing upstream rank
- select `top_n` by upstream rank only
- break rank ties by ticker only for deterministic ordering
- use `equal_weight` only

Execution and holding-period assumptions are config-owned:

- `rebalance_frequency`
- `holding_period_days`
- `top_n`
- `weight_method = equal_weight`
- `execution_lag_days`
- `execution_price_policy`
- `exit_price_policy`
- `transaction_cost_bps`
- `slippage_bps`
- `missing_price_policy`

The canonical default config lives in
`Quant_mvp/backtest_mvp/config/backtest.toml`. The root `config/backtest.toml`
is retained only as a legacy compatibility copy.

## Return Calculation

`realized_holding_return` is allowed only inside Step 17 result objects and
Step 17-owned output paths. The core computes it from selected security
execution and exit prices, then applies deterministic round-trip transaction
cost and slippage assumptions.

Missing execution or exit prices create explicit limitation flags. Missing
prices are not silently filled.

## Portfolio Aggregation

The in-memory result includes:

- period count
- selected security count
- valid security count
- skipped security count
- mean period return
- cumulative return
- average turnover proxy
- max drawdown
- limitation flags

Required limitation warnings include survivorship-bias, unknown corporate-action
adjustment, and non-point-in-time constituent-history warnings unless a future
validated data contract removes those limitations.

## Valuation Boundary

Valuation and fundamental scoring remain Step 18-gated. Step 17 does not use
PER, PBR, ROE, market-cap fundamentals, financial statements, or valuation
features. Financial or valuation columns in ranking or price inputs are rejected
before evaluation.

## Worker Boundary

`Quant_mvp/backtest_mvp` owns the core contracts, config, runner, result
aggregation, and focused tests. Step 17 guardrails, report validation,
forbidden-language checks, generated-output boundary tests, and report/docs
boundary material remain integration-facing support files.
