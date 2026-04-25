# Step 18 Valuation / Fundamental Candidate Report

This is Step 18 candidate valuation/fundamental expansion.
These fields are not activated in final ranking.
These fields are not validated alpha signals.
These fields must not be used in backtests unless availability-date rules are enforced.

## Scope

- candidate-only explanatory data
- no technical score changes
- no final ranking changes
- no backtest usage without availability-date validation

## Current Source-Controlled Snapshot

- Candidate schema: `src/valuation/contracts.py`
- Candidate registry: `config/valuation_fundamental_metrics.toml`
- Candidate validation: `src/valuation/validation.py`
- Production boundary guardrails: `src/validation/step18_valuation_fundamental_guardrails.py`

No live or external financial data is included in this report.
