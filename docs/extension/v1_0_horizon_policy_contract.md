# v1.0-rc HorizonPolicy contract

Status: Phase 2 contract for pre-freeze readiness.

## Purpose

`HorizonPolicy` makes horizon assumptions explicit for candidate-only,
evidence-only strategy evaluation. It replaces hidden next-day / 1D defaults
with a config-driven contract while preserving a documented `1d` compatibility
default when no explicit horizon is provided.

This contract does not implement Phase 4+ behavior and does not activate
production scoring, ranking, trading, valuation, futures, or live execution.

## Config

Canonical config:

- `config/horizon_policy.toml`

Supported `horizon_id` values:

- `1d`
- `1w`
- `1m`

The default resolver selects `1d` only when the caller does not provide an
explicit `horizon_id`. The returned policy records `defaulted = true` and a
`default_reason`, so default compatibility is visible to tests and downstream
manifests.

## Required fields

- `horizon_id`
- `signal_frequency`
- `entry_lag_trading_days`
- `holding_period_trading_days`
- `rebalance_frequency`
- `label_horizon`
- `simulation_horizon`
- `calendar_policy`

## Separation rules

- `label_horizon` is the label construction horizon.
- `simulation_horizon` is the simulation/evaluation horizon label.
- `holding_period_trading_days` is the position/evaluation holding length used
  in historical simulation.
- `entry_lag_trading_days` is timing between decision context and simulated
  entry.
- `rebalance_frequency` is historical/simulated cadence only.
- `calendar_policy` currently supports `trading_days`.

These fields must not be inferred from each other unless config explicitly
sets them to the same value.

## Rebalancing boundary

Historical/simulated rebalancing is allowed when it belongs to candidate
strategy logic or evaluation mechanics. If rebalancing materially affects
candidate evidence, the Phase 3 `SimulationRunManifest` must disclose it.

No `HorizonPolicy` may create live execution, broker orders, user-facing
automatic rebalance instructions, or recommendation language.

## Compatibility note

Existing `prob_up_1d_candidate` references remain archived/supporting
compatibility references. They are not the canonical v1.0 horizon source.
