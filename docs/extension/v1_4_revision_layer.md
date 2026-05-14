# v1.4 Revision Layer

## Purpose

v1.4 adds a point-in-time revision layer skeleton for earnings revision and
estimate revision evidence. The goal is not to activate a valuation or
fundamental score. The goal is to define the contract, check available data,
derive only allowlisted revision features, and compare technical-only evidence
against technical-plus-revision evidence when sufficient point-in-time inputs
exist.

All outputs remain evidence-only, candidate-only, and manual-review-support
only. v1.4 does not authorize live trading, brokerage integration, orders,
buy/sell/hold wording, production ranking replacement, automatic rebalance
instructions, future-return claims, proven-alpha language, valuation/fundamental
active scoring, or production activation.

## Outputs

The skeleton runner emits these artifact keys:

- `v1_4_revision_data_contract`
- `v1_4_revision_coverage_report`
- `v1_4_revision_feature_manifest`
- `v1_4_revision_layer_registry_entry`
- `v1_4_incremental_revision_evidence_report`
- `v1_4_revision_manual_review_section`

## Required Data

The v1.4 revision handoff requires one row per candidate where available:

- `candidate_id`: exact `EvaluationEvidenceV1` candidate ID
- `evidence_id`: exact `EvaluationEvidenceV1` evidence ID
- `revision_source_ref`: approved source, snapshot, extraction batch, or vendor
  reference
- `estimate_as_of_date`: consensus or estimate date represented by the row
- `available_at`: date this row was available to the evaluation; must be on or
  before `EvaluationEvidenceV1.date_range.end`
- `fiscal_period`: comparable fiscal target for the EPS estimate
- `sector_id`: sector bucket for relative comparison
- `eps_estimate_current`: point-in-time EPS consensus or estimate value
- `eps_estimate_1m_ago`: comparable point-in-time estimate about one month
  earlier
- `eps_estimate_3m_ago`: comparable point-in-time estimate about three months
  earlier
- `analyst_revision_up_count_1m`: upward revision count in the one-month window
- `analyst_revision_down_count_1m`: downward revision count in the one-month
  window
- `sector_revision_percentile`: point-in-time sector-relative revision
  percentile or equivalent normalized rank

Optional but recommended data for later completion:

- source license or local approval note
- extraction timestamp
- estimate vendor field names
- currency/unit metadata
- fiscal period calendar mapping
- sector taxonomy version
- stale-data flag or maximum allowed age
- restatement or correction flag when a source revises historical consensus

## Point-In-Time Rules

- `available_at` must be on or before the candidate evaluation end date.
- Rows available after the evaluation end are marked failed and excluded from
  the feature manifest.
- Missing rows remain visible in `coverage_gap_summary`.
- Duplicate `candidate_id` rows are rejected rather than merged.
- `candidate_id` and `evidence_id` must match `EvaluationEvidenceV1` exactly.
- Current or corrected consensus rows without an `available_at` lineage are not
  sufficient for v1.4.

## Allowlisted Features

Only these revision features may enter the v1.4 feature manifest:

- `eps_revision_change_1m`
- `eps_revision_change_3m`
- `revision_diffusion_1m`
- `sector_relative_revision_percentile`

Forbidden feature fields include labels, target fields, return fields,
production score fields, actual reported EPS, and post-evaluation consensus
fields.

## Layer Status

The v1.4 layer registry can only be:

- `candidate_only`
- `diagnostic_only`

It must never be `active`. When point-in-time coverage is insufficient, the
layer remains `diagnostic_only`. When coverage is sufficient, it may become
`candidate_only` for manual review comparison only.

## Temporary Diagnostic Closure

Under the current route, v1.4 is temporarily complete as
`diagnostic_only`. This means the fail-closed contract, required data list,
coverage report, empty feature manifest path, layer registry entry, and
chart_mvp diagnostic data-support builders are in place, so v1.5/v1.6 planning
can proceed without treating v1.4 as PIT-complete.

KIS revision raw snapshots may continue to accumulate during daily chart
refreshes. They are raw data-support artifacts only. Until a later explicit PIT
promotion review passes, no downstream step may auto-reference them as v1.4
revision features, score inputs, ranking inputs, valuation inputs, or
incremental evidence.

## Incremental Evidence

`v1_4_incremental_revision_evidence_report` is skipped unless all are present:

- point-in-time revision feature rows
- technical-only comparison artifact
- technical-plus-revision comparison artifact

The report is for manual review support only. It does not replace production
ranking or make performance certainty claims.

## Data Availability Status

Current v1.4 implementation is a skeleton. It defines the contract and
validators, but no approved full revision source is wired in yet. Required next
data work is:

1. Identify an approved point-in-time consensus or estimate revision source.
2. Confirm candidate-level `candidate_id` and `evidence_id` lineage.
3. Produce a local handoff fixture or generated data-support artifact with the
   required fields above.
4. Run coverage and point-in-time leakage checks before allowing
   `candidate_only` comparison.

## Chart MVP Diagnostic Handoff

`chart_mvp` can build a diagnostic-only v1.4 handoff from existing local
financial statement caches and the v1.3 candidate liquidity handoff. This
handoff can populate candidate lineage, ticker linkage, fiscal period labels,
and an EPS estimate row selected from the candidate row reference date where
available. The selector uses the candidate row `as_of_date` first, falls back to
`market_cap_as_of_date`, prefers estimate fiscal periods that contain that date,
and otherwise uses the closest available estimate period.

The generated diagnostic handoff is not sufficient point-in-time revision data.
The current chart financial cache contains latest observed statement-like rows
with columns such as `code`, `metric`, `period`, and `value`; it does not contain
`available_at`, `estimate_as_of_date`, historical 1m/3m consensus snapshots,
analyst revision breadth, or sector-relative revision percentiles. Rows built
from this source must remain `diagnostic_only` and should produce missing-field
coverage reasons in the v1.4 revision runner.

Local generation command:

```powershell
.\.venv\Scripts\python.exe chart_mvp\scripts\build_v1_4_revision_diagnostic_handoff.py
```

Default generated artifacts:

- `chart_mvp/data/v1_4_revision/v1_4_candidate_revision_diagnostic_handoff_latest.csv`
- `chart_mvp/data/v1_4_revision/v1_4_candidate_revision_diagnostic_manifest_latest.json`

`chart_mvp` can also generate a separate KRX sector diagnostic supplement:

```powershell
.\.venv\Scripts\python.exe chart_mvp\scripts\build_v1_4_krx_sector_supplement.py
```

Default generated artifacts:

- `chart_mvp/data/v1_4_revision/v1_4_krx_sector_supplement_latest.csv`
- `chart_mvp/data/v1_4_revision/v1_4_krx_sector_supplement_manifest_latest.json`

KIS revision raw snapshots can be accumulated during the existing KOSPI200
daily chart refresh. `chart_mvp/app/run_daily.py --due-only` requests
append-only KIS raw snapshots for the current KOSPI200 universe and stores the
token preflight plus collector status in the daily run metadata. This remains
diagnostic data support only; it does not promote revision features or alter
scanner output. The daily metadata must keep
`usable_for_v1_4_feature_manifest = false`,
`auto_reference_allowed = false`, and a downstream consumption policy blocking
feature, score, ranking, and incremental-evidence use until explicit PIT
promotion.

This supplement can fill `diagnostic_sector_id` and
`diagnostic_sector_name` from KRX sector classifications, but it is not an
analyst revision source and does not produce `sector_revision_percentile`.
It must remain separate from the PIT revision feature manifest until an
approved point-in-time sector taxonomy plus revision distribution is available.

## Completion Statement

Temporary v1.4 closure is complete when diagnostic-only artifacts can fail
closed, KIS raw snapshot collection can continue as isolated data support, and
downstream routes are blocked from consuming raw/diagnostic revision material
as active features. Full v1.4 completion still requires point-in-time-safe
revision inputs, explicit coverage, `candidate_only` or `diagnostic_only` layer
status, and technical-only versus technical-plus-revision evidence comparison
as manual-review support.
