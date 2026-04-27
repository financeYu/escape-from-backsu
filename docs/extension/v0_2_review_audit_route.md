# v0.2 Review And Audit Route

Status: frozen review/audit route for the post-MVP `v0.2 predictive probability
score route`.

## Required Review Order

1. Root-managed Quant subproject audit gate
   (`.agents/skills/quant-subproject-audit-gate/SKILL.md`) for model, label,
   ranking, generated-output, and backtest-feedback boundaries.
2. Validation evidence as a separate part of the audit packet; command success
   does not replace the audit verdict.
3. Contract review for label, model-input, probability output, generated-output,
   validation, config, and rollback contracts.
4. Implementation review only after root/master implementation approval.
5. `review_mvp` specialist review for code, tests, config, schemas,
   generated-output boundaries, or cross-project handoffs.
6. Cross-step conflict checkpoint before Step closure or downstream adoption.
7. Master integration decision.

## Blocking Findings

The route must HOLD or REJECT if any of these occur:

- future label appears in live scoring input
- backtest metric appears in model-input table
- generated output is committed outside approved fixture rules
- production ranking is activated before adoption review
- valuation/fundamental data enters technical or final composite
- trading recommendation wording appears
- validation profile is missing or failed
- audit verdict and validation evidence are collapsed into one unchecked status

## Specialist Review Trigger

`review_mvp_required` is true when implementation touches code, tests, config,
schemas, generated-output boundaries, cross-project handoffs, or Step-end/final
validation gates.
