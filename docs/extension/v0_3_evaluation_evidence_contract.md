# v0.3 EvaluationEvidence Contract

Status: active historical evaluation evidence contract.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Upstream registry: `docs/extension/v0_3_strategy_candidate_registry_contract.md`.
Owner lane: Backtest evaluation with root no-feedback review.

This contract defines how a `StrategyCandidate` is evaluated against historical
data after a separate approved owner-lane task. Evaluation output is
evidence-only. It is not an adoption decision, not automatic production
activation, and not proof of future profitability.

## Architecture Routing

EvaluationEvidence work must pass through the active root architecture chain
before any backtest/simulation owner-lane execution or validation begins:

`agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor -> agent-worker-pool -> agent-reporter`

The default domain compatibility target is `quant-strategy-adoption-gate`.
Subproject-wide audit or scope-watchdog work still routes to
`quant-subproject-audit-gate` when applicable, and completion acceptance
requires `quant-review-gate`. The supervisor handoff must lock allowed scope,
forbidden scope, required output, validation commands, and Korean final report
format before any approved run or evidence artifact update.

## Evaluation Boundary

Allowed:

- define EvaluationEvidence schema
- define historical evaluation window and universe fields
- define assumptions, transaction-cost assumption, risk metrics, and failure
  flags
- run approved candidate-only backtests or simulations in the owning lane
- record historical return, risk, drawdown, volatility, turnover, and
  performance summaries as evidence-only artifacts
- define no-lookahead, point-in-time, and generated-output checks
- maintain evidence-only comparison report paths
- maintain document or validator gates that block automatic production
  activation from evidence

Blocked:

- automatic production activation from backtest results
- live trading or real-trade connection

## Proposed Artifact Paths

Evaluation inputs:

- `Quant_mvp/config/v0_3_strategy_candidate_registry.toml`
- `docs/extension/v0_3_strategy_candidate_registry_contract.md`
- `docs/extension/v0_3/strategy_hypotheses/*.md`

Evaluation evidence outputs:

- `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/*.md`
- `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison/*.md`
- `Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/`

Validation proposal paths:

- `Quant_mvp/backtest_mvp/tests/fixtures/v0_3_evaluation_evidence_minimal.toml`
- `Quant_mvp/backtest_mvp/tests/test_v0_3_evaluation_evidence_schema.py`
- `Quant_mvp/backtest_mvp/tests/test_v0_3_no_feedback_boundary.py`

These paths are v0.3 evidence boundaries. Approved owner-lane tasks may create
EvaluationEvidence and generated evidence-only reports here. They must not add
runtime production outputs or production test fixtures.

## EvaluationEvidence Schema

Required identity and lineage fields:

- `evaluation_id`: stable evidence ID, for example `ee_v0_3_YYYYMMDD_slug`.
- `candidate_id`: upstream `StrategyCandidate` ID.
- `candidate_version`: evaluated StrategyCandidate version.
- `hypothesis_id`: upstream `StrategyHypothesis` ID.
- `status`: one of `contract_only`, `ready_for_approved_run`,
  `evidence_recorded`, `needs_more_evidence`, `blocked`, `invalidated`, or
  `retired`.
- `owner`: owning lane or responsible subproject, for example
  `backtest_evaluation`.
- `created_at`: local date or timestamp.
- `updated_at`: local date or timestamp.
- `source_refs`: registry, candidate, hypothesis, and evaluation contract paths.

Required evaluation design fields:

- `evaluation_window`: start date, end date, and rationale.
- `universe`: candidate-only universe boundary used for the evaluation.
- `assumptions`: explicit assumptions, including data availability and
  candidate-only interpretation.
- `transaction_cost_assumption`: cost model label, cost value, or explicit
  `not_applicable_for_contract_only`.
- `risk_metrics`: predeclared risk metrics to report, not optimize against.
- `performance_metrics`: predeclared historical performance metrics to report
  as evidence.
- `comparison_group`: candidate IDs or cohort labels used for evidence-only
  comparison.
- `evaluation_method_ref`: path to later approved runner/schema contract.
- `generated_output_boundary`: generated output path and retention rule.

Required defensive-alternative fields when the evaluation asks whether a
defensive alternative is preferable during sustained price declines:

- `defensive_alternative`: first supported value is `cash_hold`; later
  alternatives require a separate scope lock and approval.
- `defensive_alternative_assumption`: how cash holding is represented. The
  default is `cash_hold_zero_nominal_return` unless a separately approved,
  documented cash-return proxy is available without new data-ingestion
  assumptions.
- `decline_regime_definition`: predeclared sustained-decline rule, window
  construction, and benchmark or candidate price series used for regime
  labeling.
- `decline_regime_point_in_time_check`: confirms decline windows are labeled
  for evaluation evidence only and do not use future information to trigger
  runtime action.
- `defensive_comparison_question`: evidence-only question, for example whether
  `cash_hold` preserved capital better than the evaluated candidate during
  predeclared sustained-decline windows.
- `defensive_comparison_metrics`: predeclared metrics such as decline-window
  return difference versus cash, max drawdown difference, volatility
  difference, downside capture, recovery time, exposure stability, and
  opportunity-cost notes.
- `defensive_comparison_status`: one of `cash_preferred`,
  `candidate_preferred`, `inconclusive`, `not_applicable`, or
  `needs_more_evidence`.
- `defensive_no_action_check`: confirms that a cash-preferred result is a
  review finding only, not a sell instruction, allocation instruction, runtime
  signal, or production activation trigger.

Required safety check fields:

- `no_lookahead_check`: how the evidence avoids future data.
- `point_in_time_check`: how the evidence records data availability timing.
- `generated_output_check`: confirms outputs are generated artifacts, not
  default context or source-controlled runtime inputs unless explicitly
  promoted as review fixtures.
- `no_feedback_check`: confirms results do not trigger automatic production
  activation.
- `v0_2_boundary_check`: confirms `prob_up_1d_candidate` is not replaced,
  reinterpreted, or trained from evaluation metrics.
- `failure_flags`: explicit failure or invalidation flags.
- `production_boundary_check`: confirms automatic production activation claims
  are absent.

Optional evidence fields after a separately approved run:

- `metric_summary_path`
- `risk_metric_summary_path`
- `performance_metric_summary_path`
- `comparison_report_path`
- `defensive_alternative_summary_path`
- `known_limitations`
- `review_notes`
- `invalidation_reason`

## Defensive Alternative Evaluation Frame

The first defensive alternative for sustained-decline review is `cash_hold`.
It exists only as an evaluation baseline for deciding whether a strategy
candidate's historical evidence was preferable to staying uninvested during
predeclared decline regimes.

This frame may answer one of three review questions:

- `cash_preferred`: the evidence says cash holding was historically better
  than the candidate during the defined decline windows.
- `candidate_preferred`: the evidence says the candidate was historically
  better than cash holding during the defined decline windows.
- `inconclusive`: the evidence does not support either conclusion because the
  decline regime, metric coverage, no-lookahead checks, or sample size is
  insufficient.

The frame must not answer operational questions such as whether to sell,
de-risk, rebalance, or move to cash in production. Any result remains
EvaluationEvidence-only and may only feed allowlisted `AdoptionCandidate` review
summaries.

Predeclared decline regime rules should document:

- the measured series, for example candidate equity curve or KOSPI200
  benchmark within the approved universe boundary
- the sustained-decline threshold and minimum duration
- whether overlapping decline windows are merged or separated
- how window start and end dates are identified without runtime feedback
- how incomplete or data-gap windows are flagged

Suggested defensive comparison metrics:

- `decline_window_return_minus_cash`: candidate return minus cash return in
  each decline window
- `decline_window_hit_rate_vs_cash`: share of decline windows where the
  candidate outperformed cash
- `max_drawdown_difference_vs_cash`: candidate max drawdown minus cash
  drawdown in the same windows
- `volatility_difference_vs_cash`: candidate volatility minus cash volatility
- `downside_capture_vs_benchmark`: candidate downside capture relative to the
  approved benchmark during decline windows
- `recovery_time_after_decline`: days or periods needed to recover after each
  decline window
- `exposure_stability`: whether candidate exposure was stable, reduced, or
  unstable during decline windows
- `cash_opportunity_cost_note`: evidence-only note on gains forgone outside
  decline windows when cash holding is used as the comparison baseline

Any `cash_preferred` result must carry `defensive_no_action_check =
"review_finding_only_no_runtime_signal"` or an equivalent explicit boundary.
It cannot become a trade signal, ranking activation input, or production
activation trigger without a later separate approval route.

## Failure Flags

Suggested failure flags:

- `lookahead_risk_detected`
- `point_in_time_unverified`
- `generated_output_boundary_violation`
- `no_feedback_boundary_violation`
- `universe_boundary_violation`
- `data_availability_gap`
- `transaction_cost_assumption_missing`
- `performance_metric_missing`
- `risk_metric_missing`
- `candidate_contract_mismatch`
- `unsupported_production_activation_claim`
- `production_connection_detected`

Any active failure flag must prevent `evidence_recorded` from becoming an
adoption input. It may only support `invalidated`, `blocked`, or
`needs_more_evidence` downstream statuses.

## Evidence-Only Comparison Report

Candidate comparison reports must be separated from production outputs:

- They live under `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison/` or
  `Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/`.
- They compare candidates only for review context.
- They must not contain automatic production activation claims.

Required report disclaimer:

`This comparison report is evidence-only. It is not an adoption decision and not automatic production activation.`

## No-Feedback Gate Proposal

Before an evaluation evidence packet can be accepted, a document or validator
gate should check:

- no registry or candidate status changes automatically from metric values
- `no_feedback_check` is present and explicit
- production-boundary language is absent except in blocked wording policy

Suggested later command shape:

```powershell
python -m pytest Quant_mvp/backtest_mvp/tests/test_v0_3_evaluation_evidence_schema.py Quant_mvp/backtest_mvp/tests/test_v0_3_no_feedback_boundary.py
```

## Minimal Fixture Proposal

```toml
[[evaluation_evidence]]
evaluation_id = "ee_v0_3_20260428_example"
candidate_id = "sc_v0_3_20260428_example"
candidate_version = "0.1.0"
hypothesis_id = "sh_v0_3_20260428_example"
status = "contract_only"
owner = "backtest_evaluation"
created_at = "2026-04-28"
updated_at = "2026-04-28"
source_refs = [
  "docs/extension/v0_3_strategy_candidate_registry_contract.md",
  "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
]
evaluation_window = { start = "YYYY-MM-DD", end = "YYYY-MM-DD", rationale = "predeclared_window_required" }
universe = "KOSPI200_candidate_only"
assumptions = ["candidate_only_interpretation", "no_runtime_connection"]
transaction_cost_assumption = "not_applicable_for_contract_only"
risk_metrics = ["drawdown", "volatility", "turnover_proxy"]
performance_metrics = ["total_return", "annualized_return", "win_rate"]
comparison_group = ["v0_3_candidate_review_cohort"]
evaluation_method_ref = "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_method_contract.md"
generated_output_boundary = "Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/"
no_lookahead_check = "required_before_approved_run"
point_in_time_check = "required_before_approved_run"
generated_output_check = "outputs_are_generated_evidence_only"
no_feedback_check = "must_not_trigger_auto_activation"
v0_2_boundary_check = "no_prob_up_1d_training_or_reinterpretation_from_evaluation_metrics"
failure_flags = ["not_yet_run"]
production_boundary_check = "no_automatic_production_activation_claim"
defensive_alternative = "cash_hold"
defensive_alternative_assumption = "cash_hold_zero_nominal_return"
decline_regime_definition = "not_applicable_for_contract_only"
decline_regime_point_in_time_check = "required_before_approved_run"
defensive_comparison_question = "not_applicable_for_contract_only"
defensive_comparison_metrics = [
  "decline_window_return_minus_cash",
  "max_drawdown_difference_vs_cash",
  "volatility_difference_vs_cash",
]
defensive_comparison_status = "not_applicable"
defensive_no_action_check = "review_finding_only_no_runtime_signal"
```

## Acceptance Conditions

An EvaluationEvidence packet may be accepted as evidence-only only when:

- the upstream StrategyCandidate is `evaluable`
- evaluation window and universe are explicit
- assumptions and transaction-cost assumption are explicit
- risk metrics are predeclared
- historical performance metrics are predeclared
- no-lookahead and point-in-time checks are present
- generated-output boundary is present
- no-feedback check is present and passes
- failure flags are absent for `evidence_recorded`, or explicitly route the
  packet to `invalidated`, `blocked`, or `needs_more_evidence`
- comparison report, if present, is separated as an evidence-only artifact
- defensive-alternative comparison, if present, uses an approved
  `cash_hold` baseline, predeclared decline windows, point-in-time checks, and
  no-action wording
- no automatic production activation or live-trading connection is present
