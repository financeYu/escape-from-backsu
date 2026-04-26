# Current Context

This file is a compact latest-only routing aid, not an authority document.
It does not override `AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`,
the active `WORKSPACE_MANIFEST.md`, or the user's latest instruction.

## Confirmed Context Facts

- No roadmap Step is currently in progress after the MVP v0.1 freeze validation.
- KOSPI200 technical MVP v0.1 is the current frozen baseline.
- Step 20 is complete and should be treated as release/freeze provenance, not
  an active roadmap Step.
- Completed Step 1-20 outputs are trusted by default unless a conflict, regression, or provenance check requires targeted archive or release evidence review.

Ordinary planning answers should repeat no more than three context facts from this file.
They should then move to new critique, tradeoff analysis, or implementation options.

## Default-Read Context

- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/context/EXTENSION_REGISTRY.toml`
- `docs/context/CHANGE_IMPACT_MATRIX.yml`
- exactly one task-specific active packet when a task needs one
- optional routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`

Authority files named in `AGENTS.md` still govern. Keep them linked rather than
copied into active context. Use `docs/context/active_step20_packet.md` only
through `docs/context/ARCHIVE_INDEX.md` for Step 20 final-validation provenance
or post-completion review routing.

## Archive-Read Context

- `docs/context/ARCHIVE_INDEX.md`
- old Step, roadmap, checklist, validation, release, generated review, or
  context packet files listed from the archive index

Archive/history files must not be read by default. Read them only for a named
conflict, regression, provenance question, or direct evidence gap.

## Active Boundaries

- No financial or fundamental data in `technical_composite_score`.
- No financial or fundamental data in `final_composite_score`.
- No active valuation or fundamental scoring while valuation remains candidate-only.
- No generated report, backtest, or runtime output feedback into upstream score, ranking, or report construction.
- No new quant logic, scoring formulas, ranking semantics, report semantics,
  backtest semantics, valuation logic, or data ingestion outside a separately
  approved post-MVP Step/version.

## Fresh Reasoning Requirement

Future assistants and workers must separate:

- confirmed context facts: directly supported by the default-read files
- new reasoning: critique, tradeoffs, implementation options, or recommendations produced for the current request

Recommendations inferred from the confirmed facts must be labeled as inference.
Completed Step history is trusted by default and should not be restated unless the user asks for it.

## Size Budget

Keep this file under 8,000 characters. Move Step history and detailed provenance
to archive files instead of expanding this default-read context.
