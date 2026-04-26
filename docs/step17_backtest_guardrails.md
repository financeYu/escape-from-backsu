# Step 17 Conservative Backtest Guardrails

> Historical Step document. Not current authority; use
> `docs/roadmap_status.md` and `docs/context/ARCHIVE_INDEX.md` for current
> routing.

## Purpose

Step 17 opens conservative backtest evaluation for frozen technical-only
upstream outputs. It does not create a trading system, does not prove alpha,
does not alter score/rank/adoption/composite formulas, and does not use
valuation/fundamental data.

Step 17 does not use valuation/fundamental data.

The Step 17 validator is implemented in:

```text
src/validation/step17_backtest_guardrails.py
```

It accepts dict-like records, lists of records, pandas DataFrames, and generated
report text. It intentionally avoids Worker A backtest engine internals so it
can be integrated with result objects later.

## Boundary Notices

Generated Step 17 reports must contain all of these notices:

- evaluation-only
- not a trading recommendation
- does not redefine score or ranking formulas
- technical-only upstream ranking context
- valuation/fundamental scoring remains gated until Step 18

## Column Policy

The validator rejects future labels, trading fields, valuation/fundamental
fields, and adoption/ranking mutation fields when they appear in the wrong
context.

Always rejected examples:

- `future_return`
- `forward_return`
- `expected_return`
- `alpha`
- `signal`
- `buy`
- `sell`
- `hold`
- `recommendation`
- `target_price`
- `valuation_score`
- `fundamental_score`
- `per`
- `pbr`
- `roe`
- `eps`
- `bps`
- `market_cap`
- `cheap`
- `undervalued`
- `bargain`

Allowed only in Step 17 backtest output context:

- `realized_holding_return`
- `backtest_period_return`
- `evaluation_return`
- `evaluation_start_date`
- `evaluation_end_date`
- `execution_date`
- `exit_date`
- `transaction_cost_bps`
- `slippage_bps`
- `limitation_flags`

Step 17 input validation rejects those evaluation fields because input should
be frozen technical context, not realized outcome data.

## Report Language Policy

Reports must stay conservative and evaluation-only. The validator rejects
wording that presents the result as:

- alpha proof
- a profitable strategy
- a buy/sell/hold recommendation
- a target price or valuation conclusion
- a score formula improvement
- automatic adoption based on a backtest
- score definition, ranking, adoption, or trading-signal source material

Structured report text is screened recursively, including nested lists and
mapping values.

## Limitation Disclosure

Every generated Step 17 report must disclose the applicable limitations:

- survivorship bias if PIT constituent membership is unavailable
- corporate action / adjusted price uncertainty when applicable
- missing execution or exit price handling
- transaction cost and slippage assumptions
- no valuation/fundamental data used
- no return feedback into upstream scores

These limitations can be represented as text or as canonical
`limitation_flags`:

```text
survivorship_bias
corporate_action_adjustment_uncertainty
missing_execution_or_exit_price
transaction_cost_and_slippage
no_valuation_fundamental_data
no_return_feedback_to_scores
```

## No Feedback Loop

Step 17 backtest output must not update:

- Step 13 `review_status`
- Step 14 `adoption_state`
- Step 15 ranking input, rank, score, or composite fields
- Step 16 detail report score context

Any future score idea inspired by Step 17 observations must go through a new
explicit research/review cycle. It must not be silently patched into existing
score, normalization, adoption, ranking, or composite logic.

## Integration Notes For Worker A

Worker A can integrate the validator at result-boundary points without changing
its core engine contracts:

- call `validate_step17_backtest_input(...)` before consuming frozen Step 15/16
  context
- call `validate_step17_backtest_output(...)` before writing structured
  backtest results
- call `validate_step17_backtest_report(...)` before writing generated report
  text
- call `validate_step17_no_feedback_loop(...)` before any proposed upstream
  handoff that contains Step 17 evaluation fields

The validator does not compute realized returns. Tests use tiny toy fixtures
only to exercise boundary behavior.
