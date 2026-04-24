# Step 7 Technical Indicator Layer

## 목적

Step 7은 Step 6의 canonical daily OHLCV를 입력으로 받아 raw technical indicator dependency를 계산한다.

이 레이어는 score 구현이 아니다. ranking, composite, adoption decision, backtest, valuation/fundamental scoring도 수행하지 않는다.

## 입력

기본 입력 경로는 `config/data.toml`의 아래 키를 따른다.

```toml
[indicators]
input_price_path = "data/processed/daily_ohlcv.csv"
```

입력은 Step 6 canonical schema를 사용한다.

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

## 출력

기본 출력 경로는 다음과 같다.

```toml
[indicators]
output_path = "data/processed/technical_indicators.csv"
summary_report_path = "reports/indicators/indicator_summary.md"
validation_report_path = "reports/indicators/indicator_validation_summary.csv"
```

출력은 원본 OHLCV 컬럼, Step 7 상태 메타데이터, raw indicator 컬럼만 포함한다.

상태 메타데이터:

- `history_count`: ticker별 현재 row까지 확보된 일봉 개수
- `minimum_history_required`: 현재 window config 기준 최소 필요 history
- `warmup_state`: `warmup`, `insufficient_history`, `ready`

금지되는 출력:

- production score
- normalized score
- rank
- latest ranking
- technical composite
- final composite
- backtest result
- valuation/fundamental score

## 계산되는 indicator dependency

창 설정은 `config/windows.toml`에서 읽는다.

- trailing returns: `return_1d`, `return_{window}d`
- volatility: `true_range`, `atr_{window}`, `realized_vol_{window}`, `vol_of_vol_{window}`
- oscillator / bands: `rsi_{window}`, `stochastic_k_{window}`, `cci_{window}`, `williams_r_{window}`, Bollinger mid/std/upper/lower/width
- breakout dependency: `donchian_high_prior_{window}`, `donchian_low_prior_{window}`
- flow: `cmf_{window}`, `obv`, `obv_slope_{window}`, `adl`, `adl_slope_{window}`
- MACD dependency: EMA, MACD line, trigger line, histogram
- statistics: return autocorrelation, absolute-return autocorrelation, volume-return correlation, efficiency ratio, noise ratio

Donchian high/low는 same-date high/low를 쓰지 않도록 prior-bar convention을 사용한다.

## Warmup 정책

rolling indicator는 full window가 확보되기 전까지 NaN을 유지한다. Step 8 normalization protocol 전에는 NaN을 neutral 값으로 채우지 않는다.

`warmup_state`는 ticker 전체 history가 최소 필요 history보다 짧으면 `insufficient_history`, ticker history는 충분하지만 현재 row의 누적 history가 부족하면 `warmup`, 그 외에는 `ready`로 표시한다.

Step 7 입력에 as-of date 이후의 future date가 포함되면 계산을 중단한다.

## 실행 예시

```powershell
python -m src.indicators.technical --project-root .
```

## 하드 스톱

- score implementation: 수행하지 않음
- ranking generation: 수행하지 않음
- composite generation: 수행하지 않음
- backtest: 수행하지 않음
- valuation/fundamental scoring: 수행하지 않음
- price-only technical indicator를 valuation evidence로 표현하지 않음

## 다음 단계

Step 8 normalization/testing protocol은 `docs/step8_testing_normalization_protocol.md`에 별도로 정의되어 있다. Step 9 Research Tester는 명시적으로 시작되기 전까지 normalized score output이나 production score file을 만들 수 없다.
