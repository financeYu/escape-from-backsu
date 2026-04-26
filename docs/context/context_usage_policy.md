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

- `docs/context/MVP_V0_1_BASELINE.md`
- exactly one active packet
- optional `docs/context/CONTEXT_ROUTING_INDEX.md`
- authority files linked by those context docs when the task requires them

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

Step 1-20 history belongs in explicit archive files such as
`docs/context/archive/step01_to_step20_history.md`. It should not be copied into
active packets, ordinary planning answers, or default context summaries.
