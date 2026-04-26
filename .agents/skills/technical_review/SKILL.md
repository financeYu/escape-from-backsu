---
name: master-mvp-technical-review
description: Project-local Codex skill for on-demand technical score and adoption review in master_mvp. Use only when Review Gate selects technical_review_required, adoption_review_required, or full_review_required.
---

# Technical Review

## Skill Name

Technical Review

## Purpose

Review technical score or adoption material after the Review Gate routes here.
The review checks technical usefulness and misuse risk inside the KOSPI200-only,
technical-only MVP baseline.

## When To Use

Use only when `.agents/skills/review_gate/SKILL.md` outputs:

- `technical_review_required`
- `adoption_review_required`
- `full_review_required`

Use also when root/master explicitly requests technical or adoption review.

## When Not To Use

Do not use for ordinary docs/context-only edits, README wording, local policy
maintenance, valuation/fundamental review, or generic code review. Do not use as
a default review step.

## Required Inputs

Use the narrowest available inputs:

- Review Gate output
- current task summary and explicit user request
- `git diff --name-only`
- changed technical score, diagnostics, config, contract, report, or adoption
  files
- focused validation/test summary, if available
- changed docs or generated reports that make technical usefulness, alpha,
  ranking, composite, backtest, or advice claims

## Allowed File/Tool Scope

Read only targeted changed files and directly relevant policy/context docs. Use
targeted `rg`, `git diff --name-only`, and focused validation summaries.

Do not edit score formulas, weights, thresholds, normalization, config defaults,
ranking, reports, backtests, contracts, or runtime behavior from this skill. If
a fix requires those changes, output a handoff.

## Procedure

1. Confirm the Review Gate result authorizes this skill.
2. Identify reviewed paths and whether the task is technical review or adoption
   review.
3. Check technical usefulness, distinctiveness, stability, complexity cost,
   regime fit, and redundancy.
4. Check whether diagnostics or outputs are being misused as ranking,
   composite, backtest, advice, expected return, or alpha claims.
5. Check whether backtest evidence is feeding back into score definition,
   adoption, or ranking.
6. Produce the output schema. Keep findings compact and Korean by default.

## Output Schema

```yaml
technical_review_status: pass | caution | fail | blocked
scope:
  - "<path or material>"
verdict: adopt | conditional | research_only | reject | not_applicable
reason: "<concise Korean summary>"
required_fixes:
  - "<none or focused fix>"
non_blocking_risks:
  - "<none or focused risk>"
validation_seen: "<command/result summary or unavailable>"
```

Use `not_applicable` when routed here for risky wording or schema mismatch but
no actual technical score/adoption decision is present.

## Validation Expectations

Use affected checks only. Examples:

- targeted grep for score/adoption/ranking/composite wording
- config/schema parser check if config changed
- contract/report validation if output semantics changed
- affected unit tests only when code changed

Do not run the full test suite for docs-only review.

## Escalation Conditions

Escalate or hand off when:

- code, schemas, generated-output boundaries, or integration risk require
  `review_mvp`
- the task would change formulas, ranking, composite, reports, backtests, or
  valuation status
- technical outputs are used as advice, expected return, or proven alpha
- more than one review domain is triggered

## Optional Resources Or Scripts

- `docs/context/CODEX_REVIEW_GATE_POLICY.md`
- `docs/review_mvp_policy.md`
- `review_mvp/review.py` only when Review Gate sets `review_mvp_required: true`

## Hard Stops

This skill must not:

- approve a score only because one backtest looked good
- use backtests to silently redefine a score
- claim valuation support
- infer cheapness or undervaluation from price-only data
- implement KOSDAQ150, futures/options, Nasdaq, new data sources, or valuation
  scoring
