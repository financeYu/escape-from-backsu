# MVP v0.1 Freeze Record

Notice: kospi200_mvp_technical_scanner_v0_1_scope

## Freeze Decision

- Decision: GO
- Frozen version: KOSPI200 technical MVP v0.1
- Freeze timestamp: 2026-04-27T02:18:32+09:00
- Baseline commit before freeze record: `f7c3734`
- Freeze commit: recorded by the commit that adds this file.

## Frozen Scope

- Universe: KOSPI200 only.
- Data basis: daily OHLCV-derived technical and statistical fields.
- Scanner type: explainable technical multi-score latest ranking scanner.
- Ranking score: technical-only `final_composite_score`.
- `final_composite_score` equals `technical_composite_score` for MVP v0.1.

## Preserved Boundaries

- Valuation/fundamental scoring remains inactive.
- Financial/fundamental data must not enter `technical_composite_score`.
- Financial/fundamental data must not enter `final_composite_score`.
- Backtest output remains evaluation-only and must not feed upstream scoring or
  ranking.
- Generated reports, runtime outputs, chart images, local caches, raw market
  data, `.env`, and secrets are not part of the frozen source baseline.

## Post-Freeze Version Rule

MVP v0.1 is no longer a moving target. Any change to score formulas, weights,
adoption state, normalization, ranking semantics, report semantics, backtest
semantics, valuation/fundamental activation, data ingestion, or universe scope
must be managed as a separately approved post-MVP version/Step.

Allowed post-freeze work on the v0.1 line is limited to documentation
clarification, reproducibility notes, tests that prove the frozen behavior, or
bug fixes that preserve the frozen contracts and pass the required review gate.

## Explicitly Blocked From MVP v0.1

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Valuation-aware scoring, target-price logic, or trading recommendations.
- Backtest-driven score optimization or performance claims.
- Buy/sell/hold, proven-alpha, market-beating, or expected-return wording.

## Evidence Reviewed

- `docs/context/MVP_V0_1_BASELINE.md`
- `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- `docs/contracts/step20_composite_contract.md`
- `docs/contracts/step20_ranking_contract.md`
- `docs/releases/mvp_kospi200_baseline_manifest.md`
- `docs/releases/step20_mvp_final_report.md`
- `docs/release/MVP_V0_1_VALIDATION_LADDER.md`

## Validation Profile

The freeze patch must pass:

- Tier 1 context/guardrail validation.
- Cross-step conflict checkpoint for the freeze stage.
- `git diff --check`.

Broader scanner, integration, or full-suite validation is required only if the
freeze patch changes runtime behavior, score/ranking/report contracts, or
generated-output boundaries.

## Known Limitations

- MVP v0.1 does not prove investment performance.
- Local live market-data cache presence is not assumed by the frozen baseline.
- Valuation/fundamental data remains candidate-only and inactive.
- Post-MVP universe expansion remains separate.

## Next Allowed Step

Future work must open a separately approved post-MVP version/Step with routed
context, correct branch/worktree, and conflict checkpoint before changing the
frozen MVP v0.1 semantics.

COMPLETE
