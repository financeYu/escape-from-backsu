# Project Structure

## Canonical Root

Canonical root for the quant project is:

```text
master_mvp/
```

Evidence:

- user instruction says to treat `master_mvp` as canonical unless repository evidence clearly shows a different root
- root-level `AGENTS.md` exists and defines the master agent
- root-level `README.md`, `docs/project_registry.md`, and child project directories are present

No contrary repository evidence was found during Step 3 inspection.

## Child and Legacy Project Handling

Child projects under the canonical root:

- `Quant_mvp`: quant product umbrella, score governance, research intake,
  and config-policy project
  - `Quant_mvp/backtest_mvp`: Quant-dependent evaluation-only backtest
    subproject
- `reserch_mvp`: canonical upstream research-ingestion project and research
  evidence lane for the Quant product umbrella
- `chart_mvp`: current downstream runnable scanner/runtime project for
  Quant-reviewed specs
- `review_mvp`: specialist code-review and optional final-validation support project

External sibling projects near the root:

- `C:/Users/jjaew/Project/stock_mvp`: legacy or unknown prior stock project

Only projects under the canonical root are active. Child and legacy logic must
not be merged automatically. Any import, migration, or deletion requires an
explicit reason and review.

Logical Quant umbrella routing does not change the physical project layout.
`reserch_mvp` and `chart_mvp` remain separate child projects until a dedicated
post-MVP migration explicitly approves path moves, import updates, and
generated-output boundary checks.

## Target Module Boundaries

Step 3 creates these canonical target boundaries:

```text
src/loader
src/preprocess
src/indicators
src/features
src/scores
src/normalize
src/composite
src/diagnostics
src/scanner
```

These directories define future module ownership. They do not imply that existing working runtime code has been migrated.

Step 6 adds the canonical preprocessing entry point:

- `src/preprocess/daily_ohlcv.py`

This module prepares config-defined daily OHLCV processed data only. It does not implement Step 7 indicators, Step 9 scores, rankings, composites, valuation integration, or backtests.

Backtest implementation ownership now lives under:

- `Quant_mvp/backtest_mvp`

The legacy `src/backtest` package is a compatibility facade and should not own
new backtest behavior.

## Current Known Runtime Locations

Current provider/loader code remains in `chart_mvp`:

- `chart_mvp/src/stock_core/providers/naver_finance.py`
- `chart_mvp/src/stock_core/providers/naver_price_provider.py`
- `chart_mvp/src/stock_core/cache/csv_cache.py`
- `chart_mvp/src/preprocess/schema_validator.py`
- `chart_mvp/src/preprocess/price_data_validator.py`
- `chart_mvp/src/preprocess/financial_data_validator.py`

This is the current legacy/provider runtime location. Step 3 does not rename or move these files.

## Legacy Output Handling

Existing generated outputs are background artifacts:

- `chart_mvp/outputs/latest_top*`
- `chart_mvp/outputs/last_run_meta.json`
- `chart_mvp/data/scan_results/*`
- `chart_mvp/outputs/charts/*`
- `chart_mvp/reports/data_quality/*`

They are not fresh Step 3 rankings and must not be presented as current Step 3 results.

## Intentionally Not Implemented In Step 3

Step 3 does not implement:

- technical scores
- composite scores
- final rankings
- backtests
- valuation scores
- fundamental scores
- financial-data integration into technical scoring
- financial-data integration into final composite scoring
