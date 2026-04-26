"""Placeholder ranking scorer for the legacy chart runtime."""

from __future__ import annotations

import pandas as pd


LEGACY_PLACEHOLDER_SCORE_NOTICE = (
    "chart_mvp_legacy_placeholder_score_not_step20_canonical_ranking"
)


def score_stock(df: pd.DataFrame) -> float:
    """Return a placeholder score for the legacy chart runtime.

    The canonical post-Step20 ranking path lives under the repository root
    `src.scanner` modules. This function remains only for the local legacy
    chart/Top-N runner and must not be treated as Step 20 ranking evidence.
    """

    _ = df
    return 0.0


__all__ = ("LEGACY_PLACEHOLDER_SCORE_NOTICE", "score_stock")
