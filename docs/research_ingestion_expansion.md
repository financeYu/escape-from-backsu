# Research Ingestion Expansion

## 목적

이 문서는 KOSPI200 daily OHLCV 기반 technical scanner에 도움이 되는 paper universe를 넓히기 위한 research ingestion 확장 정책이다.

이 확장은 score 채택, ranking 생성, alpha 검증, backtest, valuation scoring이 아니다.

필수 guardrail:

- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Citation count is metadata only, not evidence strength.
- Scholar seeds are discovery inputs only.
- PDF fulltext download is disabled by default.
- Financial/fundamental data must not enter technical_composite_score or final_composite_score.

## Query-Set 확장 원칙

확장 query-set은 `Quant_mvp/config/research_queries.toml`에 둔다.

각 확장 query-set은 최소한 아래 metadata를 가진다.

- `name`
- `branch_hint`
- `downstream_route`
- `allowed_sources`
- `region_scope`
- `required_input_policy`
- `refresh_cadence_days`
- `precision_mode`
- `notes`

`technical_cross_sectional_momentum`은 research ingestion 후보일 뿐 실제 ranking 생성이 아니다.
`technical_rank_stability_diagnostics`는 ranking output이 아니라 diagnostic literature route다.
`technical_turnover_cost_diagnostics`는 transaction cost sensitivity literature 수집용이며 repository backtest가 아니다.
`hybrid_technical_valuation_split`은 valuation/fundamental portion을 technical 후보로 직접 보내지 않고 `hybrid_review_required.jsonl`로 분리한다.

## Classification 보강 규칙

명시적 rule 이름:

- `classify_required_inputs_boundary`
- `classify_ohlcv_compatibility`
- `classify_methodology_diagnostic`
- `classify_market_context_transfer_risk`
- `classify_hybrid_technical_valuation_split`
- `classify_forbidden_valuation_language`

보수적 분류 정책:

- `PER`, `PBR`, `ROE`, `earnings`, `book value`, `fundamental`, `analyst estimate`가 required input으로 감지되면 `valuation_agent_handoff` 또는 `hybrid_split_required`로 보낸다.
- daily OHLCV와 daily volume만 필요하고 formula path가 명확한 technical idea만 `technical_score_architect` 후보가 될 수 있다.
- transaction cost, turnover, redundancy, data snooping, survivorship, lookahead, multiple testing, publication bias 중심 문헌은 `diagnostic_backlog`로 보낸다.
- Korea/APAC/emerging market context만 있고 구현 공식이 불명확하면 transfer assumption risk를 남기고 `diagnostic_backlog`로 보낸다.
- abstract만 있고 formula/input이 불명확하면 manual review 대상으로 둔다.
- paper-reported backtest는 alpha evidence가 아니라 diagnostic risk note다.
- price-only oversold/reversal/momentum을 `cheap`, `value`, `undervalued`, `bargain`으로 표현하면 `reject_log` 또는 language guardrail violation으로 처리한다.
- hybrid paper는 technical portion과 valuation portion을 분리해야 하며 valuation/fundamental portion은 technical 후보로 직접 보내지 않는다.

## Discovery Seed Lifecycle

허용 seed:

- Google Scholar Alert email
- manual BibTeX
- manual title list
- manual citation seed
- user-provided DOI list

Lifecycle status:

- `local_seed_ingested`
- `canonical_resolution_attempted`
- `resolved_unique`
- `resolved_ambiguous`
- `unresolved`
- `manual_review_required`

Seed 규칙:

- Scholar snippet은 evidence가 아니다.
- Scholar ranking은 evidence가 아니다.
- Scholar citation count는 evidence strength가 아니다.
- Scholar seed는 approved metadata source로 canonical resolution 된 뒤에만 EvidenceCard 후보가 될 수 있다.
- Google Scholar direct scraping, headless browser automation, CAPTCHA bypass, proxy rotation, logged-in cookies are forbidden.

## New-Only Run Artifacts

Refresh 또는 corpus 확장 run은 기존 corpus를 보존하고 new-only artifact를 별도로 쓴다.

권장 artifact contract:

- `data/research/normalized/normalized_papers_new.jsonl`
- `data/research/evidence/evidence_cards_new.jsonl`
- `data/research/evidence/technical_candidates_new.jsonl`
- `data/research/evidence/diagnostic_items_new.jsonl`
- `data/research/evidence/hybrid_review_required_new.jsonl`
- `data/research/discovery/google_scholar/unresolved_seeds_new.jsonl`
- `data/research/evidence/reject_log_new.jsonl`
- `data/research/indexes/source_health_report.json`
- `reports/research_ingestion/ingestion_report.md`

`source_health_report.json` 권장 필드:

- `source`
- `adapter_version`
- `query_set`
- `request_count`
- `rate_limit_wait_count`
- `http_429_count`
- `parse_error_count`
- `schema_error_count`
- `dedup_ratio`
- `new_item_count`
- `candidate_route_counts`
- `reject_reason_counts`
- `manual_review_required_count`
- `unresolved_seed_count`
- `pdf_download_attempt_count`

`pdf_download_attempt_count`는 기본적으로 `0`이어야 한다.

## Source 확장 후보

이번 단계에서는 새 external adapter를 구현하지 않는다. 아래 source는 문서화된 후보이며, 실제 adapter 구현 전 official API, ToS, rate limit, access policy, metadata license, dedup mapping을 검토해야 한다.

| source_name | recommended_priority | use_case | access_method | adapter_required | policy_review_required | rate_limit_or_terms_review_required | dedup_mapping_requirement | metadata_license_or_access_note | risk_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KCI | medium | Korea/KOSPI local academic context | official search/API or approved export if available | yes | yes | yes | DOI/title/year/author, Korean title normalization | local policy/license 확인 필요 | 한국어 metadata 품질과 API 제한 확인 필요 |
| RePEc | medium | economics/finance working papers | official RePEc metadata services or approved dumps | yes | yes | yes | RePEc handle, DOI, title/year/author | metadata access terms 확인 필요 | working paper 중복과 version 관리 필요 |
| CORE | medium | open-access metadata discovery | official CORE API | yes | yes | yes | DOI, repository ID, title/year/author | API key and license terms 확인 필요 | OA PDF link가 있어도 PDF download는 기본 비활성화 |
| DataCite | low | DOI metadata enrichment for datasets/research outputs | official DataCite API | yes | yes | yes | DOI, related identifiers | metadata license 확인 필요 | paper가 아닌 dataset 중심 record를 reject/diagnostic 처리해야 함 |
| DOAJ | low | OA journal metadata context | official DOAJ API/export | yes | yes | yes | DOI, ISSN, title/year/author | OA journal metadata policy 확인 필요 | journal-level metadata가 signal evidence로 과장되지 않도록 주의 |
| OpenCitations | low | citation graph metadata, DOI relations | official OpenCitations endpoints | yes | yes | yes | DOI-to-DOI citation links | open citation license 확인 필요 | citation count/graph는 evidence strength가 아님 |
| Lens.org | policy_only | broad scholarly discovery/enrichment | official API if licensed | yes | yes | yes | DOI, Lens ID, title/year/author | account/license/contract 확인 필요 | 계약 조건 전까지 후보 문서화만 허용 |
| Scopus | policy_only | curated bibliographic metadata | licensed API | yes | yes | yes | DOI, Scopus ID, title/year/author | institutional license 필요 가능 | 계약/redistribution 제한이 클 수 있음 |
| Web of Science | policy_only | curated citation and bibliographic metadata | licensed API | yes | yes | yes | DOI, WoS ID, title/year/author | institutional license 필요 가능 | 계약/redistribution 제한이 클 수 있음 |
| Dimensions | policy_only | scholarly metadata and grant/patent links | official API if licensed | yes | yes | yes | DOI, Dimensions ID, title/year/author | license/access policy 확인 필요 | non-paper records와 access 제한 검토 필요 |

Forbidden source patterns:

- publisher scraping
- Scholar scraping
- paywall bypass
- automated crawling behind login walls
- PDF fulltext download without explicit OA/license/source/storage policy

## 운영 후속

Adapter 구현 필요:

- KCI, RePEc, CORE, DataCite, DOAJ, OpenCitations는 adapter 후보로 문서화 가능하다.
- Lens.org, Scopus, Web of Science, Dimensions는 정책/계약 검토 후 후보로만 유지한다.

정책 검토 필요:

- 각 source의 official API/ToS/rate limit/redistribution 조건
- raw snapshot 보관 가능 여부
- metadata license와 report 공개 가능 범위
- dedup identifier 우선순위

manual review 필요:

- unresolved seeds
- hybrid technical/valuation split
- formula unclear technical candidate
- Korea/APAC/EM transfer assumption
- price-only valuation language violation
