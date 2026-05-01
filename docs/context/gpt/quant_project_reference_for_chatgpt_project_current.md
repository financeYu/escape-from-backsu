# Quant Project Current Context

Generated at: 2026-04-28T22:59:08+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## User-Requested Context Policy

- Refresh only when the user explicitly requests this ChatGPT reference update.
- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.

## Authority Order

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/root_hard_stops.md`
4. `docs/roadmap_status.md`
5. `docs/project_checklist.md` for targeted root authority lookup
6. Related source, tests, docs, and config

## Current Roadmap Position

Post-MVP `v0.2 predictive probability score route` is active for the approved candidate-only `prob_up_1d_candidate` route. Step 20 is complete, and the KOSPI200 technical MVP v0.1 baseline is frozen.

- Current baseline: MVP v0.1 frozen KOSPI200 technical-only scanner baseline.
- Current active Step: post-MVP `v0.2 predictive probability score route`.
- Current active route skill: `.agents/skills/quant-candidate-ml-gate/SKILL.md`.
- Current repeatable route validation: `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`.
- Current completion state: v0.2 `final_composite_score` prob_up_1d semantic route completed after quant-review-gate PASS.
- In `v0_2_prob_up_1d`, `final_composite_score` is the calibrated estimated probability that `adjusted_close` will be higher on the next business day than on the feature observation business day.
- Production ranking activation, report behavior changes, data-ingestion expansion, valuation/fundamental scoring activation, and trading recommendations remain blocked unless explicitly authorized by the active route and hard stops.

## Current Baseline

- MVP universe: KOSPI200 only.
- `technical_composite_score` is technical-only; in MVP v0.1, `final_composite_score` equals it.
- Valuation/fundamental data is candidate-only and must not enter technical or final composite scores.
- Backtest output is evaluation-only and must not feed upstream scoring, ranking, or model feature construction.
- Generated reports, runtime outputs, chart images, local caches, and raw market data are not default context.
- MVP v0.1 frozen baseline changes are prohibited; later changes must be managed as `v0.2+` or a separate post-MVP version/Step.

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Production ranking activation or ranking generation unless the active route explicitly authorizes it.
- Report behavior changes or runtime score semantic changes outside the active candidate ML gate.
- `final_composite_score` replacement or silent score redefinition.
- `final_composite_score` replacement remains prohibited except under `QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2` and only after all v0.2 final score gates pass.
- Financial/fundamental data in `technical_composite_score` or `final_composite_score`.
- Valuation/fundamental scoring activation.
- Backtest metrics as model features.
- Backtest feedback into scoring, ranking, or model feature construction.
- Trading recommendations, buy/sell/hold, proven-alpha, or expected-return wording.

## Route-Only References

- Root compact hard stops: `docs/root_hard_stops.md`.
- Current roadmap status: `docs/roadmap_status.md`.
- MVP baseline: `docs/context/MVP_V0_1_BASELINE.md`.
- MVP contracts: `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`.
- Extension registry: `docs/context/EXTENSION_REGISTRY.toml`.
- Candidate ML gate skill: `.agents/skills/quant-candidate-ml-gate/SKILL.md`.
- Candidate ML gate validator: `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`.
- Candidate ML score contract: `Quant_mvp/docs/v0_2_candidate_ml_score_contract.md`.
- Candidate ML implementation gate: `Quant_mvp/docs/v0_2_candidate_ml_implementation_gate_1.md`.
- Candidate ML config: `Quant_mvp/config/v0_2_candidate_ml_score.toml`.
- Quant agent scope: `Quant_mvp/AGENTS.md`.
- Score catalog: `Quant_mvp/docs/score_catalog.md` (on-demand only; not embedded).
- Archive lookup: `docs/context/ARCHIVE_INDEX.md`.
