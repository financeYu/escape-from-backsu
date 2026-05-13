# v1.0-rc Post-Freeze Backlog Separation

This Step 4 packet promotes the temporary post-freeze backlog notes into the
active route state as blocked follow-up scope. It is evidence-only route
metadata and does not authorize final v1.0 freeze, production activation, live
trading, brokerage integration, order generation, valuation/fundamental active
scoring, futures/index/macro/regime active scoring, new market-data ingestion,
or universe expansion.

## Status

| item | status | boundary |
|---|---|---|
| valuation/fundamental diagnostic layer | candidate_only | diagnostic review only; active valuation/fundamental scoring remains blocked |
| valuation/fundamental candidate-to-active promotion gate | separate_approval_required | requires later explicit root approval |
| macro/regime/futures/index layer | separate_approval_required | diagnostic notes may remain review context only; active scoring remains blocked |
| new universe | separate_approval_required | KOSDAQ150, overseas, multi-universe, or expanded ticker coverage remains blocked |
| new data ingestion | separate_approval_required | new vendor/source/crawler/raw-data path/live dependency remains blocked |
| production ranking semantics | blocked | selector/evaluator outputs remain review-prioritization aids only |
| real-time condition layer | separate_approval_required | manual-check/private current-condition support may remain review-only; automated triggers remain blocked |
| live rebalance/execution | blocked | order generation, automatic position sizing, rebalance instructions, move-to-cash commands, and execution workflows remain blocked |
| broker integration | blocked | brokerage API, account connection, credential handling, order routing, and real-money execution remain blocked |

## Freeze Boundary

- This packet is a separation ledger, not an implementation plan.
- Items listed here are outside the v1.0-rc Phase 0-9 freeze-readiness scope.
- A later task must explicitly open one narrow route before any item can move
  from backlog metadata to candidate contract work.
- None of these items may feed runtime ranking, reports, backtests, trading,
  order generation, or production activation from this packet.
