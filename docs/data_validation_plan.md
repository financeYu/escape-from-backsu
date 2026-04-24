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

Financial collector validation is complete for Step 2.

The `chart_mvp` Naver financial loader/cache path was used to generate local runtime caches matching:

```text
chart_mvp/data/*_financial_statements.csv
```

Current validation context:

- financial cache files: 200
- financial rows: 26,208
- unique KOSPI200 codes: 200
- current report: `chart_mvp/reports/data_quality/financial_data_check.md`
- source-controlled summary: `docs/step2_financial_validation_summary.md`

These runtime caches and data-quality reports are not source-controlled project state.

Financial data remains:

```text
valuation_deferred
inventory_only
GUI display only if already present
point_in_time_status = unverified
```

The Naver financial rows currently extracted by `chart_mvp` do not include disclosure, filing, or availability dates. Therefore financial data remains unsafe for valuation scoring until a later valuation branch obtains point-in-time-safe fields and lag policy.

The follow-up is explicitly assigned to Step 18. Step 9/10 technical work must continue to reject financial/fundamental inputs.

## Report Outputs

Validation and inventory reports should live under:

```text
reports/data_quality/
```

Current Step 3 reports:

- `reports/data_quality/legacy_output_inventory.md`
- `reports/data_quality/subproject_inventory.md`

Existing child-project reports under `chart_mvp/reports/data_quality/` are legacy/background artifacts unless explicitly regenerated in a validation-only step. `financial_data_check.md` has been regenerated for Step 2 completion; the directory remains runtime output.

Step 6 preprocessing reports are configured in `config/data.toml`:

- `[preprocess].summary_report_path`
- `[preprocess].validation_summary_path`
- `[preprocess].invalid_rows_report_path`

These reports are preprocessing validation artifacts only. They must include `financial_data_status = valuation_deferred` and must not include indicators, scores, rankings, composites, or backtest results.

## Boundaries

Validation must not:

- generate rankings
- run backtests
- implement scores
- change score definitions
- merge financial data into technical scores
- merge financial data into final composite scores
- mark old outputs as current results
