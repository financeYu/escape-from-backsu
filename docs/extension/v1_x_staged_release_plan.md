# v1.x Staged Release Plan

This document opens the post-v1.0 development route after the local v1.0
freeze. It is a planning and checklist packet for staged v1.x evidence-only
releases. It does not authorize production activation, live trading, brokerage
integration, order generation, buy/sell/hold wording, automatic rebalance
instructions, production ranking replacement, future-return claims, or
proven-alpha language.

## Route Goal

Prioritize a fast historical or simulated net profitability display first, then
improve reliability through ML comparison, cost/liquidity, revision,
valuation/quality, and confidence layers.

All outputs remain:

- evidence-only
- candidate-only
- manual-review-support only
- bounded by local historical or simulated evidence
- blocked from automatic production activation

## Version Plan

| Version | Stage | Primary output | Owner lane | Status |
| --- | --- | --- | --- | --- |
| v1.1 | net profitability evidence runner | historical/simulated net profitability display packet | backtest/simulation | complete |
| v1.2 | baseline ML selector application | baseline selector comparison packet | ML/evaluator | complete |
| v1.3 | cost/turnover/liquidity reliability layer | reliability adjustment and sensitivity packet | backtest/simulation + quant governance | implemented with liquidity data gaps reported |
| v1.4 | point-in-time revision layer | point-in-time revision evidence packet | quant governance + data-support lane | temporary complete / diagnostic-only closure; KIS raw snapshots continue as data support only |
| v1.5 | point-in-time valuation + quality/profitability layer | candidate-only valuation, quality, and profitability evidence packet | quant governance | planned |
| v1.6 | confidence/robustness/review-priority integration | confidence and manual review priority packet | ML/evaluator + root governance | planned |
| v2.0 readiness | readiness packet | v2.0 readiness packet with unresolved blockers | root governance | planned |

## Stage Checklist

Each v1.x stage must produce the same compact completion packet:

- changed files
- generated artifacts
- tests run
- guardrail result
- skipped items with reason
- completion verdict
- next stage recommendation

The completion verdict must be one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`

## v1.1 Checklist

Goal: produce the fastest useful historical or simulated net profitability
display without implying a trade signal.

- [x] Confirm input artifacts are approved local historical or simulated
  evidence inputs.
- [x] Add or reuse a minimal net profitability evidence runner.
- [x] Include gross result, cost/slippage assumptions, net result, turnover,
  drawdown, volatility, and benchmark-relative context when available.
- [x] Label all outputs as evidence-only and manual-review-support.
- [x] Block buy/sell/hold wording, order language, and future-return claims.
- [x] Run targeted tests and guardrail wording checks.
- [x] Produce the v1.1 completion packet.

## v1.2 Checklist

Goal: apply a baseline ML selector as a comparison layer only.

- [x] Consume allowlisted v1.1/v0.x evidence summaries read-only.
- [x] Keep labels, features, and evaluation windows separated.
- [x] Compare baseline ML selector output against rule or non-ML baseline
  evidence.
- [x] Emit review-prioritization evidence only, not a runtime rank
  replacement.
- [x] Preserve no-lookahead and no-feedback checks.
- [x] Run targeted ML/evaluator tests and guardrail wording checks.
- [x] Produce the v1.2 completion packet.

## v1.3 Checklist

Goal: improve reliability with cost, turnover, and liquidity sensitivity.

- [x] Add explicit cost, turnover, and liquidity assumptions to the evidence
  path.
- [x] Add candidate-level liquidity handoff rows for every evidence candidate.
- [x] Show sensitivity or degradation ranges where supported by local evidence.
- [x] Keep outputs descriptive and review-oriented.
- [x] Block automatic rebalance instructions and production execution language.
- [x] Run targeted reliability-layer tests and guardrail wording checks.
- [x] Produce the v1.3 completion packet.

## v1.4 Checklist

Goal: add a point-in-time revision layer before stronger claims are considered.

- [ ] Identify which fields require point-in-time revision handling.
- [x] Draft the revision data contract and required data list.
- [x] Fail closed when revision provenance or as-of timing is missing.
- [x] Separate available, failed, and unavailable revision evidence states.
- [x] Build chart_mvp diagnostic-only handoff from existing local financial caches.
- [x] Preserve point-in-time checks in validators or packet metadata.
- [x] Run targeted point-in-time skeleton tests and guardrail wording checks.
- [x] Produce a temporary v1.4 diagnostic-only closure packet that preserves
  the missing PIT data list and blocks feature/incremental-evidence use.
- [ ] Produce the full v1.4 completion packet after approved PIT revision
  source coverage and incremental comparison.

Temporary closure rule: KIS revision raw snapshots may continue to accumulate
through the daily chart refresh, but downstream v1.5/v1.6 work must not read
those raw snapshots as revision features, scores, rankings, valuation inputs,
or incremental evidence until a later explicit PIT promotion review passes.

## v1.5 Checklist

Goal: add point-in-time valuation plus quality/profitability evidence as
candidate-only review support.

- [ ] Require point-in-time availability proof before any valuation,
  quality, or profitability field is used.
- [ ] Keep valuation/fundamental outputs candidate-only and inactive for
  production ranking.
- [ ] Separate valuation, quality, profitability, and price-only evidence.
- [ ] Block valuation/fundamental scoring activation.
- [ ] Run targeted valuation/quality/profitability tests and guardrail wording
  checks.
- [ ] Produce the v1.5 completion packet.

## v1.6 Checklist

Goal: integrate confidence, robustness, and review priority without replacing
production ranking.

- [ ] Combine only allowlisted evidence summaries from v1.1 through v1.5.
- [ ] Represent confidence as review support, not certainty or proven alpha.
- [ ] Include robustness gaps, skipped evidence, and manual review priority.
- [ ] Block future-return claims and production ranking replacement.
- [ ] Run targeted integration tests and guardrail wording checks.
- [ ] Produce the v1.6 completion packet.

## v2.0 Readiness Packet Checklist

Goal: summarize whether staged v1.x evidence is sufficient for a later v2.0
decision.

- [ ] Summarize all v1.1 through v1.6 completion packets.
- [ ] Separate completed evidence, unresolved blockers, skipped items, and
  reliability gaps.
- [ ] State whether readiness is available or unavailable from evidence.
- [ ] Recommend the single highest-priority next stage or blocker fix.
- [ ] Avoid production activation, release, push, trading, or execution
  language unless separately approved.

## Guardrail Checklist

Every v1.x stage must keep these blocked:

- live trading
- brokerage integration
- orders or order generation
- buy/sell/hold wording
- automatic rebalance instructions
- move-to-cash commands
- production ranking replacement
- future-return claims
- proven-alpha language
- valuation/fundamental scoring activation before the v1.5 point-in-time proof
  contract is satisfied and separately approved for use
- new market-data ingestion or universe expansion without separate approval

## Git Policy

Use local Git only during staged work. Do not fetch, pull, push, stage, or
commit unless the active task or end-stage instruction explicitly asks for it.
