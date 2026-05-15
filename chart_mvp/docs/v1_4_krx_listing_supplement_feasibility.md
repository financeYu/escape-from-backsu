# v1.4 KRX Listing Supplement Feasibility

Status: `blocked_candidate_only`

This note checks whether KRX or the public data portal
`금융위원회_KRX상장종목정보` can supplement v1.4 point-in-time revision inputs.
The answer is partial: listing identity fields can be supplemented, but analyst
revision history and sector-relative revision percentiles remain blocked.

## Sources Checked

- KRX Data Marketplace OPEN API service list:
  <https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd>
- KRX Data Marketplace stock basic-info services:
  - `유가증권 종목기본정보`
  - `코스닥 종목기본정보`
  - `코넥스 종목기본정보`
- Public data portal `금융위원회_KRX상장종목정보`:
  <https://www.data.go.kr/data/15094775/openapi.do>

## Local Key Readiness

The project key store contains:

- `KRX_API_KEY`: present
- `KRX_ID`: present
- `KRX_PASSWORD`: present
- `DATA_GO_KR_API_KEY`: present

Secret values were not printed. After public data portal service approval, a
live code-scoped sample request to
`https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo`
returned normal data on 2026-05-15.

## Field Coverage

Public data portal `금융위원회_KRX상장종목정보` explicitly describes these useful
fields:

| v1.4 support need | Coverage | Judgment |
| --- | --- | --- |
| `code` | `단축코드` | usable as listed instrument identity lineage |
| `ISIN` | `ISIN코드` | usable as stable instrument identifier candidate |
| `market` | `시장구분` | usable for market taxonomy such as KOSPI/KOSDAQ/KONEX |
| company mapping | `종목명`, `법인등록번호`, `법인명` | usable for company/instrument mapping |
| data as-of | `기준일자`; public page also says daily update / non-realtime timing | usable as source date lineage, not analyst availability |
| sector taxonomy | not explicitly listed on the public data portal KRX listed-info page | not enough to promote `sector_id` |

KRX Data Marketplace service list confirms separate stock basic-info services
for KOSPI, KOSDAQ, and KONEX and says data is available from 2010 or 2013
depending on the market. The static service page does not expose enough output
field detail to verify an official sector taxonomy field from that page alone.

## Existing Local KRX Sector Path

The project already has a diagnostic-only KRX sector supplement:

- `src/stock_core/ml/revision_sector_supplement.py`
- `scripts/build_v1_4_krx_sector_supplement.py`

That path uses `pykrx.get_market_sector_classifications(source_date, market)`
to collect sector classifications. It can produce:

- `diagnostic_sector_id`
- `diagnostic_sector_name`
- `sector_source_date`
- `sector_source_ref`

But it intentionally keeps:

- `pit_revision_usable=false`
- `sector_revision_percentile_usable=false`

Reason: a sector label alone is not a point-in-time analyst revision source, and
`sector_revision_percentile` still needs a PIT-safe distribution of revision
metrics inside each sector.

## What KRX Can Supplement Now

KRX / public data portal can supplement:

- listed stock `code` lineage
- ISIN lineage
- market membership / market category
- company name and legal registration mapping
- source date or base date lineage
- diagnostic sector labels only if using the separate KRX sector
  classification path

These are useful for joining KIS/OpenDART/raw financial data safely and for
reducing ticker/ISIN/company-name ambiguity.

## Daily Refresh Integration

`scripts/collect_krx_listed_info_raw_snapshots.py` and
`src/stock_core/ml/krx_listed_info_snapshot.py` collect append-only raw JSONL
snapshots under:

```text
data/krx_listed_info_raw_snapshots/YYYYMMDD/krx_listed_info_raw_snapshots_YYYYMMDDTHHMMSSZ.jsonl
```

The default mode is a supplement, not a full listed-history crawl. The
collector loads the existing local KOSPI200 universe codes and requests the
latest listed-info row for each code with `likeSrtnCd` and `numOfRows=1`. This
keeps KRX usage bounded to the names already present in chart_mvp. Full paged
listed-history collection remains available only through the explicit
`--all-history` option.

The daily chart refresh requests these code-scoped KRX listed-info raw
snapshots alongside the KIS v1.4 raw snapshots. The KRX step is fail-closed:

- success writes `krx_listed_info_raw_snapshot.status=collected` in
  `outputs/last_run_meta.json`;
- API key or gateway problems write `blocked` or `failed`;
- scanner rankings, scores, charts, KIS snapshots, and OpenDART snapshots are
  not promoted or changed by this status.

Use this opt-out flag when needed:

```powershell
app\run_daily.py --no-krx-listed-info-snapshots
```

## What Remains Blocked

The following remain blocked:

- `estimate_as_of_date`
- `eps_estimate_1m_ago`
- `eps_estimate_3m_ago`
- `analyst_revision_up_count_1m`
- `analyst_revision_down_count_1m`
- production-grade PIT taxonomy-lineage `sector_id`
- `sector_revision_percentile`

`sector_revision_percentile` especially remains blocked even if a sector label
is available, because it requires both:

1. PIT-safe sector taxonomy lineage with source date/version.
2. PIT-safe analyst revision metrics for all comparable names in the sector.

## Next Step

Run a small local-universe supplement probe after key or portal changes:

```powershell
..\.venv\Scripts\python.exe scripts\collect_krx_listed_info_raw_snapshots.py --limit 5
```

Keep the existing KRX sector
supplement only as diagnostic metadata, not as a v1.4 feature unlock.
