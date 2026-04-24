# Quant Project Checklist

## 1. Project Goal

Build a KOSPI200 constituent-level daily OHLCV technical/statistical multi-score ranking engine.

The project must remain:

- explainable
- modular
- backtest-friendly
- conservative in quant engineering assumptions
- config-first
- safe against future data and lookahead

This is not a single trading strategy repository.
This is not an AI black-box alpha repository.
Valuation and fundamental analysis are deferred until after the technical scanner is completed.

## 2. Global Rules

- Use conservative quant engineering.
- Prefer config-first implementation.
- Do not use future data.
- Do not allow lookahead.
- Do not silently redefine scores after seeing results.
- Document score definitions before implementation.
- Keep diagnostics separate from alpha signals.
- Do not infer valuation from price-only evidence.
- Do not describe technical oversoldness as cheap or value.
- Keep unknowns marked as unknown.
- Mark inference explicitly.
- Keep paths, config keys, column names, and function names in English.
- Korean summaries are allowed and preferred for user-facing status.

## 3. Agent Workflow

Stage 1: Score Architect

- Define candidate score purpose, family, branch, raw inputs, formula path, normalization candidates, minimum history, overlap risk, and failure modes.
- Do not implement, backtest, optimize, or adopt scores.

Stage 2: Research Tester

- Implement only documented and approved MVP technical score candidates.
- Produce reproducible tests, diagnostics, and normalized outputs.
- Do not redefine scores silently after results.

Stage 3: Technical Selection Reviewer

- Compare tested technical scores for usefulness, stability, redundancy, and market-structure plausibility.
- Adopt, defer, downgrade, or reject technical scores conservatively.
- Do not perform valuation review.

Stage 4: Adoption Synthesis

- Convert accepted technical-review decisions into an explicit implementation/adoption plan.
- Keep composite design transparent and documented.
- Do not merge financial data into technical or final composite scoring.

## 4. Full Roadmap

| Step | Name |
| --- | --- |
| Step 1 | 에이전트 / 운영 규칙 수립 |
| Step 2 | 네이버 파이낸셜 데이터 수집기 검증 |
| Step 3 | 디렉터리 / config / 표준 스키마 정리 |
| Step 4 | 기술 분석과 밸류에이션 경계 고정 |
| Step 5 | Score Architect: MVP 기술 점수 후보 정의 |
| Step 6 | 데이터 전처리 파이프라인 구현 |
| Step 7 | 기술 지표 계산 레이어 구현 |
| Step 8 | 테스트 / 정규화 프로토콜 작성 |
| Step 9 | Research Tester: MVP 점수 구현 |
| Step 10 | 정규화 정책 구현 |
| Step 11 | Composite Score 구조 설계 |
| Step 12 | 중복성 / 상관성 진단 구현 |
| Step 13 | Technical Selection Reviewer |
| Step 14 | Adoption Synthesis |
| Step 15 | 최신 랭킹 출력 구현 |
| Step 16 | 종목별 상세 리포트 구현 |
| Step 17 | 보수적 백테스트 |
| Step 18 | 밸류에이션 확장 준비 |
| Step 19 | 자동 실행 파이프라인 구성 |
| Step 20 | 최종 Done 검증 |

## 5. Current Status

- Step 1 = COMPLETE or mostly complete
- Step 2 = PARTIALLY COMPLETE
- Step 3 = COMPLETE
- Step 4 = COMPLETE
- Step 5 = NEXT

## 6. Step-End Reporting Format

Use this format at the end of every Step:

```text
[현재 위치]
Step N: ...

[Step 판정]
COMPLETE / PARTIALLY COMPLETE / NEEDS FIX

[완료 항목]
- ...

[미완료 / 약한 항목]
- ...

[리스크]
- ...

[다음 Step 진입 가능 여부]
Yes / Yes, with minor follow-up / No

[로드맵 진행 상태]
Step 1: ...
Step 2: ...
Step 3: ...
Step 4: ...
Step 5: ...
Step 6: ...
Step 7: ...
Step 8: ...
Step 9: ...
Step 10: ...
Step 11: ...
Step 12: ...
Step 13: ...
Step 14: ...
Step 15: ...
Step 16: ...
Step 17: ...
Step 18: ...
Step 19: ...
Step 20: ...
```

## 7. Hard Stop Rules

- No score implementation before score definitions.
- No composite score implementation before documented composite design.
- No backtest before Step 17.
- No financial data in `technical_composite_score`.
- No financial data in `final_composite_score`.
- No valuation language for price-only evidence.
- No valuation or fundamental scoring while valuation status is deferred.
- No ranking generation unless the active Step explicitly permits it.
