from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.step20_mvp_scope_guardrails import (  # noqa: E402
    validate_step20_mvp_scope_text,
)


def test_step20_ranking_sanity_report_is_fixture_based_and_scope_safe() -> None:
    report_path = PROJECT_ROOT / "reports" / "validation" / "step20_ranking_sanity_report.md"
    text = report_path.read_text(encoding="utf-8")

    validate_step20_mvp_scope_text(text, context="Step 20 ranking sanity report")
    assert "Fixture basis" in text
    assert "diagnostic-only scores are not directly ranked" in text
    assert "valuation/fundamental data is not active" in text
    assert "backtest outputs did not feed upstream scoring" in text
