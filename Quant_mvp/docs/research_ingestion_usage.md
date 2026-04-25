# Research Ingestion CLI Usage

이 문서는 `Research Ingestion Agent` 전용 사용법입니다. 이 CLI는 paper metadata와 abstract를 수집해 EvidenceCard를 만들 뿐이며, score 구현, backtest, adoption decision, alpha claim, valuation/fundamental scoring을 수행하지 않습니다.

현재 editable install 설정은 추가하지 않았으므로 PowerShell에서는 아래처럼 `PYTHONPATH=src`를 지정합니다.

```powershell
$env:PYTHONPATH='src'
```

## Approved Metadata Collection

승인된 live metadata source는 `arxiv`, `openalex`, `crossref`, `semantic_scholar`입니다. PDF fulltext 수집은 기본 비활성화입니다.

2026-04-25 확인 기준으로 OpenAlex 실수집은 `OPENALEX_API_KEY`를 요구합니다. 키가 없으면 OpenAlex source는 live collect에서 skip하고, `--dry-run` 또는 `--offline`만 사용합니다. Semantic Scholar는 public mode가 가능하지만 공유 rate limit과 throttling 위험이 있어 `SEMANTIC_SCHOLAR_API_KEY` 설정을 권장합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion collect --sources arxiv,openalex --query-set technical_momentum --run-id dev_live_001 --no-pdf
```

Collect 이후에는 query-set의 `keywords`와 `exclude_keywords`를 사용해 metadata relevance gate를 적용합니다. raw snapshot은 보존하지만, `crypto`, `options`, `intraday`, `order book`처럼 제외 키워드가 감지된 항목이나 query-set keyword와 맞지 않는 항목은 downstream EvidenceCard 후보에서 제외하고 아래 파일에 기록합니다.

- `data/research/indexes/{run_id}_collection_relevance.jsonl`
- `data/research/normalized/{run_id}_rejected_collected_papers.jsonl`

Dry-run은 network call 없이 source, query, page size, output path, guardrail을 출력합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion collect --dry-run --sources arxiv,openalex --query-set technical_momentum --run-id dry_run_001
```

Offline mode는 network call을 수행하지 않고 빈 collection artifact와 source health 기록만 생성합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion collect --offline --sources arxiv --query-set technical_momentum --run-id offline_001
```

## Backtest Methodology Collection

백테스트 관련 논문은 퀀트 알고리즘 후보 논문과 분리해 `backtest_methodology` query-set으로 수집합니다. 이 query-set은 `branch_hint = "diagnostic"` 및 `management_lane = "backtest_methodology"`로 관리하며, score 후보가 아니라 Step 17 백테스트 설계/검증 참고문헌으로만 취급합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion collect --dry-run --sources arxiv,openalex,crossref,semantic_scholar --query-set backtest_methodology --run-id bt_papers_YYYYMMDD
$env:PYTHONPATH='src'; python -m research_ingestion run-all --sources arxiv,openalex,crossref,semantic_scholar --query-set backtest_methodology --run-id bt_papers_YYYYMMDD --no-pdf
```

운영 규칙:

- 알고리즘 후보 논문은 `technical_momentum`, `technical_mean_reversion`, `technical_breakout`, `technical_volatility_liquidity` 같은 `technical_*` query-set으로 수집합니다.
- 백테스트 방법론 논문은 `backtest_methodology` query-set과 `bt_papers_*` 같은 별도 run-id로 수집합니다.
- 백테스트 방법론 EvidenceCard는 `diagnostic_backlog`로 라우팅되며, `technical_candidates.jsonl`에 넣지 않습니다.
- 이 수집은 실제 backtest, forward return 계산, score 채택, alpha 검증을 수행하지 않습니다.
- Step 17 전에는 백테스트 결과 파일이나 performance report를 생성하지 않습니다.

## Expanded Query Sets

논문 수집 범위 확장은 `config/research_queries.toml`의 query-set metadata로 관리합니다. 확장 query-set도 EvidenceCard 생성을 위한 upstream metadata collection일 뿐입니다.

필수 경계:

- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Citation count is metadata only, not evidence strength.
- Scholar seeds are discovery inputs only.
- PDF fulltext download is disabled by default.
- Financial/fundamental data must not enter technical_composite_score or final_composite_score.

확장 query-set 예:

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion collect --dry-run --sources arxiv,openalex,crossref,semantic_scholar --query-set technical_trend_efficiency --run-id trend_efficiency_YYYYMMDD --no-pdf
$env:PYTHONPATH='src'; python -m research_ingestion collect --dry-run --sources arxiv,openalex,crossref,semantic_scholar --query-set technical_rank_stability_diagnostics --run-id rank_stability_YYYYMMDD --no-pdf
$env:PYTHONPATH='src'; python -m research_ingestion collect --dry-run --sources arxiv,openalex,crossref,semantic_scholar --query-set hybrid_technical_valuation_split --run-id hybrid_split_YYYYMMDD --no-pdf
```

운영 규칙:

- `technical_cross_sectional_momentum`은 후보 논문 수집용이며 ranking output을 만들지 않습니다.
- `technical_rank_stability_diagnostics`는 diagnostic literature 수집용이며 ranking output을 만들지 않습니다.
- `technical_turnover_cost_diagnostics`는 transaction cost sensitivity literature 수집용이며 repository backtest가 아닙니다.
- `asia_pacific_equity_context`와 `emerging_market_equity_anomalies`는 KOSPI200 transfer assumption risk 때문에 diagnostic route를 우선합니다.
- `hybrid_technical_valuation_split`은 `hybrid_review_required.jsonl` route이며 valuation/fundamental portion을 technical candidate로 직접 보내지 않습니다.

## End-to-End Run

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion normalize --run-id dev_live_001
$env:PYTHONPATH='src'; python -m research_ingestion enrich --sources crossref,semantic_scholar --run-id dev_live_001 --max-records 10 --no-pdf
$env:PYTHONPATH='src'; python -m research_ingestion classify --run-id dev_live_001
$env:PYTHONPATH='src'; python -m research_ingestion evidence --run-id dev_live_001
$env:PYTHONPATH='src'; python -m research_ingestion report --run-id dev_live_001
```

`run-all`은 collect부터 report까지 이어서 실행합니다. `--enrich-sources`를 주면 normalize 직후 metadata enrichment를 선택적으로 수행합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion run-all --sources arxiv,openalex --query-set technical_momentum --run-id dev_live_001 --no-pdf
$env:PYTHONPATH='src'; python -m research_ingestion run-all --sources arxiv,openalex --query-set technical_momentum --run-id dev_live_001 --enrich-sources crossref,semantic_scholar --enrich-max-records 10 --no-pdf
```

## Periodic Refresh

`refresh`는 기존 `data/research/normalized/papers.jsonl`을 보존하면서 승인된 metadata source를 다시 조회하고, 아직 corpus에 없는 논문만 `data/research/normalized/{run_id}_refresh_new_papers.jsonl`에 기록한 뒤 dedupe된 `papers.jsonl`, EvidenceCard, Korean reports를 갱신합니다.

Refresh는 new-only artifact도 함께 쓸 수 있습니다.

- `data/research/normalized/normalized_papers_new.jsonl`
- `data/research/evidence/evidence_cards_new.jsonl`
- `data/research/evidence/technical_candidates_new.jsonl`
- `data/research/evidence/diagnostic_items_new.jsonl`
- `data/research/evidence/hybrid_review_required_new.jsonl`
- `data/research/discovery/google_scholar/unresolved_seeds_new.jsonl`
- `data/research/evidence/reject_log_new.jsonl`
- `data/research/indexes/source_health_report.json`

기본 주기와 query-set은 `config/research_policy.toml`의 `[refresh_policy]`에서 관리합니다. 현재 기본값은 14일마다 technical/methodology/backtest/Korea query-set을 점검하고, `fundamental_valuation`은 valuation 경계 때문에 opt-in으로 둡니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion refresh --dry-run --run-id refresh_20260425
$env:PYTHONPATH='src'; python -m research_ingestion refresh --run-id refresh_20260425 --no-pdf
```

특정 범위만 점검하려면 source와 query-set을 명시합니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion refresh --sources arxiv,crossref --query-sets technical_momentum,korea_kospi_context --run-id refresh_technical_001 --no-pdf
$env:PYTHONPATH='src'; python -m research_ingestion refresh --sources arxiv,crossref --query-sets backtest_methodology --run-id refresh_backtest_methodology_001 --no-pdf
```

스케줄러에 연결할 때는 위 명령을 Windows Task Scheduler 또는 cron에서 실행하고, `run-id`는 날짜 기반으로 고정합니다. 예: `refresh_YYYYMMDD`. 이 명령은 Google Scholar live request, PDF fulltext download, score adoption, backtest, valuation scoring을 수행하지 않습니다.

## Metadata Enrichment

`enrich`는 이미 정규화된 `papers.jsonl` 또는 지정한 JSONL을 읽고 Crossref DOI lookup, Semantic Scholar paper lookup을 수행합니다. Crossref와 Semantic Scholar는 metadata source이며 fulltext source가 아닙니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion enrich --sources crossref,semantic_scholar --run-id dev_live_001 --max-records 10 --no-pdf
```

Dry-run은 DOI/arXiv/Semantic Scholar ID 기반 lookup target만 출력하고 API 호출을 하지 않습니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion enrich --dry-run --sources crossref,semantic_scholar --run-id dev_live_001 --max-records 10
```

생성물:

- `data/research/normalized/{run_id}_enriched_papers.jsonl`
- `data/research/indexes/{run_id}_enrichment_index.jsonl`
- `data/research/indexes/{run_id}_enrichment_summary.json`
- source별 raw snapshot 및 redacted request metadata

Citation count, influential citation count, Crossref score는 metadata일 뿐 alpha evidence가 아닙니다.

Semantic Scholar public mode는 429 rate limit이 쉽게 발생할 수 있습니다. 이 경우 raw 실패 응답과 source health를 남기고, API key 설정 또는 더 작은 `--max-records`로 재시도합니다.

## Google Scholar Local Seeds

Google Scholar는 discovery-only입니다. `scholar.google.com`으로 live request를 보내지 않으며, headless browser, CAPTCHA bypass, proxy rotation, logged-in cookie 사용도 금지됩니다.

허용되는 입력은 사용자가 보유한 로컬 파일뿐입니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-alerts --input-dir data/research/discovery/google_scholar/alerts --run-id seed_001
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-bibtex --input-dir data/research/discovery/google_scholar/bibtex --run-id seed_001
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-endnote --input-dir data/research/discovery/google_scholar/endnote --run-id seed_001
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-refman --input-dir data/research/discovery/google_scholar/refman --run-id seed_001
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-refworks --input-dir data/research/discovery/google_scholar/refworks --run-id seed_001
$env:PYTHONPATH='src'; python -m research_ingestion import-scholar-title-list --input-path data/research/discovery/google_scholar/title_lists/titles.txt --run-id seed_001
```

Scholar seed는 approved metadata source로 canonical resolution이 되어야 EvidenceCard 후보가 될 수 있습니다.

```powershell
$env:PYTHONPATH='src'; python -m research_ingestion resolve-scholar-seeds --sources openalex,crossref,arxiv,semantic_scholar --run-id seed_001
```

## Environment Variables

API key는 코드나 config에 하드코딩하지 않습니다. 값은 raw metadata, reports, JSONL, CSV, exception text에 노출되지 않도록 redaction합니다.

추가 자료 수집을 위해 사용자에게 요청할 값은 아래 순서가 좋습니다.

- `OPENALEX_API_KEY`: OpenAlex live metadata 수집용. 현재는 가장 먼저 필요한 키입니다.
- `SEMANTIC_SCHOLAR_API_KEY`: Semantic Scholar 검색/상세조회/enrichment 안정화용.
- `CROSSREF_MAILTO`: Crossref polite pool용 연락 이메일. 비밀키는 아니지만 공개 보고서에는 필요 이상 노출하지 않습니다.
- `CROSSREF_PLUS_API_TOKEN`: 사용자가 Crossref Metadata Plus를 보유한 경우에만 선택적으로 사용합니다.
- Google Scholar Alerts, BibTeX, EndNote, RefMan, RefWorks, title list: API 키가 아니라 사용자가 직접 받은 로컬 discovery seed입니다. `scholar.google.com` 직접 요청은 금지됩니다.

키 값은 채팅, config, markdown, raw snapshot에 붙여넣지 말고 실행하는 PowerShell 세션의 환경 변수로만 설정합니다.

```powershell
$env:OPENALEX_API_KEY='...'
$env:OPENALEX_MAILTO='name@example.com'
$env:CROSSREF_MAILTO='name@example.com'
$env:CROSSREF_PLUS_API_TOKEN='...'
$env:SEMANTIC_SCHOLAR_API_KEY='...'
```

OpenAlex는 real collection에서 keyless mode를 허용하지 않습니다. Semantic Scholar는 config가 허용하는 경우 key 없이 public mode로 실행할 수 있지만, 429 rate limit이 쉽게 발생할 수 있습니다. Crossref는 sign-up 없이도 REST API를 사용할 수 있으나 가능하면 polite email을 설정합니다.

## Tests

일반 테스트는 offline-only입니다.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_ingestion
```

Live API smoke 테스트는 명시적으로 opt-in해야 합니다.

```powershell
$env:PYTHONPATH='src'; $env:RUN_LIVE_RESEARCH_API_TESTS='1'; python -m pytest tests\research_ingestion\live
```

## Boundaries

- score implementation: 수행하지 않음
- backtest: 수행하지 않음
- adoption decision: 수행하지 않음
- alpha claim: 수행하지 않음
- valuation/fundamental scoring: 수행하지 않음
- Google Scholar direct scraping: 수행하지 않음
- PDF fulltext ingestion: 명시적 OA/license/storage policy 전까지 수행하지 않음

EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.
