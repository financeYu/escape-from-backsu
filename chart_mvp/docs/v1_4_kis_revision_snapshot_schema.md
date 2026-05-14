# v1.4 KIS Revision Snapshot Schema

Status: `blocked_candidate_only`

The implementation draft lives in
`src/stock_core/ml/kis_revision_snapshot_schema.py`. It is a schema and hash
helper only; it does not call KIS APIs and does not normalize values into a
usable feature table.

KIS credential presence checks use the shared local key store under
`C:\Users\jjaew\Project\api_management\api_keys.env`. Secret values are loaded
only into the process environment and are redacted from readiness summaries.

KIS calls now go through `ensure_kis_access_token()` in
`src/stock_core/ml/kis_revision_snapshot_collector.py`. The process reads
`KIS_APP_KEY` and `KIS_APP_SECRET` from the same key store, reuses
`KIS_ACCESS_TOKEN` when `KIS_ACCESS_TOKEN_EXPIRES_AT` is still valid, and
refreshes `/oauth2/tokenP` before KIS data calls when the token is missing,
expired, near expiry, or forced. Refreshed tokens are written back only to the
local key store; token and secret values are not printed by the collector.

## Raw Snapshot Schema

Required fields:

| Field | Type | Rule |
| --- | --- | --- |
| `provider` | string | fixed provider id, currently `kis_open_api` |
| `endpoint_name` | string | one of `estimate_perform`, `invest_opinion`, `invest_opbysec` |
| `code` | string | stock code requested by the collector |
| `collected_at` | datetime string | UTC collector timestamp |
| `request_date` | string | request date or request-date range key used by collector |
| `raw_json` | JSON object or array | unmodified KIS response body for the request |
| `raw_hash` | string | SHA-256 of canonical `raw_json` |
| `source_ref` | string | KIS portal or official KIS GitHub endpoint reference |

Raw snapshots are append-only evidence inputs. A changed raw payload must
produce a different `raw_hash`; a duplicated payload should be de-duplicated by
`provider`, `endpoint_name`, `code`, `request_date`, and `raw_hash` only after
raw preservation.

Default collector output is ignored generated data under:

```text
data/kis_revision_raw_snapshots/YYYYMMDD/kis_revision_raw_snapshots_YYYYMMDDTHHMMSSZ.jsonl
```

Example dry run:

```powershell
..\.venv\Scripts\python.exe scripts\collect_kis_revision_raw_snapshots.py --code 005930 --dry-run
```

Dry runs inspect whether a usable token is already present, but they do not
refresh the token, call KIS data endpoints, or write raw snapshots.

Example raw snapshot collection:

```powershell
..\.venv\Scripts\python.exe scripts\collect_kis_revision_raw_snapshots.py --code 005930 --max-pages 1
```

## Daily Chart Refresh Integration

The daily KOSPI200 chart refresh can request append-only KIS revision raw
snapshots during the same run:

```powershell
..\.venv\Scripts\python.exe app\run_daily.py --due-only
```

The integration is data-support only. Before the chart refresh starts, it calls
`ensure_kis_access_token()` so an expired or near-expired token can be refreshed
and persisted in the local key store. It then requests one snapshot page per
supported KIS revision endpoint for the current KOSPI200 universe codes, writes
raw JSONL under `data/kis_revision_raw_snapshots/`, and records the token
preflight plus collection status in `outputs/last_run_meta.json` under
`kis_revision_raw_snapshot`.

The KIS step remains enabled for accumulation, but the metadata must keep
`usable_for_v1_4_feature_manifest = false`,
`auto_reference_allowed = false`, and a downstream consumption policy that
blocks feature, score, ranking, valuation-input, or incremental-evidence use
until a later explicit PIT promotion review passes.

If KIS credentials, token refresh, or network access are unavailable, the daily
chart refresh still completes and the KIS section records `blocked` or
`failed`. Use `--no-kis-revision-snapshots` to run the daily chart refresh
without the KIS append-only snapshot step.

## Normalized Consensus Schema Draft

This draft is intentionally not allowlisted.

| Field | Type | PIT rule |
| --- | --- | --- |
| `provider` | string | copied from raw snapshot |
| `endpoint_name` | string | copied from raw snapshot |
| `code` | string | copied from raw snapshot or response code if verified |
| `collected_at` | datetime | copied from raw snapshot |
| `request_date` | string | copied from raw snapshot |
| `available_at` | datetime or null | verified response base/publication date only; otherwise `collected_at` |
| `source_date_field` | string or null | raw field used for `available_at`; never fiscal `period` |
| `fiscal_period` | string or null | target fiscal period only; not an availability date |
| `metric_name` | string or null | normalized candidate metric name after field semantics are verified |
| `metric_value` | number/string/null | raw-preserving candidate value |
| `broker_or_member_code` | string or null | member/broker code if available and legally usable |
| `opinion_code` | string or null | raw opinion class code if provided |
| `previous_opinion_code` | string or null | raw previous opinion class code if provided |
| `raw_hash` | string | raw snapshot lineage key |
| `source_ref` | string | KIS source reference |
| `feature_allowlist_state` | string | fixed `blocked_candidate_only` until PIT validation passes |
| `usable_for_v1_4_feature_manifest` | boolean | fixed `false` until explicit PIT promotion |
| `auto_reference_allowed` | boolean | fixed `false`; downstream must not consume raw snapshots implicitly |

## PIT Rules

- Use a response base/publication date for `available_at` only when the KIS
  field definition is clear.
- If response date semantics are unclear, use `collected_at`.
- Do not use fiscal `period`, settlement month, or target period as
  `available_at`.
- Do not reconstruct 1-month or 3-month prior values from a latest snapshot.
- Keep raw snapshots separate from feature tables until enough history exists.

## Blocked Until History Available Manifest

```json
{
  "status": "blocked_candidate_only",
  "blocked_reason": "PIT-safe historical consensus snapshots are not yet collected.",
  "usable_for_v1_4_feature_manifest": false,
  "auto_reference_allowed": false,
  "downstream_consumption_policy": "raw_snapshots_may_accumulate_but_must_not_feed_v1_4_features_scores_rankings_or_incremental_evidence_until_explicit_pit_promotion",
  "blocked_features": [
    "eps_estimate_1m_ago",
    "eps_estimate_3m_ago",
    "analyst_revision_up_count_1m",
    "analyst_revision_down_count_1m",
    "sector_revision_percentile"
  ],
  "unlock_requirements": [
    "daily_or_periodic_raw_snapshots_with_collected_at",
    "verified_available_at_mapping_per_endpoint",
    "stable_ticker_to_sector_taxonomy_lineage",
    "history_window_covering_at_least_3_months",
    "no_feature_allowlist_promotion_before_pit_validation"
  ]
}
```
