# v1.1 Net Profitability Evidence Runner

This document records the v1.1 evidence runner contract opened by
`docs/extension/v1_x_staged_release_plan.md`.

The runner answers whether current candidates and review-priority selector
scores can be summarized into reproducible historical or simulated net
profitability evidence. It is evidence-only, candidate-only, and
manual-review-support only.

It does not authorize live trading, brokerage integration, order generation,
buy/sell/hold wording, production ranking replacement, automatic rebalance
instructions, future-return claims, proven-alpha language, or production
activation.

## Implementation

- Module: `Quant_mvp/backtest_mvp/net_profitability_runner_v1.py`
- Test: `tests/backtest/test_v1_1_net_profitability_runner.py`
- Owner lane: Quant backtest/simulation
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`

## Inputs

Input records are already-approved historical or simulated candidate summaries.
Each record must provide:

- `candidate_id`
- `selector_score`
- `gross_return`
- `benchmark_return`
- `turnover`
- `volatility`
- `max_drawdown`
- `date_range`
- `leakage_check_status` with value `pass`
- `no_lookahead_check_status` with value `pass`

Cost and slippage can be supplied per record or through
`NetProfitabilityRunnerConfig`. The runner computes net evidence as:

```text
net_return = gross_return - turnover * (cost_rate + slippage_rate)
```

The runner fails closed when lineage-critical fields are missing. In
particular, `date_range.start`, `date_range.end`, `leakage_check_status`, and
`no_lookahead_check_status` must come from the approved input summary rather
than being inferred by the runner.

## Outputs

The runner emits these artifact keys:

- `v1_1_net_profitability_evidence_runner`
- `v1_1_top_k_profitability_report`
- `v1_1_cost_turnover_summary`
- `v1_1_manual_review_profitability_packet`
- `v1_1_validation_manifest`
- `v1_1_top_decile_profitability_report`
- `evaluation_evidence_v1`
- `selector_score_manifest`

`evaluation_evidence_v1` is built through the existing
`EvaluationEvidenceV1` contract. Manual review packets are built through the
existing `ManualReviewPacket` contract.

## Completion Criteria

v1.1 is complete when:

- the same config, seed, and candidate inputs produce the same run id and
  metric outputs
- net return, benchmark-relative net return, max drawdown, Sharpe-like
  historical summary, turnover, and cost drag are emitted
- top-k and top-decile candidate groups are summarized net of cost
- lineage connects `HorizonPolicy -> SimulationRunManifest ->
  EvaluationEvidenceV1`
- guardrails block order, buy/sell/hold, production ranking replacement,
  automatic rebalance instructions, future-return claims, and proven-alpha
  language
- runner unit tests, fixture tests, and guardrail/language tests pass

## Completion Statement

The current frozen structure can repeatedly generate candidate-level
historical or simulated net profitability evidence from the same config, seed,
and candidate manifest inputs.
