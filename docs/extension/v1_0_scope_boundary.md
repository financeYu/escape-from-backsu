# v1.0 scope boundary

Status: pre-freeze readiness boundary for v1.0-rc planning.

## Step 1 Core Boundary Lock

Freeze-ready core boundary:

- evidence-only: locked true
- candidate-only: locked true
- manual-review-support: locked true
- live trading: locked false
- brokerage integration: locked false
- order generation: locked false
- buy/sell/hold framing: locked false
- valuation/fundamental active scoring: locked false
- futures/index/macro/regime active scoring: locked false
- production ranking replacement: locked false

## Allowed for v1.0 planning

- evidence-only candidate strategy evaluation
- candidate-only backtest/simulation planning
- horizon generalization planning
- candidate-only WeightConfig loop planning and capped dry-run plan generation
- inactive/candidate-only/diagnostic-only layer extension registration
- EvaluationEvidence and AdoptionCandidate planning
- manual-review packet planning

## Blocked

- trading instructions
- buy/sell/hold wording
- automatic rebalance
- automatic position sizing
- future-return prediction
- expected-return claims
- valuation/fundamental scoring activation
- futures/options/index trading activation
- new market-data ingestion
- multi-universe expansion
- backtest feedback into scoring/ranking/model features
- production ranking replacement
- active scoring from valuation/fundamental or futures/options/index layers

## Language boundary

Use:

- evidence-only
- historical evaluation
- manual review
- candidate prioritization
- realized/evaluation metrics
- historical risk summary
- drawdown evidence

Do not use:

- buy
- sell
- hold
- trade signal
- expected return
- guaranteed return
- proven alpha
- profitable strategy
- future return forecast
- move to cash
- automatic rebalance

## Compatibility boundary

v0.2 `prob_up_1d_candidate` may be referenced only as
archived/supporting compatibility if present.

v1.0 must not assume next-day purchase as a global default. Existing next-day
behavior may remain only as a documented compatibility/default horizon until
Phase 2 replaces it with config.

Valuation/fundamental and futures/options/index references may appear only as
future extension boundaries. They remain inactive, candidate-only, or
diagnostic-only concepts and must not become scoring, ranking, model,
backtest, or runtime behavior.

## No-feedback boundary

Historical evaluation results must not feed upstream into scoring, ranking,
score formula changes, or model feature construction. v1.0 planning may define
review artifacts that summarize realized/evaluation metrics, but those
artifacts remain manual-review inputs only until a later explicitly approved
route changes the boundary.
