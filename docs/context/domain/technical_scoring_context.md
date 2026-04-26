# Technical Scoring Context

Purpose: route technical scoring work without reopening the full history.

Canonical references:

- `docs/score_branch_policy.md`
- `docs/step5`-era score catalog docs under `Quant_mvp/docs/`
- `docs/step8_testing_normalization_protocol.md`
- `docs/step9_research_tester_scores.md`
- `docs/step10_normalization_policy.md`
- `docs/step11_composite_score_design.md`
- `docs/step14_adoption_synthesis.md`

Boundary summary:

- No silent score redefinition.
- No future returns or lookahead as score inputs.
- Diagnostics are not alpha signals.
- Financial/fundamental data must not enter `technical_composite_score` or `final_composite_score`.
- This Pre-Step19 task introduces no new formulas.
