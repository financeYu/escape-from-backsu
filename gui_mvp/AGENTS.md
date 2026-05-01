# gui_mvp Agent

## Purpose

`gui_mvp` owns local desktop GUI surfaces that coordinate existing project
APIs without changing their domain semantics.

Current scope:

- chart Top-N viewer extracted from `chart_mvp`
- archived Step 17 conservative backtest evaluation viewer, maintained only as
  an assigned compatibility surface

`gui_mvp` currently runs from the repository checkout. Do not broaden package
metadata or make standalone installation claims unless chart runtime packaging
is explicitly assigned.

## Boundaries

This module may display existing outputs and call existing runtime APIs, but it
must not:

- redefine score formulas, weights, normalization, ranking, reports, backtest
  semantics, valuation, or data ingestion
- feed backtest results into upstream scoring or ranking
- treat chart runtime `latest_top*` outputs as canonical archived Step 20
  ranking evidence or current v0.3 adoption evidence
- activate valuation/fundamental scoring or mix financial data into
  `technical_composite_score` or `final_composite_score`
- commit generated chart images, market caches, runtime reports, secrets, or
  local output files

## Compatibility

`chart_mvp/app/run_gui.py` remains a thin compatibility wrapper for existing
`python -m app.run_gui` users. New direct entrypoints should use:

```powershell
python -m gui_mvp chart
python -m gui_mvp backtest
```

## Verification

Use focused tests for GUI helper functions and import compatibility:

```powershell
python -m pytest -q -p no:cacheprovider tests/gui_mvp chart_mvp/tests/test_gui_financials.py
```
