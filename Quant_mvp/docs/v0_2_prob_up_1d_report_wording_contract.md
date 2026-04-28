# v0.2 prob_up_1d report wording contract

## Purpose

This contract defines allowed and forbidden report wording for v0.2
`final_composite_score` under `score_semantic_version = "v0_2_prob_up_1d"`.
It does not activate runtime report generation by itself.

## Required Meaning

Reports may describe `final_composite_score` as:

- "1영업일 뒤 adjusted_close 상승확률 추정값"
- "상승확률 기반 순위"
- "v0.2 확률형 최종 스코어"
- "확률형 최종 스코어"
- "상승확률 기반 점수"

## Forbidden Wording

Reports must not include:

- "매수"
- "매도"
- "보유"
- "추천"
- "투자 조언"
- "확정 상승"
- "수익 보장"
- "기대수익률"
- "초과수익"
- "검증된 알파"
- "proven alpha"
- "guaranteed return"
- "expected return"
- "buy"
- "sell"
- "hold"

## Required Disclaimer

```text
This score is a model-estimated probability signal for research/scanning use and is not investment advice.
```

The disclaimer is the only approved appearance of the phrase
`investment advice`.

## Implementation

Contract helper:

```text
src/reports/v0_2_probability_wording.py
```

Standalone check:

```text
Quant_mvp/scripts/check_report_forbidden_wording.py
```

Tests:

```text
Quant_mvp/tests/test_report_wording_forbidden_prob_up_1d.py
```
