# WORKSPACE_MANIFEST

workspace_id: quant_v0_2_candidate_ml_entry_gate
branch: quant/v0_2_candidate_ml_entry_gate
role: v0.2 candidate-only ML score entry gate
task_type: post_mvp_v0_2_candidate_ml_entry_gate
active_step: post-MVP v0.2 predictive probability score route
owner_or_worker: Codex
created_from_commit: 5b6346e

## Purpose

Prepare the entry gate for future `prob_up_1d_candidate` candidate-only ML
score implementation. This workspace is for contract, routing, schema/timing,
lineage, and validation-planning documentation only. It must not implement
model training, inference, ranking generation, runtime code, report behavior,
or production score activation.

## Allowed Scope

- v0.2 candidate score contract docs
- extension/status routing docs
- candidate-only schema/timing/lineage documentation
- validation/guardrail planning docs
- manifest update

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- Quant_mvp/docs/v0_2_candidate_ml_score_entry_gate.md
- docs/context/EXTENSION_REGISTRY.toml

## Read-Only Paths

- AGENTS.md
- docs/root_hard_stops.md
- docs/roadmap_status.md
- docs/context/MVP_V0_1_BASELINE.md
- docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml
- Quant_mvp/AGENTS.md
- docs/extension/v0_1n_implementation_approval_packet.md
- generated outputs, caches, raw data, chart images, archives, and local reports

## Forbidden Scope

- MVP v0.1 frozen baseline changes
- `technical_composite_score` changes
- `final_composite_score` changes
- production ranking activation
- report behavior changes
- backtest feedback loops
- valuation/fundamental activation
- new market data ingestion
- KOSDAQ150, futures/options, Nasdaq, or overseas universe activation
- buy/sell/hold recommendations
- proven-alpha, profitability, superior-strategy, or expected-return claims
- model training, inference, ranking generation, or runtime code

## Expected Output

- documented v0.2 candidate-only ML score completion definition
- `prob_up_1d_candidate` semantics
- label/timing/no-lookahead contract
- sidecar ranking boundary
- implementation gate checklist
- validation checklist

## Required Validation

- git diff --check
- TOML parse check for changed TOML files
- markdown/path sanity check when available
- python scripts/build_review_packet.py --step "v0.2 candidate ML score" --stage "entry-gate" when available
- Cross-Step Conflict Checkpoint using docs/cross_step_conflict_check.md when available

## Handoff Notes

This branch prepares entry-gate documentation only. Future implementation must
use a separately approved implementation scope and must preserve the candidate
boundary unless root/master explicitly opens a later gate.
