# Step 9 Research Tester Scores Part B

## 목적

이 문서는 Step 9 Part B에서 구현한 breakout / squeeze / flow / trend
raw score 범위를 기록한다.

Part B 구현은 `src/scores/trend_vol_flow_scores.py`에 한정된다. 이 작업은
raw score 계산과 toy-data tests만 포함하며, normalization, ranking,
composite score, backtest, valuation/fundamental scoring은 수행하지 않는다.

## 입력 계약

입력은 Step 7 `technical_indicators.csv` schema를 따른다.
Part B 단독 entrypoint도 forbidden output-like input columns와
valuation/fundamental columns를 거부한다.

필수 identity:

- `ticker`
- `date`

Score별 dependency:

- `donchian_breakout_distance`: `close`, `donchian_high_prior_N`
- `bollinger_width_squeeze`: `bollinger_width_N`
- `cmf_confirmation`: `cmf_N`
- `efficiency_ratio_trend`: `efficiency_ratio_N`, `return_Nd` 또는 `close`

기본 window는 `Quant_mvp/config/windows.toml`에서 로드하며 현재 Step 7
indicator dependency window와 맞춘다. `minimum_history_required`는
`Quant_mvp/config/scores.toml`의 Part B score 후보 minimum history에서
보수적으로 산출한다.

- `donchian = 20`
- `bollinger = 20`
- `cmf = 20`
- `efficiency_ratio = 20`
- `minimum_history_required = 60`

테스트에서는 toy-data를 위해 작은 window를 명시적으로 주입한다.

## 출력 계약

출력 raw columns:

- `donchian_breakout_distance_raw`
- `bollinger_width_squeeze_raw`
- `cmf_confirmation_raw`
- `efficiency_ratio_trend_raw`

출력 identity / metadata:

- `ticker`
- `date`
- `minimum_history_required`
- `score_warmup_state`
- `score_coverage_status`
- `score_data_quality_flag`

Score별 missing reason:

- `donchian_breakout_distance_missing_reason`
- `bollinger_width_squeeze_missing_reason`
- `cmf_confirmation_missing_reason`
- `efficiency_ratio_trend_missing_reason`

Forbidden outputs는 생성하지 않는다. 특히 `rank`, `ranking`,
`normalized_score`, `*_normalized`, `technical_composite_score`,
`final_composite_score`, `forward_return`, `future_return`,
`backtest_return`, `alpha`, `signal`, `buy`, `sell`, `valuation_score`를
내보내지 않는다.

## Raw Formula

`donchian_breakout_distance_raw`:

```text
(close_t / donchian_high_prior_N_t) - 1
```

`donchian_high_prior_N`는 Step 7 prior-bar convention을 사용한다. ATR-scaled
variant는 이번 Part B에서 구현하지 않았다.

`bollinger_width_squeeze_raw`:

```text
-bollinger_width_N_t
```

작은 width가 더 강한 compression context로 읽히도록 raw sign만 뒤집었다.
이는 percentile 또는 normalized score가 아니다. squeeze는 setup/regime
candidate로만 기록하며 alpha signal처럼 표현하지 않는다.

`cmf_confirmation_raw`:

```text
cmf_N_t
```

Named interaction score가 아직 없으므로 gated interaction은 구현하지 않았다.
이 값은 price-volume confirmation candidate일 뿐 standalone valuation,
final decision, 또는 ownership inference가 아니다.

`efficiency_ratio_trend_raw`:

```text
sign(return_Nd_t) * efficiency_ratio_N_t
```

`return_Nd`가 없거나 row-level로 missing이고 `close`가 있으면 ticker별
`close_t - close_{t-N}`의 sign을 사용한다. 이 fallback은 sign 계산에만
사용하며 future row를 참조하지 않는다.

## Missing / Warmup Policy

- `ticker`, `date`는 정렬 전에 string/date로 정규화한다.
- duplicate `ticker`/`date`는 fail-fast 처리한다.
- `ticker`는 string으로 유지해 leading zero를 보존한다.
- ticker별 `date` 정렬 후 계산한다.
- `history_count`가 있으면 사용하고, 없으면 ticker별 cumcount로 계산한다.
- `minimum_history_required` 미만 row는 raw score를 NaN으로 둔다.
- dependency column이 없으면 해당 score만 `missing_dependency`로 block한다.
- denominator가 0이면 유리한 값으로 채우지 않고 `zero_denominator`로 남긴다.
- raw NaN은 optimistic score로 대체하지 않는다.

## 구현하지 않은 것

- Step 10 normalization
- Step 11 composite score
- Step 15 ranking / latest ranking
- Step 17 backtest
- valuation/fundamental scoring
- Part A score columns
- production scanner 연결
- real market score result export

## 검증

Part B focused tests:

```powershell
python -m pytest tests\test_step9_scores_part_b.py
```

검증 범위:

- deterministic toy formula
- ticker별 groupby contamination 방지
- date sorting 후 계산
- ticker leading-zero preservation
- insufficient history / warmup handling
- NaN-aware calculation
- no lookahead
- forbidden output column absence
- valuation/fundamental column absence
- Part A score columns 미요구
