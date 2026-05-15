# Family Map

## Purpose

This document maps Step 5 MVP score candidates to families, roles, expected
overlap, and downstream review needs.

It is not a composite design. Family weights in config remain provisional and
must not be used for production scoring during Step 5.

## Family Summary

| family | candidates | branch | primary role | overlap risk | Step 9 implementation note |
| --- | --- | --- | --- | --- | --- |
| `mean_reversion` | `short_term_overreaction`, `atr_adjusted_oversold_distance` | `technical` | reversal candidates | high within family | implement both only if diagnostics compare distinctness |
| `breakout` | `donchian_breakout_distance`, `price_near_52w_high` | `technical` | capped continuation and narrow long-window candidate | high with trend ideas | compare short-window and long-window breakout distinctness before implementation or adoption |
| `squeeze_expansion` | `bollinger_width_squeeze` | `technical` | setup/regime context | medium with volatility diagnostics | report as conditional context unless review supports ranking use |
| `flow` | `cmf_confirmation`, `volume_price_confirmation` | `technical` | volume participation filters | medium with liquidity diagnostics | define linked score or filter role before direct use |
| `oscillator_divergence` | `rsi_price_divergence` | `technical` | deferred reversal proxy | medium-high with mean reversion | defer unless deterministic proxy adds distinct information |
| `volatility_regime` | `realized_vol_percentile` | `diagnostic` | risk/regime context | medium with squeeze and ATR scores | keep out of direct ranking use until reviewed |
| `trend_efficiency` | `efficiency_ratio_trend` | `technical` | limited trend-quality candidate | medium with breakout | signed versus unsigned role must be fixed; keep as the limited trend representative |
| `liquidity_risk` | `amihud_illiquidity_diagnostic` | `diagnostic` | cost/liquidity reliability context | medium with volume and volatility diagnostics | keep diagnostic-only unless explicitly reclassified |

## Overlap Watchlist

| overlap cluster | affected candidates | policy before adoption |
| --- | --- | --- |
| Short-term reversal cluster | `short_term_overreaction`, `atr_adjusted_oversold_distance`, `rsi_price_divergence` | compare correlation, rank overlap, warmup coverage, and trigger sparsity; downgrade duplicates |
| Trend and breakout cluster | `donchian_breakout_distance`, `price_near_52w_high`, `efficiency_ratio_trend`, folded relative-strength ideas | compare 20/60-day breakout, 252-day high proximity, and signed trend-efficiency distinctness before adoption |
| Volatility context cluster | `bollinger_width_squeeze`, `realized_vol_percentile`, ATR scaling | keep setup/regime diagnostics separate from direct ranking signals |
| Volume and activity cluster | `cmf_confirmation`, `volume_price_confirmation`, folded trading activity variability | keep confirmation/filter roles separate from liquidity and turnover diagnostics |
| Liquidity reliability cluster | `amihud_illiquidity_diagnostic`, `realized_vol_percentile`, volume filters | keep diagnostic branch outputs out of direct scoring unless reclassified through governance review |

## Research-Informed Candidate Weighting Note

The 2026-04-26 adjustment uses
`Quant_mvp/research_mvp/reports/research_ingestion/step5_candidate_evidence.md` as local
research support. It is not an adoption decision and does not activate runtime
scoring. The practical effect is:

- prioritize `short_term_overreaction` as the cleanest Korea-relevant reversal
  baseline
- keep `donchian_breakout_distance`, `price_near_52w_high`, and
  `efficiency_ratio_trend`, but require redundancy diagnostics before any
  long-window breakout or trend candidate is implemented or adopted
- treat `bollinger_width_squeeze`, `cmf_confirmation`, and
  `rsi_price_divergence` as lower-priority context/filter/deferred candidates
  rather than direct standalone ranking signals
- treat `volume_price_confirmation` as a linked filter candidate and
  `amihud_illiquidity_diagnostic` as diagnostic-only reliability context

## Downstream Handoff To Research Tester

Research Tester may later implement only candidates whose definitions remain
unchanged from `Quant_mvp/docs/score_definitions.md` or have an explicit versioned
definition update.

Minimum diagnostics expected later:

- raw coverage and NaN ratio
- warmup readiness
- outlier sensitivity
- cross-sectional score correlation
- rolling average correlation
- rank overlap
- turnover proxy
- family coverage summary
- data quality flags

## Composite Boundary

No family in this map is adopted into a composite during Step 5.

Later composite design must:

- aggregate within families only after diagnostics exist
- shrink toward neutral when coverage is weak
- keep `diagnostic` branch outputs out of direct scoring use unless explicitly
  reclassified through technical review
- exclude all financial and fundamental data while valuation status is deferred
