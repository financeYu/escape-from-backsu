---
name: master-mvp-valuation-review
description: Project-local Codex skill for on-demand valuation and fundamental review in master_mvp. Use only when Review Gate selects valuation_review_required or full_review_required, or root/master explicitly requests valuation review.
---

# Valuation Review

## Skill Name

Valuation Review

## Purpose

Review valuation or fundamental material for point-in-time safety and separation
from the KOSPI200-only, technical-only MVP baseline. This skill is review-only
and candidate-only unless a separately approved post-MVP Step explicitly
authorizes valuation activation.

This skill is the canonical valuation/fundamental review gate. Do not route
valuation work through the removed Quant-local valuation agent document; that
internal document has been replaced by this Codex skill.

## When To Use

Use only when `.agents/skills/review_gate/SKILL.md` outputs:

- `valuation_review_required`
- `full_review_required`

Use also when an explicit user, root, or master request asks for
valuation/fundamental review.

Use when Quant or research ingestion routes a candidate to
`valuation_agent_handoff`; the route name is a handoff label, not a separate
agent file.

## When Not To Use

Do not use for price-only technical review, generic code review, ordinary
docs/context-only edits, or as a default review step. Do not use it to activate
valuation scoring.

## Required Inputs

Use the narrowest available inputs:

- Review Gate output
- current task summary and explicit user request
- `git diff --name-only`
- changed valuation/fundamental docs, config, schemas, fixtures, reports, or
  field names
- focused validation/test summary, if available
- changed docs or generated reports that make valuation, cheapness, target
  price, expected return, or recommendation claims
- optional separated example config:
  `.agents/skills/valuation_review/references/valuation_scores.example.toml`

## Allowed File/Tool Scope

Read only targeted changed files and directly relevant policy/context docs. Use
targeted `rg`, `git diff --name-only`, and focused validation summaries.

Do not edit score formulas, valuation activation, ranking, report semantics,
backtests, runtime behavior, or data ingestion from this skill. If a fix
requires those changes, output a handoff.

## Procedure

1. Confirm the Review Gate result authorizes this skill.
2. Identify changed valuation/fundamental paths and claims.
3. Check whether point-in-time fundamental data is explicitly proven.
4. Check filing date, effective date, availability date, reporting-lag, and
   stale-data semantics.
5. Check whether price-only data is being described with valuation language.
6. Check whether financial/fundamental data enters technical or final composite
   scoring.
7. For every valuation candidate, check the required candidate fields below.
8. Produce the output schema. Keep findings compact and Korean by default.

## Candidate Field Expectations

For each reviewed valuation candidate, require:

- `score_name`
- `score_family`
- `valuation_status`
- `purpose`
- `economic_rationale_quality`
- `raw_input_features`
- `point_in_time_requirements`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `sector_adjustment_needed`
- `expected_overlap_risk`
- `value_trap_risk`
- `failure_modes`
- `valuation_verdict`
- `valuation_comment`

Allowed values for `valuation_status`:

- `available`
- `partially_available`
- `unavailable`

Allowed values for `valuation_verdict`:

- `adopt`
- `conditional`
- `research_only`
- `reject`
- `blocked_by_data`
- `unavailable`

## Output Schema

If point-in-time fundamental data is unavailable or unproven:

```yaml
valuation_status: unavailable
valuation_verdict: unavailable
reason: "<concise Korean summary>"
required_fixes:
  - "<none or focused fix>"
```

If data availability is explicitly documented:

```yaml
valuation_status: available | partially_available | unavailable
valuation_verdict: adopt | conditional | research_only | reject | blocked_by_data | unavailable
scope:
  - "<path or material>"
point_in_time_evidence: "<short summary or unavailable>"
reason: "<concise Korean summary>"
required_fixes:
  - "<none or focused fix>"
non_blocking_risks:
  - "<none or focused risk>"
validation_seen: "<command/result summary or unavailable>"
```

## Validation Expectations

Use affected checks only. Examples:

- targeted grep for valuation/fundamental/PER/PBR/ROE/PIT fields
- schema or field check if financial data structures changed
- focused docs/report grep for forbidden valuation or advice wording
- `powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\valuation_review\scripts\validate_valuation_review_gate.sh`

Do not run the full test suite for docs-only review.

## Extensibility Notes

Intentional contract literals:

- candidate status values: `available`, `partially_available`, `unavailable`
- candidate verdict values: `adopt`, `conditional`, `research_only`,
  `reject`, `blocked_by_data`, `unavailable`
- protected score fields: `technical_composite_score`, `final_composite_score`
- forbidden advice language families: buy/sell/hold, target prices, expected
  return

Extension points:

- Add new valuation candidate example records under
  `.agents/skills/valuation_review/references/`, not in `Quant_mvp/config`.
- Add new required candidate fields in the Candidate Field Expectations section
  before enforcing them in validators.
- Add new data-availability checks through focused task validation rather than
  widening this review skill into runtime data ingestion.

## Escalation Conditions

Escalate or hand off when:

- valuation activation is requested
- point-in-time evidence is missing or ambiguous
- financial/fundamental fields may enter `technical_composite_score` or
  `final_composite_score`
- code, schemas, generated-output boundaries, or integration risk require
  `review_mvp`
- price-only data is described as cheap, undervalued, value, target price,
  expected return, or recommendation

## Optional Resources Or Scripts

- `docs/context/CODEX_REVIEW_GATE_POLICY.md`
- `.agents/skills/valuation_review/references/valuation_scores.example.toml`
- `.agents/skills/valuation_review/scripts/validate_valuation_review_gate.sh`
- `docs/review_mvp_policy.md`
- `review_mvp/review.py` only when Review Gate sets `review_mvp_required: true`

## Hard Stops

This skill must not:

- infer valuation from price-only data
- call drawdown, low RSI, oversold state, low price level, recent
  underperformance, or moving-average distance cheap, undervalued, or value
- activate valuation scoring, fundamental scoring, valuation-aware ranking, or
  valuation-aware `final_composite_score`
- invent point-in-time evidence from `collected_at` alone
- issue buy/sell/hold advice, target prices, or expected return claims
