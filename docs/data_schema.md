# Data Schema

## Status

Step 3 standard schema cleanup.

This document defines the canonical OHLCV schema target. Existing runtime files may still use aliases and legacy provider locations.

## Standard OHLCV Schema

Required columns:

| column | expected type | requirement |
| --- | --- | --- |
| `ticker` | string | Six characters, leading zeros preserved |
| `date` | date-like | Parseable by `pandas.to_datetime(..., errors="coerce")` |
| `open` | numeric-like | Numeric-convertible without silent loss |
| `high` | numeric-like | Numeric-convertible without silent loss |
| `low` | numeric-like | Numeric-convertible without silent loss |
| `close` | numeric-like | Numeric-convertible without silent loss |
| `volume` | numeric-like | Numeric-convertible without silent loss |

Optional runtime metadata columns:

- `source`
- `name`
- `market`
- `data_vendor`
- `collected_at`

## Ticker Policy

Ticker values must be handled as strings.

Rules:

- six characters required
- leading zeros must be preserved
- integer ticker loading is invalid because it can turn `005930` into `5930`
- alphanumeric six-character tickers are allowed for preferred-share style codes

## Date Policy

Dates must be parseable.

Preferred format:

```text
YYYY-MM-DD
```

Datetime-normalizable values are acceptable for validation, but invalid parse results must be reported.

## Numeric Policy

Columns `open`, `high`, `low`, `close`, and `volume` must be numeric-convertible.

Validation may use:

```python
pd.to_numeric(values, errors="coerce")
```

Failures must be counted and reported. They must not be silently coerced away.

## Duplicate Key Policy

The canonical row key is:

```text
ticker + date
```

Duplicate `ticker`/`date` rows are invalid or must be explicitly reported before downstream use.

## Step 6 Preprocessed Output

Step 6 writes clean daily OHLCV data to the config-defined path:

```text
config/data.toml -> [preprocess].processed_price_output_path
```

The preprocessed output preserves only the canonical OHLCV columns:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

Rows with invalid ticker, invalid date, future date, unsafe numeric value, negative volume, missing required value, or duplicate `ticker`/`date` key are rejected from the processed output and reported separately.

## Current Alias Mapping

Current Naver cache columns may be normalized as:

| current column | standard column |
| --- | --- |
| `종목코드`, `code` | `ticker` |
| `날짜`, `일자` | `date` |
| `시가` | `open` |
| `고가` | `high` |
| `저가` | `low` |
| `종가` | `close` |
| `거래량` | `volume` |
| `data_source` | `source` |

## Financial Data Boundary

Financial data status remains:

```text
valuation_deferred
inventory_only
```

Financial data must not be used in technical scoring or final composite scoring.
