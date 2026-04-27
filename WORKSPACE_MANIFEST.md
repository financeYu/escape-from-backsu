# WORKSPACE_MANIFEST

workspace_id: quant_v0_2_predictive_probability_impl
branch: quant/v0-2-predictive-probability-impl
role: v0.2 candidate-only ML score implementation
task_type: post_mvp_v0_2_candidate_ml_score
active_step: post-MVP v0.2 predictive probability candidate implementation
owner_or_worker: Codex
created_from_commit: 4f2b349

## Purpose

Implement the approved `prob_up_1d_candidate` candidate-only ML scoring path in
a separate role worktree. The implementation covers a deterministic candidate
feature table, label-separated training/evaluation pipeline, as-of-date
candidate inference, candidate-only sidecar ranking artifact, validation tests,
guardrails, and documentation.

This work must keep the MVP v0.1 production ranking and composite semantics
unchanged. The output is a candidate probability artifact only.

## Approved User Scope

- Build `prob_up_1d_candidate` so higher values mean higher modeled probability
  that `adjusted_close[t+1] > adjusted_close[t]`.
- Keep old technical scores as optional feature inputs, not as production
  ranking replacements.
- Keep labels separated from feature rows and exclude the current row when the
  next-day label is unavailable.
- Generate a sidecar candidate-only ranking artifact ordered by
  `prob_up_1d_candidate` descending and ticker ascending for ties.
- Add validation tests for no-lookahead, forbidden inputs, output schema,
  candidate-only naming, sidecar ranking behavior, and production-boundary
  guardrails.

## Allowed Scope

- Candidate ML docs.
- Candidate ML config.
- Candidate ML source.
- Candidate ML tests.
- Candidate ML validation guardrails.
- Generated-output boundary docs.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- src/scores/
- src/validation/
- tests/
- Quant_mvp/config/
- Quant_mvp/docs/
- docs/extension/
- reports/ml_candidate/README.md

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

- Do not change the MVP v0.1 frozen baseline.
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
- Do not feed back backtest or evaluation results into score formulas, model
  parameters, ranking behavior, production reports, or adoption decisions.
- Do not commit generated reports, market caches, chart images, secrets, `.env`
  files, or nested worktree artifacts.

## Expected Handoff Output

- Candidate feature table builder with explicit feature/label separation.
- Candidate training/evaluation pipeline with no production ranking side
  effects.
- Candidate probability output containing `prob_up_1d_candidate`, required
  timing fields, and optional diagnostics only.
- Candidate-only sidecar ranking artifact sorted by candidate probability.
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
