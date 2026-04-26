# Research Ingestion Optimization Handoff

## 목적

이 문서는 root/master agent가 동일한 최적화 검토를 반복하지 않도록 이번 작업의 범위와 완료 항목을 압축해 기록한다.

## 작업 위치

- branch: `research/step20-ingestion-ops-optimization`
- worktree: `C:\Users\jjaew\Project\worktrees\research_step20-ingestion-ops-optimization`
- active roadmap state: Step 20 COMPLETE 이후 research support patch
- responsible project: `reserch_mvp`

## 완료한 6개 항목

1. dedupe 확장성
   - `deduplicate_papers`가 duplicate merge 때마다 전체 `PaperDedupeIndex.rebuild()`를 호출하지 않도록 변경했다.
   - 병합 row만 incremental index에 다시 등록한다.
   - 회귀 테스트: `test_dedupe_updates_incremental_index_after_merge`

2. enrichment 처리량
   - Semantic Scholar enrichment 기본 경로에 batch endpoint 지원을 추가했다.
   - `SemanticScholarAdapter.fetch_batch_response()`와 `parse_batch_json()`을 추가했다.
   - `cmd_enrich`는 기본 fetch 경로에서 `semantic_scholar` target을 batch로 묶어 처리한다.
   - 회귀 테스트: `test_semantic_scholar_batch_fetch_uses_post_and_rate_limiter`, `test_semantic_scholar_enrichment_batches_default_fetch`
   - Root/master 주의: 이 항목은 이미 구현됨. 단건 enrichment를 다시 구현하거나 같은 batch 작업을 반복하지 말 것.

3. full refresh 요청 예산
   - collect dry-run plan에 `request_budget`을 추가했다.
   - refresh dry-run plan에 child query-set budget aggregate를 추가했다.
   - `full_refresh` dry-run 기준 보수적 상한은 `worst_case_request_count=288`, `full_page_request_count=104`로 출력된다.

4. query-set metadata 일관성
   - 기존 core query-set에도 `downstream_route`, `allowed_sources`, `region_scope`, `required_input_policy`, `refresh_cadence_days`, `precision_mode`, `notes`를 추가했다.
   - 대상: `technical_momentum`, `technical_mean_reversion`, `technical_breakout`, `technical_volatility_liquidity`, `methodology_diagnostics`, `backtest_methodology`, `fundamental_valuation`, `korea_kospi_context`
   - 이는 EvidenceCard handoff metadata 정리이며 score adoption이나 ranking 생성이 아니다.

5. CLI 실행성
   - source tree에서 설치 없이 `python -m research_ingestion ...`를 실행할 수 있도록 root wrapper package를 추가했다.
   - 설치된 package 경로는 변경하지 않았고, local source-tree 실행 때만 `src/research_ingestion`을 package path로 확장한다.
   - 회귀 테스트: `test_source_tree_module_cli_runs_without_pythonpath`

6. live source health smoke
   - opt-in live smoke test 실행 결과: 3 passed, 1 skipped.
   - arXiv, OpenAlex, Crossref live smoke는 passed.
   - Semantic Scholar live smoke는 `SEMANTIC_SCHOLAR_API_KEY`가 없으면 skipped로 고정했다.
   - Google Scholar live request, PDF fulltext download, paywalled publisher scraping은 수행하지 않았다.

## 검증

- `python -m pytest -q -p no:cacheprovider reserch_mvp\tests\research_ingestion` = 102 passed, 4 skipped
- `$env:RUN_LIVE_RESEARCH_API_TESTS='1'; python -m pytest -q -p no:cacheprovider reserch_mvp\tests\research_ingestion\live` = 3 passed, 1 skipped
- `python -m research_ingestion collect --dry-run --run-id opt_check_collect --sources arxiv,openalex --query-set technical_momentum --max-results 2 --page-size 1` passed
- `python -m research_ingestion refresh --dry-run --run-id opt_check_refresh --profile fast_refresh` passed
- `python -m research_ingestion refresh --dry-run --run-id opt_check_full --profile full_refresh` passed

## 금지 범위 확인

- score implementation: not changed
- score adoption: not changed
- ranking output: not changed
- `technical_composite_score`: not changed
- `final_composite_score`: not changed
- backtest: not changed
- valuation/fundamental scoring: not activated
- trading recommendation or proven alpha language: not introduced
- Google Scholar live scraping: not performed
- PDF fulltext download: not performed

## 남은 리스크

- Semantic Scholar live smoke는 API key가 없는 환경에서 public mode를 신뢰하지 않는다.
- 이번 patch는 source collection/enrichment 운영 최적화이며, new external adapter 추가나 score 품질 검증이 아니다.
- watchdog audit trigger는 존재한다: config/runtime/generation boundary 관련 변경이므로 master integration 전 scope watchdog 또는 equivalent master gate에서 이 handoff와 diff를 확인해야 한다.

