# Step 2 Financial Validation Summary

## Status

Step 2 financial collector validation is complete.

This document records source-controlled summary evidence only. The generated
financial caches and data-quality reports remain runtime artifacts.

## Current Validation Snapshot

| item | value |
| --- | --- |
| source project | `chart_mvp` |
| loader/cache path | `chart_mvp/src/stock_core/providers/naver_finance.py`, `chart_mvp/src/stock_core/cache/csv_cache.py` |
| runtime cache pattern | `chart_mvp/data/*_financial_statements.csv` |
| financial cache files | 200 |
| financial rows | 26,208 |
| unique KOSPI200 codes | 200 |
| regenerated report | `chart_mvp/reports/data_quality/financial_data_check.md` |
| point-in-time status | `unverified` |
| future valuation safety | `unsafe_without_availability_dates` |

## Reproduction

From `chart_mvp/`:

```powershell
python scripts/refresh_financial_cache.py
```

Optional smoke run:

```powershell
python scripts/refresh_financial_cache.py --limit 3 --skip-existing
```

The script refreshes local runtime caches only. It does not produce rankings,
composites, valuation scores, technical scores, forward returns, or backtests.

## Boundary

- `collected_at` is an observation timestamp only.
- `collected_at` must not verify historical point-in-time financial availability.
- Valuation scoring remains deferred until disclosure, filing, or availability dates exist and a reporting-lag policy is documented.
- Financial/fundamental data must not enter `technical_composite_score`.
- Financial/fundamental data must not enter `final_composite_score`.
- Financial/fundamental data must not enter technical scoring.

## Required Follow-Up

The next valuation-related step must start from a point-in-time financial
metadata schema before any valuation score or valuation-aware composite work.

Required fields:

- `ticker`
- `period`
- `metric`
- `value`
- `filing_date`
- `availability_date`
- `disclosure_id` or `source_report_id`
- `source_vendor`
- `collected_at`

Required guardrails:

- no valuation scoring while `point_in_time_status = unverified`
- row-level exclusion for missing or unparseable filing/availability dates
- no technical or final composite integration before explicit adoption policy
