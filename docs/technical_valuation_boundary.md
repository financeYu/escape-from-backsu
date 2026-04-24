# 기술 분석 / 밸류에이션 경계

## 목적

이 문서는 KOSPI200 퀀트 프로젝트에서 technical analysis와 valuation analysis의 경계를 고정한다.

Step 4는 경계와 정책을 정하는 단계다. 이 문서는 score, composite score, ranking, backtest, valuation review를 구현하지 않는다.

## 현재 상태

- technical scanner: active project direction
- valuation_status: deferred
- financial_data_usage_now: inventory_only_or_gui_display_only
- point_in_time_status: disclosure 또는 availability date가 없으면 unverified
- financial_data_in_technical_score: false
- financial_data_in_final_composite_score: false

## Technical Evidence

Technical evidence는 일봉 OHLCV에서 파생된 입력만 사용할 수 있다.

예시:

- open, high, low, close, volume
- rolling returns
- rolling volatility
- moving averages
- drawdown and distance-from-high measures
- volume-derived statistics
- price/volume diagnostics

Technical evidence는 technical claim 또는 diagnostic claim만 뒷받침한다.

허용되는 표현:

- momentum
- trend
- volatility
- mean reversion
- overbought 또는 oversold technical condition
- liquidity 또는 volume condition
- data quality diagnostic

## Valuation Evidence

Valuation evidence는 point-in-time-safe fundamental data가 있어야만 사용할 수 있다.

valuation scoring 전에 필요한 것:

- fundamental field definition
- effective date 또는 filing date
- disclosure 또는 availability date
- reporting lag policy
- stale data policy
- 필요한 경우 market capitalization 또는 share-count logic
- sector-relative valuation을 제안하는 경우 sector 또는 industry metadata

위 조건이 없으면 valuation_status는 `deferred` 또는 `unavailable`이다.

## Hard Boundary Rules

- Price-only evidence는 valuation evidence가 아니다.
- Drawdown depth는 valuation이 아니다.
- Low RSI는 valuation이 아니다.
- Oversold technical state는 cheapness가 아니다.
- Low absolute price는 valuation이 아니다.
- Recent underperformance는 value가 아니다.
- Price distance from moving average는 valuation이 아니다.
- Financial data는 `technical_composite_score`에 들어가지 않는다.
- Financial data는 `final_composite_score`에 들어가지 않는다.
- Valuation이 deferred인 동안 financial data는 technical ranking에 영향을 주면 안 된다.

## 현재 Financial Data 사용 범위

Financial data는 아래 범위에서만 허용된다.

- inventory documentation
- schema inspection
- 이미 존재하는 경우 GUI display
- future valuation planning notes

Financial data는 아래 용도로 사용할 수 없다.

- technical score implementation
- composite score implementation
- ranking generation
- alpha claims
- point-in-time safety 없는 valuation verdict

## Handoff Rule

사용자가 valuation-aware work를 요청하면 아래 문서로 라우팅한다.

```text
Quant_mvp/agents/valuation/AGENTS.md
```

메인 technical workflow는 valuation이 unavailable, deferred, blocked by data라고 기록할 수 있다. 하지만 valuation opinion을 만들어내면 안 된다.
