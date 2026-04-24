# Roadmap Status

## Current Active Step

Step 5 = Score Architect: MVP 기술 점수 후보 정의

## Current Verdicts

- Step 1 verdict: COMPLETE or mostly complete
- Step 2 verdict: PARTIALLY COMPLETE
- Step 3 verdict: COMPLETE
- Step 4 verdict: COMPLETE
- Step 5 permission: Yes, with minor follow-up

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

## Step 4 Boundary Status

- Technical and valuation boundaries are fixed in `docs/technical_valuation_boundary.md`.
- Price-only evidence must not be described as valuation evidence.
- Financial data remains excluded from technical and final composite scoring.
- Valuation review remains deferred until point-in-time-safe financial data is available.

## Active Guardrails

- no future data
- no lookahead
- no silent score redefinition
- config-first implementation
- no score implementation before documented score definitions
- no backtest before Step 17
- no valuation language for price-only evidence
