# Step 20 Ranking Sanity Report

Notice: kospi200_mvp_technical_scanner_v0_1_scope
Scope: KOSPI200 daily OHLCV technical scanner v0.1
Fixture basis: deterministic synthetic Step 20 fixture; no live market cache or network data was used.

This is a static output-quality sanity report only. It is not a trading
recommendation, not a performance report, and not valuation/fundamental review.

## Ranking Snapshot

Top 20 ranking snapshot, fixture-limited:

| rank | ticker | final_composite_score | key contributors |
| --- | --- | --- | --- |
| 1 | `000660` | 1.25 | `trend_breakout_family_score`, balanced direct scores |
| 2 | `005930` | 1.00 | `mean_reversion_family_score`, trend context |
| 3 | `051910` | 1.00 | deterministic tie resolved by ticker |
| 4 | `035420` | 0.50 | lower direct technical score context |

Bottom 20 ranking snapshot, fixture-limited:

| rank | ticker | final_composite_score | key contributors |
| --- | --- | --- | --- |
| 4 | `035420` | 0.50 | lower direct technical score context |
| 3 | `051910` | 1.00 | deterministic tie resolved by ticker |
| 2 | `005930` | 1.00 | `mean_reversion_family_score`, trend context |
| 1 | `000660` | 1.25 | `trend_breakout_family_score`, balanced direct scores |

## Distribution Summary

| metric | fixture result |
| --- | --- |
| family score distribution | two direct families: `mean_reversion`, `trend_breakout` |
| coverage distribution | 4 adequate rows, 0 partial rows, 0 blocked rows |
| warmup status distribution | 4 ready rows, 0 blocked rows |
| data quality flag summary | 4 valid rows |
| blocked row count | 0 |
| missing/neutral-shrinkage count | 0 in base fixture; focused tests cover nonzero shrinkage |
| tie count | 1 deterministic tie pair: `005930` and `051910` |

## Boundary Confirmations

- diagnostic-only scores are not directly ranked.
- rejected scores are not directly ranked.
- blocked_by_data scores are not directly ranked.
- valuation/fundamental data is not active.
- backtest outputs did not feed upstream scoring.
- KOSDAQ150 was not implemented.
- Futures/options were not implemented.
- MVP remains KOSPI200-only.

## Limitations

- This report uses a deterministic fixture because real local market data is not
  assumed available in Step 20 validation.
- The fixture validates output shape, deterministic ranking, coverage/warmup
  reporting, neutral-shrinkage visibility, and boundary language.
- This report does not claim live production data quality or investment results.
