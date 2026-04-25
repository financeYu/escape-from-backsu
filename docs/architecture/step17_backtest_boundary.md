# Step 17 Backtest Boundary

## Role

Step 17 is a conservative evaluation layer. It may consume frozen technical-only
Step 15/16 context and produce backtest-specific evaluation artifacts, but it
does not own score design, ranking design, adoption decisions, valuation
analysis, or trading recommendations.

Allowed direction:

```text
Step 15 latest ranking output
-> Step 16 technical-only detail report context
-> Step 17 conservative backtest evaluation output
```

Forbidden reverse direction:

```text
Step 17 realized/evaluation return
-> Step 13 review_status
-> Step 14 adoption_state
-> Step 15 ranking input or composite fields
-> Step 16 detail report score context
```

## Generated Output Boundary

Step 17 reports belong under `reports/backtest/generated/` by default. They are
generated-output artifacts, not canonical repository state. Source-controlled
fixtures require explicit test/review promotion and must preserve the
evaluation-only boundary notice.

## Valuation Boundary

Step 18 remains the only future roadmap area for valuation/fundamental
expansion preparation. Step 17 must not use financial statements, PER, PBR, ROE,
market cap fundamentals, valuation scores, or fundamental scores.

## Conservative Assumptions

Backtest reports must disclose conservative assumptions and unresolved data
limits, including survivorship bias, adjusted price uncertainty, missing
execution or exit price handling, transaction cost and slippage assumptions,
no valuation/fundamental data use, and no return feedback into upstream scores.
