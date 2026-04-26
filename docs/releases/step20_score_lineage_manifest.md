# Step 20 Score Lineage Manifest

Notice: kospi200_mvp_technical_scanner_v0_1_scope
MVP scope: KOSPI200 daily OHLCV technical multi-score scanner
Post-MVP only: KOSDAQ150, futures, options, valuation/fundamental scoring

This manifest freezes the Step 20 v0.1 score lineage. The ranking layer may use
only the scores marked `ranking_inclusion = direct`. Other scores remain
context, diagnostic, review-routed, rejected, or blocked material.

Neutral value for normalized z-score space is `0.0`.

## Lineage Table

| score_name | score_family | score_branch | raw_input_columns | raw_score_column | normalized_score_column | normalization_scope | score_direction | higher_is_better meaning | neutral_value | adoption_state | ranking_inclusion | diagnostic_only | rejected | blocked_by_data | coverage_requirement | warmup_requirement | family_composite_contribution | technical_composite_contribution | known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `short_term_overreaction` | `mean_reversion` | `technical` | `ticker`, `date`, `close`, `return_N` when available | `short_term_overreaction_raw` | `short_term_overreaction_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Stronger technical oversold reversal setup. Not valuation cheapness. | `0.0` | `core_adopted` | direct | false | false | false | source row ready, score status adequate, quality valid | `score_warmup_state = ready` | contributes to `mean_reversion_family_score` | yes | Can overlap with other reversal scores and can reward persistent downtrends. |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `technical` | `ticker`, `date`, `close`, `atr_14`, `bollinger_mid_20` | `atr_adjusted_oversold_distance_raw` | `atr_adjusted_oversold_distance_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Deeper ATR-scaled technical oversold distance. | `0.0` | `conditional_adopted` | review_routed | false | false | false | same Step 10 status/quality policy if later allowed | ready required before direct use | no direct v0.1 contribution | no | High redundancy risk with simpler reversal score; review-routed in v0.1. |
| `donchian_breakout_distance` | `trend_breakout` | `technical` | `ticker`, `date`, `close`, `donchian_high_prior_N` | `donchian_breakout_distance_raw` | `donchian_breakout_distance_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Closer to or above prior Donchian high. | `0.0` | `core_adopted` | direct | false | false | false | source row ready, score status adequate, quality valid | `score_warmup_state = ready` | contributes to `trend_breakout_family_score` | yes | False breakout risk; overlaps with trend strength. |
| `bollinger_width_squeeze` | `volatility_context` | `technical` | `ticker`, `date`, `bollinger_width_20` | `bollinger_width_squeeze_raw` | `bollinger_width_squeeze_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Stronger compression context because raw is negative width; not standalone direction. | `0.0` | `regime_only` | context_only | false | false | false | visible as context only | ready required before any future use | no direct v0.1 contribution | no | Direction after compression is unresolved. |
| `cmf_confirmation` | `volume_flow` | `technical` | `ticker`, `date`, `cmf_N` | `cmf_confirmation_raw` | `cmf_confirmation_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Stronger positive price-volume confirmation context. | `0.0` | `conditional_adopted` | review_routed | false | false | false | same Step 10 status/quality policy if later allowed | ready required before direct use | no direct v0.1 contribution | no | Confirmation role is not standalone selection evidence in v0.1. |
| `rsi_price_divergence` | `mean_reversion` | `technical` | `ticker`, `date`, `close`, `rsi_14`, `return_N` | `rsi_price_divergence_raw` | `rsi_price_divergence_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Stronger deterministic bullish divergence proxy, subject to sparsity review. | `0.0` | `conditional_adopted` | review_routed | false | false | false | same Step 10 status/quality policy if later allowed | ready required before direct use | no direct v0.1 contribution | no | Sparse proxy and overlap with reversal cluster. |
| `realized_vol_percentile` | `volatility_context` | `diagnostic` | `ticker`, `date`, `realized_vol_20` | `realized_vol_percentile_raw` | `realized_vol_percentile_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Higher realized volatility regime; not better or worse by itself. | `0.0` | `diagnostic_only` | diagnostic_only | true | false | false | diagnostic coverage only | ready required for diagnostic display | no direct v0.1 contribution | no | Must not become direct ranking evidence. |
| `efficiency_ratio_trend` | `trend_breakout` | `technical` | `ticker`, `date`, `close`, `efficiency_ratio_N`, `return_N` when available | `efficiency_ratio_trend_raw` | `efficiency_ratio_trend_cross_sectional_robust_z` | same-date cross-sectional robust z | preserved from raw | Cleaner positive signed trend. | `0.0` | `core_adopted` or `technical_only` | direct | false | false | false | source row ready, score status adequate, quality valid | `score_warmup_state = ready` | contributes to `trend_breakout_family_score` | yes | Can overlap with Donchian breakout and penalize noisy reversals. |

## Allowed Direct Ranking Columns

- `short_term_overreaction_cross_sectional_robust_z`
- `donchian_breakout_distance_cross_sectional_robust_z`
- `efficiency_ratio_trend_cross_sectional_robust_z`
- `mean_reversion_family_score`
- `trend_breakout_family_score`
- `technical_composite_score`
- `final_composite_score`

## Excluded From Direct Ranking

- diagnostic-only: `realized_vol_percentile`
- context/setup: `bollinger_width_squeeze`
- confirmation/review-routed: `cmf_confirmation`
- conditional/review-routed: `atr_adjusted_oversold_distance`,
  `rsi_price_divergence`
- rejected or `blocked_by_data` rows from Step 14 adoption synthesis

Financial/fundamental fields, backtest returns, future returns, target prices,
trading recommendations, and KOSDAQ150/futures/options fields are not allowed
ranking inputs or outputs for v0.1.
