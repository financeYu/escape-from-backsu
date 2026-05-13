# v1.0-rc WeightConfig loop contract

Status: Phase 4 contract for pre-freeze readiness.

## Purpose

`WeightConfig` defines candidate-only score weight combinations for historical
evaluation planning. The loop is config-driven, deterministic, capped, and
evidence-only. It consumes Phase 2 `HorizonPolicy` and attaches a Phase 3
`SimulationRunManifest` snapshot to every planned candidate run.

The loop does not select a live strategy, tune production scoring, replace
`technical_composite_score` or `final_composite_score`, or feed backtest
results upstream into scoring, ranking, or model feature construction.

## Config

Canonical config:

- `config/weight_config_loop.toml`

The default candidate set is explicit and small. It is intended for fixture and
contract validation, not for broad optimization.

## Contract fields

Each `WeightConfig` candidate records:

- `weight_config_id`
- `weight_config_version`
- `weight_config_source`
- `score_family`
- `score_group`
- `score_weights`
- `normalization_ref`
- `horizon_policy_id`
- `horizon_policy_snapshot`
- `candidate_id`
- `evaluation_mode`
- `generated_by`
- `grid_spec`
- `candidate_set_spec`
- `constraints`
- `weight_sum_policy`
- `missing_score_policy`
- `inactive_score_policy`
- `diagnostic_score_policy`
- `created_at`
- `config_digest`
- `evidence_only_notice`
- `prohibited_actions_notice`

## Loop output

`build_weight_config_loop_plan` returns a `WeightConfigLoopPlan` with one
record per candidate. Each record includes:

- `weight_config_snapshot`
- `simulation_run_manifest_ref`
- `simulation_run_manifest_snapshot`
- `rebalance_frequency`
- `rebalance_disclosure`
- `run_status = "planned_candidate_only"`

`dry_run_plan_only` is supported so Phase 4 can validate contracts without
running expensive simulations or changing existing runner behavior.

## Rebalancing disclosure

Historical/simulated rebalancing is allowed. Every planned run keeps the
resolved `rebalance_frequency` from `HorizonPolicy` and records
`rebalance_disclosure`. Rebalancing in this contract is historical simulation
context only and never a user instruction.

## Boundaries

Allowed:

- candidate-only backtest/simulation planning
- deterministic explicit candidate sets
- capped plan generation
- SimulationRunManifest snapshot attachment
- manual-review support for later Phase 6 evidence conversion

Blocked:

- live execution
- brokerage/order integration
- recommendation or trade-signal framing
- live automatic rebalance instructions
- production ranking replacement
- selecting a best weight as an action
- backtest-driven score optimization
- valuation/fundamental scoring activation
- Phase 6 `EvaluationEvidenceV1` implementation
