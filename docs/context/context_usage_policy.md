# Context Usage Policy

This policy is a routing aid, not an authority document. It reduces repeated
answers caused by over-reading completed roadmap history.

## Task Start Context Optimization Directive

Do not read full repository history at task start. Default context must be
limited to:

1. current root authority state and hard stops
2. the affected subproject `AGENTS.md`
3. exactly one active context packet for the current task
4. one required domain context stub, when needed
5. targeted source, test, or config files that may be changed

Completed Step 1-20 outputs are trusted by default. Archive files and old Step
detail documents may be read only for conflict, regression, provenance, or
release-evidence checks, and then only through the narrowest relevant file.

Answers and handoffs must not repeat completed Step history. State no more than
three confirmed context facts before focusing on current judgment, changes,
validation, and remaining risk.

Active packets must not copy long document bodies, validation logs, generated
outputs, raw market data, caches, chart images, or archive content. Use file
paths and short purpose notes instead.

If work touches scoring, ranking, reports, backtests, valuation, generated-output
boundaries, roadmap verdicts, or root policy, follow the existing guardrails and
worktree/branch separation policy.

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
