# GPT Context Generation Rules v2

Status: internal context-generation policy only / routing aid, not an authority document.

Do not paste this document into GPT. Use it inside Codex or the repository
tooling to generate a short GPT context brief.

## Purpose

Define internal rules for generating GPT-facing context briefs with low token
waste, clear baseline trust, and no repetitive reuse of old Step summaries.

## Current Baseline Rule

- Step 20 is complete.
- KOSPI200 technical MVP v0.1 is freeze-ready but not yet frozen.
- GPT-facing context must treat Step 1-20 as trusted baseline.
- Completed Step 1-20 history is archive-only.
- GPT-facing context must not repeat completed Step history by default.

## Default GPT Context Shape

Default GPT input = one generated brief only: `docs/context/gpt_context_quant.md`.
The brief is built from compact baseline facts plus one active request packet.

Use this shape:

1. current baseline, compressed to no more than 3 confirmed facts
2. current request and decision needed now
3. boundaries and forbidden scope for the current request
4. route-only task file paths for deeper lookup
5. instruction to produce fresh reasoning for the current decision

Do not include a Step-by-Step roadmap table in default GPT context.
Do not include this rules file, the budget policy, or the routing index in the
GPT prompt body.
Generate the submission brief directly as `docs/context/gpt_context_quant.md`,
not under `docs/context/generated/`.

## Maximum Size Rules

- Default GPT context max 80 lines.
- Active task packet max 120 lines.
- Ordinary planning context may include at most 3 confirmed context facts.
- Generated GPT sample briefs must stay under 80 lines.

## Anti-Repetition Rules

- Do not repeat completed Step history.
- Do not paste repeated Step completion summaries.
- Do not paste old validation logs.
- Do not paste the full score catalog.
- Full validation logs are archive-only.
- Full score catalog is not default context.
- Do not copy long guardrail prose from older context.
- Use the compact baseline as trusted context and focus on the current decision.

Mandatory phrase for generated GPT context:

```text
Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.
```

## Baseline Compression Rule

Compress baseline context to the smallest useful set. Prefer:

- Step 20 complete; MVP v0.1 is freeze-ready but not yet frozen.
- KOSPI200 v0.1 is technical-only.
- Valuation/fundamental, KOSDAQ150, futures/options, Nasdaq, and trading
  recommendation work remain outside the current baseline unless a later routed
  task explicitly opens them.

## Context Fact Limit

Ordinary planning context may include at most 3 confirmed context facts before
moving to current reasoning, critique, tradeoffs, or requested output.

## Archive Lookup Rule

Archive lookup is allowed only for conflict, regression, provenance, or
release/freeze verification. Completed Step 1-20 history, full validation logs,
and full score catalog material are archive-only.

## Route-Instead-Of-Paste Rule

List file paths instead of embedding file bodies. Route to targeted files for
detail, and read archives only on demand for an allowed reason.

## Fresh Reasoning Requirement

GPT-facing context must ask for new reasoning about the active request. It must
not reward restating the old roadmap, old Step summaries, old validation totals,
or old score catalog entries.

## Decision-vs-Context Separation

Keep confirmed context facts separate from the new decision. Context briefs
should say what is known, what is being decided now, and what must stay out of
scope.

## GitHub/Local Work Rule

For local Codex work, link to local file paths and current repository context.
For GitHub-facing work, include repository/PR identifiers and route to GitHub
discussion or diff paths instead of pasting long bodies.

## Forbidden Claims

GPT-facing context must not claim or imply:

- active valuation/fundamental scoring
- KOSDAQ150, futures, options, or Nasdaq implementation
- score formula changes
- ranking behavior changes
- report behavior changes
- backtest feedback into scoring or ranking
- trading recommendations
- proven alpha, market-beating performance, or expected return signals

## Generated Context Template

```text
# GPT Context Brief

Status: routing aid, not an authority document.

## Confirmed Context
- Fact 1:
- Fact 2:
- Fact 3:

## Current Request
- Task:
- Decision needed:

## Do Not Repeat
Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.

## Boundaries
- No quant/scoring/ranking/report/backtest/valuation/data-ingestion logic changes unless explicitly requested and allowed.
- No KOSDAQ150/futures/options/Nasdaq implementation unless the routed task opens it.
- No trading recommendation or proven-alpha language.

## Route-Only References
- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/context/EXTENSION_REGISTRY.toml`
- `docs/context/CHANGE_IMPACT_MATRIX.yml`
- task-specific paths only
```

## Validation Requirements

- `docs/context/GPT_CONTEXT_GENERATION_RULES.md` exists.
- Rules include max 3 confirmed context facts.
- Rules include default GPT input = compact baseline + one active request packet.
- Rules include the mandatory anti-repetition phrase.
- Rules mark Step 1-20 history as archive-only.
- Rules forbid full validation logs in default context.
- Rules forbid full score catalog dumps.
- Routing index default GPT routes do not point directly to archive history.
- Generated sample GPT brief, if present, stays under 80 lines.
- Generated sample GPT brief does not contain Step 1-20 detailed roadmap history.
