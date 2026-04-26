# Context Index

Use this index to pick the smallest useful context set before starting a task.
Workers should start from routed context and use targeted search only when a
direct conflict, missing contract, or unclear boundary is found.

## Default Prompt Context

- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/context/EXTENSION_REGISTRY.toml`
- `docs/context/CHANGE_IMPACT_MATRIX.yml`
- exactly one task-specific active packet when a task needs one
- optional routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`

Authority files named in `AGENTS.md` still govern, but they should be linked
instead of copied into active context packets.

Default answers should not repeat completed Step summaries. Use no more than
three confirmed context facts before moving to new reasoning.

## Domain Context

- GPT submission brief: `docs/context/gpt/gpt_context_quant.md`
- GPT project reference snapshot: `docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md`
- Internal GPT context generation rules: `docs/context/GPT_CONTEXT_GENERATION_RULES.md`
- Post-MVP agent update source: `docs/context/post_mvp_agent_update_chatgpt_source.md`
- Technical scoring: `docs/context/domain/technical_scoring_context.md`
- Normalization: `docs/step10_normalization_policy.md`
- Ranking: `docs/context/domain/ranking_context.md`
- Detail reports: `docs/context/domain/report_context.md`
- Backtest: `docs/context/domain/backtest_context.md`
- Valuation/fundamental: `docs/context/domain/valuation_context.md`
- Pipeline/automation: `docs/context/domain/pipeline_context.md`
- Future multi-universe: `docs/context/domain/future_multi_universe_context.md`
- Future derivatives: `docs/context/domain/future_derivatives_context.md`

## Contract Context

- Input schema: `docs/data_schema.md`, affected Step docs, and affected source contracts.
- Output schema: Step-specific docs and validation guardrails for the affected domain.
- Step 20 MVP contracts: `docs/contracts/step20_composite_contract.md` and `docs/contracts/step20_ranking_contract.md`.
- Step 20 release evidence: `docs/releases/step20_mvp_final_report.md`, `docs/releases/step20_mvp_gap_audit.md`, `docs/releases/step20_score_lineage_manifest.md`, and `docs/releases/mvp_kospi200_baseline_manifest.md`.
- Generated report boundaries: `reports/*/README.md` files and Step-specific generated-output guardrails.
- No-lookahead / no-future-data boundaries: `docs/project_checklist.md`, `docs/cross_step_conflict_check.md`, and Step-specific boundary docs.

## Archive / History Context

- Start at `docs/context/ARCHIVE_INDEX.md`.
- Open old Step, roadmap, checklist, validation, release, generated review, or
  context packet files only when the archive index and the current task justify
  the lookup.
- Old review packets: do not read or change by default.
- Obsolete generated snapshots: do not embed in context packets.

Completed Step artifacts are trusted by default unless the current task touches
their boundary, consumes their output downstream, or appears to violate a hard
stop.
