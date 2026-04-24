"""Scoring interfaces for batch stock ranking."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScoreContext:
    code: str
    name: str
    source: str


class StockScorer:
    """Placeholder interface for future ranking strategies."""

    def score(self, df: pd.DataFrame, context: ScoreContext) -> float:
        raise NotImplementedError

