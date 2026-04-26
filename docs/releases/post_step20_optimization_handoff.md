# Post-Step20 Optimization Handoff

Status: implementation handoff for root/master review
Branch: `codex-step20-post-mvp-optimization`
Scope: five user-requested optimizations after Step 20 COMPLETE

This handoff is intentionally compact so root/master does not repeat the same
investigation or implementation pass. Completed Step 1-20 artifacts remain
trusted by default.

## Hard-Stop Summary

- No score formula changed.
- No score weight changed.
- No `technical_composite_score` or `final_composite_score` semantic changed.
- No valuation/fundamental scoring activated.
- No financial/fundamental data entered technical or final composite scoring.
- No backtest return feedback entered upstream scoring/ranking.
- No KOSDAQ150, futures, options, multi-universe, or new external data source was added.
- No trading recommendation or proven-alpha claim was added.

## Completed Optimization Items

| Item | Result | Primary changed files |
| --- | --- | --- |
| 1. Legacy/canonical ranking boundary | `chart_mvp` Top-N output now carries `runtime_boundary_notice`; meta points canonical ranking to root `src.scanner.latest_ranking`; README and temporary override clarify the legacy boundary. | `chart_mvp/src/stock_core/ranking/scorer.py`, `chart_mvp/src/stock_core/pipeline/daily_update.py`, `chart_mvp/src/stock_core/ranking/selector.py`, `chart_mvp/README.md`, `chart_mvp/TEMPORARY_TOP5_OVERRIDE.md` |
| 2. Naver I/O separation | Price refresh no longer refreshes financial statements by default; statement refresh remains opt-in through `refresh_financials=True` or dedicated financial-cache script. | `chart_mvp/src/stock_core/cache/csv_cache.py`, `chart_mvp/src/stock_core/providers/naver_price_provider.py`, `chart_mvp/tests/test_naver_finance.py` |
| 3. Chart refetch avoidance | Chart rendering reuses already processed indicator rows when they cover the chart display window; it fetches only when processed rows are insufficient. | `chart_mvp/src/stock_core/pipeline/daily_update.py`, `chart_mvp/tests/test_pipeline.py` |
| 4. Windows temp validation | Added local validation runner that sets `TMP`, `TEMP`, `PYTEST_DEBUG_TEMPROOT`, and pytest `--basetemp` under `.pytest_tmp/local_validation/`; shortened sandbox temp fixture names with a deterministic hash to avoid Windows path-length failures. | `scripts/run_local_validation.py`, `tests/context/test_local_validation_runner.py`, `docs/development_environment.md`, `conftest.py` |
| 5. Step16/17 scaling overhead | Step16 bulk report generation prepares metadata once per call; Step17 price lookup uses binary search instead of full boolean scan. | `src/reports/security_detail_report.py`, `tests/reports/test_step16_security_detail_report.py`, `src/backtest/engine.py` |

## Validation To Run

Use the local validation runner where possible to avoid repeating temp-root
permission debugging:

```powershell
python scripts/run_local_validation.py chart
python scripts/run_local_validation.py context
python scripts/run_local_validation.py reports-backtest
python scripts/context/check_context_staleness.py
python scripts/context/check_context_conflicts.py
python scripts/build_review_packet.py --step "Post-Step20" --stage "post-mvp-optimization"
git diff --check
```

## Validation Results In This Worktree

- `python scripts/run_local_validation.py chart`: 52 tests passed.
- `python scripts/run_local_validation.py context`: 28 tests passed.
- `python scripts/run_local_validation.py reports-backtest`: 94 tests passed.
- `python scripts/run_local_validation.py full`: 728 passed, 4 skipped, 25 subtests passed.
- `python scripts/context/check_context_staleness.py`: no warnings.
- `python scripts/context/check_context_conflicts.py`: no findings.
- `python scripts/build_review_packet.py --step "Post-Step20" --stage "post-mvp-optimization"`: generated compact review packet.
- `python review_mvp/review.py ... --fail-on medium`: 0 high, 0 medium; 7 low single-responsibility notes only.
- `git diff --check`: pass after manifest EOF cleanup.

## Residual Risks

- `chart_mvp` still has a legacy placeholder score path by design. This patch
  labels that path clearly; it does not replace it with Step 20 ranking logic.
- Financial statement refresh remains available but opt-in. Operators who need
  fresh statement inventory should run `chart_mvp/scripts/refresh_financial_cache.py`.
- Step17 selection/return semantics are intended to be unchanged; validation
  should focus on existing backtest tests rather than new performance claims.

## Root/Master Review Shortcut

Root/master can review this branch by checking:

1. The hard-stop summary above.
2. The five-row completed item table.
3. The validation outputs listed above.
4. The diff for the listed primary files only, unless a validation failure
   points elsewhere.

No archive or full completed-Step history reread is needed for this patch.
