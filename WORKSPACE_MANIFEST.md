# WORKSPACE_MANIFEST

workspace_id: quant_v0_2_candidate_ml_implementation_gate_1
branch: quant/v0-2-candidate-ml-implementation-gate-1
role: v0.2 candidate-only ML implementation gate 1
task_type: post_mvp_v0_2_candidate_ml_implementation_gate_1
active_step: post-MVP v0.2 predictive probability score route
owner_or_worker: Codex root agent
created_from_commit: cb84964

## Purpose

Prepare implementation gate 1 for the future `prob_up_1d_candidate`
candidate-only ML score route. This workspace freezes the contract for
`adjusted_close` availability, technical-only feature allowlisting,
no-lookahead validation, and candidate-only sidecar output naming.

This workspace is contract and validation-planning only. It must not train
models, implement inference, generate sidecar rankings, alter production
ranking, alter reports, modify score formulas, or change the frozen MVP v0.1
KOSPI200 technical-only baseline.

## Allowed Scope

- Update this manifest for the dedicated implementation gate 1 branch/worktree.
- Create `Quant_mvp/docs/v0_2_candidate_ml_implementation_gate_1.md`.
- Read only route references and narrow source/config/docs paths needed to
  verify existing schema, timing, adjusted-close naming, and output-path
  conventions.
- Define contract-only validation and test requirements.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- Quant_mvp/docs/v0_2_candidate_ml_implementation_gate_1.md

## Read-Only Paths

- AGENTS.md
- docs/root_hard_stops.md
- docs/roadmap_status.md
- Quant_mvp/AGENTS.md
- Quant_mvp/docs/v0_2_candidate_ml_score_entry_gate.md
- docs/context/EXTENSION_REGISTRY.toml
- docs/extension/v0_2_generated_output_boundary.md
- docs/extension/v0_2_prob_up_1d_label_contract.md
- docs/extension/v0_2_raw_feature_lineage_contract.md
- config/data.toml
- Quant_mvp/config/
- src/preprocess/
- src/indicators/
- src/scores/
- src/scanner/
- src/validation/
- tests/validation/
- tests/scanner/
- tests/reports/
- generated outputs, caches, raw data, chart images, archives, and local reports

## Forbidden Scope

- model training
- inference pipeline implementation
- sidecar ranking generation
- production ranking activation
- report behavior changes
- score formula, weight, normalization, ranking, or runtime scoring changes
- MVP v0.1 frozen baseline changes
- valuation or fundamental feature activation
- new market-data ingestion
- KOSDAQ150, futures/options, Nasdaq, overseas, or multi-universe activation
- backtest metrics as model features
- trading recommendations, buy/sell/hold wording, proven-alpha claims,
  profitability claims, superior-strategy claims, or expected-return claims
- network Git operations

## Expected Output

- dedicated local branch/worktree confirmation
- frozen `adjusted_close` availability contract
- frozen technical-only feature allowlist and default-deny exclusions
- frozen no-lookahead validation/test contract
- frozen candidate-only sidecar output path and naming convention
- validation summary proving no runtime score/report/ranking/model code changed

## Required Validation

- git diff --check
- changed-lines check for production ranking/report activation wording
- changed-lines check that forbidden financial-claim wording appears only as
  explicit forbidden/boundary language, not as a claim
- check that `technical_composite_score` and `final_composite_score` logic were
  not changed
- check that no model training, inference, or sidecar ranking generation code
  was added
- TOML parse check only if `docs/context/EXTENSION_REGISTRY.toml` changes
- run any newly added tests or static contract checks
- git status --short

## Handoff Notes

This gate does not modify `docs/context/EXTENSION_REGISTRY.toml`. Route-only
metadata remains unchanged unless root/master explicitly asks for a metadata
update in a later step.
