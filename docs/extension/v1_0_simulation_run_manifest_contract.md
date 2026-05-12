# v1.0-rc SimulationRunManifest contract

Status: Phase 3 contract for pre-freeze readiness.

## Purpose

`SimulationRunManifest` records the exact candidate-only simulation or
backtest context used to generate evidence. It makes the selected
`HorizonPolicy` snapshot auditable and keeps evidence artifacts separate from
runtime scoring, ranking, model feature construction, production activation,
or live execution.

Phase 3 consumes Phase 2 `HorizonPolicy`. It does not implement the Phase 4
`WeightConfig` loop.

## Required scope

A manifest must include:

- run identity and route scope
- candidate identity and references
- input/output artifact references
- data context and universe scope
- date range
- selected `horizon_policy_id`
- complete `horizon_policy_snapshot`
- separated horizon fields copied from the snapshot
- rebalancing disclosure
- cost/slippage model references or labels
- turnover tracking flag
- local code/config version references when available
- evidence-only and prohibited-action notices
- false live/brokerage/order/user-facing automatic rebalance flags

## Rebalancing disclosure

Historical/simulated rebalancing is allowed. The manifest must disclose whether
`rebalance_frequency` is part of tested strategy logic or evaluation mechanics.
If the code cannot infer that safely, the caller must provide
`rebalance_disclosure`.

The manifest must never present rebalancing as a user instruction.

## Blocked semantics

The manifest validator rejects live execution, brokerage integration, order
generation, trade-signal framing, user-facing automatic rebalance instruction,
move-to-cash command, production execution, and Phase 4 weight-loop activation
values outside explicit prohibited-action notices.

## Implementation

Contract/helper module:

- `Quant_mvp/backtest_mvp/simulation_run_manifest.py`

Focused tests:

- `tests/backtest/test_v1_0_simulation_run_manifest.py`
