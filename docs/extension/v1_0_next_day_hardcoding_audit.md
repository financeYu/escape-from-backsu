# v1.0 next-day / 1D hardcoding audit

## Purpose

This audit prepares Phase 2 HorizonPolicy work. It classifies current next-day,
1D, horizon, holding-period, and rebalance assumptions so Phase 2 can replace
or preserve them deliberately. It does not change runtime behavior.

## Search scope

Searched directories and root files:

- `AGENTS.md`
- `WORKSPACE_MANIFEST.md`
- `.agents/skills`
- `chart_mvp`
- `config`
- `docs/architecture`
- `docs/context`
- `docs/extension`
- `docs/root_hard_stops.md`
- `docs/roadmap_status.md`
- `docs/step16_security_detail_report.md`
- `docs/step17_conservative_backtest_core.md`
- `gui_mvp`
- `Quant_mvp`
- `scripts`
- `src`
- `tests`

Excluded directories:

- `.git`
- `__pycache__`
- `.pytest_cache`
- `docs/roadmap_archive`
- `docs/context/archive`
- `docs/releases`
- `reports`
- nested `reports`
- nested `data`
- nested `cache`
- nested `caches`
- nested `charts`
- nested `logs`
- `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence`
- `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison`
- `Quant_mvp/research_mvp/input`

No generated outputs, raw data, caches, chart images, release evidence, or
archive history were opened for this audit.

## Search patterns

- `next_day`
- `next-day`
- `D+1`
- `1d`
- `1D`
- `prob_up_1d_candidate`
- `entry_date`
- `entry_lag`
- `label_horizon`
- `holding_period`
- `rebalance`
- `buy_next_day`
- `purchase_next_day`
- `next trading day`
- `following trading day`
- `one_day`
- `one-day`

## Summary table

| category | count | notes |
| --- | ---: | --- |
| remove_or_generalize | 2 | Active 1D price-feature label contract should become Phase 2 HorizonPolicy-controlled or compatibility-wrapped. |
| keep_for_compatibility | 4 | v0.2 `prob_up_1d_candidate` references and guardrails remain archived/supporting compatibility boundaries. |
| unclear_needs_manual_review | 7 | Active v0.3 backtest, selector, strategy-hypothesis, and UI/config horizon semantics need Phase 2 ownership decisions. |
| not_relevant | 2 | Guardrail-language and false-positive references do not encode HorizonPolicy implementation work. |

## Findings

### Finding 1

- category: remove_or_generalize
- file: `chart_mvp/src/stock_core/ml/price_feature_table.py`
- line: 43
- matched text or short paraphrase: `label_horizon_days: int = 1`
- current role: default label horizon for the v0.3 ML-useful price feature table.
- why it matters: Phase 2 should not treat next-day labels as the global v1.0
  default once multi-horizon planning starts.
- proposed Phase 2 action: define a HorizonPolicy contract first, then route
  this default through the policy or mark it as a compatibility default.
- risk if ignored: v1.0 selector inputs could silently keep a next-day label
  assumption while claiming multi-horizon readiness.

### Finding 2

- category: remove_or_generalize
- file: `chart_mvp/src/stock_core/ml/price_feature_table.py`
- line: 52
- matched text or short paraphrase: non-1D `label_horizon_days` raises because
  current label columns use the 1D contract.
- current role: explicit guard that blocks non-1D supervised label horizons.
- why it matters: this is the clearest implementation point Phase 2 must not
  bypass. It protects current schema correctness, but it is also the concrete
  place where HorizonPolicy must define new behavior.
- proposed Phase 2 action: replace the hard guard only after HorizonPolicy
  defines horizon naming, output columns, compatibility defaults, and
  validation.
- risk if ignored: Phase 2 could add policy docs without changing the active
  implementation that still rejects non-1D horizons.

### Finding 3

- category: unclear_needs_manual_review
- file: `docs/extension/v0_3_kospi200_price_ml_feature_table_contract.md`
- line: 73
- matched text or short paraphrase: required label columns include
  `label_horizon_days`, `label_forward_return_1d`, and `label_up_1d`.
- current role: active handoff contract for chart_mvp price features used by
  v0.3 review workflows.
- why it matters: the contract names 1D output columns directly.
- proposed Phase 2 action: decide whether Phase 2 creates generalized label
  columns, per-horizon columns, or a versioned compatibility schema.
- risk if ignored: implementation and contract could diverge when
  HorizonPolicy starts.

### Finding 4

- category: unclear_needs_manual_review
- file: `Quant_mvp/backtest_mvp/contracts.py`
- line: 150
- matched text or short paraphrase: `holding_period_days: int = 20`
- current role: default conservative backtest holding period.
- why it matters: it is not next-day behavior, but it is an active evaluation
  horizon assumption.
- proposed Phase 2 action: decide whether HorizonPolicy owns this value or
  whether SimulationRunManifest owns it in Phase 3.
- risk if ignored: multi-horizon planning may conflate label horizon,
  evaluation holding period, and simulation run horizon.

### Finding 5

- category: unclear_needs_manual_review
- file: `Quant_mvp/backtest_mvp/contracts.py`
- line: 156
- matched text or short paraphrase: `execution_lag_days: int = 1`
- current role: conservative backtest execution lag.
- why it matters: this is a one-trading-day execution timing assumption, not a
  label horizon. Phase 2 should decide whether it remains a simulation
  assumption outside HorizonPolicy.
- proposed Phase 2 action: document execution lag separately from label and
  holding horizons.
- risk if ignored: Phase 2 may incorrectly generalize execution timing as if it
  were the prediction/evaluation horizon.

### Finding 6

- category: unclear_needs_manual_review
- file: `config/backtest.toml`
- line: 11
- matched text or short paraphrase: `holding_period_days = 20`
- current role: root-level default backtest config.
- why it matters: config defaults can become hidden route assumptions if not
  mapped before Phase 2.
- proposed Phase 2 action: decide whether to keep this as a legacy/default
  simulation config or move it under a future manifest/policy boundary.
- risk if ignored: user-visible config may contradict new HorizonPolicy docs.

### Finding 7

- category: unclear_needs_manual_review
- file: `Quant_mvp/backtest_mvp/config/backtest.toml`
- line: 14
- matched text or short paraphrase: `execution_lag_days = 1`
- current role: Quant backtest config default.
- why it matters: same timing assumption as Finding 5, mirrored in the
  subproject config.
- proposed Phase 2 action: keep mirrored config behavior unchanged for now, but
  classify it before Phase 3 SimulationRunManifest.
- risk if ignored: future manifest work may leave two config sources with
  unstated precedence.

### Finding 8

- category: unclear_needs_manual_review
- file: `Quant_mvp/backtest_mvp/candidate_rank_adapter.py`
- line: 41
- matched text or short paraphrase: default `rebalance_step_days: int = 20`.
- current role: v0.3 candidate-only signal-to-rank snapshot cadence.
- why it matters: cadence is horizon-like but not the same as label horizon or
  holding period.
- proposed Phase 2 action: decide whether HorizonPolicy names only label and
  evaluation horizons or also covers rebalance cadence.
- risk if ignored: Phase 2 could over-broaden HorizonPolicy and accidentally
  change ranking snapshot semantics.

### Finding 9

- category: unclear_needs_manual_review
- file: `Quant_mvp/scripts/build_v0_3_strategy_hypotheses.py`
- line: 141
- matched text or short paraphrase: strategy templates hardcode 5-day and
  20-day holding periods and rebalance rules.
- current role: source of v0.3 StrategyHypothesis defaults.
- why it matters: these are candidate strategy assumptions that Phase 2 must
  either preserve as candidate-specific horizons or express through policy.
- proposed Phase 2 action: map each template field to HorizonPolicy,
  SimulationRunManifest, or candidate-local scope before editing code.
- risk if ignored: Phase 2 may generalize one layer while strategy templates
  continue to emit fixed horizons.

### Finding 10

- category: unclear_needs_manual_review
- file: `Quant_mvp/scripts/run_v0_3_momentum_evaluation_evidence_cohort.py`
- line: 328
- matched text or short paraphrase: rebalance and holding periods are parsed
  from text with `_parse_first_int`.
- current role: evaluation-evidence cohort runner converts textual candidate
  assumptions into backtest config values.
- why it matters: parsing the first integer from text is fragile once
  multi-horizon policy and manifests exist.
- proposed Phase 2 action: classify this as a Phase 3 dependency if
  HorizonPolicy needs machine-readable run horizons.
- risk if ignored: future horizon docs may be precise while the runner still
  infers numeric horizons from prose.

### Finding 11

- category: unclear_needs_manual_review
- file: `Quant_mvp/scripts/build_v0_3_selector_feature_matrix.py`
- line: 88
- matched text or short paraphrase: `holding_period` is excluded from training
  features when missing or unavailable.
- current role: feature-matrix boundary for selector inputs.
- why it matters: Phase 2 must preserve the no-feedback boundary and avoid
  turning realized evaluation design fields into model features.
- proposed Phase 2 action: keep horizon metadata as review/evaluation metadata
  unless a later gate explicitly allows an input field.
- risk if ignored: horizon fields could become model features without a
  deliberate selector input allowlist.

### Finding 12

- category: keep_for_compatibility
- file: `src/scores/prob_up_1d_candidate.py`
- line: 3
- matched text or short paraphrase: v0.2 `prob_up_1d_candidate` path derives a
  next-day up label in separated train/evaluation tables.
- current role: archived/supporting v0.2 compatibility implementation.
- why it matters: it should not be reinterpreted as the v1.0 target.
- proposed Phase 2 action: leave intact unless the task explicitly opens
  archived/supporting compatibility migration.
- risk if ignored: v1.0 work could accidentally mutate the compatibility path
  instead of creating a new policy boundary.

### Finding 13

- category: keep_for_compatibility
- file: `Quant_mvp/docs/v0_2_candidate_ml_score_contract.md`
- line: 55
- matched text or short paraphrase: next-day label uses
  `adjusted_close[t+1] > adjusted_close[t]`.
- current role: v0.2 candidate ML score contract.
- why it matters: this is intentional compatibility documentation.
- proposed Phase 2 action: reference only as archived/supporting
  compatibility, not as active v1.0 design.
- risk if ignored: a v0.2 label could be treated as v1.0 default behavior.

### Finding 14

- category: keep_for_compatibility
- file: `Quant_mvp/docs/next_horizon_up_probability_score_design.md`
- line: 259
- matched text or short paraphrase: uses `prob_up_1d_candidate` with
  `horizon_trading_days = 1` as the only active candidate score.
- current role: historical candidate probability design note.
- why it matters: it documents the old one-horizon candidate state.
- proposed Phase 2 action: keep as compatibility evidence; do not edit during
  Phase 0+1.
- risk if ignored: Phase 2 may inherit old candidate-score assumptions.

### Finding 15

- category: keep_for_compatibility
- file: `Quant_mvp/scripts/build_v0_3_selector_inputs.py`
- line: 50
- matched text or short paraphrase: `prob_up_1d_candidate` is a forbidden
  selector key.
- current role: guardrail excluding archived/supporting probability output
  from v0.3 selector inputs.
- why it matters: this is a useful compatibility boundary.
- proposed Phase 2 action: preserve the exclusion unless a later gate
  explicitly authorizes archived/supporting compatibility inputs.
- risk if ignored: old candidate probability output could leak into selector
  inputs.

### Finding 16

- category: not_relevant
- file: `docs/root_hard_stops.md`
- line: 195
- matched text or short paraphrase: automatic rebalance appears in forbidden
  scope.
- current role: root hard-stop wording.
- why it matters: this is a boundary statement, not a hardcoded horizon.
- proposed Phase 2 action: preserve the hard stop.
- risk if ignored: none for HorizonPolicy implementation; it remains a guardrail.

### Finding 17

- category: not_relevant
- file: `docs/extension/v0_5_personal_decision_support_route.md`
- line: 83
- matched text or short paraphrase: `rebalance` appears in blocked language.
- current role: v0.5 personal decision support language boundary.
- why it matters: this is forbidden output wording, not an implementation
  horizon assumption.
- proposed Phase 2 action: preserve the boundary.
- risk if ignored: none for HorizonPolicy implementation; it remains a wording
  guardrail.

## High-priority Phase 2 targets

- `chart_mvp/src/stock_core/ml/price_feature_table.py`
- `docs/extension/v0_3_kospi200_price_ml_feature_table_contract.md`
- `Quant_mvp/backtest_mvp/contracts.py`
- `Quant_mvp/backtest_mvp/candidate_rank_adapter.py`
- `Quant_mvp/scripts/build_v0_3_strategy_hypotheses.py`
- `Quant_mvp/scripts/run_v0_3_momentum_evaluation_evidence_cohort.py`
- `Quant_mvp/scripts/build_v0_3_selector_feature_matrix.py`

## Compatibility notes

`prob_up_1d_candidate` references remain archived/supporting compatibility by
default. They should not be edited during Phase 2 unless the task explicitly
opens a compatibility migration path through the candidate ML gate.

The current 1D chart feature labels may remain as a documented compatibility
or default horizon until Phase 2 defines HorizonPolicy, schema naming, and
validation.

## Manual review queue

- Decide whether HorizonPolicy owns only label horizons or also holding period,
  execution lag, and rebalance cadence.
- Decide whether v0.3 price feature columns become versioned per-horizon
  columns or remain 1D compatibility columns beside new policy-driven outputs.
- Decide whether StrategyHypothesis templates keep candidate-local horizon
  prose or move to machine-readable policy fields.
- Decide whether `_parse_first_int` remains acceptable until
  SimulationRunManifest or must be blocked by Phase 2 entry.
- Decide whether selector feature-matrix horizon metadata remains excluded
  from model features in all v1.0 phases.

## Guardrail check

- no runtime behavior changed
- no score formula changed
- no ranking behavior changed
- no backtest semantic changed
- no model feature construction changed
- no valuation/fundamental scoring activated
- no futures/options/index trading activated
- no trading recommendation language added
- no expected/future return claim added
- no new market-data ingestion added

## Implementation constraints

For Phase 0 and Phase 1, do not change current runtime behavior. Only create or
update planning and audit documents. Lightweight tests/checks may be added only
if the repository already has a narrow validation path for these documents.

## Optional lightweight validation

No new validation framework is required for Phase 0 and Phase 1. Focused local
validation should include:

- `git diff --check`
- `git status --short`
- `git diff -- docs/extension/v1_0_freeze_plan.md docs/extension/v1_0_scope_boundary.md docs/extension/v1_0_next_day_hardcoding_audit.md`
- forbidden wording grep over the changed documents, with matches classified as
  required blocked-language, search-pattern, or audit-reference text rather
  than allowed output language.
