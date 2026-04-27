# v0.2 Predictive Probability Score Route Approval Packet

Status: implementation approved for the scoped candidate-only
`prob_up_1d_candidate` branch/worktree. This document does not modify MVP v0.1
or activate production ranking, report, backtest feedback, valuation,
`final_composite_score` replacement, trading recommendations, or data-ingestion
behavior.

## Purpose

This packet records the approval requirements for the `v0.2 predictive
probability score route` and the limited implementation approval for
`prob_up_1d_candidate`.

The intended `v0.2` product goal is to create a candidate
`prob_up_1d_candidate` where higher values mean higher model-estimated
probability that `adjusted_close[t+1] > adjusted_close[t]`. This draft separates
that goal from activation: candidate model implementation is approved only for
the feature table, label-separated training/evaluation pipeline, candidate
probability output, and validation tests. Production ranking or trading use is
not approved.

Supporting draft artifacts:

- `docs/extension/v0_2_candidate_score_list.md`
- `docs/extension/v0_2_score_specification_schema.md`
- `docs/extension/v0_2_predictive_probability_route.md`
- `docs/extension/v0_2_prob_up_1d_label_contract.md`
- `docs/extension/v0_2_old_score_feature_boundary.md`

MVP v0.1 remains the frozen historical baseline. A later approved `v0.2` line
may supersede v0.1 scoring semantics for v0.2 outputs, but it must do so through
versioned contracts and must not rewrite v0.1 release evidence.

- KOSPI200-only.
- Technical-only.
- Backtest output remains evaluation-only and must not feed scoring or ranking.
- Valuation or fundamental data must not enter `technical_composite_score`.
- Valuation or fundamental data must not enter `final_composite_score` in this
  draft. Any later valuation-aware final-composite route requires separate
  versioned approval, point-in-time availability proof, and updated contracts.

## Candidate Scope

The future `v0.2` predictive probability route may only be considered after a concrete
proposal defines:

- `prob_up_1d_candidate` output schema
- `up_1d_label` timing and no-lookahead rules
- old-score feature set
- model-input feature boundary
- probability calibration and normalization plan
- minimum history and split requirements
- warmup, missingness, and invalid-row behavior
- baseline comparison plan
- failure modes and rejection criteria
- implementation owner and validation profile

Allowed score branches for proposal review:

- `predictive_probability`
- `old_score_feature`
- `diagnostic_old_score_feature`
- `out_of_scope`

No candidate score is implemented or adopted by this draft. No production field,
report, or ranking behavior changes are authorized by this packet.

## Hard Boundaries

The future score revision must not:

- silently redefine existing MVP v0.1 scores
- use future returns or post-decision values as score inputs
- use backtest result metrics as model input features
- use diagnostics as ranking signals without explicit adoption review
- introduce valuation or fundamental data into `technical_composite_score`
- introduce valuation or fundamental data into `final_composite_score` from
  this draft
- introduce new market data ingestion
- activate new markets, asset classes, or multi-universe ranking
- connect backtest output to scoring, model feature construction, ranking,
  adoption, or optimization
- introduce trading recommendation language
- change report ordering or interpretation without a separately approved report
  contract

## Required Architecture Review

Before implementation approval, the Score Architect must produce a candidate
score specification covering:

- `score_name`
- `score_family`
- `score_branch`
- `purpose`
- `market_regime_where_it_helps`
- `raw_input_features`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `expected_overlap_risk`
- `failure_modes`
- `data_requirements`
- `notes_on_interpretability`

Any ambiguous formula, timing rule, data requirement, or branch classification
must be resolved before code work starts.

## Required Testing And Diagnostics Plan

Before implementation approval, the Research Tester plan must define:

- raw score output schema
- normalized score output schema
- cross-sectional normalization rules
- time-series normalization rules
- NaN, warmup, and insufficient-history handling
- outlier handling
- coverage diagnostics
- rank stability diagnostics
- turnover proxy diagnostics
- score correlation and redundancy diagnostics
- generated-output boundary

The plan must state which checks are required before any candidate can move to
technical selection review.

Minimum Research Tester gate requirements:

- `raw_score_output_schema`: exact candidate raw output columns, units,
  directionality, invalid-state representation, and per-row timing fields.
- `normalized_score_output_schema`: exact normalized output columns,
  normalized range, orientation, shrinkage behavior, and data-quality flags.
- `cross_sectional_normalization_rules`: same-date eligible population,
  exclusion rule, minimum population size, tie handling, and missing-value
  handling.
- `time_series_normalization_rules`: per-symbol lookback window, warmup rule,
  rolling percentile or z-score method, and current/prior-only data rule.
- `nan_warmup_insufficient_history_policy`: explicit invalid state for NaN,
  warmup, and insufficient-history rows; no optimistic fills.
- `outlier_policy`: clipping, winsorization, robust scale, or reject rule for
  price gaps, range spikes, and volume spikes.
- `coverage_diagnostics`: per-symbol and per-date valid-row ratios, warmup
  coverage, and missing-input counts.
- `rank_stability_diagnostics`: same-date rank movement, rolling rank
  stability, and sensitivity to missing components.
- `turnover_proxy_diagnostics`: rank-change or top-bucket membership-change
  proxy for review only; no trading recommendation language.
- `score_correlation_redundancy_diagnostics`: score-to-score correlation,
  family overlap, rank overlap, and redundancy flags.
- `generated_output_boundary`: expected generated paths, source-control
  exclusion rule, fixture promotion rule, and cleanup responsibility.

## Required Technical Selection Review

Before adoption can be considered, the Technical Selection Reviewer must review
each implemented candidate for:

- technical relevance
- technical distinctiveness
- technical stability
- technical complexity cost
- regime fit
- redundancy risk
- implementation clarity
- data sufficiency

Minimum Technical Selection gate requirements:

- `technical_relevance`: whether the candidate has a clear technical purpose
  for KOSPI200 constituent ranking or diagnostics.
- `technical_distinctiveness`: whether the candidate adds information not
  already captured by existing or proposed scores.
- `technical_stability`: whether diagnostics show acceptable coverage,
  sensitivity, and rank stability across review windows.
- `technical_complexity_cost`: whether the candidate's complexity is justified
  by interpretability and diagnostic value.
- `regime_fit`: which market or stock-specific regimes the candidate describes,
  and where it is expected to fail.
- `redundancy_risk`: measured overlap with other candidates, families, and
  existing v0.1 score behavior.
- `implementation_clarity`: whether the implementation followed the frozen
  score specification without silent formula, input, or normalization changes.
- `data_sufficiency`: whether available approved data, warmup coverage, and
  missing-data handling are adequate for review.

Allowed review outcomes:

- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

Outcome definitions:

- `core_adopted`: candidate may enter the core technical composite only after
  all required reviews pass and redundancy is acceptable.
- `conditional_adopted`: candidate may remain in the versioned adoption plan,
  but only with named unresolved conditions and follow-up validation.
- `technical_only`: candidate may be used as a technical signal but must not
  imply valuation, fundamentals, or recommendation language.
- `regime_only`: candidate may describe a regime, shrinkage context, or gating
  context without becoming a direct ranking signal by default.
- `diagnostic_only`: candidate remains diagnostic and must not feed ranking
  unless a later adoption review changes its branch.
- `research_only`: candidate remains useful for investigation but is not ready
  for production scoring or ranking.
- `rejected`: candidate is removed from the adoption path because ambiguity,
  redundancy, fragility, or implementation risk is too high.
- `blocked_by_data`: candidate cannot proceed because approved data,
  availability timing, or lineage is insufficient.

This draft does not assign any of these outcomes. It only defines the approval
path needed before outcomes may be assigned.

## Timing And No-Lookahead Contract

Every future implementation request must include a complete timing contract
before code work, scoring review, ranking review, report review, or evaluation
work starts. A request that omits any required timing field is incomplete and
must be blocked until the ambiguity is resolved.

Required timing fields:

- `decision_time`: decision timestamp or decision date for each scored row.
- `source_data_availability_time`: when each source input is available for use.
- `feature_construction_time`: when derived features are constructed and which
  source rows they may include.
- `normalization_population_time`: which population is eligible for
  cross-sectional or time-series normalization at the decision time.
- `report_generation_time`: when the report is generated relative to the
  decision time and source availability.
- `evaluation_label_time`: when evaluation labels become knowable, when
  evaluation is performed.

No-lookahead requirements:

- Information after `decision_time` must not be used as score input.
- Cross-sectional normalization must use only the eligible same-date population
  available at `decision_time`.
- Time-series normalization must use only prior and current eligible values.
- Evaluation labels must remain separate from scoring, ranking, normalization,
  report-generation, and adoption inputs.
- Rows with unresolved timing or availability ambiguity must be excluded or
  marked non-evaluable.

## Backtest And Evaluation Boundary

Backtest or simulation output for `v0.2` score candidates is evaluation-only.
It may support diagnostics, leakage review, stability review, and candidate
comparison, but it must not feed upstream scoring, ranking, adoption, or
parameter optimization.

Any evaluation report must state:

- candidate-only status
- data window and eligibility rules
- timing assumptions
- leakage checks
- limitations
- generated-output boundary
- no production adoption unless a later approval explicitly grants it

Backtest and evaluation hard rules:

- `evaluation_only`: every backtest or simulation artifact must be labeled as
  evaluation-only.
- `no_feedback_to_scoring`: evaluation outputs must not change formulas, input
  features, normalization, weights, score branches, composite membership, or
  ranking behavior.
- `no_parameter_optimization_feedback`: parameter choices must not be optimized
  from evaluation results unless a separate approved research protocol allows
  and versions that process.
- `candidate_only_report_status`: evaluation reports must state the candidate
  status of every evaluated score.
- `data_window`: evaluation reports must state start date, end date, exclusions,
  and whether the window is exploratory or approval-grade.
- `eligibility_rules`: evaluation reports must state universe membership,
  symbol eligibility, missing-data exclusions, and warmup exclusions.
- `timing_assumptions`: evaluation reports must state decision time, feature
  availability, normalization population timing, execution/evaluation timing,
  and label timing when labels exist.
- `leakage_check`: evaluation reports must state no-lookahead checks, same-date
  population checks, label separation checks, and any unresolved ambiguity.
- `limitations`: evaluation reports must list known fragility, coverage gaps,
  redundancy, instability, and data-quality limits.
- `generated_output_boundary`: evaluation reports must state generated paths,
  source-control exclusion, fixture promotion rules, and cleanup ownership.
- `no_result_only_adoption`: backtest or simulation results alone must not
  approve adoption; Technical Selection Review, scope watchdog review, and
  master integration remain required.

## Schema And Lineage Freeze Before Implementation

Implementation approval requires every contract below to be `frozen` in a
versioned approval artifact before code work starts. `Frozen` means the contract
has an artifact path, version, owner role, exact field semantics, required
validation checks, approval reference, and change-review trigger.

Required frozen contracts:

- `score_specification_schema`: schema version, required candidate fields,
  allowed lifecycle states, controlled branch values, invalid-row
  representation, and state-transition rules.
- `raw_feature_lineage`: approved source data scope, raw input columns, derived
  feature mapping, adjustment policy, source availability timing, exclusion
  rules, and no-future-input proof.
- `normalized_score_lineage`: raw-to-normalized transform, normalization
  population, time-series window rules, score range, orientation, missing-value
  handling, warmup handling, outlier handling, and neutral-shrinkage behavior.
- `composite_handoff_boundary`: exact fields that may be handed to composite or
  ranking review, branch activation status, candidate-only flags, and the rule
  that `v0.2` contracts must not rewrite MVP v0.1 release evidence.
- `diagnostic_output_schema`: diagnostic columns, units, flags, invalid states,
  report-only status, and the rule that diagnostics are not ranking signals
  unless adoption review explicitly changes the branch.
- `generated_output_source_control_policy`: generated paths, cache/report
  exclusion rules, fixture-promotion criteria, cleanup responsibility, and raw
  data or secret exclusion.
- `config_ownership`: config artifact paths and owner roles for windows,
  thresholds, weights, toggles, branch enablement, defaults, and config-change
  review.
- `validation_profile_required_tests`: required profile, exact checks or test
  commands, pass/fail thresholds, forbidden-scope greps, generated-output
  boundary checks, and cross-step conflict checkpoint requirement.
- `rollback_deactivation_rule`: feature toggle or branch-disable behavior,
  prior-config restoration, output cleanup, user-visible status wording, and
  confirmation that rollback does not modify MVP v0.1 evidence.

This draft records the required freeze gate, not a completed freeze. The
current freeze status for every item above remains `not_frozen` until a later
approval artifact records it as `frozen`.

Any later change to score meaning, formula, input lineage, normalization
semantics, adoption state, ranking use, validation profile, config ownership, or
rollback behavior must trigger a new approval review.

## Review And Audit Gate Checklist

Before or during implementation, the approved implementation route must preserve:

- root/master scope confirmation
- correct post-MVP version or Step assignment
- correct role branch/worktree and workspace manifest
- scope watchdog review when score, ranking, composite, report, backtest, or
  generated-output boundaries are touched
- architecture review
- testing and diagnostics plan review
- technical selection review plan
- no-lookahead review
- generated-output and cache boundary review
- valuation/fundamental hard-stop review
- backtest feedback hard-stop review
- cross-step conflict checkpoint
- `review_mvp` specialist review when code, tests, config, schemas,
  generated-output boundaries, or cross-project handoffs are included

## Remaining Risks And Blockers

Implementation may proceed only inside the approved role branch/worktree. The
following controls are resolved for implementation entry and remain active as
hard limits:

- post-MVP `v0.2 predictive probability score route` Step is open for contract
  freeze and approval preparation only
- `prob_up_1d_candidate` is the active predictive candidate
- old technical/diagnostic scores are frozen as old-score features, not direct
  production score candidates
- score specification schema is approved for candidate specification authoring
- candidate specification summaries are frozen for the Score Architect
  candidate-definition layer
- raw feature lineage contract is frozen in
  `docs/extension/v0_2_raw_feature_lineage_contract.md`
- probability output normalization/calibration contract is frozen in
  `docs/extension/v0_2_probability_output_contract.md`
- model-input and candidate probability handoff contract is frozen in
  `docs/extension/v0_2_model_input_handoff_contract.md`
- diagnostic output schema is frozen in
  `docs/extension/v0_2_diagnostic_output_schema.md`
- label timing and no-lookahead contract is frozen in
  `docs/extension/v0_2_prob_up_1d_label_contract.md`
- diagnostics plan is frozen in
  `docs/extension/v0_2_diagnostic_output_schema.md`
- generated-output boundary is frozen in
  `docs/extension/v0_2_generated_output_boundary.md`
- config ownership contract is frozen in
  `docs/extension/v0_2_config_ownership_contract.md`
- validation profile is frozen in
  `docs/extension/v0_2_predictive_validation_profile.md`
- rollback or deactivation rule is frozen in
  `docs/extension/v0_2_rollback_deactivation_rule.md`
- review/audit route is frozen in
  `docs/extension/v0_2_review_audit_route.md`

## Approval Verdict

`v0.2` score revision status: approved for scoped candidate-only
`prob_up_1d_candidate` implementation.

Approved implementation scope:

- feature table for approved old-score/model input features
- label-separated training/evaluation pipeline for
  `adjusted_close[t+1] > adjusted_close[t]`
- candidate probability output `prob_up_1d_candidate`
- focused validation tests

Not approved:

- production ranking
- trading recommendations
- `final_composite_score` replacement
- valuation/fundamental data
- backtest metrics as model features
- report behavior changes
- data ingestion changes
