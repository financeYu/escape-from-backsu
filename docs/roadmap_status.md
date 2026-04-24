# 로드맵 상태

## 현재 활성 단계

Step 6 = 데이터 전처리 파이프라인 구현

## 현재 판정

- Step 1 verdict: COMPLETE or mostly complete
- Step 2 verdict: PARTIALLY COMPLETE
- Step 3 verdict: COMPLETE
- Step 4 verdict: COMPLETE
- Step 5 verdict: COMPLETE
- Step 6 permission: Yes

## Step 5 완료 상태

완료:

- `Quant_mvp/docs/score_catalog.md` 작성
- `Quant_mvp/docs/score_definitions.md` 작성
- `Quant_mvp/docs/family_map.md` 작성
- `Quant_mvp/config/scores.toml`에 Step 5 정의 문서 경로 추가
- `realized_vol_percentile`을 direct technical alpha가 아닌 `diagnostic` branch 후보로 정정

유지되는 제한:

- score implementation 없음
- Research Tester implementation 없음
- ranking generation 없음
- composite scoring 없음
- backtest 없음
- valuation/fundamental scoring 없음

## Step 2 Follow-up 상태

완료 또는 Step 4 guardrail로 반영됨:

- `schema_validator.py` 강화
- dtype expectations 추가
- date parseability check 추가
- numeric conversion safety check 추가
- duplicate key validation 추가
- ticker leading-zero preservation check 명시
- legacy outputs 문서화 완료: `docs/legacy_output_inventory.md`
- financial data는 `valuation_deferred` 상태 유지

남은 항목:

- financial statement sample이 생기면 financial validation 실행
- 기존 `chart_mvp/reports/data_quality/*`는 background report이므로 downstream evidence로 쓰기 전 current validation context에서 재확인

## 밸류에이션 상태

- `valuation_status = deferred`
- `financial_data_usage_now = inventory_only_or_gui_display_only`
- `point_in_time_status = unverified`, 단 disclosure 또는 availability date가 있으면 별도 검증 가능
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`

## Step 4 경계 상태

- 기술 분석과 밸류에이션 경계는 `docs/technical_valuation_boundary.md`에 고정했다.
- score branch 분류는 `docs/score_branch_policy.md`에 고정했다.
- Step 5 진입 전 routing 기준은 `docs/selection_criteria.md`에 정리했다.
- price-only evidence를 valuation evidence로 표현하지 않는다.
- financial data는 technical scoring과 final composite scoring에서 제외한다.
- point-in-time-safe financial data가 확보되기 전까지 valuation review는 deferred 상태다.
- root `config/scores.toml`은 runtime score/composite를 비활성화한다.
- `Quant_mvp/config/scores.toml`의 `enabled = true`는 candidate registry visibility이며 `runtime_enabled = false`로 production scoring을 막는다.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- Step 17 전 backtest 금지
- price-only evidence에 valuation language 사용 금지
