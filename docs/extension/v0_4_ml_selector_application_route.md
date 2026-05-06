# v0.4 ML Selector Application Route

Status: active evidence-only ML/rule selector application route.
Parent input route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Training contract: `docs/extension/v0_4_selector_model_training_contract.md`.
Manifest contract: `docs/extension/v0_4_selector_model_manifest_contract.md`.

## Purpose

v0.4 starts at ML selector application. v0.3 remains the
research-to-strategy adoption evidence lane and owns `StrategyCandidate`,
`EvaluationEvidence`, selector labels, and the v0.3 feature matrix. v0.4
consumes those prepared inputs to check trainability and, only when every gate
passes, apply an evidence-only baseline ML or rule selector for
`AdoptionCandidate` review prioritization.

This route does not authorize live trading, brokerage integration, order
generation, buy/sell recommendations, production activation, valuation
activation, market-data ingestion expansion, or universe expansion.

## Path Boundary

Commands run from the `master_mvp` repository root. v0.4 script paths are:

- `Quant_mvp/scripts/ml/train_v0_4_selector_baseline.py`
- `Quant_mvp/scripts/ml/score_v0_4_selector_candidates.py`

v0.3 input artifacts are read-only inputs. v0.4 outputs are written under:

- `Quant_mvp/data/v0_4/selector_model_training/`
- `Quant_mvp/data/v0_4/selector_scores/`

## Inputs

- v0.3 selector feature matrix, currently
  `v0_3_selector_feature_matrix_v1_0`.
- v0.3 selector feature matrix manifest.
- Candidate-level `EvaluationEvidence` metric summaries represented in the
  v0.3 feature matrix rows.

Generic momentum proxy data may be retained only as benchmark/reference
context. It must not become a supervised label or candidate-level metric.

The current v0.3 input manifest is expected to provide both positive and
negative labels. If those classes are present but the local ML dependency is
missing, v0.4 must record `blocked_missing_ml_dependency` rather than
fabricating labels, installing packages, or silently falling back to a trained
claim.

## Outputs

Allowed outputs are:

- trainability manifest
- model manifest, only if a model is actually trained
- selector score manifest, only if scores are generated
- readiness report
- AdoptionCandidate review ranking input

Every output remains evidence-only and review-prioritization-only. It is not a
trade signal and not an activation decision.

## Trainability Gate

The first v0.4 gate checks:

- candidate-level `EvaluationEvidence` exists
- positive and negative supervised labels both exist
- required core features are present
- label, status, reason, adoption, selector, and prediction columns are absent
  from training features
- generic proxy rows are not used as supervised labels
- ML dependencies are available before fitting

Known blockers:

- `blocked_no_candidate_level_evidence`
- `blocked_no_positive_negative_classes`
- `blocked_missing_ml_dependency`
- `blocked_label_leakage_columns_found`
- `blocked_missing_required_core_feature`
- `blocked_generic_proxy_used_as_label`

If the gate blocks, no model fit is performed, no model artifact is created,
and `prediction_value_row_count` remains `0`.

## Warnings

Warnings do not block training by themselves:

- `limited_insufficient_training_rows`
- `high_feature_correlation_warning`

## Baseline Model

The first baseline candidate is logistic regression with conservative defaults:

- `class_weight = balanced`
- `max_iter = 1000`
- training features limited to the six v0.3 core columns

The baseline is for rule replication and review-prioritization audit only. It
must not be described as a future return predictor or trading model.

## Next Required Work

The next required work is to keep adding candidate-level `EvaluationEvidence`
and positive/negative labels. Model application quality cannot improve safely
without broader candidate-level evidence coverage.
