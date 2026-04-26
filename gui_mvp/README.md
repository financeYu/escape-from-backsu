# gui_mvp

Local desktop GUI module for post-MVP viewers.

This module is intended to run from the repository checkout. The chart viewer
depends on `chart_mvp/src/stock_core` and is not packaged as a standalone wheel.

Run the extracted chart Top-N viewer:

```powershell
python -m gui_mvp chart
```

Run the conservative backtest evaluation viewer:

```powershell
python -m gui_mvp backtest
```

The backtest viewer is display-only. It calls `src.backtest` and keeps realized
returns inside Step 17 result objects; it does not update scoring, ranking,
reports, or configuration.
