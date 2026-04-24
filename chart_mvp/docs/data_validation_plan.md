# Data Validation Plan

Status: Project Step 2 collector and data layer validation.

## Scope

This step validates Naver Finance collector outputs and cache readiness. It does not implement trading scores, composite scores, backtests, stock rankings, or financial-statement-driven analysis.

## Source Files

Price data:

- `src/stock_core/providers/naver_finance.py`
- `src/stock_core/providers/naver_price_provider.py`
- `src/stock_core/cache/csv_cache.py`
- `data/<code>_daily_prices.csv`

Financial statement data:

- `src/stock_core/providers/naver_finance.py`
- `src/stock_core/cache/csv_cache.py`
- `data/<code>_financial_statements.csv`

## Price Validation Checks

The price validator checks:

- required column existence
- ticker format
- date parseability
- numeric OHLCV types
- duplicate ticker-date rows
- per-ticker date ordering
- open/high/low/close `<= 0`
- volume `< 0`
- high `< low`
- high `< open`
- high `< close`
- low `> open`
- low `> close`
- missing close
- missing volume
- suspicious large return jumps
- latest date coverage by ticker
- minimum history length by ticker
- warmup eligibility
- suspended-like rows such as zero volume or repeated flat OHLC patterns

Thresholds are configurable in `PriceValidationConfig`:

| key | default |
| --- | --- |
| `min_history_length` | `120` |
| `warmup_min_history_length` | `60` |
| `suspicious_return_threshold` | `0.30` |
| `flat_pattern_window` | `5` |
| `latest_coverage_lag_days` | `10` |

## Financial Statement Validation Checks

The financial statement validator only checks:

- available columns
- fiscal period columns
- disclosure date or availability date presence
- `point_in_time_status`
- whether data is safe or unsafe for future financial-statement work

If disclosure date or availability date is unavailable, the validator marks `point_in_time_status = unverified`.

Current Step 2 completion note:

- `chart_mvp` loader/cache functions were used to populate 200 local `data/<code>_financial_statements.csv` caches.
- The refreshed financial cache contains 26,208 inventory rows across 200 unique KOSPI200 codes.
- Financial statement validation was rerun in schema-inventory mode only.
- Current extracted Naver financial rows do not include disclosure, filing, or availability dates, so `point_in_time_status = unverified`.
- Financial data remains inventory-only and must not enable valuation scoring, technical scoring, composite scoring, ranking, or backtesting.

## Reports

Reports are written to `reports/data_quality/`:

- `loader_inventory.md`
- `price_data_check.md`
- `financial_data_check.md`
- `schema_validation.csv`
- `missing_data_summary.csv`

## Operating Rules

- Do not alter loader logic during validation unless a documented loader bug blocks validation.
- Do not silently fill missing data.
- Keep threshold values configurable.
- Treat financial statement data as inventory only until point-in-time safety is verified.
- Keep price and financial statement data separate for this step.
