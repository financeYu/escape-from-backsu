# Ranking Context

Canonical references:

- Step 15 latest ranking docs and guardrails.
- `docs/architecture/research_backtest_boundary_design.md`.
- `src/scanner/latest_ranking.py` only when implementation review is explicitly in scope.

Boundary summary:

- Ranking output is Step 15-owned behavior and is trusted as completed unless touched.
- Do not re-rank securities through report, backtest, valuation, or context-routing work.
- Do not add valuation/fundamental inputs to ranking.
- This Pre-Step19 task changes no ranking logic.
