# chart_mvp Benchmark Data Handoff Request

## Purpose

Request `chart_mvp` to own the forward data-attachment process needed for
benchmark construction in `Quant_mvp`.

This handoff does not request new score formulas, ranking semantics,
valuation scoring, backtest feedback, or trading recommendations. It only
requests a repeatable data-export path from `chart_mvp` runtime/cache data into
Quant-readable benchmark inputs.

## Current Quant Gap

`Quant_mvp/config/data.toml` expects these benchmark inputs, but the current
Quant workspace does not contain them:

- `data/ohlcv`
- `data/universe_membership/membership.parquet`
- `data/reference/tickers.parquet`
- benchmark-ready coverage and data-quality summaries

`chart_mvp` already owns the local KOSPI200 runtime data-fetching pipeline,
CSV cache behavior, universe snapshot, Naver Finance price provider, chart
rendering, and runtime outputs. Future benchmark input generation should
therefore be routed through `chart_mvp` rather than implemented inside Quant.

## Requested chart_mvp Process

Create a chart-owned export process that can produce Quant benchmark input
artifacts from chart runtime/cache data.

Minimum process stages:

1. Load the active KOSPI200 universe from the chart-owned universe provider.
2. For each ticker, load or refresh daily price data through the existing
   chart-owned provider/cache path.
3. Normalize price data to a Quant-compatible OHLCV schema.
4. Validate price data before export.
5. Export benchmark-ready files to a chart-owned generated-output directory.
6. Emit a manifest describing source, date range, row counts, validation
   status, and known limitations.
7. Keep generated runtime outputs out of source control unless promoted as
   small fixtures through explicit review.

## Minimum Quant-Compatible Price Schema

Required columns:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `source`

Preferred optional columns when safely available:

- `name`
- `market`
- `data_vendor`
- `collected_at`
- `adj_open`
- `adj_high`
- `adj_low`
- `adj_close`
- `adj_volume`

If adjusted prices are unavailable, the manifest must explicitly state
`adjusted_price_status = unavailable`.

## Universe and Metadata Requirements

Export or document:

- active universe id, expected default `kospi200`
- universe snapshot source path
- ticker code normalization policy
- ticker display name
- market or exchange segment when available
- point-in-time membership status

If historical point-in-time membership is unavailable, the manifest must state:

- `point_in_time_membership = false`
- `survivorship_bias_risk = present`

## Validation Requirements

Before export, chart should run or reuse checks for:

- required column presence
- ticker string format and leading-zero preservation
- duplicate `ticker` + `date`
- parseable and sorted dates
- non-positive OHLC prices
- negative volume
- high/low/open/close consistency
- suspicious return jumps
- latest date coverage lag
- minimum history length
- warmup eligibility
- zero-volume or flat-price flags

The export should include a compact data-quality summary with:

- ticker count
- date range
- rows by ticker
- missing rows or failed tickers
- validation warning counts
- benchmark readiness verdict

## Quant Consumption Target

Quant should be able to consume chart exports as benchmark inputs equivalent to:

- `data/ohlcv`
- `data/universe_membership/membership.parquet`
- `data/reference/tickers.parquet`

The exact physical location can remain chart-owned, but it must be documented
and stable enough for Quant to reference through config or a handoff manifest.

## Explicit Non-Goals

Do not include:

- new score adoption
- score formula changes
- ranking generation changes
- composite score activation
- backtest result feedback into scoring
- valuation or fundamental scoring
- financial data merge into `technical_composite_score`
- financial data merge into `final_composite_score`
- trading recommendation language
- KOSDAQ, overseas, futures, options, or multi-universe activation

Financial statement cache data may remain inventory-only unless a separate
root/master-approved valuation workflow verifies point-in-time availability.

## Suggested chart_mvp Owned Files

Suggested implementation area, subject to chart local review:

- `chart_mvp/src/stock_core/providers/`
- `chart_mvp/src/stock_core/cache/`
- `chart_mvp/src/preprocess/`
- `chart_mvp/scripts/`
- `chart_mvp/docs/`
- `chart_mvp/tests/`

Do not modify Quant score definitions, Quant ranking contracts, root roadmap
status, or root policy from chart work.

## Acceptance Criteria

The chart-side process is ready for Quant benchmark use when:

- a deterministic offline test covers the export schema
- the output manifest records source, date range, ticker count, and validation
  verdict
- generated exports are excluded from source control by default
- adjusted-price and point-in-time-membership limitations are explicit
- Quant can map the chart export to its configured data inputs without copying
  runtime cache internals blindly

## Requested Owner

- Primary owner: `chart_mvp`
- Consumer: `Quant_mvp`
- Review route: chart local review first, then master-up if the change touches
  generated-output boundaries, data schema, cache semantics, or cross-project
  handoff behavior
