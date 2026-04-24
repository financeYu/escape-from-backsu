# Valuation Pretest Selection

## Current repository verdict

Weaknesses first:

- valuation work is separated from the main technical agent
- valuation examples live in `agents/valuation/valuation_scores.example.toml`
- `point_in_time_fundamentals = false`
- `quality_fields = false`
- `analyst_revisions = false`
- `sector_metadata = false`

Because of those blockers, valuation is unavailable for implementation in the current round.
No valuation candidate should move to first-pass testing yet.

## Deferred shortlist once data is unlocked

High priority:

1. `earnings_yield`
2. `book_to_price`
3. `operating_cash_flow_yield`

Secondary adjustments:

1. `gross_profitability`
2. `accrual_quality_penalty`
3. `sector_relative_earnings_yield`

Rejected for the current design:

1. `revision_supported_value`
2. `kospi200_relative_drawdown_discount`

## Reason for conservative deferral

The issue is not that raw valuation ideas are impossible in principle.
The issue is that point-in-time-safe fundamentals are not yet available in config, so any implementation now would risk unsafe valuation claims.
See `docs/valuation_prescreening.md` for the full candidate-level screen.
