# Research Tester Output Contract

## Purpose

Define the output schema for future Step 9 Research Tester outputs without
generating production rankings. This contract is documentation-only readiness
work. It does not implement score formulas, compute raw scores, normalize score
series, create composites, export production score tables, or run backtests.

## Input Contract

Expected input from Step 6/7:

- `ticker`
- `date`
- validated OHLCV columns
- required technical indicator columns if Step 7 provides them
- `data_quality_flag`
- `warmup_state` if available

| input_field | requirement | notes |
|---|---|---|
| `ticker` | required | Six-character string with leading zeros preserved. |
| `date` | required | Parseable scoring date. |
| `open` | required | Validated numeric field from the Step 6 processed data interface. |
| `high` | required | Validated numeric field from the Step 6 processed data interface. |
| `low` | required | Validated numeric field from the Step 6 processed data interface. |
| `close` | required | Validated numeric field from the Step 6 processed data interface. |
| `volume` | required | Validated numeric field from the Step 6 processed data interface. |
| `data_quality_flag` | required | Should identify missing, invalid, stale, duplicate, or insufficient-history rows. |
| `warmup_state` | expected when available | Should distinguish ready, warmup, and insufficient indicator history. |
| technical indicator columns | conditional | Required only for predefined scores whose dependencies are available from Step 7. |

## Output Contract

Future Research Tester output may include:

- `ticker`
- `date`
- `score_name`
- `score_family`
- `raw_score`
- `normalized_score_time_series`
- `normalized_score_cross_sectional`
- `warmup_state`
- `coverage_status`
- `data_quality_flag`
- `implementation_status`
- `implementation_deviation_note`

| output_field | requirement | notes |
|---|---|---|
| `ticker` | required | Same identifier as input. |
| `date` | required | Same scoring date as input. |
| `score_name` | required | Must match a predefined score in `Quant_mvp/docs/score_definitions.md` or a versioned Score Architect update. |
| `score_family` | required | Must match the candidate registry and family map. |
| `raw_score` | conditional | Allowed only after the formula is locked and Step 9 implementation is explicitly opened. |
| `normalized_score_time_series` | conditional | Allowed only after Step 10 implementation is explicitly opened and implements the Step 8 time-series normalization protocol. |
| `normalized_score_cross_sectional` | conditional | Allowed only after Step 10 implementation is explicitly opened and implements the Step 8 cross-sectional normalization protocol. |
| `warmup_state` | required | Must identify ready, warmup, insufficient, or blocked warmup state. |
| `coverage_status` | required | Must identify adequate, partial, sparse, or blocked coverage status. |
| `data_quality_flag` | required | Must carry Step 6/8 data quality state into the score output. |
| `implementation_status` | required | Suggested values: `not_implemented`, `blocked_by_prerequisite`, `implemented_for_research`, `diagnostic_only`, `deferred`. |
| `implementation_deviation_note` | required | Empty only when implementation exactly matches the locked definition. Otherwise explain the difference and route it for review. |

Do not include:

- `final_composite_score`
- production rank
- latest ranking
- `valuation_composite_score` unless valuation branch is explicitly opened later

## Production Output Restrictions

- Do not export `reports/score_results.parquet` from real market data until Step
  9 is explicitly opened and prerequisites are complete.
- Do not create latest ranking files before Step 15.
- Do not create `technical_composite_score` or `final_composite_score` during
  Research Tester readiness.
- Do not run backtests before Step 17.
- Do not use financial or fundamental data in this output contract.

## Schema-Only Toy Test Guidance

Toy-data tests may validate only column presence, status-field naming, and
contract compatibility. They must not compute real score formulas, derive ranks,
create composites, read real market data, or export production reports.

Allowed toy checks:

- Required input columns are present.
- Required output columns are present in a hand-built empty or toy frame.
- `score_name` belongs to the predefined candidate registry.
- `implementation_status` uses an allowed readiness status.
- Forbidden output columns are absent.

Forbidden toy checks:

- Formula correctness for production score logic.
- Cross-sectional rank generation.
- Latest ranking output.
- Backtest metrics.
- Financial or fundamental data joins.
