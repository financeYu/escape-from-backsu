"""Placeholder scoring implementation."""

from __future__ import annotations

import pandas as pd

from stock_core.ranking.base import ScoreContext, StockScorer


class ZeroScorer(StockScorer):
    """Return 0.0 for every stock while keeping the pipeline operational."""

    def score(self, df: pd.DataFrame, context: ScoreContext) -> float:
        _ = (df, context)
        return 0.0

