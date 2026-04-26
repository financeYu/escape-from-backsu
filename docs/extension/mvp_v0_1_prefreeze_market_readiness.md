# MVP v0.1 Pre-Freeze Market Readiness

Status: Step 20 closure and MVP v0.1 freeze preparation only. This document does
not authorize Step 21 entry, new market data ingestion, KOSDAQ/NASDAQ universe
activation, futures/options logic, cross-universe comparison outputs, score
changes, valuation activation, or backtest feedback.

## Confirmed Baseline

- Step 20 remains the terminal MVP v0.1 roadmap Step.
- MVP v0.1 remains KOSPI200-only and technical-only.
- `technical_composite_score` and `final_composite_score` semantics are unchanged.
- Future KOSDAQ, futures/options, and NASDAQ/overseas work still requires a
  separately approved post-freeze Step.

## Readiness Fixes Allowed In This Lane

- Make KOSPI200, Naver Finance, Korean six-character ticker, and equity-only
  assumptions explicit policy defaults.
- Add policy injection points for future symbol validation, universe metadata,
  provider/cache namespace, and ranking-output validation.
- Add deterministic tests using synthetic symbols such as `AAPL` or synthetic
  option contract metadata.
- Preserve all existing MVP guardrails and default behavior.

## Still Blocked

- Live KOSDAQ, futures, options, NASDAQ, or overseas data providers.
- New ticker lists, contract chains, option surfaces, futures roll logic, or
  derivative pricing.
- Ranking across multiple universes or cross-market score comparison.
- Score formula, normalization, adoption, composite, ranking, report, backtest,
  or valuation semantic changes.
- Financial/fundamental data in technical or final composite scores.

## Required Next Contracts Before Activation

1. `MarketSpec`: market ID, timezone, currency, trading calendar, provider set.
2. `InstrumentSpec`: `instrument_id`, `symbol`, `asset_class`, `market`,
   `name`, and asset-class-specific metadata.
3. `ProviderSpec`: canonical schema emitted by the provider and cache namespace.
4. `UniverseSpec`: membership source, expected size rule, symbol policy,
   metadata columns, and point-in-time membership policy.
5. `RankingScope`: whether the output is single-universe, cross-universe, or
   asset-class-specific. MVP ranking remains single KOSPI200 only.

## Handoff Rule

If a future task needs activation rather than readiness, stop and request
root/master approval with the target market, asset class, data provider,
contract files, validation plan, and expected generated-output boundary.
