# v0.2 Candidate ML Implementation Gate 1

Status: frozen implementation gate 1 contract. This document prepares the
future candidate-only `prob_up_1d_candidate` implementation path. It does not
train a model, implement inference, generate a sidecar ranking artifact, change
production ranking, change reports, change score formulas, activate valuation,
add market-data ingestion, or expand the KOSPI200 universe.

## Confirmed Context

1. MVP v0.1 remains a frozen KOSPI200 technical-only baseline.
2. The v0.2 candidate-only ML score entry gate is complete.
3. This gate freezes `adjusted_close`, feature allowlist, no-lookahead, and
   sidecar output-path contracts before implementation expands.

## Gate 1 Freeze Target

Gate 1 freezes four implementation prerequisites:

- `adjusted_close` availability for label construction
- technical-only feature allowlist for `prob_up_1d_candidate`
- deterministic no-lookahead validation and test contract
- candidate-only sidecar output path and naming convention

All behavior remains candidate-only. Any future code work must prove that these
contracts are satisfied before model training, inference, sidecar generation,
or broader validation can proceed.

## Existing Path And Schema Verification

Narrow verification found:

- MVP v0.1 canonical OHLCV currently uses `ticker`, `date`, `open`, `high`,
  `low`, `close`, and `volume`.
- Current Step 7 technical indicators are produced from the canonical OHLCV
  path `data/processed/technical_indicators.csv`.
- Current production latest ranking is sorted by `final_composite_score`
  descending and `ticker` ascending.
- Existing v0.2 generated-output roots are
  `reports/v0_2_predictive_probability/` and
  `reports/validation/v0_2_predictive_probability/`.

Because `adjusted_close` is not part of the current MVP v0.1 canonical OHLCV
contract, the future v0.2 implementation must validate an explicit
`adjusted_close` source before constructing labels. `Quant_mvp/config/data.toml`
currently lists optional `adj_close`-style OHLCV fields, but this is not yet a
canonical `adjusted_close` implementation contract. It must not reinterpret the
existing `close` column as adjusted close.

## `adjusted_close` Availability Contract

Canonical label source:

```text
up_1d_label = adjusted_close[t+1] > adjusted_close[t]
```

Frozen rules:

- `adjusted_close` is required for label construction.
- `up_1d_label` is the label column for the future implementation.
- Current repo availability verdict:
  `BLOCKER_UNTIL_CONFIRMED_ADJUSTED_CLOSE_SOURCE`.
- The only narrow repo evidence found is optional `adj_close` support in
  `Quant_mvp/config/data.toml`; implementation must first normalize an approved
  source or alias to canonical `adjusted_close`.
- `adjusted_close[t+1]` and `adjusted_close[t]` must come from the approved
  adjusted-close source for the same ticker and trading calendar.
- Missing `adjusted_close` must fail fast before label construction.
- Missing, null, non-finite, unparseable, duplicate, or timing-ambiguous
  `adjusted_close` rows must fail fast or be marked non-evaluable before
  training/evaluation rows are built.
- The implementation must not silently fall back from `adjusted_close` to
  `close`.
- The implementation must not infer labels from future returns, realized
  returns, generated outputs, backtest results, reports, or rankings.
- `label_availability_time` is the canonical label-availability timestamp for
  this gate.
- A labeled training/evaluation row must not expose `up_1d_label`,
  `adjusted_close[t+1]`, or any label-derived value as a feature.
- As-of-date candidate inference must be possible without known
  `up_1d_label`, `adjusted_close[t+1]`, or `label_availability_time`.

Fail-fast examples for future implementation:

- required column `adjusted_close` is absent
- `adjusted_close` exists only as a report/generated-output field
- `adjusted_close` contains non-numeric values after safe parsing
- the same ticker/date has conflicting adjusted-close values
- the next trading-day adjusted close is unavailable for a labeled
  training/evaluation row
- the code path tries to use `close` when `adjusted_close` is missing

## Feature Allowlist Contract

Default policy:

- Any feature not explicitly allowlisted in this section is disallowed.
- The config allowlist in `Quant_mvp/config/v0_2_candidate_ml_score.toml` is
  the machine-readable Gate 1 source for allowed source fields, allowed feature
  families, and forbidden feature patterns.
- Every feature must be available at or before `decision_time`.
- Every feature must be technical-only under the MVP v0.1 baseline.
- Every rolling or cross-sectional feature must have documented source fields,
  lookback window, and timestamp/availability rule before implementation.

Allowed identity and timing fields:

- `ticker` or future-normalized `symbol`
- `date`
- `decision_time`
- `source_data_availability_time`
- `feature_construction_time`
- same-date KOSPI200 eligibility metadata when it is already available at or
  before `decision_time`

These fields may be used for joining, grouping, validation, and lineage. They
are not ranking outputs and must not be treated as predictive numeric features
unless a later contract explicitly permits an encoded technical use.

Allowed technical source fields:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `adjusted_close`, but only for same-date or trailing technical features and
  label construction under the `adjusted_close` availability contract

Allowed pre-existing technical indicator families:

- trailing returns from current/past price rows
- true range and ATR-style trailing range fields
- trailing realized volatility and volatility-of-volatility fields computed
  only from past returns
- RSI, stochastic, CCI, Williams %R, Bollinger, Donchian-prior, CMF, MACD,
  OBV, ADL, autocorrelation, volume-return correlation, efficiency-ratio, and
  noise-ratio style fields already produced by the project indicator layer
- warmup, coverage, and data-quality metadata used only for validation,
  filtering, or missing-state handling

Allowed derived feature families:

- trailing cumulative return from `adjusted_close`
- trailing absolute-return sum from `adjusted_close`
- prior rolling channel distance, where the feature name and implementation
  exclude current-row channel leakage when using a `prior` convention
- trailing drawdown, rolling peak/trough, downside volatility, and recovery
  ratios computed only from rows available at or before `decision_time`
- trailing volume mean/median, volume surprise, up/down session balance, and
  volume coverage computed only from available OHLCV rows
- same-date KOSPI200 cross-sectional percentile or population-relative fields,
  using only the eligible population available at `decision_time`

Candidate old-score feature routes may be implemented only if each column is
resolved back to the allowlisted technical source or indicator families above.
`technical_composite_score`, `final_composite_score`, production `rank`, and
report-generated fields remain excluded even if they are technical-only outputs.

## Explicit Feature Exclusions

The following are disallowed as model features by default:

- future prices, including `adjusted_close[t+1]` and `next_adjusted_close`
- future returns, forward returns, target returns, realized future returns, and
  label returns
- `up_1d_label` and all label-derived columns
- backtest metrics, evaluation outputs, paper backtest results, diagnostics
  derived from realized outcomes, and performance summaries
- generated rankings, production `rank`, latest ranking outputs, generated
  reports, and generated sidecar outputs
- `technical_composite_score` and `final_composite_score`
- valuation, fundamental, accounting, analyst, filing-date, market-cap,
  PER/PBR/ROE, profitability, quality, or revision fields
- new market-data vendor fields or live vendor assumptions not already approved
  by the project route
- KOSDAQ150, futures/options, Nasdaq, overseas, or multi-universe inputs
- recommendation, target-price, forecasted-return, position-size, alpha, or
  strategy-superiority fields
- any feature whose availability timestamp is after `decision_time`
- any feature filled from missing/warmup state with optimistic values

## Timing Field Definitions

- `decision_time`: timestamp when candidate features are frozen; no feature may
  depend on values unavailable at or before this time.
- `execution_time`: next simulated actionable timestamp after `decision_time`;
  it is metadata only and does not authorize execution guidance.
- `label_time`: timestamp represented by `adjusted_close[t+1]`.
- `label_availability_time`: timestamp when `up_1d_label` can be known. For
  labeled training/evaluation rows, this must be after `decision_time`.

## No-Lookahead Validation And Test Contract

Future implementation must provide deterministic validation before model work
is accepted.

Required static/schema checks:

- reject missing `adjusted_close` before label construction
- reject any attempt to substitute `close` for missing `adjusted_close`
- reject feature columns not in the allowlist
- reject `up_1d_label`, `next_adjusted_close`, and label-derived
  columns from feature inputs
- reject backtest/evaluation/generated-output/report/ranking fields from
  feature inputs
- reject valuation/fundamental fields from feature inputs
- reject production `technical_composite_score` and `final_composite_score` as
  candidate ML features

Required timing checks:

- validate `decision_time`, `execution_time`, `label_time`, and
  `label_availability_time` fields exist in training/evaluation contract rows
- validate every feature timestamp is `<= decision_time`
- validate every source row used for a feature has
  `source_data_availability_time <= decision_time`
- validate label data is unavailable before `label_availability_time`
- validate `label_availability_time` is after `decision_time` for labeled rows
- validate as-of-date inference rows can be built without any label field

Required missing/warmup checks:

- missing and warmup values must remain missing, invalid, blocked, or handled by
  a deterministic predeclared rule
- missing/warmup values must not be filled with optimistic values such as known
  future outcomes, cross-sectional winners, best-case returns, or favorable
  ranks
- any imputation rule must be fixed before training and must not depend on
  validation/test outcomes

Preferred tests:

- `adjusted_close` missing-column fail-fast test
- no silent `close` fallback test
- feature allowlist/default-deny test
- label-derived column exclusion test
- backtest/report/ranking/generated-output feature exclusion test
- timestamp no-lookahead test
- label-availability timing test
- as-of-date inference-without-label contract test
- warmup/missing-state conservative handling test

These tests should be deterministic unit or static contract checks first.
Broad integration tests are not required for this gate.

## Sidecar Candidate Output Path Contract

Future candidate-only sidecar outputs must use this root and naming convention:

```text
reports/v0_2_predictive_probability/candidate_sidecar/
  prob_up_1d_candidate_candidate_only_sidecar_{as_of_date}.csv
```

Recommended optional metadata path:

```text
reports/v0_2_predictive_probability/candidate_sidecar/
  prob_up_1d_candidate_candidate_only_sidecar_{as_of_date}.manifest.json
```

Path rules:

- `{as_of_date}` must be an unambiguous date token such as `YYYYMMDD`.
- The artifact name must include `candidate_only` and `sidecar`.
- The sidecar output root must not overwrite production outputs such as
  `reports/selection/latest_ranking.csv`.
- The sidecar must not be consumed by final reports as production ranking.
- The sidecar must not replace `technical_composite_score`.
- The sidecar must not replace `final_composite_score`.
- The sidecar must not alter GUI, scanner, backtest, pipeline, or report
  ordering unless a later explicit candidate-display gate opens that route.
- Generated sidecar artifacts remain non-source-controlled runtime outputs by
  default.

Frozen sidecar ordering:

1. `prob_up_1d_candidate` descending
2. `ticker` ascending

Minimum future sidecar columns:

- `ticker`
- `date`
- `decision_time`
- `execution_time`
- `prob_up_1d_candidate`
- `prob_up_1d_candidate_status`
- `prob_up_1d_candidate_sample_role`
- `feature_set_version`
- `label_contract_version`

The sidecar must not include production `rank`, `technical_composite_score`,
`final_composite_score`, trading recommendation fields, forecasted-return fields,
or valuation/fundamental fields.

## Gate 1 Validation Profile

This gate is docs-only, so code-level tests are not added here. The required
validation is:

- `git diff --check`
- changed-lines check for production ranking/report activation wording
- changed-lines check that forbidden financial-claim wording appears only as
  explicit forbidden or boundary language
- check that `technical_composite_score` and `final_composite_score` logic were
  not changed
- check that no model training, inference, or sidecar ranking generation code
  was added
- TOML parse check only if `docs/context/EXTENSION_REGISTRY.toml` changes
- `git status --short`

## Gate 1 Verdict

Implementation gate 1 is frozen as a contract-only gate. The next gate may
begin only after a future worker keeps this contract intact and scopes code
changes to validation, schema, feature-table construction, and label separation
without model training, inference activation, runtime ranking generation,
production report changes, score logic changes, valuation activation, new data
ingestion, or universe expansion.
