# MVP v0.1 Baseline

This file is the compact default baseline after Step 20. It is a routing aid,
not an authority document.

## Current Version

- Version: KOSPI200 technical MVP v0.1 frozen baseline.
- Status: Step 20 COMPLETE; MVP v0.1 is frozen.
- Git baseline: `f7c3734` before the freeze-record commit.
- Freeze record: `docs/releases/mvp_v0_1_freeze_record.md`.

## Authority Order

1. User's latest explicit instruction.
2. `AGENTS.md`.
3. `docs/project_checklist.md`.
4. `docs/roadmap_status.md`.
5. Active packet and targeted routing docs.

## Score Contract

- MVP universe is KOSPI200 only.
- Inputs are daily OHLCV-derived technical/statistical fields.
- `technical_composite_score` is technical-only.
- `final_composite_score` equals `technical_composite_score` for MVP v0.1.
- Missing direct score inputs shrink to neutral `0.0`.
- No financial/fundamental data enters technical or final composite scoring.

## Ranking Contract

- Latest ranking uses one same-date eligible snapshot.
- Higher `final_composite_score` ranks better.
- Ties are deterministic by ticker ascending.
- Blocked rows receive no rank and sort after rankable rows.
- Ranking context exposes coverage, warmup, validity, neutral shrinkage, direct
  components, family scores, and a technical-only notice.

## Boundaries

- Valuation/fundamental: candidate-only and inactive.
- Backtest: evaluation-only; results must not feed upstream scoring or ranking.
- Reports: explanatory technical context only.
- Generated outputs, caches, charts, and local reports are not default context.
- Future changes are managed as separately approved post-MVP versions/Steps, not
  as modifications to MVP v0.1.

## Out Of Scope

- KOSDAQ150, futures, options, and multi-universe ranking.
- New score formulas, weights, ranking semantics, or data ingestion.
- Valuation-aware scoring, target-price logic, or trading recommendations.
- Backtest-driven score optimization or performance claims.

## Validation Summary

- Step 20 context tests: passed.
- Scanner/report/validation focused tests: passed.
- Integration tests: passed.
- Full pytest suite: passed at Step 20 final integration.
- Context staleness/conflict checks: passed.
- `review_mvp` Step 20 specialist review: 0 high, 0 medium findings.

## Targeted Lookup

- Release evidence: `docs/releases/`.
- Freeze record: `docs/releases/mvp_v0_1_freeze_record.md`.
- Contracts: `docs/contracts/step20_composite_contract.md`,
  `docs/contracts/step20_ranking_contract.md`.
- Archive/provenance: on-demand only.
