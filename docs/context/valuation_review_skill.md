# Valuation Review Skill

This is a legacy context note for the repo-local Codex skill at
`.agents/skills/valuation_review/SKILL.md`.

It runs only when `.agents/skills/review_gate/SKILL.md` selects:

- `valuation_review_required`
- `full_review_required`

It should also run when an explicit user request asks for valuation/fundamental
review, or when changed file paths, docs, reports, fields, or claims touch
valuation, fundamentals, PER, PBR, ROE, quality, profitability, accounting,
revision, filing dates, availability dates, or point-in-time financial data.

## Purpose

Review whether valuation or fundamental material is point-in-time safe,
available, and correctly separated from the KOSPI200-only technical MVP
baseline. This skill is review-only and candidate-only unless a separately
approved post-MVP Step explicitly authorizes valuation activation.

## Review Inputs

Use the narrowest available inputs:

- current task summary and user request
- `git diff --name-only`
- changed valuation/fundamental docs, config, schemas, fixtures, reports, or
  field names
- focused validation/test summary, when available
- changed docs or generated reports that make valuation, cheapness, target
  price, expected return, or recommendation claims

Do not infer missing data availability from old roadmap status, generated
reports, price-only outputs, or market drawdown context.

## Required Output

If point-in-time fundamental data is unavailable or not proven, output:

```text
valuation_status: unavailable
valuation_verdict: unavailable
reason: <concise Korean summary>
required_fixes: <none or focused list>
```

When data availability is explicitly documented, use:

```text
valuation_status: available | partially_available | unavailable
valuation_verdict: adopt | conditional | research_only | reject | blocked_by_data | unavailable
scope: <changed paths or reviewed materials>
point_in_time_evidence: <short summary or unavailable>
reason: <concise Korean summary>
required_fixes: <none or focused list>
non_blocking_risks: <none or focused list>
validation_seen: <command/result summary or unavailable>
```

## Review Criteria

Evaluate:

- explicit point-in-time fundamental values
- filing date, effective date, or availability date semantics
- reporting-lag and stale-data policy
- required raw input fields and missing/negative value handling
- sector or industry metadata when sector-relative logic is proposed
- economic rationale quality
- overlap with other valuation candidates
- value-trap and sector-distortion risks
- whether valuation language appears in price-only technical outputs

## Hard Stops

This skill must not:

- infer valuation from price-only data
- call drawdown, low RSI, oversold state, recent underperformance, moving
  average distance, or low price level "cheap", "undervalued", or "value"
- activate valuation scoring, fundamental scoring, valuation-aware ranking, or
  valuation-aware `final_composite_score`
- put financial/fundamental data into `technical_composite_score` or
  `final_composite_score`
- change score formulas, ranking behavior, report behavior, or backtest behavior
- invent point-in-time evidence from `collected_at` alone
- issue buy/sell/hold advice, target prices, or expected return claims

If the task asks for valuation activation without verified point-in-time data
and explicit post-MVP authorization, stop with `valuation_status: unavailable`
or `valuation_verdict: blocked_by_data`.
