# 로드맵 상태

## 현재 활성 단계

Step 5 = Score Architect: MVP 기술 점수 후보 정의

## 현재 판정

- Step 1 verdict: COMPLETE or mostly complete
- Step 2 verdict: PARTIALLY COMPLETE
- Step 3 verdict: COMPLETE
- Step 4 verdict: COMPLETE
- Step 5 permission: Yes, with minor follow-up

## Step 2 남은 Follow-up

- `schema_validator.py` 강화
- dtype expectations 추가
- date parseability check 추가
- numeric conversion safety check 추가
- duplicate key validation 추가
- ticker leading-zero preservation check 명시
- financial statement sample이 생기면 financial validation 실행
- `outputs/latest_top*`, `data/scan_results/*` 같은 legacy outputs 문서화
- financial data는 `valuation_deferred` 상태 유지

## 밸류에이션 상태

- `valuation_status = deferred`
- `financial_data_usage_now = inventory_only_or_gui_display_only`
- `point_in_time_status = unverified`, 단 disclosure 또는 availability date가 있으면 별도 검증 가능
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`

## Step 4 경계 상태

- 기술 분석과 밸류에이션 경계는 `docs/technical_valuation_boundary.md`에 고정했다.
- price-only evidence를 valuation evidence로 표현하지 않는다.
- financial data는 technical scoring과 final composite scoring에서 제외한다.
- point-in-time-safe financial data가 확보되기 전까지 valuation review는 deferred 상태다.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- Step 17 전 backtest 금지
- price-only evidence에 valuation language 사용 금지
