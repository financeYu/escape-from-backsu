# v0.1n Strategy Registry Contract

Status: Stage A doc-contract only. This document defines the candidate registry
shape for future review. It does not create or activate a production config
file.

## Purpose

Define the contract that a later candidate-only base strategy registry must
satisfy before any v0.1n strategy composition implementation can proceed. The
registry exists to keep the future ML path inspectable: predefined base strategy
signals first, meta-level composition second.

## Registry Location

Proposed future artifact, not created by this Stage A document:

```text
Quant_mvp/config/v0_1n_strategy_registry.toml
```

Creating that TOML file requires a separate implementation scope. The TOML file
must remain candidate-only and must not activate production ranking.

## Registry Header

Required top-level fields:

| field | required value |
| --- | --- |
| `registry_version` | Explicit version string. |
| `candidate_line` | `v0.1n`. |
| `candidate_status` | `v0.1n_candidate`. |
| `target_release_line` | `v0.2`. |
| `allowed_universe` | `KOSPI200`. |
| `production_enabled` | `false`. |
| `ranking_enabled` | `false`. |
| `model_training_enabled` | `false` unless a later implementation scope explicitly allows training. |
| `backtest_enabled` | `false` unless a later simulation-contract scope explicitly allows evaluation. |

## Strategy Entry Contract

Each strategy entry must include:

| field | required | allowed values or rule |
| --- | --- | --- |
| `strategy_id` | yes | Stable snake_case identifier. |
| `strategy_family` | yes | `mean_reversion`, `breakout`, `trend`, `volatility`, `flow`, `regime`, or `diagnostic`. |
| `strategy_role` | yes | `base_signal`, `gate`, `risk_filter`, or `diagnostic_only`. |
| `version` | yes | Strategy contract version. |
| `candidate_status` | yes | `v0.1n_candidate`, `rejected`, or `frozen_v0.2` only after freeze. |
| `input_columns` | yes | Technical-only fields available by `decision_time`. |
| `parameters` | yes | Windows, thresholds, and transforms, config-owned. |
| `output_columns` | yes | Signal columns emitted by the strategy. |
| `minimum_history` | yes | Minimum trailing bars before valid output. |
| `warmup_policy` | yes | How invalid early rows are marked. |
| `model_input_allowed` | yes | False for `diagnostic_only`; true only for approved inputs. |
| `allowed_universe` | yes | Must remain `KOSPI200` for v0.1n. |
| `data_sources` | yes | Existing approved OHLCV/technical inputs only. |
| `lookahead_review_status` | yes | `pending`, `passed`, or `blocked`. |
| `owner_agent` | yes | Score Architect, Research Tester, ML/Validation, or Audit. |
| `review_status` | yes | `draft`, `ready_for_review`, `approved_candidate`, `blocked`, or `rejected`. |

## Forbidden Registry Inputs

Registry entries must not reference:

```text
adjusted_close[t+1]
forward_return_1d
label_up_1d_candidate
backtest_return
realized_pnl
future_rank
PER
PBR
ROE
valuation_score
financial_statement_fields
new_market_data_sources
```

## Diagnostic-Only Rule

If `strategy_role = "diagnostic_only"`, then:

```text
model_input_allowed = false
```

Diagnostic-only outputs may support coverage, warmup, missingness, stability,
or audit checks. They must not be promoted into predictive inputs without a new
reviewed registry version and explicit root/master approval.

## Versioning Rule

Any change to the following fields requires a new `registry_version`:

- `strategy_id`
- `strategy_family`
- `strategy_role`
- `input_columns`
- `parameters`
- `output_columns`
- `minimum_history`
- `warmup_policy`
- `model_input_allowed`
- `lookahead_review_status`

Viewing validation or backtest results and then changing the registry in place
is data snooping. That requires a new candidate recipe/version and must not
retroactively alter the evaluated version.

## Review Gates

A registry proposal is blocked until:

- every strategy has `lookahead_review_status = "passed"` or is excluded
- no forbidden input appears in `input_columns` or `parameters`
- diagnostic-only entries have `model_input_allowed = false`
- KOSPI200-only and existing approved data-source boundaries are preserved
- no production ranking/report/backtest/GUI activation flag is true
- review/audit confirms the registry is candidate-only

## Blocking Criteria

- BLOCK if a registry entry depends on future labels, realized returns, PnL,
  valuation/fundamental fields, or backtest results.
- BLOCK if any entry activates KOSDAQ150, futures/options, overseas markets,
  multi-universe behavior, or new market data sources.
- BLOCK if production ranking or GUI display is enabled.
- BLOCK if strategy complexity hides inspectability or creates a single opaque
  alpha model.
- BLOCK if registry changes are made after test/backtest results without a new
  version.

