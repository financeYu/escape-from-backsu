# v0.2 Predictive Probability Validation Profile

Status: frozen validation profile for the post-MVP `v0.2 predictive probability
score route`. This profile does not approve runtime implementation.

## Required Validation Layers

Before implementation approval:

- schema/contract consistency check
- forbidden-scope grep
- label no-lookahead review
- model-input boundary review
- generated-output boundary review
- scope watchdog review
- `review_mvp` specialist review when code, tests, config, schemas, generated
  outputs, or cross-project handoffs are included

After implementation, before adoption:

- time-ordered train/validation/test split check
- feature availability check
- label separation check
- leakage check
- calibration diagnostics
- baseline comparison against old-score features
- stability and drift diagnostics
- generated-output source-control check

## Minimum Metrics For Review

- Brier score or equivalent probability-quality metric
- calibration table or reliability curve
- AUC or rank-order diagnostic
- baseline comparison
- coverage and missingness summary
- limitation report

No single metric may approve adoption by itself.

## Forbidden Validation Shortcuts

- full-sample normalization or training leakage
- future labels in live scoring inputs
- backtest metrics as model features
- parameter tuning from evaluation results without a separately approved
  versioned protocol
- trading recommendation wording
