# Root Hard Stops

Latest-only root summary for task start. Routing aid only; it does not replace
`AGENTS.md`, `docs/project_checklist.md`, or `docs/roadmap_status.md`.

## Authority Order

1. User's latest explicit instruction.
2. `AGENTS.md`.
3. `docs/project_checklist.md` for root policy and roadmap-order authority.
4. `docs/roadmap_status.md` for current latest-only status.
5. Active packet, affected subproject `AGENTS.md`, and targeted files.

`docs/project_checklist.md` has historical pre-freeze Step detail. Read its
long body only for named roadmap, hard-stop, provenance, regression, or release
evidence questions.

## Current Baseline

- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.
- Post-MVP `v0.2 predictive probability score route` Step is active for the
  approved candidate-only implementation of `prob_up_1d_candidate` in a
  separate role branch/worktree.
- The active Step authorizes only the scoped feature table, label-separated
  training/evaluation pipeline, candidate probability output, and validation
  tests. It does not authorize production ranking activation, report behavior
  changes, trading recommendations, `final_composite_score` replacement,
  backtest metrics as model features, valuation/fundamental scoring, data
  ingestion changes, or universe expansion.

## Forbidden Scope Without Explicit Approval

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Runtime score formula, weight, adoption, normalization, ranking, report,
  backtest, or valuation semantic changes outside the approved
  `prob_up_1d_candidate` candidate-only implementation scope.
- Financial/fundamental data in `technical_composite_score` or
  `final_composite_score`.
- Backtest feedback into scoring/ranking or model feature construction.
- Trading recommendations, buy/sell/hold, proven-alpha, or expected-return wording.

## Archive Read Gate

Completed Step 1-20 outputs are trusted. Read archives, old Step detail, logs,
generated packets, raw data, caches, charts, or runtime reports only for named
conflict, regression, provenance, or release/freeze verification. Start from
`docs/context/ARCHIVE_INDEX.md`.

## Generated Output Boundary

Generated reports, runtime outputs, charts, caches, raw data, `.env`, and
secrets are not default context or source-controlled unless promoted as small
review fixtures.

## Step-End Status

At the end of a Step or assigned gate, report exactly one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`
