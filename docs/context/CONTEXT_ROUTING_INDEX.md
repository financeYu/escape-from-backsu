# Context Routing Index

This index is a routing aid, not an authority document. Use file paths and
targeted lookup only; do not paste long file bodies into active context.

## Default Prompt Context

- `docs/context/MVP_V0_1_BASELINE.md` - compact post-Step20 MVP baseline.
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml` - route-only pointer to
  canonical MVP v0.1 contracts.
- `docs/context/EXTENSION_REGISTRY.toml` - route-only registry for disabled
  post-MVP extension ideas.
- `docs/context/CHANGE_IMPACT_MATRIX.yml` - route-only change impact matrix.
- exactly one task-specific active packet when a task needs one.
- `docs/context/CONTEXT_ROUTING_INDEX.md` - optional targeted lookup index.

## Routes

- Historical pre-freeze optimization:
  `docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md`
  - archive-only completed routing; not an active packet.
- Release quickstart: `docs/release/MVP_V0_1_QUICKSTART.md` - high-level MVP
  usage and boundaries.
- Validation ladder: `docs/release/MVP_V0_1_VALIDATION_LADDER.md` - tiered
  validation commands and failure meaning.
- Pre-freeze duplicate-work handoff:
  `docs/release/PREFREEZE_OPTIMIZATION_HANDOFF.md` - completed local cache,
  config-status, and release-documentation work.
- Local market cache readiness:
  `reports/validation/mvp_v0_1_local_market_data_readiness.md` - compact
  read-only cache evidence; rerun only when cache or universe changes.
- KOSDAQ150 expansion planning: `docs/context/domain/future_multi_universe_context.md`
  - planning only; no implementation.
- Futures/options research planning: `docs/context/domain/future_derivatives_context.md`
  - planning only; no implementation.
- Valuation/fundamental activation design: `docs/context/domain/valuation_context.md`
  - candidate-only boundary and future activation references.
- Scoring review: `docs/context/domain/technical_scoring_context.md` - scoring
  contract pointers and guardrails.
- Ranking review: `docs/context/domain/ranking_context.md` - latest ranking
  contract pointers and guardrails.
- Report review: `docs/context/domain/report_context.md` - detail report and
  generated-output boundary pointers.
- Backtest review: `docs/context/domain/backtest_context.md` - evaluation-only
  backtest boundary pointers.
- Release/freeze verification: `docs/releases/step20_mvp_final_report.md` -
  on-demand release evidence; use compact summary first.
- Code review: `docs/review_flow.md`, `docs/review_mvp_policy.md` - review
  routing and specialist-review policy.
- Archive/provenance lookup: start at `docs/context/ARCHIVE_INDEX.md`; open
  listed historical files only for an allowed lookup reason.

## Internal GPT Route Map

Use file paths only. Do not embed document bodies. This section is an internal
route selector for building a generated GPT brief; do not paste this table into
GPT by default.

| GPT route | internal file paths only | lookup status |
| --- | --- | --- |
| planning / critique | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`, `docs/context/EXTENSION_REGISTRY.toml`, `docs/context/CHANGE_IMPACT_MATRIX.yml`, `docs/context/GPT_CONTEXT_GENERATION_RULES.md`, `docs/context/CONTEXT_BUDGET_POLICY.md`, `docs/context/CONTEXT_ROUTING_INDEX.md` | default-safe |
| Codex prompt writing | `docs/context/GPT_CONTEXT_GENERATION_RULES.md`, `docs/context/CONTEXT_BUDGET_POLICY.md`, `docs/context/CONTEXT_ROUTING_INDEX.md`, `AGENTS.md` | default-safe |
| validation prompt writing | `docs/context/GPT_CONTEXT_GENERATION_RULES.md`, `docs/context/CONTEXT_BUDGET_POLICY.md`, `docs/release/MVP_V0_1_VALIDATION_LADDER.md`, `docs/cross_step_conflict_check.md` | default-safe |
| release/freeze verification | `docs/context/MVP_V0_1_BASELINE.md`, `docs/releases/step20_mvp_final_report.md`, `docs/releases/mvp_kospi200_baseline_manifest.md`, `docs/contracts/step20_composite_contract.md`, `docs/contracts/step20_ranking_contract.md` | on-demand verification |
| scoring review | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/technical_scoring_context.md`, `docs/contracts/step20_composite_contract.md`, `docs/releases/step20_score_lineage_manifest.md` | on-demand review |
| ranking review | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/ranking_context.md`, `docs/contracts/step20_ranking_contract.md`, `docs/contracts/step20_composite_contract.md` | on-demand review |
| report review | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/report_context.md`, `docs/step16_security_detail_report.md`, `docs/architecture/step16_report_backtest_boundary.md` | on-demand review |
| valuation boundary review | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/valuation_context.md`, `docs/architecture/step18_valuation_fundamental_boundary.md`, `docs/technical_valuation_boundary.md` | on-demand review |
| KOSDAQ150 planning | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/future_multi_universe_context.md`, `docs/context/post_mvp_agent_update_chatgpt_source.md`, `docs/context/GPT_CONTEXT_GENERATION_RULES.md` | on-demand planning |
| futures/options planning | `docs/context/MVP_V0_1_BASELINE.md`, `docs/context/domain/future_derivatives_context.md`, `docs/context/post_mvp_agent_update_chatgpt_source.md`, `docs/context/GPT_CONTEXT_GENERATION_RULES.md` | on-demand planning |
| archive/provenance lookup | `docs/context/ARCHIVE_INDEX.md`, listed archive files only when needed | on-demand only |

## Archive Routes

- Archive routes are on-demand only.
- Use archive routes only for conflict investigation, regression investigation,
  provenance check, or release/freeze verification.
- Archive routes are not default-read context.
- Do not read old Step plans directly from search results. Start with
  `docs/context/ARCHIVE_INDEX.md` and then open the narrowest listed file.
