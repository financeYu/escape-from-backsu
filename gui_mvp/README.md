# gui_mvp

Local desktop GUI module for post-MVP viewers.

This module is intended to run from the repository checkout. The chart viewer
depends on `chart_mvp/src/stock_core` and is not packaged as a standalone wheel.

Run the unified tabbed GUI:

```powershell
python -m gui_mvp
```

The unified GUI separates the current chart workflow and conservative backtest
evaluation into these tabs:

- `현재 주가 기준`
- `백테스트 전용`

Run the extracted chart Top-N viewer directly:

```powershell
python -m gui_mvp chart
```

The backtest tab is display-only. It calls `Quant_mvp.backtest_mvp` and keeps
realized returns inside Step 17 result objects; it does not update scoring,
ranking, reports, or configuration.
