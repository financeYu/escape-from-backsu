# Research Ingestion Report

- run_id: `refresh_20260511`
- run timestamp: `2026-05-11T00:03:05Z`
- selected sources: openalex
- selected query-set: `technical_momentum,technical_mean_reversion,technical_breakout,technical_volatility_liquidity,technical_trend_efficiency,technical_volume_price_confirmation`
- raw records by source: openalex=300
- collection relevance rejected: 224
- collection relevance manual review: 17
- enrichment target count: 0
- enrichment records by source: 없음
- normalized paper count: 691
- deduped paper count: 691
- EvidenceCard count: 668
- rejected item count: 105
- manual review required: 526
- retracted / blocked paper count: 0
- unresolved Scholar seed count: 0
- PDF fulltext used: no

## 핵심 제한 사항
- 이번 실행은 score 채택을 수행하지 않았습니다.
- 이번 실행은 backtest를 수행하지 않았습니다.
- 논문 claim은 검증된 alpha가 아닙니다.
- valuation 후보는 valuation review skill로 handoff해야 합니다.
- Google Scholar snippet, ranking, citation count는 evidence로 사용하지 않았습니다.
- EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.

## branch별 분류 건수
- diagnostic: 253
- hybrid: 81
- out_of_scope: 105
- technical: 168
- valuation: 61

## downstream_route별 건수
- diagnostic_backlog: 253
- hybrid_split_required: 81
- reject_log: 105
- technical_score_architect: 168
- valuation_agent_handoff: 61

## source 오류 / rate-limit 요약
- 기록된 오류/rate-limit 요약이 없습니다. 자세한 내용은 source_health.md를 확인하세요.

## unresolved Scholar seeds
- 없음

## 다음 작업 제안
- 수동 검토가 필요한 hybrid / unresolved seed를 먼저 정리합니다.
- technical 후보는 Score Architect에서 별도 score definition으로만 검토합니다.
- valuation 후보는 point-in-time fundamentals 검증 전까지 unavailable로 유지합니다.
