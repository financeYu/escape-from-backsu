# Data Validation Plan

## Status

Step 3 schema and validation-boundary cleanup.

This plan does not generate rankings, run scanner scripts, implement scores, implement composites, run backtests, or perform valuation scoring.

## Schema-Level Validation

Schema validation should report:

- required column presence
- alias normalization availability
- ticker string-like dtype
- six-character ticker format
- leading-zero preservation
- date parseability
- OHLCV numeric convertibility
- duplicate `ticker`/`date` absence
- report-friendly summary rows

## Price-Level Validation

Price validation remains separate from score implementation.

Existing validation concepts include:

- missing required fields
- date ordering
- minimum history length
- warmup eligibility
- non-positive OHLC values
- negative volume
- impossible high/low relationships
- suspicious return jumps
- suspended-like zero volume or flat OHLC patterns

Thresholds should come from config. They are validation thresholds, not alpha thresholds.

## Financial Validation Status

Financial validation is not complete.

Step 3 inspection found no cached file matching:

```text
chart_mvp/data/*_financial_statements.csv
```

Therefore financial validation has not actually been run against a cached sample.

Financial data remains:

```text
valuation_deferred
inventory_only
GUI display only if already present
```

## Report Outputs

Validation and inventory reports should live under:

```text
reports/data_quality/
```

Current Step 3 reports:

- `reports/data_quality/legacy_output_inventory.md`
- `reports/data_quality/subproject_inventory.md`

Existing child-project reports under `chart_mvp/reports/data_quality/` are legacy/background artifacts unless explicitly regenerated in a validation-only step.

## Boundaries

Validation must not:

- generate rankings
- run backtests
- implement scores
- change score definitions
- merge financial data into technical scores
- merge financial data into final composite scores
- mark old outputs as current results

