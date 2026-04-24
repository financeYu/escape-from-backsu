# Valuation Agent Examples

이 문서는 메인 `AGENTS.md`에서 밸류 전담 에이전트를 분리한 뒤, 언제 어떤 식으로 별도 밸류 에이전트를 써야 하는지 보여주는 예시입니다.

## 핵심 원칙

메인 에이전트는 기술적 스코어 설계, 구현, 진단, 선택을 담당합니다.
밸류 판단은 `agents/valuation/AGENTS.md`의 별도 에이전트가 담당합니다.

가격 기반 약세, 낙폭, RSI 과매도, 이동평균 이격은 밸류가 아닙니다.
밸류 판단에는 point-in-time 재무 데이터와 명시적인 공시 지연 규칙이 필요합니다.

---

## 예시 1: 메인 에이전트가 처리하면 안 되는 요청

사용자 요청:

```text
최근 많이 빠진 종목을 저평가 점수로 만들어줘.
```

메인 에이전트의 올바른 반응:

```text
이 요청은 가격 기반 낙폭을 밸류로 해석하고 있습니다.
drawdown은 기술적 또는 리스크 진단 feature일 수 있지만 valuation score는 아닙니다.
밸류 판단이 필요하면 point-in-time fundamental data를 확인한 뒤 별도 valuation agent로 넘겨야 합니다.
```

판정:
- 메인 에이전트: `reject as valuation`
- 가능한 대안: `technical drawdown / mean-reversion diagnostic`
- 밸류 에이전트 호출: 아직 불필요

---

## 예시 2: 별도 밸류 에이전트로 넘겨야 하는 요청

사용자 요청:

```text
KOSPI200 종목에 earnings yield 기반 밸류 점수를 추가하고 싶어.
```

메인 에이전트의 올바른 반응:

```text
earnings yield는 valuation branch에 속하므로 별도 valuation agent에서 검토해야 합니다.
먼저 point-in-time earnings, market cap, filing date, stale-data policy가 있는지 확인해야 합니다.
```

밸류 에이전트가 확인할 항목:
- `ttm_net_income_pti`
- `market_cap_t`
- `filing_date` 또는 `effective_date`
- `filing_lag_days`
- 음수 이익 처리 정책
- 섹터 왜곡 여부

가능한 밸류 에이전트 출력:

```yaml
score_name: earnings_yield
score_family: value
valuation_status: partially_available
valuation_verdict: blocked_by_data
valuation_comment: filing lag policy is missing, so point-in-time safety is not established
```

---

## 예시 3: 데이터가 있을 때만 가능한 요청

사용자 요청:

```text
book-to-price와 gross profitability를 같이 써서 밸류 composite을 만들어줘.
```

밸류 에이전트의 판단 순서:

1. `common_equity_pti`가 있는지 확인합니다.
2. `gross_profit_pti`와 `sales_pti`가 있는지 확인합니다.
3. 두 지표의 공시일 또는 유효일이 point-in-time으로 정리되어 있는지 확인합니다.
4. 섹터별 왜곡을 raw score와 별도로 다룰지 결정합니다.
5. value score와 quality/profitability adjustment를 섞되, 역할을 분리해서 출력합니다.

좋은 출력 방향:

```yaml
valuation_status: available
valuation_verdict: conditional
valuation_comment: usable only after stale fundamental observations are invalidated and sector-neutral diagnostics are reported
```

---

## 예시 4: 기술 + 밸류 결합 요청

사용자 요청:

```text
기술 composite이 높은데 밸류도 싼 종목만 최종 후보로 보고 싶어.
```

올바른 처리:

```text
먼저 메인 기술 에이전트가 technical_composite_score를 만듭니다.
그 다음 별도 valuation agent가 valuation_composite_score를 만듭니다.
마지막 adoption synthesis에서 두 결과를 명시적으로 결합합니다.
```

주의점:
- 기술 에이전트가 밸류 점수를 임의로 만들면 안 됩니다.
- 밸류 에이전트가 기술 점수를 임의로 재해석하면 안 됩니다.
- 결합 규칙은 config에 있어야 하며 코드에 하드코딩하면 안 됩니다.

---

## 예시 5: 밸류 에이전트를 호출하지 않아도 되는 요청

사용자 요청:

```text
RSI divergence와 Donchian breakout의 중복도를 점검해줘.
```

처리:
- 메인 기술 에이전트가 처리합니다.
- 밸류 에이전트는 호출하지 않습니다.
- 필요한 출력은 technical redundancy diagnostic입니다.

---

## 기억할 문장

```text
싸 보이는 가격 움직임은 밸류가 아니다.
밸류는 point-in-time 재무 데이터가 있을 때만 판단한다.
기술 에이전트는 밸류를 만들지 않고, 밸류 에이전트는 기술 신호를 재포장하지 않는다.
```
