# Legacy Output Inventory

## Status

This inventory documents existing legacy/background runtime artifacts found in the workspace.

- No scanner script was run for this inventory.
- No ranking was generated for this inventory.
- Existing ranking-like outputs must not be reused as Step 3 validation evidence or Step 5 score-definition evidence.
- Existing ranking-like outputs must not be treated as adoption, alpha, backtest, valuation, or final composite evidence.
- Cached data can be used only as background inventory until schema and point-in-time boundaries are explicitly validated.

## Inventory

| path | artifact_type | source_step | current_status | can_use_for_current_step | notes |
|---|---|---:|---|---|---|
| `chart_mvp/outputs/latest_top.csv` | ranking_output | unknown | legacy | No | Existing runtime output dated 2026-04-21; generated before current score definitions. Do not reuse as Step 3/5 evidence. |
| `chart_mvp/outputs/latest_top.json` | ranking_output | unknown | legacy | No | Existing runtime output dated 2026-04-21; generated before current score definitions. Do not reuse as Step 3/5 evidence. |
| `chart_mvp/outputs/latest_top5.csv` | ranking_output | unknown | legacy | No | Existing runtime output dated 2026-04-21; `score` values are `0.0` and metadata indicates a temporary Top-5 override. |
| `chart_mvp/outputs/latest_top5.json` | ranking_output | unknown | legacy | No | Existing runtime output dated 2026-04-21; paired with `latest_top5.csv`. Do not reuse as score evidence. |
| `chart_mvp/outputs/last_run_meta.json` | run_metadata | unknown | legacy | No | Existing runtime metadata dated 2026-04-21; contains local absolute output paths and `temporary_top5_override = true`. |
| `chart_mvp/data/scan_results/top5_scan_20260419.csv` | ranking_output | unknown | legacy | No | Existing scan output from 2026-04-19. Generated before current score-definition work. |
| `chart_mvp/data/scan_results/top5_scan_20260420.csv` | ranking_output | unknown | legacy | No | Existing scan output from 2026-04-20. Generated before current score-definition work. |
| `chart_mvp/data/scan_results/api_render_test.png` | generated_image | unknown | background | No | Rendering artifact, not score evidence or validation evidence for current Step 5. |
| `chart_mvp/outputs/charts/*.png` | generated_chart | unknown | background | No | 10 generated chart images observed. Useful only as prior rendering artifacts, not ranking or score evidence. |
| `chart_mvp/data/*_daily_prices.csv` | cached_price_data | unknown | background | Maybe | 200 cached daily-price CSV files observed. Use only after schema/date/numeric/ticker validation; not a ranking result. |
| `chart_mvp/data/005930_chart_preview.png` | generated_image | unknown | background | No | Local chart preview artifact under the cache directory. |
| `chart_mvp/reports/data_quality/financial_data_check.md` | validation_report | Step 2 follow-up | background | Maybe | Background data-quality report only; financial data remains `valuation_deferred`. |
| `chart_mvp/reports/data_quality/loader_inventory.md` | validation_report | Step 2 follow-up | background | Maybe | Background loader inventory only; does not authorize score implementation or ranking use. |
| `chart_mvp/reports/data_quality/missing_data_summary.csv` | validation_report | Step 2 follow-up | background | Maybe | Background missing-data report only; requires current schema context before reuse. |
| `chart_mvp/reports/data_quality/price_data_check.md` | validation_report | Step 2 follow-up | background | Maybe | Background price-data report only; not score adoption evidence. |
| `chart_mvp/reports/data_quality/schema_validation.csv` | validation_report | Step 2 follow-up | background | Maybe | Background schema report only; use only for validation context. |
| `reports/data_quality/legacy_output_inventory.md` | prior_inventory_report | Step 3 | superseded_by_docs | Maybe | Prior Step 3 inventory report. Superseded as the canonical inventory by this document. |
| `reports/data_quality/subproject_inventory.md` | prior_inventory_report | Step 3 | background | Maybe | Prior Step 3 project inventory. Useful for project-boundary context only. |

## Current-Step Boundary

Current active step: Step 5, Score Architect.

Allowed use:

- inventory awareness
- path and artifact classification
- identifying what must not be reused as evidence
- background validation context where explicitly marked `Maybe`

Disallowed use:

- treating legacy rankings as current rankings
- using legacy rankings as Step 3 completion evidence
- using legacy rankings as Step 5 score-definition evidence
- inferring score usefulness, alpha, robustness, valuation, or backtest results from these artifacts
- regenerating or deleting runtime outputs as part of this inventory

## Excluded From This Inventory

- `Quant_mvp/reports/research_ingestion/*`: research-ingestion and Step 5 handoff materials, not legacy ranking outputs.
- `Quant_mvp/reports/technical_review/*`: governance/review material, not scanner runtime output.
- `Quant_mvp/reports/valuation_review/*`: valuation-boundary material; valuation remains deferred.
- Source files under `src/`, `chart_mvp/src/`, `Quant_mvp/src/`, and tests: source-controlled project state, not legacy output.

