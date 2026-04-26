# Quant Backtest MVP

`Quant_mvp/backtest_mvp` is the canonical home for the conservative
evaluation-only backtest module.

The module consumes read-only technical ranking snapshots and OHLCV price rows.
It returns backtest-specific result objects only; it does not define scores,
change rankings, update reports, activate valuation/fundamental data, or feed
realized returns upstream.

Canonical import:

```python
from Quant_mvp.backtest_mvp import BacktestConfig, run_conservative_backtest
```

Legacy import compatibility remains available through `src.backtest` while
callers migrate.

Canonical config:

```text
Quant_mvp/backtest_mvp/config/backtest.toml
```

Generated outputs remain outside source control by default, normally under
`reports/backtest/generated/`.
