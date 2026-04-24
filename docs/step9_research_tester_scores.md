# Step 9 Research Tester Scores

## 목적

이 문서는 Step 9 Part A / Part B raw score 구현의 통합 상태를 기록한다.

Step 9 산출물은 raw score testing layer다. 아래 작업은 하지 않는다.

- Step 10 normalization
- Step 11 composite score
- Step 15 ranking 또는 latest ranking
- Step 17 backtest
- forward / future return 계산
- valuation/fundamental scoring
- score adoption decision

## 통합 Entry Point

통합 호출 함수:

```text
src/scores/technical_scores.py -> calculate_all_raw_scores(df: pd.DataFrame) -> pd.DataFrame
```

입력은 Step 7 raw indicator output contract를 따른다.

필수 identity / metadata:

- `ticker`
- `date`
- `history_count`
- `minimum_history_required`
- `warmup_state`

통합 entrypoint는 다음을 거부한다.

- forbidden output-like input columns
- `PER`, `PBR`, `ROE`, `valuation_score`, `market_cap` 등 valuation/fundamental columns
- Part A와 Part B의 `ticker`/`date` alignment 불일치

## 구현 상태

| score_name | raw_column | status | note |
| --- | --- | --- | --- |
| `short_term_overreaction` | `short_term_overreaction_raw` | `implemented_for_research` | MVP locked variant: `-return_N`, where `N = [returns].short`. |
| `atr_adjusted_oversold_distance` | `atr_adjusted_oversold_distance_raw` | `implemented_for_research` | MVP locked variant: `(bollinger_mid_N - close) / ATR_M`, using configured Bollinger and ATR windows. |
| `rsi_price_divergence` | `rsi_price_divergence_raw` | `implemented_for_research` | MVP locked deterministic proxy: `max(0, -return_N) * max(0, RSI_t - RSI_{t-N})`. |
| `realized_vol_percentile` | `realized_vol_percentile_raw` | `implemented_for_research` | ticker-local current/prior `realized_vol_20` trailing percentile. Diagnostic context only. |
| `donchian_breakout_distance` | `donchian_breakout_distance_raw` | `implemented_for_research` | `(close_t / donchian_high_prior_N_t) - 1`, Step 7 prior-bar convention 사용. |
| `bollinger_width_squeeze` | `bollinger_width_squeeze_raw` | `implemented_for_research` | `-bollinger_width_N_t`. Setup/regime candidate이며 alpha signal이 아니다. |
| `cmf_confirmation` | `cmf_confirmation_raw` | `implemented_for_research` | `cmf_N_t`. Confirmation candidate이며 valuation 또는 final decision이 아니다. |
| `efficiency_ratio_trend` | `efficiency_ratio_trend_raw` | `implemented_for_research` | `sign(return_Nd_t) * efficiency_ratio_N_t`. Signed variant is documented for Step 9 testing. |

## 출력 Schema

Identity columns:

- `ticker`
- `date`

Raw columns:

- `short_term_overreaction_raw`
- `atr_adjusted_oversold_distance_raw`
- `donchian_breakout_distance_raw`
- `bollinger_width_squeeze_raw`
- `cmf_confirmation_raw`
- `rsi_price_divergence_raw`
- `realized_vol_percentile_raw`
- `efficiency_ratio_trend_raw`

Metadata columns:

- `score_warmup_state`
- `score_coverage_status`
- `score_data_quality_flag`
- `minimum_history_required`

Score-specific missing reason columns:

- `short_term_overreaction_missing_reason`
- `atr_adjusted_oversold_distance_missing_reason`
- `rsi_price_divergence_missing_reason`
- `realized_vol_percentile_missing_reason`
- `donchian_breakout_distance_missing_reason`
- `bollinger_width_squeeze_missing_reason`
- `cmf_confirmation_missing_reason`
- `efficiency_ratio_trend_missing_reason`

Forbidden outputs remain absent:

- `rank`, `ranking`, `latest_rank`
- `normalized_score`, `*_normalized`
- `technical_composite_score`, `final_composite_score`
- `forward_return`, `future_return`, `backtest_return`
- `alpha`, `signal`, `buy`, `sell`
- `valuation_score`

## Boundary Notes

- `enabled = true` in `Quant_mvp/config/scores.toml` remains candidate registry visibility only.
- `runtime_enabled = false` remains active; scanner/ranking/composite runtime is not connected.
- `realized_vol_percentile_raw` is diagnostic/regime context only, not direct alpha evidence.
- `bollinger_width_squeeze_raw` is setup/regime context only.
- `cmf_confirmation_raw` is price-volume confirmation context only.
- `rsi_price_divergence_raw` is a deterministic proxy only; discretionary
  swing-point detection remains out of scope.
- No raw score uses financial/fundamental columns.
- Missing and warmup rows are not filled with optimistic values.

## Tests

Focused and integration tests:

```powershell
python -m pytest tests\test_step9_scores_part_a.py
python -m pytest tests\test_step9_scores_part_b.py
python -m pytest tests\test_step9_scores_integration.py
python -m pytest tests\indicators\test_step7_indicators.py
```

The integration tests verify:

- Part A/B output coexistence
- the eight allowed raw score columns
- locked Part A formula variants and missing-reason behavior
- no-lookahead on toy future-row mutation
- ticker/date sorting and leading-zero preservation
- valuation/fundamental input rejection
- forbidden output column absence
