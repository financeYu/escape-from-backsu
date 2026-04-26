# Step 20 Composite Contract

Notice: kospi200_mvp_technical_scanner_v0_1_scope

This contract freezes the KOSPI200 v0.1 technical composite semantics. It
clarifies existing Step 15 behavior and the Step 20 neutral-shrinkage hardening.
It does not activate valuation/fundamental scoring and does not add any
post-MVP universe.

## Layers

1. Raw score layer
   - Source: Step 9 raw score columns.
   - Raw scores remain traceability inputs and are not ranked directly.
   - Raw direction is the source of truth; Step 10 preserves direction.

2. Normalized score layer
   - Source: Step 10 same-date cross-sectional robust z-score columns.
   - Candidate direct normalized inputs must be finite, status `adequate`,
     quality `valid`, source warmup `ready`, and source coverage not blocked.
   - Neutral value in z-score space is `0.0`.

3. Family score layer
   - Direct scores are aggregated within family before the technical composite.
   - Missing direct score values are shrunk to neutral `0.0`, not dropped
     optimistically.
   - v0.1 direct families:
     - `mean_reversion_family_score`
     - `trend_breakout_family_score`
   - Context or diagnostic families do not directly contribute.

4. `technical_composite_score`
   - Mean of direct family scores after neutral shrinkage.
   - A row with fewer than the configured minimum valid direct scores is blocked
     and receives no technical composite score.
   - The score is technical/statistical only.

5. `final_composite_score`
   - For v0.1, this equals `technical_composite_score`.
   - Meaning: final MVP ranking score within the KOSPI200 technical scanner.
   - It is not valuation-aware and does not include financial/fundamental data.

## Exclusion Rules

- Diagnostic-only scores cannot directly enter family scores or the technical
  composite.
- Rejected scores cannot enter the composite.
- `blocked_by_data` scores cannot enter the composite.
- Manual-review rows cannot enter direct ranking until source-controlled review
  resolves the issue.
- Context/setup/confirmation rows are visible context only unless a later
  approved roadmap step changes the contract.

## Coverage And Warmup Policy

- `score_warmup_state != ready` blocks direct score contribution.
- Source coverage statuses `blocked`, `blocked_by_data`, `insufficient_input`,
  or `insufficient_data` block direct score contribution.
- Score status must be `adequate`.
- Score quality flag must be `valid`.
- Missing or invalid direct score values are counted in
  `neutral_shrinkage_count` and contribute neutral `0.0`.
- If all direct scores are invalid, the row is blocked and rank is missing.

## Missing Data Policy

- Missing values are never filled with favorable values.
- Neutral shrinkage is explicit and visible.
- `coverage_metric = valid_score_count / expected_score_count`.
- `coverage_status` is:
  - `adequate` when all direct scores are valid
  - `partial` when at least one but not all direct scores are valid
  - `blocked` when no direct score is valid

## Forbidden Inputs

- `future_return`, `forward_return`, `expected_return`, `realized_return`
  as upstream score/ranking inputs
- Step 17 backtest output fields
- `valuation_score`, `fundamental_score`, `PER`, `PBR`, `ROE`, target prices,
  analyst ratings, market-cap fundamentals, or other financial/fundamental data
- KOSDAQ150, futures, options, and multi-universe fields
- trading recommendation, buy/sell/hold, or proven-alpha fields

## Forbidden Output Language

Output must not claim:

- trading recommendations
- buy/sell/hold calls
- proven alpha or market-beating evidence
- valuation cheapness, undervaluation, bargain, or target-price support
- backtest-driven score improvement

The MVP wording is:

```text
KOSPI200 technical-only scanner v0.1
```
