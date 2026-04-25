# 로드맵 상태

이 파일은 현재 작업 판단에 필요한 compact status만 유지한다. 완료 Step의 긴 구현/검증 이력은 `docs/roadmap_archive/` 아래 archive 문서를 확인한다.

## 현재 활성 단계

Step 14 = Adoption Synthesis, NEXT / not started

- Recently completed: Step 13 = Technical Selection Reviewer, COMPLETE
- Recently completed before that: Step 12 = redundancy / correlation diagnostics, COMPLETE
- Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11/12/13/14 technical work.

## 전체 Step 판정

| Step | Status |
| --- | --- |
| Step 1 | COMPLETE or mostly complete |
| Step 2 | COMPLETE |
| Step 3 | COMPLETE |
| Step 4 | COMPLETE |
| Step 5 | COMPLETE |
| Step 6 | COMPLETE |
| Step 7 | COMPLETE |
| Step 8 | COMPLETE |
| Step 9 | COMPLETE |
| Step 10 | COMPLETE |
| Step 11 | COMPLETE |
| Step 12 | COMPLETE |
| Step 13 | COMPLETE |
| Step 14 | NEXT / not started |
| Step 15 | WAITING / not started |
| Step 16 | WAITING / not started |
| Step 17 | WAITING / not started |
| Step 18 | DEFERRED / waiting for valuation expansion |
| Step 19 | WAITING / not started |
| Step 20 | WAITING / not started |

## Research ingestion 범위 확장 상태

- `Quant_mvp/config/research_queries.toml`에 technical, diagnostic, Korea/APAC/EM context, hybrid split query-set 확장 metadata를 추가했다.
- `Quant_mvp/config/research_classification.toml`에 required input boundary, forbidden valuation language, 명시적 classification rule name을 추가했다.
- `Quant_mvp/config/research_scholar_discovery.toml`에 user-provided DOI seed와 seed lifecycle을 문서화했다.
- `docs/research_ingestion_expansion.md`에 source 확장 후보와 정책 검토 조건을 문서화했다.
- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Citation count is metadata only, not evidence strength.
- Scholar seeds are discovery inputs only.
- PDF fulltext download is disabled by default.
- Financial/fundamental data must not enter technical_composite_score or final_composite_score.
- ranking, latest ranking, composite score, backtest, valuation/fundamental scoring은 여전히 생성하지 않는다.

## 최근 완료 Step 요약

### Step 13 = Technical Selection Reviewer

- Step 13 review contract, status vocabulary, validation guardrail, reviewer engine, report builder, and generated report path/language guardrails are implemented.
- Step 13 output remains technical review recommendation material for Step 14 only.
- `review_status` values are technical recommendations, not final adoption states.
- `diagnostic_only` and context roles remain constrained to diagnostic/context recommendation paths.
- Severe redundancy or blocked candidate diagnostics cannot auto-promote to adoption.
- Generated Step 13 reports are constrained to `reports/selection/` and must include `technical selection review material only`.
- Latest recorded validation: `$env:PYTHONPATH="src"; python -m pytest` = 277 passed, 4 skipped.

### Step 12 = Redundancy / Correlation Diagnostics

- Same-date cross-sectional Spearman redundancy/correlation diagnostics are implemented for review material.
- Normalized score columns are required; raw score fallback is not allowed.
- Diagnostics remain non-alpha, non-adoption, non-ranking, non-backtest, and non-valuation material.

## 상세 이력 위치

- Full archived Step history through Step 13: `docs/roadmap_archive/step_history_through_step13.md`
- Step-specific governing docs remain source of detail, including:
  - `docs/step13_technical_selection_reviewer.md`
  - `docs/step12_redundancy_correlation_diagnostics.md`
  - `docs/step11_composite_score_design.md`
  - `docs/step10_normalization_policy.md`
  - `docs/step9_research_tester_scores.md`
  - `docs/step8_testing_normalization_protocol.md`
  - `docs/step7_indicator_layer.md`
  - `docs/step2_financial_validation_summary.md`

## Step 14 진입 기준

- Use Step 13 technical review recommendations as Step 14 input material.
- Convert technical review recommendations into an explicit adoption synthesis plan only.
- Keep diagnostic/context-only candidates visibly separate from direct candidate signal adoption.
- Do not generate latest ranking output before Step 15.
- Do not implement backtest before Step 17.
- Do not implement valuation/fundamental scoring before Step 18.
- Do not merge financial/fundamental data into `technical_composite_score` or `final_composite_score`.

## Step 간 충돌 체크포인트

Run a Cross-Step Conflict Checkpoint whenever an important in-Step stage ends and before each Step is closed.

Required trigger examples:

- design or output contract is locked
- implementation is ready for master-up
- cross-project handoff is about to be consumed downstream
- Step-end validation has passed and code review is about to begin
- required review fixes are complete and validation is about to be rerun

Use `docs/cross_step_conflict_check.md` and generate a compact review packet with:

```powershell
python scripts/build_review_packet.py --step "Step 14" --stage "<stage name>"
```

Completed Step artifacts are trusted by default. The checkpoint checks only whether the current stage conflicts with roadmap order, hard stops, cross-project handoffs, generated-output boundaries, or unresolved carry-forward risks.

## 밸류에이션 상태

- `valuation_status = deferred`
- `financial_data_usage_now = inventory_only_or_gui_display_only`
- `point_in_time_status = unverified`, unless separate disclosure or availability dates are validated later.
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`
- Step 18 owns point-in-time financial metadata schema and valuation/fundamental expansion preparation.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- documented composite design 전 composite score implementation 금지
- active Step이 명시적으로 허용하기 전에는 ranking generation 금지
- Step 17 전 backtest 금지
- valuation status가 deferred인 동안 valuation/fundamental scoring 금지
- financial data를 `technical_composite_score`에 넣지 않는다
- financial data를 `final_composite_score`에 넣지 않는다
- price-only evidence에 valuation language 사용 금지
