# Step 17 Conservative Backtest Reports

This directory is reserved for Step 17 generated conservative backtest report
artifacts.

Intended generated report directory:

```text
reports/backtest/generated/
```

Generated backtest reports are runtime evaluation artifacts. They are not
canonical score definitions, ranking sources, adoption sources, trading signal
sources, roadmap status, or valuation/fundamental scoring outputs. In short:
generated backtest reports are not canonical score definitions. Do not commit
generated report files by default unless a small fixture is explicitly promoted
for tests or review.

Required report notices:

- evaluation-only
- not a trading recommendation
- does not redefine score or ranking formulas
- technical-only upstream ranking context
- valuation/fundamental scoring remains gated until Step 18

## Allowed Content

- frozen Step 15/16 technical-only ranking or report context
- evaluation dates, execution date, exit date, and conservative timing notes
- Step 17 output-only return fields such as `realized_holding_return`,
  `backtest_period_return`, and `evaluation_return`
- transaction cost and slippage assumptions
- explicit `limitation_flags`
- generated-output boundary notes

## Required Limitation Disclosures

Every generated Step 17 report must disclose applicable conservative
limitations, including:

- survivorship bias if PIT constituent membership is unavailable
- corporate action / adjusted price uncertainty when applicable
- missing execution or exit price handling
- transaction cost and slippage assumptions
- no valuation/fundamental data used
- no return feedback into upstream scores

## Forbidden Content

Step 17 reports must not:

- present a backtest as score adoption evidence
- redefine score, ranking, adoption, or composite formulas
- create buy/sell/hold signals or trading recommendations
- claim alpha proof, profitability, tradability, or target prices
- call a security cheap, undervalued, or a bargain
- use PER/PBR/ROE, market cap fundamentals, or valuation/fundamental scoring
- feed realized returns back into Step 13 review status, Step 14 adoption
  state, Step 15 ranking input, or Step 16 detail report score context

Step 18 remains the only future roadmap area for valuation/fundamental
expansion preparation.
