# v0.4 Selector Baseline Freeze

Status: frozen v0.4 evidence-only selector baseline.
Route: `docs/extension/v0_4_ml_selector_application_route.md`.

## Freeze Decision

v0.4 selector baseline is frozen as a scikit-learn LogisticRegression model.
The baseline is evidence-only and review-assistive. It does not produce trading
orders, live execution signals, brokerage actions, or investment
recommendations.

The frozen baseline uses:

- model family: `logistic_regression`
- model library: `scikit-learn`
- selector score source: `ml_model`
- allowed use: `AdoptionCandidate` review prioritization only

This freeze does not authorize live trading, order generation, buy/sell
recommendation language, valuation/fundamental activation, production
activation, new market-data ingestion, or universe expansion.

## Frozen Artifacts

- model artifact path:
  `Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_baseline_model.pkl`
- model manifest path:
  `Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_model_manifest.json`
- trainability manifest path:
  `Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_trainability_manifest.json`
- leakage check manifest path:
  `Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_leakage_check_manifest.json`
- coefficient diagnostics path:
  `Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_logistic_coefficients.json`
- score manifest path:
  `Quant_mvp/data/v0_4/selector_scores/v0_4_selector_score_manifest.json`
- score rows path:
  `Quant_mvp/data/v0_4/selector_scores/v0_4_selector_scores.jsonl`

## Frozen Counts

- scored candidate count: 62
- prediction value row count: 62

These counts describe the current frozen v0.4 selector scoring artifact. They
are review-prioritization counts only, not trade counts or production coverage
claims.

## Warning Policy

Known baseline warnings:

- `limited_insufficient_training_rows`
- `high_feature_correlation_warning`

Both warnings are intentional baseline diagnostic warnings, not training
failures. They must remain visible in the trainability, model, score, leakage,
and coefficient diagnostics artifacts when applicable.

Because `limited_insufficient_training_rows` is present, this freeze does not
make a predictive performance claim. Manifest fields should keep
`performance_claim_allowed: false` and
`evaluation_mode: baseline_diagnostic_only`.

Because `high_feature_correlation_warning` is present, coefficient
interpretation is diagnostic-only. Individual coefficients may be unstable
when correlated features are present.

## Interpretation Limits

- The LogisticRegression score is an evidence-only review prioritization aid.
- The score is not a trading signal, investment recommendation, order
  instruction, or production activation input.
- Limited training rows prevent strong predictive claims.
- High feature correlation limits coefficient interpretation to diagnostics.

## RandomForest Challenger

LogisticRegression remains the frozen v0.4 baseline. RandomForest is added
only as a nonlinear challenger for diagnostic comparison against the same
candidate set.

This stage is not model replacement. The default `selector_score_source`
remains the frozen LogisticRegression baseline path, and any switch in selector
policy is deferred to a separate approval.

The LR/RF score comparison is a research aid for review prioritization. It is
diagnostic-only and does not claim RandomForest performance superiority.

## v0.4.1 ML Score Ranking

v0.4.1 adds an extensible ML score ranking/comparison layer. The initial model
registry compares only:

- `logistic_regression` as the frozen baseline and baseline-relative reference
- `random_forest` as `nonlinear_challenger`

The ranking artifact is diagnostic-only:

- ranking rows:
  `Quant_mvp/data/v0_4/selector_scores/v0_4_1_selector_ml_score_ranking.jsonl`
- ranking manifest:
  `Quant_mvp/data/v0_4/selector_scores/v0_4_1_selector_ml_score_ranking_manifest.json`
- evaluation mode: `diagnostic_ranking_only`
- selector score source unchanged: `true`
- performance claim allowed: `false`
- trading signal allowed: `false`

Ranking fields may include model-specific score, rank, availability, and
baseline-relative delta values. Baseline-relative deltas are anchored to the
frozen LogisticRegression baseline. They must not change `selector_score`,
`selector_rank`, runtime ranking, trading behavior, or AdoptionCandidate
selection/ordering logic.

## Next Steps

AdoptionCandidate review packets may link the v0.4.1 ranking manifest only as a
diagnostic reference. Candidate follow-up work:

- connect selector scores to the AdoptionCandidate review packet builder
- record `selector_score_source=ml_model` at packet level
- propagate packet-level selector warnings
- include: "Selector scores are review-prioritization aids only and are not
  trading signals."
