# Source Health

## Scope

이번 보완 작업에서는 research ingestion 운영 최적화 검증을 위해 opt-in live smoke test를 실행했다.

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
