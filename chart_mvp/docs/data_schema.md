# Data Schema

Status: Project Step 2 schema baseline.

## Standard Price Schema

Required columns:

| column | type | description |
| --- | --- | --- |
| `ticker` | string | Instrument identifier validated by the active `SymbolPolicy`. The default KOSPI200 policy keeps the existing six-character Korean equity ticker rule. |
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
| `data_vendor` | string | Vendor identifier from the active `PriceProviderSpec`; the default provider remains `naver_finance`. |
| `collected_at` | datetime | Collector runtime timestamp when available. |

## Current Naver Price Cache Mapping

The default Naver price loader stores Korean column names in the legacy-compatible cache path `data/<code>_daily_prices.csv`. Non-legacy cache policies may namespace files by provider and universe.

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

- If `disclosure_date`, `availability_date`, `available_at`, or `filing_date` is present and populated with parseable dates for the relevant rows, `point_in_time_status` may be marked `verified`.
- `collected_at` records only the local observation or collection time. It does not prove historical financial-statement availability and must not verify point-in-time safety by itself.
- If none of those columns is present, `point_in_time_status = unverified`.
- Financial statement data must not be merged into any technical score during Project Step 2.

## v1.4 Revision Diagnostic Handoff

`scripts/build_v1_4_revision_diagnostic_handoff.py` can repackage existing
financial statement cache rows into a diagnostic-only handoff for the root v1.4
revision layer. This is a data availability artifact, not a point-in-time
revision source.

Default output path:

| artifact | path |
| --- | --- |
| diagnostic handoff CSV | `data/v1_4_revision/v1_4_candidate_revision_diagnostic_handoff_latest.csv` |
| diagnostic manifest JSON | `data/v1_4_revision/v1_4_candidate_revision_diagnostic_manifest_latest.json` |
| KRX sector supplement CSV | `data/v1_4_revision/v1_4_krx_sector_supplement_latest.csv` |
| KRX sector supplement manifest JSON | `data/v1_4_revision/v1_4_krx_sector_supplement_manifest_latest.json` |

The handoff can populate `candidate_id`, `evidence_id`, `source_ticker`,
`company_name`, `revision_source_ref`, `fiscal_period`,
`eps_estimate_current`, `selection_reference_date`, and `selection_reason` when
an EPS estimate row exists in the local cache. EPS estimate row selection uses
the candidate handoff row `as_of_date` first, then `market_cap_as_of_date`.
Estimate fiscal periods containing that reference date are preferred, narrower
matching periods are preferred over broader ones, and otherwise the closest
available estimate period is selected.

The handoff intentionally leaves `available_at`, `estimate_as_of_date`,
`eps_estimate_1m_ago`, `eps_estimate_3m_ago`,
`analyst_revision_up_count_1m`, `analyst_revision_down_count_1m`, `sector_id`,
and `sector_revision_percentile` blank because those fields are not present in
the current chart financial cache. The manifest records this as
`pit_revision_ready = false`.

`scripts/build_v1_4_krx_sector_supplement.py` can collect KRX sector
classifications through `pykrx.get_market_sector_classifications` and join them
to the v1.3 candidate liquidity handoff by ticker. This may populate
`diagnostic_sector_id` and `diagnostic_sector_name` in a separate diagnostic
supplement.

The KRX sector supplement is not a point-in-time analyst revision source. It
does not provide `available_at`, `estimate_as_of_date`, historical 1-month or
3-month EPS consensus snapshots, analyst up/down revision counts, or
`sector_revision_percentile`. Its manifest therefore keeps
`pit_revision_ready = false` and `usable_for_v1_4_feature_manifest = false`.

## v1.4 KIS Revision Raw Snapshots

`scripts/collect_kis_revision_raw_snapshots.py` stores append-only KIS revision
raw payloads under `data/kis_revision_raw_snapshots/`. The daily KOSPI200 chart
refresh first runs a KIS token preflight, invokes the same collector by default,
and records token plus collection status in `outputs/last_run_meta.json` under
`kis_revision_raw_snapshot`.

These raw snapshots are data-support artifacts only. They do not update ranking
outputs, do not enter a feature allowlist, and cannot fill 1-month or 3-month
revision fields until enough PIT-safe history is collected and validated.
Daily metadata must keep `usable_for_v1_4_feature_manifest = false` and
`auto_reference_allowed = false` while this collection is in the accumulation
phase.
