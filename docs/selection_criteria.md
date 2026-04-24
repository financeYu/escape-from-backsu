# Step 4 Selection And Review Criteria

## Purpose

This document records Step 4 routing criteria before Step 5 begins.

It is not the Agent Workflow Stage 3 Technical Selection Reviewer output, and it is not Stage 4 Adoption Synthesis. It only defines how to separate technical, valuation, diagnostic, hybrid, and out-of-scope ideas before score definition work.

## Review Split

| request or candidate | route | reason |
| --- | --- | --- |
| OHLCV-only technical signal | `technical_score_architect` | can be defined in Step 5 if formula, inputs, normalization, and failure modes are explicit |
| PER, PBR, ROE, earnings, revenue, quality, profitability, book equity, cash flow, or analyst revision idea | `valuation_agent_handoff` | requires point-in-time fundamentals and valuation review |
| data quality, leakage, redundancy, stability, turnover, or overfitting concern | `diagnostic_backlog` | diagnostic only, not alpha or valuation |
| technical plus valuation idea | `hybrid_split_required` | split the branches before any scoring or composite work |
| unsupported data, opaque model, intraday-only, or non-MVP idea | `reject_log` or `out_of_scope` | not allowed in the current technical-first roadmap |

## Candidate Acceptance For Step 5

A technical candidate may enter Step 5 only if all are true:

- it uses daily OHLCV or derived technical/statistical inputs only
- it has a clear `score_branch = technical` or `diagnostic`
- valuation/fundamental inputs are not required
- it does not claim cheapness, value, or undervaluation from price-only evidence
- formula design can be documented before implementation
- normalization candidates and minimum history can be stated
- known failure modes can be stated

Step 5 acceptance means definition work may begin. It does not mean implementation, adoption, ranking, or backtest is approved.

## Valuation Deferral Criteria

Any candidate must remain deferred or unavailable if it requires:

- point-in-time fundamentals that are not validated
- disclosure or availability dates that do not exist
- reporting lag assumptions that are not documented
- stale-data handling that is not documented
- sector-relative comparison without sector metadata
- PER, PBR, ROE, earnings, revenue, profitability, quality, book equity, or cash flow inputs

## Diagnostic Criteria

Diagnostic candidates may be retained when they help review:

- coverage
- data quality
- warmup readiness
- redundancy
- correlation
- stability
- lookahead risk
- overfitting risk

They must be labeled as diagnostic and must not be shown as alpha or stock-selection scores.

## Current Pre-Step-5 Decision

The repository may proceed to Step 5 Score Architect work only under these limits:

- score definitions only
- no production score implementation
- no `technical_composite_score`
- no `final_composite_score`
- no Research Tester implementation
- no valuation/fundamental scoring
- no backtest
- no new ranking generation as Step 5 evidence

