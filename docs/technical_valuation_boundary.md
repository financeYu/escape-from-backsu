# Technical / Valuation Boundary

## Purpose

This document fixes the boundary between technical analysis and valuation analysis for the KOSPI200 quant project.

Step 4 is a boundary and policy step. It does not implement scores, composite scores, rankings, backtests, or valuation review.

## Current Status

- technical scanner: active project direction
- valuation_status: deferred
- financial_data_usage_now: inventory_only_or_gui_display_only
- point_in_time_status: unverified unless disclosure or availability date exists
- financial_data_in_technical_score: false
- financial_data_in_final_composite_score: false

## Technical Evidence

Technical evidence may use daily OHLCV-derived inputs such as:

- open, high, low, close, volume
- rolling returns
- rolling volatility
- moving averages
- drawdown and distance-from-high measures
- volume-derived statistics
- price/volume diagnostics

Technical evidence can support technical or diagnostic claims only.

Allowed language:

- momentum
- trend
- volatility
- mean reversion
- overbought or oversold technical condition
- liquidity or volume condition
- data quality diagnostic

## Valuation Evidence

Valuation evidence requires point-in-time-safe fundamental data.

Required before valuation scoring:

- fundamental field definition
- effective date or filing date
- disclosure or availability date
- reporting lag policy
- stale data policy
- market capitalization or share-count logic when needed
- sector or industry metadata when sector-relative valuation is proposed

Without these, valuation_status remains `deferred` or `unavailable`.

## Hard Boundary Rules

- Price-only evidence is not valuation evidence.
- Drawdown depth is not valuation.
- Low RSI is not valuation.
- Oversold technical state is not cheapness.
- Low absolute price is not valuation.
- Recent underperformance is not value.
- Price distance from moving average is not valuation.
- Financial data must not enter `technical_composite_score`.
- Financial data must not enter `final_composite_score`.
- Financial data must not affect technical ranking while valuation is deferred.

## Current Financial Data Use

Financial data may be used only for:

- inventory documentation
- schema inspection
- GUI display if already present
- future valuation planning notes

Financial data must not be used for:

- technical score implementation
- composite score implementation
- ranking generation
- alpha claims
- valuation verdicts without point-in-time safety

## Handoff Rule

If a user requests valuation-aware work, route it to:

```text
Quant_mvp/agents/valuation/AGENTS.md
```

The main technical workflow may record that valuation is unavailable, deferred, or blocked by data, but it must not fabricate a valuation opinion.
