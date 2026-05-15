# v1.5 Valuation Quality Profitability Layer

## Purpose

v1.5 adds a point-in-time fundamental contract and a pending-data valuation,
quality, profitability, and investment diagnostic layer for candidate review.
Rows with insufficient PIT data are held as `pending_data` and excluded from
feature manifests until the missing data is supplied. The layer is
candidate-only and manual-review-support only. It does not activate
valuation/fundamental scoring, production ranking replacement, live execution,
order generation, or production behavior.

The implementation extends the existing Step 18 candidate-only valuation
contract in `src/valuation` by adding v1.x artifacts, feature manifests,
sector-relative diagnostics, incremental-comparison scaffolding, and a
ManualReviewPacket-compatible valuation section.

## Implementation

- Module: `Quant_mvp/backtest_mvp/valuation_quality_layer_v1_5.py`
- Test: `tests/backtest/test_v1_5_valuation_quality_layer.py`
- Owner lane: Quant governance with separated valuation/fundamental review
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`
- Valuation review gate: `.agents/skills/valuation_review/SKILL.md`

## Inputs

Inputs are read-only `EvaluationEvidenceV1` records plus optional point-in-time
fundamental handoff rows.

Required fundamental row fields:

- `candidate_id`
- `evidence_id`
- `ticker`
- `evaluation_date`
- `fiscal_period`
- `report_period_end_date`
- `filing_date` or `disclosure_date`
- `availability_date` or equivalent `available_at`
- `source_ref` or equivalent source identifier
- `field_name`
- `value`
- `unit`

Optional but supported fields include:

- `currency`
- `sector_id`
- `industry_id`
- `industry_name`
- `reporting_lag_policy`
- `stale_data_policy`
- `restatement_policy`
- `pit_validation_status`
- `coverage_status`
- `data_quality_flags`
- `pending_reason`
- `blocked_reason`

## Point-In-Time Rules

- `availability_date` must be on or before `evaluation_date`.
- `filing_date` or `disclosure_date` must be on or before
  `evaluation_date`.
- `report_period_end_date` must not be after `evaluation_date`.
- Records with missing availability metadata are marked `pending_data`.
- Records available only after evaluation are marked `pending_data` and
  excluded from feature manifests.
- Later restated values require restatement availability metadata; otherwise
  the row remains `pending_data`.
- Stale rows remain `pending_data` when they exceed the configured stale-age
  policy.
- Duplicate `candidate_id` plus `field_name` rows are rejected.

## Outputs

The runner emits these artifact keys:

- `v1_5_fundamental_data_contract`
- `v1_5_pit_validation_report`
- `v1_5_valuation_feature_manifest`
- `v1_5_quality_profitability_feature_manifest`
- `v1_5_investment_feature_manifest`
- `v1_5_sector_relative_valuation_report`
- `v1_5_layer_registry_entry`
- `v1_5_incremental_valuation_evidence_report`
- `v1_5_manual_review_valuation_section`
- `v1_5_validation_manifest`
- `v1_5_completion_report`

## Feature Manifests

Supported valuation fields are derived only from PIT-safe rows:

- `price_to_book`
- `book_to_price`
- `price_to_earnings`
- `earnings_to_price`
- `price_to_sales`
- `sales_to_price`
- `dividend_yield`

Supported quality and profitability fields are emitted only when PIT-safe rows
exist:

- `roe`
- `roa`
- `gross_profitability_assets`
- `operating_margin`
- `net_margin`
- `debt_ratio`
- `interest_coverage`
- `cash_flow_quality`
- `earnings_stability`

Supported investment diagnostics are accepted only as precomputed PIT rows:

- `asset_growth`
- `capex_intensity`
- `accruals_proxy`
- `share_issuance_dilution_proxy`
- `inventory_growth`

The runner does not infer multi-period investment diagnostics from incomplete
single-period fundamentals. Unsupported or unavailable features remain visible
with `pending_data` status.

## Sector-Relative Diagnostics

`v1_5_sector_relative_valuation_report` keeps raw values separate from
sector-adjusted values. A sector-adjusted value is emitted only when
`sector_id` exists and the configured minimum peer count is met. Otherwise the
row is marked `pending_data`.

## Incremental Evidence

`v1_5_incremental_valuation_evidence_report` remains `pending_data` unless all are
available:

- PIT valuation, quality, profitability, or investment feature rows
- technical plus ML comparison artifacts
- technical plus ML plus valuation-quality comparison artifacts

The comparison framework is limited to manual-review diagnostics such as
false-positive reduction, coverage changes, risk-adjusted evidence comparison,
data-quality limitations, sector-relative usefulness, and pending-data status.

## Layer Status

The v1.5 layer registry entry can only be:

- `candidate_only`
- `diagnostic_only`

It must never be `active`. The current repository registry keeps v1.5
`diagnostic_only` until real PIT fundamental data coverage is verified beyond
fixtures.

## Data Availability Status

Current v1.5 implementation is LIMITED COMPLETE when fixture or available rows
prove the contract path, but repository-wide real PIT fundamental coverage is
not verified. Missing real-data requirements remain pending:

1. Candidate-level PIT fundamental source references.
2. `availability_date` and filing or disclosure lineage.
3. Sector metadata with enough peers for sector-relative diagnostics.
4. Restatement and stale-data policy metadata.
5. Paired technical plus ML and technical plus ML plus valuation comparison
   artifacts.

## Minimum Real-Data Handoff Request

Real-data risk can be reduced by supplying an offline PIT-safe handoff file
that matches the v1.5 contract. Each row must represent one
`candidate_id` plus `evidence_id` plus `field_name` value that was available
by `evaluation_date`.

Minimum columns:

- `candidate_id`
- `evidence_id`
- `ticker`
- `evaluation_date`
- `fiscal_period`
- `report_period_end_date`
- `filing_date` or `disclosure_date`
- `availability_date`
- `source_ref`
- `field_name`
- `value`
- `unit`
- `currency`
- `sector_id`
- `industry_id`
- `reporting_lag_policy`
- `stale_data_policy`
- `restatement_policy`
- `data_quality_flags`

Plain-language data request:

- For every reviewed candidate: the ticker, evaluation date, and matching
  `candidate_id` / `evidence_id`.
- For every fundamental value: the fiscal period, report period end date,
  filing or disclosure date, availability date, source reference, field name,
  numeric value, unit, and currency.
- For sector-relative checks: sector and industry IDs, plus enough same-sector
  peer rows.
- For restatement safety: whether the value was original, restated, or
  restated after the evaluation date.
- For incremental comparison: the existing technical+ML comparison packet and
  the technical+ML+valuation comparison packet.

Recommended coverage:

- Include all candidates present in the corresponding `EvaluationEvidenceV1`
  packet, or provide explicit `pending_data` rows with reasons.
- Include enough same-sector rows to satisfy the configured sector peer-count
  policy before interpreting sector-relative diagnostics.
- Include original disclosure or filing lineage, not latest-only restated
  values.
- Keep labels, realized future returns, analyst recommendations, production
  ranks, and runtime scores out of the handoff.

Additional root approval is required before adding a new live/vendor data
ingestion path, expanding the universe, querying external market-data services,
or treating valuation diagnostics as active ranking or production evidence.

## Chart Local Pending Handoff

`chart_mvp` can repackage existing local financial cache rows into a v1.5
handoff-shaped pending-data file:

- Builder: `chart_mvp/src/stock_core/ml/v1_5_valuation_quality_handoff.py`
- CLI: `chart_mvp/scripts/build_v1_5_valuation_quality_handoff.py`
- Default output directory: `chart_mvp/data/v1_5_valuation`

This fills only data that already exists locally:

- `candidate_id`
- `evidence_id`
- `ticker`
- `company_name`
- `evaluation_date`
- selected local financial cache metrics mapped to v1.5 `field_name`
- `value`
- `unit`
- `source_ref`
- `sector_id` and `industry_name` when the v1.4 sector supplement exists

The chart-local handoff cannot make the row `available` for v1.5 because the
local chart financial cache does not prove:

- `filing_date` or `disclosure_date`
- `availability_date`
- source lineage proving the value was available by `evaluation_date`
- restatement policy metadata
- stale data policy metadata
- reporting lag policy metadata

Therefore emitted rows must remain `pending_data` and excluded from active
feature manifests until the missing PIT metadata is supplied.

## Local Supplementation Plan

`chart_mvp/src/stock_core/ml/v1_5_supplementation.py` adds the safe local
supplementation layer on top of the pending handoff. It performs no external
network collection. It can:

- attach locally imported OpenDART metadata when a CSV import is supplied
- attach disclosure-list metadata from a local
  `opendart_v1_4_raw_snapshots/*/*.jsonl` snapshot when the CSV import is absent
- apply `opendart_rcept_dt_next_trading_day_v1` as the availability-date policy
- create a source-lineage hash report for chart financial cache rows
- export collected OpenDART `single_account` rows as a normalized
  `v1_5_opendart_fundamental_collection_latest.csv` file
- compare formula-mappable chart-local ratio fields against collected
  OpenDART statement rows in
  `v1_5_fundamental_value_reconciliation_latest.csv`
- emit formula-variance review and component tables for `price_to_earnings`
  and `price_to_book`
- emit a chart-ratio policy reconstruction table showing whether local
  `PER/PBR` values are internally reconstructable from chart-cache `EPS/BPS`
- emit a formula policy proposal that keeps chart-local valuation ratios
  `reference_only_until_reconciled`
- emit a candidate-only valuation scoring readiness report that explains why
  valuation scoring remains blocked or ready for manual scoring review, while
  separating quality/profitability diagnostic readiness
- create a v1.5 PIT policy registry
- create technical+ML baseline and valuation-overlay comparison scaffolding
- keep real incremental evidence marked `skipped_insufficient_pit_fundamentals`
  until PIT-safe valuation data is available

OpenDART metadata import columns:

- `corp_code`
- `stock_code`
- `report_nm`
- `rcept_no`
- `rcept_dt`

When the helper uses a local raw snapshot, only disclosure-list rows with
`availability_date <= evaluation_date` may be attached. Snapshot-derived
metadata remains metadata-only and does not reconcile the chart-local ratio
values.

Supplementation outputs:

- `v1_5_dart_pit_metadata_enriched_handoff_latest.csv`
- `v1_5_dart_pit_metadata_enriched_manifest_latest.json`
- `v1_5_opendart_fundamental_collection_latest.csv`
- `v1_5_opendart_fundamental_collection_manifest_latest.json`
- `v1_5_fundamental_value_reconciliation_latest.csv`
- `v1_5_fundamental_value_reconciliation_manifest_latest.json`
- `v1_5_valuation_formula_reconciliation_review_latest.csv`
- `v1_5_valuation_formula_reconciliation_review_manifest_latest.json`
- `v1_5_valuation_formula_components_latest.csv`
- `v1_5_valuation_formula_components_manifest_latest.json`
- `v1_5_chart_ratio_policy_reconstruction_latest.csv`
- `v1_5_chart_ratio_policy_reconstruction_manifest_latest.json`
- `v1_5_chart_local_ratio_source_lineage_latest.csv`
- `v1_5_chart_local_ratio_source_lineage_latest.json`
- `v1_5_chart_local_vendor_source_policy_pack_latest.csv`
- `v1_5_chart_local_vendor_source_policy_pack_latest.json`
- `v1_5_per_pbr_formula_candidate_grid_latest.csv`
- `v1_5_per_pbr_formula_candidate_grid_latest.json`
- `v1_5_per_pbr_formula_match_report_latest.json`
- `v1_5_dividend_pit_source_lineage_latest.csv`
- `v1_5_dividend_pit_source_lineage_latest.json`
- `v1_5_feature_level_readiness_latest.csv`
- `v1_5_feature_level_readiness_latest.json`
- `v1_5_valuation_formula_policy_latest.json`
- `v1_5_valuation_scoring_readiness_latest.csv`
- `v1_5_valuation_scoring_readiness_manifest_latest.json`
- `v1_5_fundamental_source_lineage_report_latest.json`
- `v1_5_pit_policy_registry_latest.json`
- `v1_5_technical_ml_baseline_comparison_latest.csv`
- `v1_5_technical_ml_plus_valuation_shadow_comparison_latest.csv`
- `v1_5_incremental_valuation_evidence_report_latest.csv`
- `v1_5_missing_pit_fundamental_requirements_latest.json`
- `v1_5_limited_completion_update_latest.json`

Even when metadata is attached, rows are not promoted to `available` unless
value reconciliation against a PIT-safe fundamental source also passes.

The repeatable local automation entry point is
`chart_mvp/scripts/run_v1_5_fundamental_supplementation_pipeline.py`. By
default it rebuilds local handoff and supplementation outputs without network
collection. With `--collect-opendart`, it collects only the candidate tickers
already present in the v1.5 pending handoff, using existing OpenDART snapshot
support, then rebuilds the v1.5 supplementation artifacts. The automation still
does not promote any field to `available`.

Current reconciliation supports diagnostic comparison only:

- `roe` via OpenDART net income divided by average equity
- `operating_margin` via operating income divided by revenue
- `net_margin` via net income divided by revenue
- `debt_ratio` via total liabilities divided by total equity

`price_to_earnings` and `price_to_book` can be attempted with local evaluation
date close and prior v1.3 `shares_outstanding`, but the current diagnostic
calculation produces formula variance against the chart-local ratios and must
not be promoted without chart-local ratio source lineage, PIT market-source,
and adjusted-price compatibility review.

`dividend_yield` now has a separate PIT source-lineage diagnostic path using
OpenDART `alotMatter` raw snapshots where available. It can be marked
`diagnostic_ready` in `v1_5_feature_level_readiness_latest.csv` when
dividend-per-share, receipt date, conservative availability date, and local
price reference are present. This remains diagnostic only and does not
activate a valuation score.

The valuation scoring readiness report is not a score. It keeps
`scoring_activation_allowed=false` and reports valuation fields as
`blocked_by_reconciliation` until core valuation fields such as
`price_to_earnings` and `price_to_book` are formula-reconciled. It may report
`quality_profitability_readiness_status=diagnostic_ready` for matched fields
such as `debt_ratio`, `net_margin`, `operating_margin`, and `roe`, and
`candidate_overall_readiness_status=partial_diagnostic_ready` when only those
diagnostics are usable. Any actual valuation score, valuation-aware ranking, or
production use still requires separate approval after PIT data review passes.

The formula reconciliation review classifies P/E and P/B variance as blocked
diagnostics rather than failed rows. The PER/PBR formula-candidate grid tests
market-cap, close-times-shares, adjusted-close, EPS, and BPS denominator
candidates and currently recommends `no_safe_match_keep_blocked` because no
formula both matches and has chart-local source availability lineage. Current
likely mismatch families include
fiscal-period/cache ratio policy, adjusted-price or market-cap policy,
shares-outstanding policy, and EPS/BPS denominator differences between the
chart-local ratio source and the recomputed OpenDART plus local-market-source
formula. The current review table also records chart-cache `EPS(원)` and
`BPS(원)` implied prices, making it clear when chart-local ratios embed a price
that differs from the evaluation-date local close.

The chart-ratio policy reconstruction output shows that local `PER/PBR` values
can be reconstructed exactly from chart-cache `EPS/BPS`, but that embedded
price differs materially from the evaluation-date close. This is useful
diagnostic evidence, not promotion evidence. Promotion still requires the
external or vendor lineage for the chart-local ratio source price date,
adjusted/unadjusted price policy, share or per-share denominator policy, and
availability by `evaluation_date`.

The chart-local vendor source policy pack records the recoverable source facts
for the existing `*_financial_statements.csv` rows. Current local files identify
the origin as `Naver Finance` and preserve source row hashes and fiscal/as-of
labels, but they do not preserve vendor snapshot date, source available date,
ratio price date, price policy, adjusted-price policy, or shares policy. The
pack therefore remains `incomplete_reference_only` and keeps chart-local
PER/PBR as `reference_only_until_reconciled`.

## Completion Statement

v1.5 can be marked LIMITED COMPLETE when the contract, validators, feature
manifests, sector-relative scaffolding, incremental-comparison framework,
manual-review section, fixture tests, and pending-data reports exist,
while real PIT fundamental data limitations remain explicit.
