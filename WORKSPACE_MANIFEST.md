# WORKSPACE_MANIFEST

workspace_id: quant_v0_2_predictive_probability_impl
branch: quant/v0-2-predictive-probability-impl
role: quant-score-implementation
task_type: post_mvp_v0_2_predictive_probability_candidate
active_step: post-MVP v0.2 predictive probability implementation
owner_or_worker: Codex
created_from_commit: 4f2b349

## Purpose

Implement the approved `prob_up_1d_candidate` candidate-only predictive
probability path in a separate role worktree. The implementation covers a
feature table, label-separated training/evaluation pipeline, candidate
probability output, and validation tests.

This work must keep the MVP v0.1 production ranking and composite semantics
unchanged. The output is a candidate probability artifact only.

## Approved User Scope

- Build `prob_up_1d_candidate` so higher values mean higher modeled probability
  that `adjusted_close[t+1] > adjusted_close[t]`.
- Keep old technical scores as optional feature inputs, not as production
  ranking replacements.
- Keep labels separated from feature rows and exclude the current row when the
  next-day label is unavailable.
- Add validation tests for no-lookahead, forbidden inputs, output schema, and
  pipeline behavior.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- src/scores/
- tests/
- Quant_mvp/config/
- Quant_mvp/docs/
- docs/extension/

## Read-Only Paths

- AGENTS.md
- docs/root_hard_stops.md
- docs/roadmap_status.md
- docs/context/POST_MVP_AGENT_TASK_PACKET.md
- docs/context/EXTENSION_REGISTRY.toml
- docs/context/CHANGE_IMPACT_MATRIX.yml
- docs/contracts/
- chart_mvp/
- reserch_mvp/
- review_mvp/
- generated reports, caches, raw data, chart images, and runtime outputs

## Forbidden Actions

- Do not activate production ranking.
- Do not create trading, buy, sell, hold, expected-return, or proven-alpha
  recommendation outputs.
- Do not replace or redefine `technical_composite_score` or
  `final_composite_score`.
- Do not use valuation, fundamental, PER, PBR, ROE, accounting, filing, or
  point-in-time financial data.
- Do not use backtest metrics, realized returns, paper backtest results, or
  evaluation diagnostics as model features.
- Do not add data ingestion, external vendor assumptions, new markets, KOSDAQ,
  derivatives, NASDAQ, or overseas universe support.
- Do not commit generated reports, market caches, chart images, secrets, `.env`
  files, or nested worktree artifacts.

## Expected Handoff Output

- Candidate feature table builder with explicit feature/label separation.
- Candidate training/evaluation pipeline with no production ranking side
  effects.
- Candidate probability output containing `prob_up_1d_candidate` and optional
  diagnostics only.
- Focused validation tests and a master-up summary.

## Required Validation

- python -m pytest -q -p no:cacheprovider <focused v0.2 probability tests>
- python -m pytest -q -p no:cacheprovider tests/test_step9_scores_integration.py tests/test_step11_composite_schema.py
- git diff --check
- targeted forbidden-scope grep for ranking activation, trading wording,
  valuation/fundamental inputs, and backtest feature leakage

## Handoff Notes

This branch implements a candidate-only probability pipeline. It does not adopt
the candidate into production ranking, reports, composite scores, GUI behavior,
or trading workflows.
