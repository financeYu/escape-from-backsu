# Step 20 Ranking Contract

Notice: kospi200_mvp_technical_scanner_v0_1_scope

This contract freezes the v0.1 latest ranking behavior for the KOSPI200 daily
OHLCV technical scanner.

## Ranking Date Selection

- Default `ranking_date` is the maximum normalized input `date` that is not
  later than `max_allowed_date`.
- If `as_of_date` is provided, it must exist in the normalized score input and
  must not be in the future relative to `max_allowed_date`.
- v0.1 uses a single same-date snapshot. It does not carry stale per-ticker rows
  forward from older dates.
- Ticker-level selection requires at most one row per `ticker` and selected
  `date`; duplicate ticker/date rows are rejected upstream.
- Ticker strings follow the KOSPI200/Naver six-character uppercase
  alphanumeric policy (`^[0-9A-Z]{6}$`); numeric-only codes must preserve
  leading zeroes as strings.

## Rank Direction And Ties

- Higher `final_composite_score` ranks better.
- Sort keys are deterministic:
  1. `final_composite_score` descending
  2. `ticker` ascending
- Tied scores therefore sort by policy-normalized ticker string.
- Rank values are consecutive for rankable rows.
- Blocked rows receive no rank and sort last.

## Coverage, Warmup, And Blocked Rows

- `warmup_status = ready` only when source `score_warmup_state = ready`.
- `coverage_metric` is valid direct score count divided by expected direct score
  count.
- `neutral_shrinkage_count` records missing or invalid direct scores that were
  shrunk to neutral `0.0`.
- `coverage_status` is `adequate`, `partial`, or `blocked`.
- `ranking_validity_flag` mirrors the conservative row state:
  `valid`, `partial`, or `blocked`.
- Rows with fewer than the minimum valid score count receive missing composite
  scores and no rank.

## Required Ranking Output Columns

The v0.1 ranking output must include:

- `ticker`
- `date`
- `rank`
- `technical_composite_score`
- `final_composite_score`
- `coverage_metric`
- `data_quality_flag`
- `warmup_status`
- direct component normalized score fields
- family score fields
- `coverage_status`
- `ranking_validity_flag`
- `valid_score_count`
- `expected_score_count`
- `neutral_shrinkage_count`
- `review_routed_score_count`
- `final_score_policy`
- `technical_only_notice`

Optional diagnostic columns are allowed only when they are not score-like,
financial/fundamental, future/performance, trading, or post-MVP universe fields.

## Forbidden Columns

Ranking output must not include:

- `future_return`
- `forward_return`
- `realized_return` as an upstream score input
- `expected_return`
- `alpha`
- `proven_alpha`
- buy/sell/hold recommendation fields
- `target_price`
- `valuation_score`
- `fundamental_score`
- `undervalued`
- `cheap`
- KOSDAQ150, futures, options, or multi-universe ranking fields

## Step 16 And Step 17 Boundaries

- Step 16 may display Step 15/20 ranking fields as read-only technical context.
- Step 16 must not re-rank, recommend trades, or add valuation language.
- Step 17 may consume ranking as frozen input context.
- Step 17 outputs must not feed back into scoring, ranking, adoption states, or
  report semantics.
