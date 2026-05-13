# v1.0-rc EvaluationEvidenceV1 contract

Phase 6 adds `EvaluationEvidenceV1` as a candidate-only, evidence-only
contract. It consumes `HorizonPolicy`, `SimulationRunManifest`,
`WeightConfig` snapshots when present, optional `LayerRegistry` validation
status, and provided candidate-only simulation/backtest result summaries.

It does not alter production ranking, create recommendations, create trading
signals, claim future or expected returns, claim proven alpha, or activate
valuation/fundamental scoring.

## Metric policy

Allowed metrics are historical or simulated review summaries only. The
allowlist lives in `config/evaluation_evidence_v1.toml` and includes names
such as `realized_return_summary`, `realized_drawdown_summary`,
`realized_turnover_summary`, `coverage_ratio`, `invalid_period_count`, and
`missing_data_count`.

Blocked metric names include `expected_return`, `predicted_return`,
`future_return`, `alpha_signal`, `trade_signal`, `buy_score`, `sell_score`,
`guaranteed_return`, and `production_score`.

## Rebalancing disclosure

Historical or simulated rebalancing is allowed when it is part of the tested
strategy mechanics or materially affects candidate evidence. In that case
`rebalance_frequency`, `rebalancing_role`, and `rebalance_disclosure` must be
recorded. The disclosure is context for manual review, not a user instruction.

## Selector allowlist

Phase 7 may consume only the explicit `selector_feature_allowlist` fields in
`EvaluationEvidenceV1`. Raw future labels, live execution flags, order fields,
production ranking fields, and valuation/fundamental activation fields are
blocked as selector inputs.
