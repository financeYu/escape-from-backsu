# v1.4 KIS Revision Source Feasibility

Status: `blocked_candidate_only`

This report reviews Korea Investment Securities KIS Developers Open API as a
candidate source for the v1.4 point-in-time revision layer. It creates no live
collector, no trading path, no production ranking input, and no feature
allowlist promotion.

## Source Feasibility Report

Primary sources checked on 2026-05-14:

- KIS Developers portal: <https://apiportal.koreainvestment.com/apiservice>
- KIS official GitHub Open Trading API repo:
  <https://github.com/koreainvestment/open-trading-api>
- KIS MCP domestic stock config:
  <https://github.com/koreainvestment/open-trading-api/blob/main/MCP/Kis%20Trading%20MCP/configs/domestic_stock.json>
- KIS generated endpoint examples:
  <https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/estimate_perform>
  <https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/invest_opinion>
  <https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/invest_opbysec>

The portal page is dynamic, so request paths, request fields, TR IDs, and
observed response-field mappings were cross-checked against the official KIS
GitHub samples generated for the same APIs. The initial metadata check did not
use credential values. A later collector smoke test on 2026-05-14 used local
credentials from `api_management` and wrote generated raw snapshot output only;
secret values were not printed or committed.

| Endpoint key | KIS API name | Path | TR ID | Feasibility |
| --- | --- | --- | --- | --- |
| `estimate_perform` | 국내주식 종목추정실적 | `/uapi/domestic-stock/v1/quotations/estimate-perform` | `HHKST668300C0` | usable for raw snapshots only; response semantics need live payload verification |
| `invest_opinion` | 국내주식 종목투자의견 | `/uapi/domestic-stock/v1/quotations/invest-opinion` | `FHKST663300C0` | usable for raw snapshots and possible opinion-history coverage |
| `invest_opbysec` | 국내주식 증권사별 투자의견 | `/uapi/domestic-stock/v1/quotations/invest-opbysec` | `FHKST663400C0` | usable for raw snapshots and possible per-member opinion-history coverage |

Credential source:

KIS credential values must be stored outside the repository under the project
collection key store, for example
`C:\Users\jjaew\Project\api_management\api_keys.env`. The local env loader
does not read `chart_mvp/.env` or `master_mvp/.env` for these API keys.

Required names:

- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_ACCESS_TOKEN`
- `KIS_ACCESS_TOKEN_EXPIRES_AT`
- `KIS_ENV_DV`
- `KIS_BASE_URL`

`KIS_APP_KEY` and `KIS_APP_SECRET` are user-managed secrets. `KIS_ACCESS_TOKEN`
and `KIS_ACCESS_TOKEN_EXPIRES_AT` are locally managed by the collector token
refresh process. `KIS_ENV_DV` defaults to `real`; `KIS_BASE_URL` is optional
and should normally stay empty unless a narrower integration check requires an
override.

Common request envelope:

| Field | Source | Storage rule |
| --- | --- | --- |
| `appkey` | `KIS_APP_KEY` loaded from `api_management` | never persist secret value |
| `appsecret` | `KIS_APP_SECRET` loaded from `api_management` | never persist secret value |
| `authorization` | `Bearer ${KIS_ACCESS_TOKEN}` loaded from `api_management` | never persist token value |
| `tr_id` | endpoint-specific TR ID | may persist as endpoint metadata |
| `tr_cont` | continuation flag | may persist as request metadata if paging is used |
| query params | endpoint-specific fields below | persist only non-secret request parameters |

## Collection Process Status

- Token handling: implemented as a local-only refresh step before KIS data
  calls. It reads `KIS_APP_KEY` and `KIS_APP_SECRET` from
  `C:\Users\jjaew\Project\api_management\api_keys.env`, reuses a valid
  `KIS_ACCESS_TOKEN`, refreshes `/oauth2/tokenP` when needed, and writes
  `KIS_ACCESS_TOKEN` plus `KIS_ACCESS_TOKEN_EXPIRES_AT` back to the same file.
- Raw snapshot output: implemented as append-only JSONL under ignored generated
  data path `data/kis_revision_raw_snapshots/`.
- Daily chart refresh integration: `app/run_daily.py --due-only` now requests
  append-only KIS revision raw snapshots during the same KOSPI200 daily refresh
  window and records the status in `outputs/last_run_meta.json`. It performs a
  token preflight before the chart refresh begins, using the existing local
  token refresh flow when the token is missing, expired, or near expiry. The
  KIS step is isolated from ranking/chart output; credential or network
  blockers do not promote features or alter scanner output. The collection
  should continue for history accumulation, but metadata keeps
  `usable_for_v1_4_feature_manifest = false` and
  `auto_reference_allowed = false` so downstream routes cannot consume raw
  snapshots without explicit PIT promotion.
- PIT stance: collector stores `collected_at` for each response and does not
  infer historical 1-month or 3-month consensus from a latest snapshot.
- OpenDART supplement: `docs/v1_4_opendart_supplement.md` adds raw
  `corpCode`, disclosure-search, and filing-based key-account snapshots for
  receipt-date lineage. This supplements `available_at`/`filing_date`
  evidence, but does not provide analyst consensus history or revision counts.
- KRX listing supplement: `docs/v1_4_krx_listing_supplement_feasibility.md`
  confirms that KRX/public-data listing sources can supplement
  `code`/ISIN/market/company mapping. Sector labels remain diagnostic-only
  unless a PIT-safe taxonomy lineage and PIT-safe revision distribution are
  available.
- Feature status: still `blocked_candidate_only`; no feature allowlist or
  runtime score/ranking path consumes these snapshots.

## Required Field Coverage Report

| Required v1.4 input | KIS coverage | PIT decision |
| --- | --- | --- |
| `available_at` | `stck_bsop_date` appears in the two opinion endpoints; `estimate_perform` has `estdate`/`dt` but semantics are not sufficiently clear from generated samples alone | use verified response base date only after live/doc confirmation; otherwise use `collected_at` |
| `estimate_as_of_date` | no explicit consensus as-of timestamp confirmed | blocked until historical raw snapshots exist |
| `eps_estimate_1m_ago` | no historical consensus snapshot can be reconstructed from a single latest response | blocked until at least 1-month snapshot history exists |
| `eps_estimate_3m_ago` | no historical consensus snapshot can be reconstructed from a single latest response | blocked until at least 3-month snapshot history exists |
| `analyst_revision_up_count_1m` | opinion endpoints expose current/previous opinion fields, but revision counts require historical row history and de-duplication rules | blocked until repeated snapshots or verified historical rows are available |
| `analyst_revision_down_count_1m` | same as above | blocked until repeated snapshots or verified historical rows are available |
| PIT taxonomy-lineage `sector_id` | not provided by these KIS endpoints | blocked; continue using separate KRX lineage supplement only if approved |
| `sector_revision_percentile` | requires sector lineage plus revision metrics | blocked until both sector lineage and revision history are PIT-safe |

Observed request/response coverage:

| Endpoint | Request fields confirmed | Response sections | Observed response fields from KIS generated check script |
| --- | --- | --- | --- |
| `estimate_perform` | `SHT_CD` | `output1`, `output2`, `output3`, `output4` | `sht_cd`, `item_kor_nm`, `estdate`, `capital`, `forn_item_lmtrt`, `data1` to `data5`, `dt` |
| `invest_opinion` | `FID_COND_MRKT_DIV_CODE`, `FID_COND_SCR_DIV_CODE`, `FID_INPUT_ISCD`, `FID_INPUT_DATE_1`, `FID_INPUT_DATE_2` | `output` | `stck_bsop_date`, `invt_opnn`, `invt_opnn_cls_code`, `rgbf_invt_opnn`, `rgbf_invt_opnn_cls_code`, `hts_goal_prc`, `stck_prdy_clpr`, `stck_nday_esdg`, `nday_dprt`, `stft_esdg`, `dprt` |
| `invest_opbysec` | `FID_COND_MRKT_DIV_CODE`, `FID_COND_SCR_DIV_CODE`, `FID_INPUT_ISCD`, `FID_DIV_CLS_CODE`, `FID_INPUT_DATE_1`, `FID_INPUT_DATE_2` | `output` | `stck_bsop_date`, `stck_shrn_iscd`, `hts_kor_isnm`, `invt_opnn`, `invt_opnn_cls_code`, `rgbf_invt_opnn`, `rgbf_invt_opnn_cls_code`, `stck_prpr`, `prdy_vrss`, `prdy_vrss_sign`, `prdy_ctrt`, `hts_goal_prc`, `stck_prdy_clpr`, `stft_esdg`, `dprt` |

## Feature Promotion Judgment

`v1.4 feature 승격 불가`.

Reason: the endpoints are usable as raw snapshot source candidates, but the
project still lacks PIT-safe historical consensus history, verified
`available_at` semantics for every endpoint, and taxonomy lineage needed for
sector-relative revision metrics. Latest snapshots must not be used to infer
1-month or 3-month prior consensus values.

## Next Collection Step

1. Ask the user to place KIS credentials in
   `C:\Users\jjaew\Project\api_management\api_keys.env`.
2. Run a small live probe for a few KOSPI200 codes and store raw snapshots with
   `collected_at`, `request_date`, `raw_json`, and `raw_hash`.
3. Compare raw payload dates against portal field definitions before accepting
   any response field as `available_at`.
4. Collect repeated snapshots for at least 3 months before computing revision
   deltas.
