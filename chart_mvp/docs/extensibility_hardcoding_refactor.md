# Extensibility Hardcoding Refactor

Status: post-Step20 chart runtime support.

This refactor keeps the current KOSPI200 + Naver Finance behavior as the
default and moves expansion-sensitive assumptions into explicit policy objects.

## Runtime Specs

- `SymbolPolicy`: ticker normalization and validation.
- `UniverseSpec`: universe id, display name, CSV filenames, expected size, and
  live refresh availability.
- `PriceProviderSpec`: provider id, display name, data vendor, rows per page,
  and request pacing.
- `PriceCachePolicy`: legacy-compatible cache layout or provider/universe
  namespaced cache layout.
- `TradingCalendarPolicy`: weekday set and explicit holiday dates.

## Preserved Defaults

- Default universe: `KOSPI200_UNIVERSE_SPEC`
- Default price provider: `NAVER_PRICE_PROVIDER_SPEC`
- Default symbol policy: six-character Korean equity identifiers
- Default cache path: `data/<code>_daily_prices.csv`
- Default financial cache path: `data/<code>_financial_statements.csv`
- Default calendar behavior: weekday-only

## Future Extension Path

Future KOSDAQ, NASDAQ, futures, or options support should add new specs first
and then pass them into the existing runtime seams. Adding the spec is not the
same as activating a new live data source or multi-universe ranking.

Expected order:

1. Define a symbol policy for the instrument identifier format.
2. Define a universe spec with explicit expected-size behavior.
3. Define a provider spec and cache policy.
4. Add deterministic fixture tests for schema, cache paths, and universe load.
5. Only then wire an approved provider into the runtime.

This branch does not add new market data ingestion, multi-universe ranking,
valuation/fundamental scoring, trading recommendations, or score changes.
