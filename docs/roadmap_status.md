# 로드맵 상태

이 파일은 현재 작업 판단에 필요한 latest-only status만 유지한다. 완료 Step의 긴 구현/검증 이력은 기본 컨텍스트가 아니며 `docs/context/archive/`와 `docs/roadmap_archive/`에서 필요한 경우에만 확인한다.

## 현재 활성 단계

Step 20 = KOSPI200 MVP Completeness Hardening & Final Done Validation, COMPLETE / KOSPI200 technical MVP v0.1 freeze-ready

- Active: no in-progress roadmap Step.
- Current baseline: Step 20 completed KOSPI200 MVP completeness hardening and final Done validation.
- Current gate: future expansion needs a separately approved post-MVP Step, routed context packet, correct role branch/worktree, and conflict checkpoint when required.

## 컨텍스트 운영 상태

- 기본 시작점: `docs/context/current_context.md`, `docs/context/MVP_V0_1_BASELINE.md`, active packet 1개.
- Targeted lookup: `docs/context/CONTEXT_ROUTING_INDEX.md`와 필요한 domain stub만 사용한다.
- Archive lookup: conflict, regression, provenance, release-evidence 확인이 있을 때만 가장 좁은 파일을 읽는다.
- 답변과 handoff는 confirmed context fact를 최대 3개만 반복하고 현재 판단, 변경, 검증, 남은 리스크를 중심으로 작성한다.
- 완료 Step 1-20 산출물은 기본적으로 신뢰한다.

## 병렬 Workspace 운영 메모

- Step 14 이후 병렬 구현, review, research ingestion, audit/scope watchdog, master integration 작업은 `docs/workspace_parallel_work_policy.md`를 따른다.
- Step 15부터는 Step implementation, Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, master integration을 별도 branch/worktree로 분리한다.
- 모든 하위 에이전트는 파일 편집 전에 role branch/worktree를 만들거나 선택하고 루트 `WORKSPACE_MANIFEST.md`를 작성해야 한다.
- `C:\Users\jjaew\Project\master_mvp`는 integration / verification / status-control 전용 workspace로 유지한다.
- 이 운영 메모는 Step 상태를 변경하지 않는다.

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
| Step 14 | COMPLETE |
| Step 15 | COMPLETE |
| Step 16 | COMPLETE |
| Step 17 | COMPLETE |
| Step 18 | COMPLETE |
| Step 19 | COMPLETE |
| Step 20 | COMPLETE / KOSPI200 MVP Completeness Hardening & Final Done Validation |

## 현재 Baseline 핵심

- MVP universe는 KOSPI200 only다.
- `technical_composite_score`는 technical-only이며 MVP v0.1에서 `final_composite_score`와 같다.
- Valuation/fundamental data는 candidate-only이며 technical/final composite에 들어가지 않는다.
- Backtest output은 evaluation-only이며 upstream scoring/ranking에 feedback하지 않는다.
- Generated reports, runtime outputs, chart images, local caches, raw market data는 default context가 아니다.

## Research Ingestion 상태

- Research ingestion 확장 상태는 `docs/research_ingestion_expansion.md`와 affected research config를 targeted read한다.
- EvidenceCard는 score definition, adoption decision, alpha evidence, valuation verdict가 아니다.
- Paper-reported backtest와 citation count는 diagnostic metadata only다.
- PDF fulltext download는 기본 비활성화 상태다.
- Financial/fundamental data must not enter `technical_composite_score` or `final_composite_score`.

## 밸류에이션 상태

- `valuation_status = candidate_only_not_activated`
- `financial_data_usage_now = candidate_schema_and_synthetic_fixtures_only`
- `point_in_time_status = availability_date_required_for_candidate_records`; live vendor PIT availability remains unverified until separately proven.
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`
- Step 18 candidate data remains separate from technical scoring, final ranking, and Step 17 backtest inputs.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- documented composite design 전 composite score implementation 금지
- active Step이 명시적으로 허용하기 전에는 ranking generation 금지
- valuation status가 candidate-only인 동안 active valuation/fundamental scoring 금지
- financial data를 `technical_composite_score`에 넣지 않는다
- financial data를 `final_composite_score`에 넣지 않는다
- price-only evidence에 valuation language 사용 금지
- backtest feedback을 upstream scoring/ranking에 넣지 않는다
- trading recommendation, proven alpha, expected return signal language 금지

## 상세 이력 위치

- Compact post-Step20 baseline: `docs/context/MVP_V0_1_BASELINE.md`
- Context routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`
- Step 1-20 archive: `docs/context/archive/step01_to_step20_history.md`
- Older roadmap archive: `docs/roadmap_archive/`
- Release evidence: `docs/releases/`
- Contracts: `docs/contracts/step20_composite_contract.md`, `docs/contracts/step20_ranking_contract.md`

## Step 간 충돌 체크포인트

Run a Cross-Step Conflict Checkpoint whenever an important in-Step stage ends and before each Step is closed.

Use `docs/cross_step_conflict_check.md` and generate a compact review packet with:

```powershell
python scripts/build_review_packet.py --step "<current step>" --stage "<stage name>"
```

Completed Step artifacts are trusted by default. The checkpoint checks only whether the current stage conflicts with roadmap order, hard stops, cross-project handoffs, generated-output boundaries, context-routing boundaries, or unresolved carry-forward risks.
