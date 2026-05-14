# v1.4 OpenDART Supplement

Status: `blocked_candidate_only`

OpenDART is approved here only as a raw disclosure and financial-statement
lineage supplement for the v1.4 point-in-time work. It does not provide analyst
consensus snapshots, analyst estimate histories, broker revision counts, or
sector taxonomy lineage.

## Official Endpoints

Source references checked on 2026-05-14:

- Corporation code:
  <https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018>
- Disclosure search:
  <https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001>
- Single-company key accounts:
  <https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016>

Implemented endpoint keys:

| Endpoint key | Path | v1.4 coverage |
| --- | --- | --- |
| `corp_code` | `/api/corpCode.xml` | stock code to OpenDART `corp_code` lineage |
| `disclosure_list` | `/api/list.json` | `rcept_no`, `rcept_dt`, report name, filing receipt lineage |
| `single_account` | `/api/fnlttSinglAcnt.json` | filing-based financial account raw values keyed by `rcept_no` |

## Credential Rule

`OPENDART_API_KEY` is loaded from:

```text
C:\Users\jjaew\Project\api_management\api_keys.env
```

The collector prints only readiness status and never prints the API key value.

## Raw Snapshot Output

Default output is ignored generated data:

```text
data/opendart_v1_4_raw_snapshots/YYYYMMDD/opendart_v1_4_raw_snapshots_YYYYMMDDTHHMMSSZ.jsonl
```

Each JSONL record uses the shared raw snapshot fields:

- `provider`
- `endpoint_name`
- `code`
- `collected_at`
- `request_date`
- `raw_json`
- `raw_hash`
- `source_ref`

Example dry run:

```powershell
..\.venv\Scripts\python.exe scripts\collect_opendart_v1_4_raw_snapshots.py --code 005930 --dry-run
```

Example raw snapshot collection:

```powershell
..\.venv\Scripts\python.exe scripts\collect_opendart_v1_4_raw_snapshots.py --code 005930 --max-pages 1
```

## PIT Contribution

OpenDART can supplement these fields:

| Needed field | OpenDART contribution | PIT rule |
| --- | --- | --- |
| `available_at` | `disclosure_list.rcept_dt` after report matching | usable as filing receipt date, not fiscal period |
| `availability_date` | same as `rcept_dt` when the report row is verified | use as raw lineage candidate |
| `disclosure_date` | `rcept_dt` | raw disclosure receipt date candidate |
| `filing_date` | `rcept_dt` | raw filing receipt date candidate |
| `source_ref` | official endpoint guide URL and `rcept_no` in raw payload | preserve as lineage |

OpenDART cannot fill these v1.4 revision fields:

- `estimate_as_of_date`
- `eps_estimate_1m_ago`
- `eps_estimate_3m_ago`
- `analyst_revision_up_count_1m`
- `analyst_revision_down_count_1m`
- PIT taxonomy-lineage `sector_id`
- `sector_revision_percentile`

Those remain blocked until a PIT-safe analyst estimate/revision source and a
separate sector taxonomy lineage source are available.

## Feature Promotion Judgment

`v1.4 feature promotion: blocked`.

The OpenDART supplement improves filing-date lineage for financial statement
raw records. It does not by itself unlock revision features, consensus history,
or sector-relative revision percentiles.
