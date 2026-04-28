# v0.3 EvaluationEvidence Contract

Status: active historical evaluation evidence contract.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Upstream registry: `docs/extension/v0_3_strategy_candidate_registry_contract.md`.
Owner lane: Backtest evaluation with root no-feedback review.

This contract defines how a `StrategyCandidate` is evaluated against historical
data after a separate approved owner-lane task. Evaluation output is
evidence-only. It is not production ranking input, not a `final_composite_score`
input, not a runtime model feature, not an adoption decision, and not proof of
future profitability.

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
- maintain document or validator gates that block feedback into scoring,
  ranking, model features, or automatic adoption

Blocked:

- production ranking reflection
- `final_composite_score` reflection
- score optimization from backtest results
- runtime model feature creation from backtest metrics
- live trading or real-trade connection
- profitability-proof wording
- trading recommendations

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
  `evidence_recorded`, `invalidated`, or `retired`.
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
  as evidence, not as future-performance promises.
- `comparison_group`: candidate IDs or cohort labels used for evidence-only
  comparison.
- `evaluation_method_ref`: path to later approved runner/schema contract.
- `generated_output_boundary`: generated output path and retention rule.

Required safety check fields:

- `no_lookahead_check`: how the evidence avoids future data.
- `point_in_time_check`: how the evidence records data availability timing.
- `generated_output_check`: confirms outputs are generated artifacts, not
  default context or source-controlled runtime inputs unless explicitly
  promoted as review fixtures.
- `no_feedback_check`: confirms results do not feed production scoring,
  ranking, report behavior, model features, score weights, or automatic
  adoption.
- `v0_1_boundary_check`: confirms frozen MVP v0.1 score/ranking/report behavior
  is unchanged.
- `v0_2_boundary_check`: confirms `prob_up_1d_candidate` is not replaced,
  reinterpreted, or trained from evaluation metrics.
- `failure_flags`: explicit failure or invalidation flags.
- `forbidden_claim_check`: confirms profitability-proof, expected-return,
  proven-alpha, and recommendation claims are absent except in blocked wording
  policy.

Optional evidence fields after a separately approved run:

- `metric_summary_path`
- `risk_metric_summary_path`
- `performance_metric_summary_path`
- `comparison_report_path`
- `known_limitations`
- `review_notes`
- `invalidation_reason`

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
- `unsupported_profitability_claim`
- `production_connection_detected`

Any active failure flag must prevent `evidence_recorded` from becoming an
adoption input. It may only support `invalidated`, `blocked`, or
`needs_more_evidence` downstream statuses.

## Evidence-Only Comparison Report

Candidate comparison reports must be separated from production outputs:

- They live under `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison/` or
  `Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/`.
- They compare candidates only for review context.
- They must not write production ranking files.
- They must not write `final_composite_score` fields.
- They must not export model feature tables.
- They must not contain recommendation, expected-return, proven-alpha, or
  profitability-proof claims.

Required report disclaimer:

`This comparison report is evidence-only. It is not a production ranking input, not a final score input, not a model feature source, not an adoption decision, and not proof of future profitability.`

## No-Feedback Gate Proposal

Before an evaluation evidence packet can be accepted, a document or validator
gate should check:

- no output path points to production ranking or report directories
- no output schema includes active `technical_composite_score` or
  `final_composite_score` writes
- no output schema exports evaluation metrics as runtime model features
- no registry or candidate status changes automatically from metric values
- no field connects evidence metrics to score weights, ranking inputs, or model
  training inputs
- `no_feedback_check` is present and explicit
- forbidden performance or recommendation language is absent except in blocked
  wording policy

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
no_feedback_check = "must_not_feed_scores_rankings_reports_models_or_auto_adoption"
v0_1_boundary_check = "no_v0_1_score_ranking_report_change"
v0_2_boundary_check = "no_prob_up_1d_training_or_reinterpretation_from_evaluation_metrics"
failure_flags = ["not_yet_run"]
forbidden_claim_check = "no_recommendation_profitability_expected_return_or_proven_alpha_claim"
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
- failure flags are absent or explicitly route the packet to `invalidated` or
  `needs_more_evidence`
- comparison report, if present, is separated as an evidence-only artifact
- no production ranking, final score, score optimization, runtime model feature,
  recommendation, or live-trading connection is present
