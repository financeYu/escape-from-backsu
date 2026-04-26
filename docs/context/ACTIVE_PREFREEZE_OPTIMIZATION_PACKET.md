# Active Pre-Freeze Optimization Packet

This packet is a routing aid, not an authority document. It does not override
`AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`, the active
`WORKSPACE_MANIFEST.md`, or the user's latest instruction.

## Task

- task: `prefreeze_optimization`
- step label: Step 20.5
- status: post-Step20 pre-freeze optimization patch
- objective: make MVP v0.1 easier to preserve, explain, validate, and extend
  later with minimal context overhead.
- quant logic: this patch does not change quant logic, score formulas, score
  weights, ranking behavior, backtest logic, valuation activation, or data
  ingestion behavior.

## Allowed Scope

- Compact default baseline documentation.
- One active packet for current pre-freeze work.
- Context budget policy and targeted routing index.
- Release quickstart and validation ladder documentation.
- Context/release documentation tests under `tests/context/`.
- Context checker reference updates only when needed for renamed docs.

## Forbidden Scope

- Quant score formula, score weight, or indicator logic changes.
- `technical_composite_score` or `final_composite_score` semantic changes.
- Ranking sort, tie-break, neutral shrinkage, or report generation logic changes.
- Backtest logic changes or backtest-driven score optimization.
- Valuation/fundamental scoring activation.
- Data ingestion, KOSDAQ150, futures, or options implementation.
- Trading recommendation language or proven-alpha/performance claims.

## Files Allowed For Edit

- `docs/context/**`
- `docs/release/**`
- `scripts/context/**`
- `tests/context/**`
- `WORKSPACE_MANIFEST.md` only if workspace role identity needs an update.

## Inspect Only If Needed

- `docs/architecture/**`
- `docs/roadmap_status.md`
- `docs/project_checklist.md`
- `docs/contracts/**`
- `docs/releases/**`

## Do Not Edit Unless A Tiny Path-Reference Fix Is Required

- `src/scoring/**`
- `src/scanner/**`
- `src/reports/**`
- `src/backtest/**`
- `src/valuation/**`
- `src/pipeline/**`

If any tiny path-reference fix is required, document why it is not a logic
change before editing.

## Validation Commands

- `python -m pytest -q tests/context`
- `python scripts/context/check_context_staleness.py`
- `python scripts/context/check_context_conflicts.py`

Run broader release checks only after focused context checks pass.

## Rollback Criteria

- Any quant/scoring/ranking/backtest/valuation/data-ingestion logic changes.
- Any default context file embeds long Step 1-20 history.
- Any archive file becomes default-read context.
- Any release doc implies a trading recommendation or performance proof.
- Any context checker reports unresolved staleness or conflict findings.

## Completion Criteria

- Required baseline, active packet, budget policy, routing index, quickstart,
  and validation ladder exist.
- Required docs respect line limits.
- Tests cover line limits, archive-only history, default context shape, routing
  hygiene, release wording, and archive route exclusion.
- Focused context tests and context checker scripts pass.
- Final report confirms no quant/scoring/ranking/backtest/valuation/data
  ingestion logic changed.

## Archive Lookup Conditions

Read archive/history only for a named conflict investigation, regression
investigation, provenance check, or release/freeze verification. Use the
narrowest archive file and do not copy archive bodies into default context.
