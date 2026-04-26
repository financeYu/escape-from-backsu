# Context Index

Use this index to pick the smallest useful context set before starting a task. Workers should start from routed context and use targeted search only when a direct conflict, missing contract, or unclear boundary is found.

## Always-Read Control Files

- `AGENTS.md`
- `docs/project_checklist.md`
- `docs/roadmap_status.md`
- `WORKSPACE_MANIFEST.md` in the active role worktree
- `docs/context/current_context.md`, if present later

## Domain Context

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
- Generated report boundaries: `reports/*/README.md` files and Step-specific generated-output guardrails.
- No-lookahead / no-future-data boundaries: `docs/project_checklist.md`, `docs/cross_step_conflict_check.md`, and Step-specific boundary docs.

## Archive / History Context

- Completed Step history: `docs/roadmap_archive/`
- Old review packets: do not read or change by default.
- Obsolete generated snapshots: do not embed in context packets.

Completed Step artifacts are trusted by default unless the current task touches their boundary, consumes their output downstream, or appears to violate a hard stop.
