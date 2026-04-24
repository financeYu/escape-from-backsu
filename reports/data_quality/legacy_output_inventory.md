# Legacy Output Inventory

## Status

This inventory was created during Step 3 directory/config/schema cleanup.

No scanner script was run.
No ranking was generated.
The files below are existing legacy/background artifacts, not fresh Step 3 outputs.

## chart_mvp outputs

| path | type | observed status | note |
| --- | --- | --- | --- |
| `chart_mvp/outputs/latest_top.csv` | ranking-like CSV | legacy/background | Existing file dated 2026-04-21; not generated in Step 3 |
| `chart_mvp/outputs/latest_top.json` | ranking-like JSON | legacy/background | Existing file dated 2026-04-21; not generated in Step 3 |
| `chart_mvp/outputs/latest_top5.csv` | ranking-like CSV | legacy/background | Existing file dated 2026-04-21; not generated in Step 3 |
| `chart_mvp/outputs/latest_top5.json` | ranking-like JSON | legacy/background | Existing file dated 2026-04-21; not generated in Step 3 |
| `chart_mvp/outputs/last_run_meta.json` | run metadata | legacy/background | Existing metadata from prior runtime execution |

## chart_mvp scan results

| path | type | observed status | note |
| --- | --- | --- | --- |
| `chart_mvp/data/scan_results/top5_scan_20260419.csv` | ranking-like scan CSV | legacy/background | Existing scan output; not generated in Step 3 |
| `chart_mvp/data/scan_results/top5_scan_20260420.csv` | ranking-like scan CSV | legacy/background | Existing scan output; not generated in Step 3 |
| `chart_mvp/data/scan_results/api_render_test.png` | generated image | legacy/background | Rendering artifact, not a ranking |

## chart_mvp chart images

Existing chart images are present under:

```text
chart_mvp/outputs/charts/
```

Observed examples:

- `000100.png`
- `000270.png`
- `000660.png`
- `000670.png`
- `000810.png`
- `005380.png`
- `005930.png`
- `373220.png`
- `402340.png`
- `legend_layout_test.png`

These are generated chart artifacts and are not Step 3 validation outputs.

## Existing child-project validation reports

Existing files under `chart_mvp/reports/data_quality/`:

- `financial_data_check.md`
- `loader_inventory.md`
- `missing_data_summary.csv`
- `price_data_check.md`
- `schema_validation.csv`

These reports are treated as prior/background validation artifacts unless explicitly regenerated in a validation-only step.

## Child project ranking-like outputs

No ranking-like output files were found under `Quant_mvp`, `reserch_mvp`, or `review_mvp` during Step 3 inspection.

The external sibling `C:/Users/jjaew/Project/stock_mvp` contains code files named `scorer.py`, `backtest.py`, and `report.py`, but no ranking output files were inspected or merged during Step 3.

