# Data Schema

Status: Project Step 2 schema baseline.

## Standard Price Schema

Required columns:

| column | type | description |
| --- | --- | --- |
| `ticker` | string | Six-character Korean market ticker. Digits and uppercase letters are allowed because preferred-share codes may contain letters. |
| `date` | date | Trading date, parseable by `pandas.to_datetime`. |
| `open` | numeric | Daily open price. |
| `high` | numeric | Daily high price. |
| `low` | numeric | Daily low price. |
| `close` | numeric | Daily close price. |
| `volume` | numeric | Daily trading volume. |
| `source` | string | Source path or collection mode such as `cache` or `fetched`. |

Optional columns:

| column | type | description |
| --- | --- | --- |
| `name` | string | Security name when available. |
| `market` | string | Market segment when available. |
| `data_vendor` | string | Vendor identifier, currently `naver_finance` for Naver Finance data. |
| `collected_at` | datetime | Collector runtime timestamp when available. |

## Current Naver Price Cache Mapping

The current Naver price loader stores Korean column names in `data/<code>_daily_prices.csv`.

| current column | standard column |
| --- | --- |
| `날짜` | `date` |
| `시가` | `open` |
| `고가` | `high` |
| `저가` | `low` |
| `종가` | `close` |
| `거래량` | `volume` |
| file name prefix | `ticker` |
| validation input source | `source` |

The cache may also contain indicator columns such as `MA5`, `MA20`, `BB_MID`, `BB_UPPER`, `BB_LOWER`, `RSI14`, `RSI_SIGNAL`, and `VOLUME_MA20`. These are downstream technical columns and are not required for raw collector validation.

## Financial Statement Collector Schema

Current extracted financial statement rows use:

| column | description |
| --- | --- |
| `code` | Ticker passed to the collector. |
| `table_index` | HTML table index from the Naver main page extraction pass. |
| `metric` | Row label extracted from the statement-like table. |
| `period` | Fiscal period label from the source table. |
| `value` | Raw extracted cell text. |

Point-in-time status policy:

- If `disclosure_date`, `availability_date`, `available_at`, `collected_at`, or `filing_date` is present, `point_in_time_status` may be marked `verified`.
- If none of those columns is present, `point_in_time_status = unverified`.
- Financial statement data must not be merged into any technical score during Project Step 2.

