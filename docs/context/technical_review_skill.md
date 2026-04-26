# Technical Review Skill

This is a legacy context note for the repo-local Codex skill at
`.agents/skills/technical_review/SKILL.md`.

It runs only when `.agents/skills/review_gate/SKILL.md` selects one of:

- `technical_review_required`
- `adoption_review_required`
- `full_review_required`

It must not run as a default step for ordinary docs, context, README, or local
policy maintenance work.

## Purpose

Review technical score or adoption material after the Review Gate routes here.
This skill evaluates whether technical score outputs are useful, distinct,
stable, and safe to interpret inside the KOSPI200-only technical MVP baseline.

## Review Inputs

Use the narrowest available inputs:

- current task summary and user request
- `git diff --name-only`
- changed technical score, diagnostics, config, contract, report, or adoption
  files
- focused validation/test summary, when available
- changed docs or generated reports that make technical usefulness, alpha,
  ranking, composite, backtest, or advice claims

Do not read archive/history files or full validation logs unless a named
conflict, regression, provenance question, or release-evidence check requires
the narrowest possible lookup.

## Review Criteria

Evaluate:

- technical usefulness
- technical distinctiveness and redundancy risk
- stability and coverage across expected data conditions
- complexity cost versus interpretability
- regime fit and market-structure plausibility
- turnover, friction, and fragility concerns when evidence is available
- whether diagnostics are being misused as direct ranking, composite, backtest,
  alpha, or advice signals
- whether backtest output is being fed back into score definition, adoption, or
  ranking
- whether reports imply a recommendation, expected return, or proven alpha

## Required Output

```text
technical_review_status: pass | caution | fail | blocked
scope: <changed paths or reviewed materials>
verdict: adopt | conditional | research_only | reject | not_applicable
reason: <concise Korean summary>
required_fixes: <none or focused list>
non_blocking_risks: <none or focused list>
validation_seen: <command/result summary or unavailable>
```

Use `not_applicable` when the gate routed here because of risky wording or
schema mismatch but no actual technical score/adoption decision is present.

## Hard Stops

This skill must not:

- change score formulas, weights, thresholds, normalization, or config defaults
- change ranking behavior, composite behavior, report behavior, or backtest
  behavior
- activate a score, composite member, ranking rule, or production report
  semantic by itself
- approve a score only because one backtest looked good
- use backtest results as permission to silently redefine a score
- claim valuation support
- infer valuation, cheapness, or undervaluation from price-only data
- implement KOSDAQ150, futures/options, Nasdaq, new data sources, or valuation
  scoring

If a required fix would alter runtime logic, contracts, schemas, reports,
ranking, composite, or backtest behavior, stop with a focused handoff instead of
editing those areas from this skill.
