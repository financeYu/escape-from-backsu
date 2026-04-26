# Step 18 Valuation / Fundamental Boundary

## What Step 18 Adds

Step 18 adds a conservative candidate-only valuation/fundamental expansion layer.
It defines:

- a candidate record schema for point-in-time valuation/fundamental observations
- a candidate metric registry
- validation guardrails for availability dates, metric names, numeric values, and unsafe imputation
- candidate-only report text that is separate from production ranking output
- tests proving valuation/fundamental fields do not enter technical scoring, final ranking, or Step 17 backtest inputs

This layer treats valuation/fundamental data as explanatory candidate data.
It is not an activated trading score.

## What Step 18 Does Not Add

Step 18 does not add:

- a valuation score
- a fundamental score
- a valuation-aware composite
- changes to `technical_composite_score`
- changes to `final_composite_score`
- new ranking behavior
- alpha validation based on valuation/fundamental fields
- Step 17 backtest input changes
- trading recommendations, position sizing, or execution logic
- external network data calls

`ev_ebitda` is intentionally excluded from the default registry until explicit
enterprise value inputs are available.

## Boundary Definitions

`technical score` means daily OHLCV-derived technical/statistical signals and
the existing normalized technical inputs that feed the Step 15 ranking layer.

`valuation/fundamental candidate data` means sidecar observations such as `per`,
`pbr`, `roe`, `debt_to_equity`, or growth metrics with explicit report timing and
availability timing. These records can be parsed, validated, and reported, but
they are not score inputs.

`final ranking score` means the Step 15 `final_composite_score`, which remains
equal to the technical-only composite in the current production ranking output.
Step 18 does not modify that behavior.

`backtest inputs` means frozen Step 15/16-compatible technical ranking snapshots
and OHLCV price data consumed by the Step 17 conservative backtest. Step 18
candidate data is not accepted as a backtest input unless a later roadmap step
explicitly defines and validates that path.

## Canonical Metadata Schema

Step 18 candidate records use this canonical metadata schema:

- `ticker`
- `period`
- `metric`
- `value`
- `filing_date`
- `availability_date`
- `disclosure_id` or `source_report_id`
- `source_vendor`
- `collected_at`

Additional explanatory fields such as `company_name`, `metric_unit`,
`metric_category`, `report_date`, `source`, `quality_flags`, and `notes` may be
carried with the candidate record. Legacy input aliases such as `symbol`,
`fiscal_period`, `metric_name`, `metric_value`, `available_date`, and
`as_of_date` are accepted only as ingestion compatibility aliases and are
normalized to the canonical fields.

## Availability Dates

Every candidate record must include `availability_date`, with `available_date`
or `as_of_date` accepted only as ingestion aliases. This date represents the
earliest date the metric is allowed to be used. `collected_at` is not enough to
prove historical point-in-time availability.

Records without a valid availability date are rejected. Records with
`availability_date` after the evaluation date are rejected for that evaluation.
Rows without parseable `filing_date`, `availability_date`, `source_vendor`,
`collected_at`, and either `disclosure_id` or `source_report_id` are excluded by
validation. Missing values are not filled from future values or cross-sectional
peers. Unsafe imputation flags such as `future_filled`, `backfilled`, or
`cross_sectional_imputed` are blocking errors.

## Reporting Lag And Stale Data Policy

Step 18 records compute reporting lag as `availability_date - filing_date`.
Negative reporting lag is rejected. Reporting lag above 120 calendar days is
rejected by the candidate validator because the availability path is too weak
for point-in-time candidate use.

When an `evaluation_date` is supplied, candidate records older than 540 calendar
days from `availability_date` are rejected as stale. Later valuation adoption
work may replace these conservative defaults only with explicit sector/source
policy and tests. Step 18 does not fill stale records from newer filings.

## Safe Future Integration

A later roadmap step may integrate valuation/fundamental data only after it
adds explicit adoption policy, point-in-time source verification, sector and
stale-data rules where needed, and tests proving no leakage into technical
scores or backtest selection. Until then, Step 18 candidate reports remain
separate explanatory material.
