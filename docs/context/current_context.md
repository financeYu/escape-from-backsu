# Current Context

This file is a compact latest-only routing aid, not an authority document.
It does not override `AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`,
the active `WORKSPACE_MANIFEST.md`, or the user's latest instruction.

## Confirmed Context Facts

- Step 20 = COMPLETE / KOSPI200 MVP Completeness Hardening & Final Done Validation.
- No roadmap Step is currently in progress after the MVP v0.1 freeze-ready validation.
- Completed Step 1-20 outputs are trusted by default unless a conflict, regression, or provenance check requires targeted archive or release evidence review.

Ordinary planning answers should repeat no more than three context facts from this file.
They should then move to new critique, tradeoff analysis, or implementation options.

## Default-Read Context

- `AGENTS.md`
- `docs/project_checklist.md`
- `docs/roadmap_status.md`
- active `WORKSPACE_MANIFEST.md`
- `docs/context/current_context.md`
- `docs/context/context_usage_policy.md`
- `docs/context/context_routing.md`

Use `docs/context/active_step20_packet.md` only for Step 20 final-validation
provenance or post-completion review routing.
Use task-specific domain stubs from `docs/context/context_routing.md` for scoring,
ranking, report, backtest, valuation boundary, research ingestion, code review, or planning work.

## Archive-Read Context

- `docs/context/archive/step01_to_step19_summary.md`
- `docs/roadmap_archive/`
- old generated review or context packets

Archive/history files must not be read by default. Read them only for a named
conflict, regression, provenance question, or direct evidence gap.

## Active Boundaries

- No financial or fundamental data in `technical_composite_score`.
- No financial or fundamental data in `final_composite_score`.
- No active valuation or fundamental scoring while valuation remains candidate-only.
- No generated report, backtest, or runtime output feedback into upstream score, ranking, or report construction.
- No new quant logic, scoring formulas, ranking semantics, report semantics,
  backtest semantics, valuation logic, or data ingestion outside a separately
  approved post-MVP Step.

## Fresh Reasoning Requirement

Future assistants and workers must separate:

- confirmed context facts: directly supported by the default-read files
- new reasoning: critique, tradeoffs, implementation options, or recommendations produced for the current request

Recommendations inferred from the confirmed facts must be labeled as inference.
Completed Step history is trusted by default and should not be restated unless the user asks for it.

## Size Budget

Keep this file under 8,000 characters. Move Step history and detailed provenance
to archive files instead of expanding this default-read context.
