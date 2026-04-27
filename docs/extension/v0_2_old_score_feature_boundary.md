# v0.2 Old Score Feature And Evaluation Boundary

Status: frozen boundary contract for using old scores in the v0.2 predictive
probability route. This contract does not approve runtime model implementation.

## Purpose

Existing technical scores may be reused as `old_score_features` for
`prob_up_1d_candidate` only when they are available at or before
`decision_time`.

The old scores must not be silently redefined to improve the predictive target.

## Allowed Uses

- model input features, when computed with no lookahead
- diagnostic features for coverage, stability, missingness, and redundancy
- baseline comparison against `prob_up_1d_candidate`
- evaluation-only reports

## Forbidden Uses

- backtest result metrics as model input features
- future returns or labels as model input features
- retroactive score formula tuning from evaluation results
- automatic production ranking activation
- valuation/fundamental scoring or financial data merge
- trading recommendation language

## Backtest Metrics Boundary

Backtest metrics may be reported only as generated evaluation artifacts.

Examples of evaluation-only metrics:

- hit rate against `up_1d_label`
- calibration curve
- AUC or rank-correlation diagnostics
- turnover or rank-stability diagnostics
- simple baseline comparison

These metrics must not feed scoring, ranking, model feature construction, or
parameter selection unless a separate approved research protocol explicitly
versions that process.
