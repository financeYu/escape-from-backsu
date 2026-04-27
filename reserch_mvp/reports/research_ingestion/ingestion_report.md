# Research Ingestion Report

## 실행 개요

이번 보완 작업은 research-ingestion 코드 리뷰 finding 수정과 비실시간 검증이다.

live metadata 수집은 실행하지 않았다. arXiv, OpenAlex, Crossref, Semantic Scholar API 호출을 새로 수행하지 않았고, Google Scholar direct request 및 PDF fulltext 다운로드도 수행하지 않았다.

## 이번 실행에서 하지 않은 일

- score 채택을 수행하지 않았다.
- backtest를 수행하지 않았다.
- alpha claim을 하지 않았다.
- valuation/fundamental scoring을 수행하지 않았다.
- Google Scholar 직접 요청을 수행하지 않았다.
- PDF fulltext를 다운로드하지 않았다.
- live research metadata collection을 수행하지 않았다.

## 검증 범위

- backtest_methodology lane이 dedupe 이후에도 diagnostic backlog로 유지되는지 테스트로 고정했다.
- Semantic Scholar retraction field 요청 config를 보완했다.
- OpenAlex, Crossref, Semantic Scholar adapter가 source-level rate-limit wrapper를 호출하는지 테스트했다.
- non-live research_ingestion 테스트만 실행 대상으로 삼는다.

## 현재 산출물 상태

- normalized paper count: live 수집 미실행으로 새 count 없음
- EvidenceCard count: live 수집 미실행으로 새 count 없음
- rejected item count: live 수집 미실행으로 새 count 없음
- manual review required: live 수집 미실행으로 새 count 없음
- retracted / blocked paper count: live 수집 미실행으로 새 count 없음
- PDF fulltext used: no

## source freshness / currentness

- 이 보고서의 source-health 관련 내용은 해당 실행 시점의 snapshot이며 현재 vendor availability 또는 최신 연구 검증을 증명하지 않는다.
- cache hit 또는 stale cache 상태는 research 후보 관리용 metadata이며 MVP scoring/ranking 입력이 아니다.
- research source freshness는 `technical_composite_score`, `final_composite_score`, ranking 순서를 변경하지 않는다.

## 핵심 제한 사항

- 이번 실행은 score 채택을 수행하지 않았습니다.
- 이번 실행은 backtest를 수행하지 않았습니다.
- 논문 claim은 검증된 alpha가 아닙니다.
- valuation 후보는 별도 valuation agent로 handoff해야 합니다.
- Google Scholar snippet, ranking, citation count는 evidence로 사용하지 않았습니다.

## 다음 작업 제안

- live 수집이 필요하면 별도 opt-in 실행으로 수행하고 run_id, source_health, raw snapshot 위치를 새 보고서에 명시한다.
- 커밋 전에는 runtime data/research artifacts와 source-controlled report의 경계를 다시 확인한다.
