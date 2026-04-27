# v0.2 Generated Output Boundary

Status: frozen generated-output boundary for the post-MVP `v0.2 predictive
probability score route`.

## Generated Output Roots

Generated artifacts for this route must live outside source-controlled contract
files by default. Approved generated-output roots:

- `reports/v0_2_predictive_probability/`
- `reports/validation/v0_2_predictive_probability/`
- local runtime caches under ignored cache/output roots

## Source-Control Rule

Do not commit generated probability tables, local market data, model artifacts,
charts, caches, or full evaluation reports by default.

Small review fixtures may be promoted only when all are true:

- fixture is deterministic and minimal
- fixture contains no secrets or raw local market cache
- fixture has a documented purpose
- fixture is reviewed by scope watchdog and `review_mvp` when code/config/schema
  changes are included

## Required Generated Metadata

Every generated evaluation artifact must identify:

- route: `v0_2_predictive_probability`
- model version
- feature-set version
- label contract version
- decision-time policy
- data window
- validation split
- generated-at timestamp
- candidate-only status

## Forbidden Generated Outputs Before Adoption

- production `rank`
- active `technical_composite_score` replacement
- active `final_composite_score` replacement
- buy/sell/hold lists
- expected-return reports
- proven-alpha language
