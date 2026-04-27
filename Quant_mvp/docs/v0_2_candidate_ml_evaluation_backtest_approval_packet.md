# v0.2 Candidate ML Evaluation-Only Backtest Approval Packet

Status: root approved for evaluation-only diagnostic implementation. This
document defines the limited connection from `prob_up_1d_candidate` artifacts
to a diagnostic evaluator.

## Purpose

Define the limited scope under which candidate probability artifacts may be
evaluated by a backtest component after explicit root approval.

The evaluation is diagnostic only. It must not promote `prob_up_1d_candidate`
into production ranking, reports, `technical_composite_score`, or
`final_composite_score`.

## Candidate Artifact Inputs

Allowed candidate inputs after approval:

- candidate output field: `prob_up_1d_candidate`
- identity fields: `ticker`, `date`, `as_of_date`, `decision_time`
- timing fields: `execution_time`, `label_time`, `label_availability_time`
- sample role field: `prob_up_1d_candidate_sample_role`
- feature metadata: `feature_set_version`, `feature_schema_version`,
  `feature_schema_columns`, `prob_up_1d_feature_status`,
  `prob_up_1d_feature_valid_count`, `feature_coverage_ratio`
- label contract metadata: `label_contract_version`
- adjusted-close metadata: `adjusted_close_source_field`,
  `adjusted_close_canonical_source_status`
- model metadata: `model_version`, `model_type`

Allowed artifact sources:

- candidate output from `run_prob_up_1d_candidate_pipeline`
- candidate-only sidecar export
- candidate sidecar selection packet
- walk-forward diagnostic outputs as evaluation context only

## Explicitly Forbidden Inputs

The evaluation-only backtest must not consume:

- model feature matrices as a way to rebuild or tune the model
- `technical_composite_score`
- `final_composite_score`
- production `rank`, production ranking files, or report ordering fields
- label-derived feature columns
- future-return, forward-return, or realized-return feature columns
- generated report fields, cache-derived upstream inputs, or production report
  outputs
- valuation, fundamental, accounting, filing, analyst, or market-cap fields

## Evaluation-Only Interface Draft

The approved implementation defines an adapter with this shape:

```text
load_candidate_probability_artifact(
  artifact_path,
  expected_artifact_type,
  required_schema,
  as_of_date
) -> candidate_probability_frame

run_evaluation_only_backtest(
  candidate_probability_frame,
  evaluation_config
) -> evaluation_diagnostic_artifact
```

Required interface properties:

- reads candidate probability artifact only
- validates artifact type before evaluation
- validates required timing fields before evaluation
- validates candidate-only boundary fields before evaluation
- writes evaluation diagnostics to a generated evaluation path
- returns diagnostics only

Forbidden interface properties:

- must not call candidate feature builders
- must not call model training or model-selection routines
- must not write production ranking outputs
- must not write report outputs
- must not update score, ranking, or feature config from evaluation results

## Feedback Boundary Contract

Backtest outputs may be used only as downstream diagnostics.

The following remain false unless a later root-approved gate changes them:

```toml
backtest_feedback_into_features = false
backtest_feedback_into_model = false
backtest_feedback_into_scoring = false
backtest_feedback_into_ranking = false
backtest_feedback_into_reports = false
backtest_feedback_into_final_composite_score = false
backtest_feedback_into_technical_composite_score = false
model_selection_from_backtest = false
feature_selection_from_backtest = false
cutoff_selection_from_backtest = false
```

## Required Validators Before Implementation

Before implementation begins, the next gate must define or run:

- candidate ML gate contract validator:
  `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`
- quant review gate validator:
  `.agents/skills/quant-review-gate/scripts/validate_review_gate.sh`
- artifact schema validator for candidate outputs:
  `validate_v0_2_candidate_artifact_columns`
- feature leakage validator:
  `validate_v0_2_candidate_feature_columns`
- selection packet schema validator:
  `validate_prob_up_1d_selection_packet_schema`
- no-lookahead timing validator for `decision_time`, `execution_time`,
  `label_time`, and `label_availability_time`
- generated-output boundary validator confirming the evaluator reads candidate
  artifacts only and never reports, cache files, production ranking outputs, or
  composite outputs as upstream inputs
- forbidden feedback-loop test that fails if evaluation diagnostics are written
  into model, feature, score, ranking, report, or composite paths

## Forbidden Feedback Loop Test Plan

Minimum tests for the implementation gate:

- reject candidate artifact missing `decision_time`
- reject candidate artifact missing `prob_up_1d_candidate`
- reject artifact containing `technical_composite_score`
- reject artifact containing `final_composite_score`
- reject artifact containing production `rank`
- reject artifact containing label-derived feature columns
- reject artifact containing future-return, forward-return, or realized-return
  feature columns
- reject evaluator config that writes to production ranking or report paths
- reject evaluator config that updates model parameters, feature allowlists,
  score weights, ranking rules, or composite definitions
- confirm generated evaluation artifacts are diagnostic-only and source-control
  excluded by default

## Implementation Blockers

Implementation was opened by root approval. The following conditions remain
required for any further expansion:

- candidate artifacts remain diagnostic-only
- no-lookahead timing validation remains enforced
- generated-output boundary validation remains enforced
- forbidden feedback-loop tests remain passing
- output root for evaluation diagnostics is approved
- integration review confirms no production ranking or report exposure

## Root Approval Requirement

Root approval has been received for this evaluation-only diagnostic connection.
Any expansion beyond diagnostic-only use still requires a separate root gate.
