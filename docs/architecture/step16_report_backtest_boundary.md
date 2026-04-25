# Step 16 Report / Backtest Boundary

## Purpose

Step 16 reports are explanatory artifacts. They explain a per-security
technical snapshot that may include Step 15 ranking context, score context,
coverage status, data-quality status, adoption traceability, and diagnostic
limitations.

The required generated-report notice is:

```text
technical-only detail report
```

## One-Way Boundary

Allowed direction:

```text
Step 15 latest ranking output -> Step 16 detail report -> possible Step 17 backtest input later
```

Step 16 may later be consumed by Step 17 as input context. Step 16 does not
approve Step 17 and does not implement any Step 17 behavior.

Step 16 itself must not compute future returns, labels, hit rates, CAGR, MDD,
Sharpe, turnover, slippage, fees, or portfolio results.

Step 17 metrics must not flow backward into Step 16 wording, Step 15 ranking,
score definitions, normalization policy, adoption states, or report contracts.

## Allowed Step 16 Content

Step 16 may include:

- ticker, date, and as-of-date identifiers
- existing Step 15 technical ranking fields as read-only snapshot information
- technical composite and final composite display values from Step 15
- technical score details and normalized technical score context
- coverage, warmup, data-quality, and validity status
- adoption synthesis traceability
- diagnostic/context fields only as explanation or limitations

`rank` may be displayed only as Step 15 read-only context. Step 16 validation
must not create `new_rank`, `step16_rank`, re-rank columns, or rank deltas.

## Forbidden Step 16 Content

Step 16 must not introduce buy/sell/hold decisions.

Step 16 must not introduce PER/PBR/ROE or financial/fundamental scoring.

Step 16 must not include:

- forward returns or future returns
- realized return, realized PnL, or attribution
- backtest return, hit rate, CAGR, MDD, Sharpe, turnover, slippage, fees, or
  portfolio results
- strategy rules or trading signals
- target price, expected return, or position size
- valuation language such as cheap, bargain, undervalued, or value stock
- diagnostic/context scores described as direct alpha signals
- any new ranking or re-ranking output

## Generated Output Boundary

Generated per-security reports are runtime artifacts. They should be written
under `reports/security/generated/` unless a later source-controlled contract
assigns a different generated-output path.

Generated report files should not be committed by default. A small fixture may
be source-controlled only when a test or review explicitly promotes it and the
fixture documents that it is not canonical roadmap state.

## Validation Contract

`src/validation/step16_detail_report_guardrails.py` validates the Step 16
boundary without depending on a report generator implementation. The validator
is intentionally read-only with respect to Step 15 ranking data.

The validator must:

- reject future/performance/backtest fields
- reject valuation/fundamental fields
- reject trading signal fields
- require `technical-only detail report` on generated output text
- allow Step 15 fields only as technical-only display context
- treat diagnostic/context fields as context-only, not alpha evidence
- reject re-rank fields and changed rank values when input/output rank can be
  compared

This document does not close Step 16. It is Worker B guardrail and boundary
material for later master integration.
