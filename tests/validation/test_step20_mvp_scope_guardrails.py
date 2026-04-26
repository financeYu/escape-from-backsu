from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.step20_mvp_scope_guardrails import (  # noqa: E402
    STEP20_MVP_SCOPE_NOTICE,
    validate_step20_mvp_scope_columns,
    validate_step20_mvp_scope_frame,
    validate_step20_mvp_scope_text,
    validate_step20_release_report_text,
)


def test_scope_columns_reject_post_mvp_universe_and_valuation_activation() -> None:
    for column in ("kosdaq150_rank", "futures_signal", "valuation_score", "target_price"):
        with pytest.raises(ValueError, match="forbidden Step 20 MVP columns"):
            validate_step20_mvp_scope_columns(["ticker", "date", column])


def test_scope_text_rejects_positive_expansion_but_allows_post_mvp_note() -> None:
    with pytest.raises(ValueError, match="KOSDAQ150 implementation"):
        validate_step20_mvp_scope_text("KOSDAQ150 ranking is implemented and active.")

    validate_step20_mvp_scope_text(
        "KOSDAQ150 was not implemented and remains a post-MVP extension track."
    )


def test_scope_frame_rejects_backtest_evaluation_fields_as_upstream_material() -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "realized_holding_return": 0.1,
            }
        ]
    )

    with pytest.raises(ValueError, match="Step 17 evaluation fields"):
        validate_step20_mvp_scope_frame(frame)


def test_release_report_requires_explicit_mvp_freeze_confirmations() -> None:
    text = f"""
    {STEP20_MVP_SCOPE_NOTICE}
    KOSDAQ150 was not implemented.
    Futures/options were not implemented.
    Valuation/fundamental scoring remains inactive.
    Backtest outputs did not feed upstream scoring or ranking.
    MVP remains KOSPI200-only.
    """

    validate_step20_release_report_text(text)

    with pytest.raises(ValueError, match="missing required Step 20 confirmations"):
        validate_step20_release_report_text(f"{STEP20_MVP_SCOPE_NOTICE}\nMVP remains KOSPI200-only.")
