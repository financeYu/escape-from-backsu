# Context Usage Policy

This policy is a routing aid, not an authority document. It reduces repeated
answers caused by over-reading completed roadmap history.

## Default Answer Rules

- Default answers must not repeat completed Step summaries.
- Archive/history must not be read unless a conflict, regression, or provenance check is required.
- Responses must separate `confirmed context facts` from `new reasoning` when planning, reviewing, or recommending work.
- Ordinary planning answers must repeat no more than three context facts before moving to current reasoning.

## Fresh Reasoning Rules

Future assistants and workers must:

- avoid repeating prior roadmap summaries unless requested
- produce new critique, tradeoff analysis, or implementation options for the current request
- label inferred recommendations as inference
- treat completed Step history as trusted by default, not something to restate

## Confirmed Context Facts

Use this label only for statements directly supported by default-read files:

- `AGENTS.md`
- `docs/project_checklist.md`
- `docs/roadmap_status.md`
- active `WORKSPACE_MANIFEST.md`
- `docs/context/current_context.md`
- `docs/context/context_routing.md`
- task-specific context files routed by `docs/context/context_routing.md`

## New Reasoning

Use this label for current analysis, tradeoffs, implementation options, review
judgment, or recommendations. If a recommendation is derived from the confirmed
facts but not directly stated by them, label it as inference.

## Archive Read Gate

Do not read archive/history by default. Archive read is allowed only when one of
these conditions is present:

- a named conflict between current files and prior Step evidence
- a suspected regression against a completed Step boundary
- a provenance question about why a decision exists
- a missing evidence item that cannot be resolved from default-read files

When archive read is used, name the reason and read the narrowest archive file.

## Step History Compression

Step 1-19 history belongs in `docs/context/archive/step01_to_step19_summary.md`
or other explicit archive files. It should not be copied into active packets,
ordinary planning answers, or default context summaries.
