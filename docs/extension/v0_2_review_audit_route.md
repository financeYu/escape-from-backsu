# v0.2 Review And Audit Route

Status: frozen review/audit route for the post-MVP `v0.2 predictive probability
score route`.

## Required Review Order

1. Scope watchdog pre-work check for model, label, ranking, generated-output,
   and backtest-feedback boundaries.
2. Contract review for label, model-input, probability output, generated-output,
   validation, config, and rollback contracts.
3. Implementation review only after root/master implementation approval.
4. `review_mvp` specialist review for code, tests, config, schemas,
   generated-output boundaries, or cross-project handoffs.
5. Cross-step conflict checkpoint before Step closure or downstream adoption.
6. Master integration decision.

## Blocking Findings

The route must HOLD or REJECT if any of these occur:

- future label appears in live scoring input
- backtest metric appears in model-input table
- generated output is committed outside approved fixture rules
- production ranking is activated before adoption review
- valuation/fundamental data enters technical or final composite
- trading recommendation wording appears
- validation profile is missing or failed

## Specialist Review Trigger

`review_mvp_required` is true when implementation touches code, tests, config,
schemas, generated-output boundaries, cross-project handoffs, or Step-end/final
validation gates.
