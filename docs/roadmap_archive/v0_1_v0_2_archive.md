# v0.1 and v0.2 Archive Routing

Status: archive/reference only.
Current active route: post-MVP `v0.3 research-to-strategy adoption route`.

This packet separates completed v0.1 and v0.2 material from current v0.3
progress. It is a routing aid, not an active task packet, roadmap, or
implementation instruction.

## Archive Rule

v0.1 and v0.2 are not current progress. Do not load their details by default
when working on v0.3.

Open v0.1/v0.2 files only for a named:

- provenance lookup
- regression check
- compatibility check
- release/freeze verification
- contract-boundary question

When lookup is required, open the narrowest file and section that answers the
question, then return to the v0.3 route.

## v0.1 Archive

Meaning:

- KOSPI200 technical MVP v0.1 is frozen.
- Step 20 is complete.
- v0.1 files are frozen baseline references, not active implementation work.

Primary references:

- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/contracts/step20_composite_contract.md`
- `docs/contracts/step20_ranking_contract.md`
- `docs/releases/mvp_kospi200_baseline_manifest.md`
- `docs/releases/step20_mvp_final_report.md`

Do not treat v0.1 as:

- current roadmap state
- active scoring work
- active ranking/report work
- a source of new strategy adoption instructions

## v0.2 Archive

Meaning:

- v0.2 predictive probability work is archived as a supporting compatibility
  reference.
- `prob_up_1d_candidate` may be inspected only for explicit compatibility or
  provenance tasks.
- v0.2 is not the active product goal and not the current implementation route.

Primary references:

- `docs/extension/v0_2_predictive_probability_route.md`
- `docs/extension/v0_2_probability_output_contract.md`
- `docs/extension/v0_2_prob_up_1d_label_contract.md`
- `docs/extension/v0_2_model_input_handoff_contract.md`
- `docs/extension/v0_2_predictive_validation_profile.md`
- `Quant_mvp/docs/v0_2_candidate_ml_score_entry_gate.md`

Route any explicit `prob_up_1d_candidate` compatibility task through:

- `.agents/skills/quant-candidate-ml-gate/SKILL.md`

Do not treat v0.2 as:

- active route state
- current product goal
- production ranking/report authority
- final score replacement authority
- a source of automatic strategy selection or adoption

## Current v0.3 Boundary

Current v0.3 work starts from:

- `docs/root_hard_stops.md`
- `docs/roadmap_status.md`
- `.agents/skills/quant-strategy-adoption-gate/SKILL.md`
- active v0.3 route artifacts under `docs/extension/v0_3_*.md`

v0.3 owns:

- research idea intake
- StrategyHypothesis drafting
- StrategyCandidate registry work
- candidate-only backtest/simulation evidence
- ML or rule-based selector/evaluator review
- AdoptionCandidate evidence packets

v0.3 does not inherit v0.1/v0.2 details into default context.
