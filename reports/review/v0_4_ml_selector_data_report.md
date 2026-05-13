# v0.4 ML Selector 데이터 검토 보고서

상태: evidence-only 검토 보고서

## 한 줄 결론

현재 ML 산출물은 **후보 검토 우선순위를 정하는 보조 큐로는 사용 가능**합니다. 다만 학습 표본이 작고 feature 상관 경고가 있어, 이 결과를 결정 레이어나 성과 예측 근거로 해석하면 안 됩니다.

## 이번 보고서가 보는 데이터

대상은 v0.4 ML selector가 만든 산출물입니다.

- `Quant_mvp/data/v0_4/selector_model_training/`
- `Quant_mvp/data/v0_4/selector_scores/`

이 산출물의 허용 용도는 `AdoptionCandidate review prioritization only`입니다. 즉, 사람이 어떤 후보부터 검토할지 정리하는 자료입니다. 실거래, 주문, production ranking 교체, valuation/fundamental scoring 활성화, 미래 수익 주장에는 사용할 수 없습니다.

## 핵심 요약

| 항목 | 값 |
| --- | --- |
| 모델 버전 | `v0_4_selector_baseline_v0_1` |
| 단계 | `v0_4_ml_selector_application` |
| 기준 모델 | `logistic_regression` |
| 비교 모델 | `random_forest` |
| 학습 가능 row | `62` |
| positive row | `25` |
| negative row | `37` |
| 모델 artifact 생성 | `true` |
| ML score 생성 row | `62` |
| 성과 주장 허용 | `false` |
| 거래 신호 허용 | `false` |

기준 모델과 비교 모델 모두 정상적으로 산출물을 만들었습니다. 하지만 두 모델 모두 review-prioritization 및 diagnostic 용도입니다.

## 사용된 feature

학습에 들어간 feature는 6개입니다.

| feature | 의미 |
| --- | --- |
| `total_return` | 후보 evidence의 총수익 요약 |
| `excess_return_vs_proxy` | proxy 대비 초과수익 요약 |
| `max_drawdown_abs` | 최대 낙폭 절대값 |
| `sharpe` | 위험 조정 성과 요약 |
| `turnover` | 회전율 요약 |
| `volatility` | 변동성 요약 |

LogisticRegression 계수 진단은 아래와 같습니다.

| 중요도 순위 | feature | coefficient |
| ---: | --- | ---: |
| `1` | `max_drawdown_abs` | `-1.266735` |
| `2` | `sharpe` | `-1.257603` |
| `3` | `total_return` | `0.937504` |
| `4` | `volatility` | `0.409680` |
| `5` | `turnover` | `-0.248987` |
| `6` | `excess_return_vs_proxy` | `0.034369` |

주의할 점은 `high_feature_correlation_warning`이 남아 있다는 것입니다. 따라서 계수의 방향과 크기는 모델 내부 진단으로만 봐야 하고, 개별 feature의 독립적인 설명력으로 과장하면 안 됩니다.

## 점수 산출 상태

| 산출물 | row 수 | source | 상태 |
| --- | ---: | --- | --- |
| LogisticRegression selector score | `62` | `ml_model` | 생성 완료 |
| RandomForest challenger score | `62` | `random_forest_challenger` | 생성 완료 |
| LR/RF comparison | `62` | diagnostic comparison | 생성 완료 |
| v0.4.1 ranking | `62` | baseline selector source 유지 | 생성 완료 |

점수 범위:

| 모델 | 최소 | 최대 |
| --- | ---: | ---: |
| LogisticRegression | `0.188087` | `0.917520` |
| RandomForest | `0.000000` | `1.000000` |

## 우선 검토 후보 Top 5

아래 후보들은 ML score 기준으로 먼저 사람이 확인할 만한 후보입니다. 이 표는 검토 순서 큐이지, 채택 결정이 아닙니다.

| 순위 | candidate_id | LogisticRegression score | RandomForest 순위 | RandomForest score |
| ---: | --- | ---: | ---: | ---: |
| `1` | `sc:ecard:036ba7277bc6db18ab53` | `0.917520` | `1` | `1.000000` |
| `2` | `sc:ecard:0910c98f460841de26c5` | `0.917520` | `2` | `1.000000` |
| `3` | `sc:ecard:222478c272a5cd16615d` | `0.917520` | `3` | `1.000000` |
| `4` | `sc:ecard:2ec5dd54f5df4127e5c8` | `0.917520` | `4` | `1.000000` |
| `5` | `sc:ecard:33f1eb352ff88f335f81` | `0.917520` | `5` | `1.000000` |

좋은 점은 두 모델이 Top 5 후보 집합에는 동의한다는 것입니다. 다만 전체 62개 후보 중 56개에서 RandomForest 순위와 LogisticRegression 순위가 달랐고, 순위 차이는 `-50`부터 `6`까지 벌어졌습니다. 즉, 최상단 후보는 비교적 안정적이지만 중하위 후보의 순서는 모델에 민감합니다.

## Top 5 동점 원인

Top 5 후보가 같은 점수를 받은 가장 직접적인 이유는 **학습 feature 6개가 모두 동일하기 때문**입니다. 현재 LogisticRegression과 RandomForest가 보는 입력은 아래 6개뿐입니다.

| feature | Top 5 공통 값 |
| --- | ---: |
| `total_return` | `4.59248614414884` |
| `excess_return_vs_proxy` | `4.858687645713552` |
| `max_drawdown_abs` | `0.49924422265194046` |
| `sharpe` | `0.5932409139655367` |
| `turnover` | `0.686318407960199` |
| `volatility` | `0.39104534114120565` |

그래서 LogisticRegression은 같은 입력 벡터에 대해 같은 `0.9175195973185256`을 냈고, RandomForest도 같은 분기 경로를 타면서 같은 `1.0`을 냈습니다. 현재 1-5위 순서는 score가 더 높아서 갈린 것이 아니라, 동점 묶음 안에서 기존 row 순서와 candidate_id 순서가 반영된 진단용 정렬로 보는 편이 안전합니다.

공통 구조도 뚜렷합니다.

- Top 5 모두 `strategy_type = volatility`, `signal_family_candidate = volatility_liquidity`입니다.
- Top 5 모두 candidate-level EvaluationEvidence가 있고, `recorded_walk_forward_pass`, `candidate_metric_match = true`, `failure_flag_count = 0`입니다.
- Top 5 모두 동일한 평가 기간과 동일한 volatility 상태 bucket 평가 템플릿을 통과했습니다.
- 따라서 현재 ML score는 "이 다섯 후보 중 무엇이 더 낫다"보다는 "이 다섯 후보가 같은 evidence profile bucket에 있다"는 신호에 가깝습니다.

## Top 5를 더 갈라볼 여지

모델 학습 feature는 같지만, 원문 메타데이터에는 차이가 있습니다. 이 차이는 자동 점수로 바로 승격할 근거가 아니라, 수동 검토나 tie-breaker 후보 축으로 볼 수 있습니다.

| 후보 | 원문 제목 요약 | 중요도 | confidence | 발행일 | 추가로 볼 지점 |
| --- | --- | ---: | --- | --- | --- |
| `036ba7277bc6db18ab53` | Carbon Price Volatility and Stock Returns | `89` | `low` | `2026-02-02` | 분류 신뢰도가 낮고 source target이 options로 기록되어 KOSPI200 equity 적용 적합성 확인 필요 |
| `0910c98f460841de26c5` | Investors trade more after stock performance | `94` | `medium` | `2006-07-01` | 오래된 글로벌 evidence라 현재 KOSPI200 후보로 옮길 때 시장 구조 차이 확인 필요 |
| `222478c272a5cd16615d` | Technical Indicators in IDX30 Stock Selection | `97` | `low` | `2024-09-19` | 중요도는 가장 높지만 분류 신뢰도가 낮아 volatility bucket으로 단순 매핑한 근거 점검 필요 |
| `2ec5dd54f5df4127e5c8` | Volatility and Trading Volume in Indonesia transport/logistics | `94` | `medium` | `2025-02-13` | 섹터와 국가가 좁아 KOSPI200 전체 universe로 일반화 가능한지 확인 필요 |
| `33f1eb352ff88f335f81` | Trading activities forecast recessions | `94` | `medium` | `2016-01-01` | Top 5 중 transaction cost 논의가 기록된 후보라 비용 민감도 검토의 비교 기준으로 쓸 수 있음 |

추가 평가를 한다면 우선순위는 아래가 좋습니다.

1. **동점 bucket 분리**: 같은 6개 feature를 가진 후보는 같은 score bucket으로 묶고, 개별 순위 대신 "공동 1위 후보군"으로 표시합니다.
2. **원문 적합성 검토**: 논문 제목, DOI, source target, publication date, classification confidence를 사람이 확인해 현재 KOSPI200 daily OHLCV evidence route와 맞는지 봅니다.
3. **feature 확장 후보 검토**: `importance_score`, `classification_confidence`, `transaction_costs_discussed`, `publication_year`, `risk_flag_count`, `formula_clarity`, `reproducibility_level`은 현재 학습 feature에서 제외되어 있어 동점 해소에 쓰이지 않았습니다. 다만 이런 메타 feature를 학습에 넣으려면 leakage와 cohort memorization 위험을 별도로 검증해야 합니다.
4. **EvaluationEvidence 세부 비교**: walk-forward fold별 수익, 비용 민감도, coverage/warmup, source-target 적합성, point-in-time limitation을 후보별로 표준화해서 비교합니다.
5. **선택 결론 보류**: 현재 데이터만으로는 Top 5 내부의 review-preferred candidate를 고르는 근거가 부족하므로, 결론은 `selection unavailable / evidence insufficient` 쪽이 더 안전합니다.

## 안전장치 확인

| 체크 | 결과 |
| --- | --- |
| 허용 feature column 기록 | `pass` |
| feature config leakage column | 없음 |
| feature value forbidden column | 없음 |
| feature value leakage row | `0` |
| diagnostic ranking에서 selector score source 유지 | `true` |
| performance claim allowed | `false` |
| trading signal allowed | `false` |
| production activation | `false` |

남아 있는 경고:

- `limited_insufficient_training_rows`
- `high_feature_correlation_warning`

## 내가 볼 때의 해석

현재 결과는 “후보를 어디서부터 들여다볼까?”라는 질문에는 도움이 됩니다. 특히 Top 5는 두 모델이 같은 후보군을 상단에 놓았기 때문에, 다음 수동 검토 대상으로 삼기 좋습니다.

반대로 “어떤 후보가 실제로 좋다”까지 말하기에는 아직 부족합니다. 표본이 62개뿐이고, feature 간 상관 경고가 있으며, 후보별 EvidenceCard와 EvaluationEvidence 원문 검토가 아직 필요합니다.

## 다음에 할 일

가장 먼저 할 일은 Top 5 후보의 EvidenceCard와 EvaluationEvidence를 열어 아래를 확인하는 것입니다.

- 후보가 현재 route와 scope 안에 있는지
- evidence 품질과 coverage가 충분한지
- leakage/no-lookahead 상태가 통과인지
- 비용, 회전율, drawdown, 변동성 제한이 과하지 않은지
- 제한사항이 `AdoptionCandidate` 수동 검토 packet으로 넘길 수 있는 수준인지

이 확인이 끝나기 전까지는 `selection unavailable / evidence insufficient` 상태로 보는 것이 안전합니다.
