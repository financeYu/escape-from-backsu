# GPT Context Generation Rules v2

Status: internal context-generation policy only / routing aid, not an authority document.

Do not paste this document into GPT. Use it inside Codex or the repository
tooling to generate a short GPT context brief.

## Purpose

Define internal rules for generating GPT-facing context briefs with low token
waste, clear baseline trust, and no repetitive reuse of old Step summaries.

## Current Route Rule

- Post-MVP v0.3 research-to-strategy adoption is the active route.
- Post-v1.0 v1.x staged release development is active; v1.1 through v1.6
  are upstream evidence/status layers, and v2.0 evidence-readiness preparation
  is the current route.
- KOSPI200 technical MVP v0.1 is frozen archive baseline.
- v0.2 `prob_up_1d_candidate` is archived/supporting compatibility only.
- GPT-facing context must treat Step 1-20 as trusted archive baseline.
- Completed Step 1-20 history is archive-only.
- GPT-facing context must not repeat completed Step history by default.

## Default GPT Context Shape

Default GPT input = one generated brief only: `docs/context/gpt/gpt_context_quant.md`.
The brief is built from compact baseline facts plus one active request packet.
The local ChatGPT project reference snapshot is
`docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md`.
Both GPT-facing outputs are generated only when the user explicitly requests a
GPT or ChatGPT context refresh. The default is no GPT-folder refresh unless the
user explicitly asks for it.

Use this shape:

1. current baseline, compressed to no more than 3 confirmed facts
2. current request and decision needed now
3. boundaries and forbidden scope for the current request
4. north-star goal memory and evidence conditions/gaps for the current request
5. route-only task file paths for deeper lookup
6. instruction to produce fresh reasoning for the current decision

Do not include a Step-by-Step roadmap table in default GPT context.
Do not include this rules file, the budget policy, or the routing index in the
GPT prompt body.
Generate the submission brief directly as `docs/context/gpt/gpt_context_quant.md`,
not under `docs/context/generated/` or the default `docs/context/` root.

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

- v0.3 research-to-strategy adoption is the active route.
- v1.x staged release development is active after the local v1.0 freeze;
  v1.1 net profitability, v1.2 ML selector comparison, v1.3
  cost/turnover/liquidity reliability, v1.4 revision diagnostics, and v1.5
  valuation/quality/profitability readiness, and v1.6 confidence/review
  priority are upstream evidence/status layers for v2.0 readiness preparation.
- v0.1 is frozen KOSPI200 technical baseline; v0.2 `prob_up_1d_candidate` is
  archived/supporting compatibility only.
- Valuation/fundamental activation, universe expansion, new data ingestion,
  production activation, live trading, and trading recommendation work remain
  outside scope unless a later routed task explicitly opens them.

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

## Forbidden Phrase Exclusion Rule

GPT-facing context must not repeat prohibited action, recommendation,
activation, guarantee, or unsupported-performance phrases as examples. State
the safe boundary category instead, and route to `docs/root_hard_stops.md` for
the exact authority wording when a human needs the full list.

Do not copy blocked wording from authority docs into
`docs/context/gpt/gpt_context_quant.md` or the ChatGPT project reference
snapshot. Use safe phrases such as "manual-review evidence support only" and
"activation or instruction framing stays out of GPT-facing wording."

## Fresh Reasoning Requirement

GPT-facing context must ask for new reasoning about the active request. It must
not reward restating the old roadmap, old Step summaries, old validation totals,
or old score catalog entries.

## Decision-vs-Context Separation

Keep confirmed context facts separate from the new decision. Context briefs
should say what is known, what is being decided now, and what must stay out of
scope.

## North-Star Goal Memory Rule

When the user asks to refresh GPT context around their investing/quant goal,
record the goal as an evidence objective, not as a performance claim. The
brief may say the user wants to use machine learning on KOSPI200 strategy
candidates with technical, valuation, quality, risk, cost, and robustness
evidence to identify review-preferred candidates with repeatable historical
risk-adjusted evidence. It must also state that this is not a live trading
system, not a guarantee, and not authorization for valuation/fundamental score
activation or production ranking.

The brief should ask GPT to report:

- required evidence conditions, such as point-in-time data, no-lookahead
  labels/features, predeclared candidates, benchmark/risk/cost comparisons,
  walk-forward or split stability, and lineage
- current gaps or blockers, especially valuation readiness limits, formula
  reconciliation limits, missing upstream artifacts, insufficient coverage,
  or manual-review-only constraints
- the single highest-priority next task that advances evidence quality without
  crossing hard stops

## GitHub/Local Work Rule

For local Codex work, link to local file paths and current repository context.
For GitHub-facing work, include repository/PR identifiers and route to GitHub
discussion or diff paths instead of pasting long bodies.

## Forbidden Claims

GPT-facing context must not claim or imply:

- v0.2 is the active route unless the task is an explicit archived/supporting
  compatibility check
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

## North-Star Goal Memory
- Goal:
- Current framing:
- Priority:

## Conditions And Gaps To Report
- Required conditions:
- Current gaps or blockers:
- Highest-priority next task:

## Do Not Repeat
Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.

## Boundaries
- No quant/scoring/ranking/report/backtest/valuation/data-ingestion logic changes unless explicitly requested and allowed.
- Keep prohibited activation, recommendation, guarantee, and unsupported-performance phrases out of the GPT-facing prompt; route to authority docs for exact wording.

## Route-Only References
- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/context/EXTENSION_REGISTRY.toml`
- `docs/extension/v1_x_staged_release_plan.md`
- `docs/context/CHANGE_IMPACT_MATRIX.yml`
- task-specific paths only
```

## Validation Requirements

- `docs/context/GPT_CONTEXT_GENERATION_RULES.md` exists.
- `.agents/skills/gpt-context-refresh/SKILL.md` exists and preserves explicit
  user-request, local-only, latest-only, v0.3 route controls, and v1.x current
  stage controls.
- Rules include max 3 confirmed context facts.
- Rules include default GPT input = compact baseline + one active request packet.
- GPT-facing output refresh commands require `--user-requested`; GPT submission
  brief generation also requires a non-empty `--request`.
- Paired GPT-facing refresh updates both `docs/context/gpt/` files with their
  respective generators so the project reference and request brief do not drift.
- Rules include the mandatory anti-repetition phrase.
- Rules mark Step 1-20 history as archive-only.
- Rules forbid full validation logs in default context.
- Rules forbid full score catalog dumps.
- Routing index default GPT routes do not point directly to archive history.
- Generated sample GPT brief, if present, stays under 80 lines.
- Generated sample GPT brief does not contain Step 1-20 detailed roadmap history.
