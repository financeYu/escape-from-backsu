# Source Health

## Scope

이번 보완 작업에서는 research ingestion 운영 최적화 검증을 위해 opt-in live smoke test를 실행했다.

## Freshness / Currentness

- 이 보고서는 해당 실행 시점의 source-health snapshot이며 현재 vendor availability 또는 최신 연구 검증을 증명하지 않는다.
- source-health, cache hit, stale cache 상태는 MVP scoring/ranking 입력이 아니다.
- 오래된 source-health 결과를 현재 검증처럼 사용하려면 안 되며, 필요한 경우 별도 opt-in live 또는 offline CLI run으로 새 run_id를 생성해야 한다.

실행 명령:

```powershell
$env:RUN_LIVE_RESEARCH_API_TESTS='1'; python -m pytest -q -p no:cacheprovider reserch_mvp\tests\research_ingestion\live
```

## Reviewed Source Channels

- local code/tests: yes
- live arXiv API smoke: passed
- live OpenAlex API smoke: passed
- live Crossref API smoke: passed
- live Semantic Scholar API smoke: skipped without `SEMANTIC_SCHOLAR_API_KEY`
- Google Scholar direct requests: 0
- PDF fulltext downloads: 0
- paywalled publisher scraping: 0
- local Scholar seed imports: 0

## Result

- live smoke validation: 3 passed, 1 skipped
- Semantic Scholar public mode was previously observed as unavailable in this environment; live smoke now requires explicit `SEMANTIC_SCHOLAR_API_KEY`.
- API keys were not printed or stored in reports.
- No Google Scholar live request was performed.
- No PDF fulltext download was performed.

## Notes

- source adapter rate-limit enforcement is covered by non-live unit tests.
- source health counts should be regenerated only by an explicit live or offline CLI run.
