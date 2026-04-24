# Roadmap Status

## Current Active Step

Step 3 = 디렉터리 / config / 표준 스키마 정리

## Current Verdicts

- Step 1 verdict: COMPLETE or mostly complete
- Step 2 verdict: PARTIALLY COMPLETE
- Step 3 permission: Yes, with minor follow-up

## Step 2 Remaining Follow-Ups

- strengthen `schema_validator.py`
- add dtype expectations
- add date parseability check
- add numeric conversion safety check
- add duplicate key validation
- add explicit ticker leading-zero preservation check
- run financial validation once financial statement sample exists
- document legacy outputs such as `outputs/latest_top*` and `data/scan_results/*`
- keep financial data `valuation_deferred`

## Valuation Status

- `valuation_status = deferred`
- `financial_data_usage_now = inventory_only_or_gui_display_only`
- `point_in_time_status = unverified` unless disclosure or availability date exists
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`

## Active Guardrails

- no future data
- no lookahead
- no silent score redefinition
- config-first implementation
- no score implementation before documented score definitions
- no backtest before Step 17
- no valuation language for price-only evidence

