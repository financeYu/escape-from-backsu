from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backtest_report_readme_declares_generated_output_boundary() -> None:
    readme = (PROJECT_ROOT / "reports" / "backtest" / "README.md").read_text(
        encoding="utf-8"
    )

    required_phrases = (
        "Generated backtest reports are runtime evaluation artifacts.",
        "not canonical score definitions",
        "not a trading recommendation",
        "does not redefine score or ranking formulas",
        "valuation/fundamental scoring remains gated until Step 18",
        "no return feedback into upstream scores",
    )
    for phrase in required_phrases:
        assert phrase in readme


def test_step17_guardrail_doc_declares_no_feedback_and_limitation_boundary() -> None:
    doc = (PROJECT_ROOT / "docs" / "step17_backtest_guardrails.md").read_text(
        encoding="utf-8"
    )

    required_phrases = (
        "does not create a trading system",
        "does not prove alpha",
        "does not alter score/rank/adoption/composite formulas",
        "does not use valuation/fundamental data",
        "Step 13 `review_status`",
        "Step 14 `adoption_state`",
        "Step 15 ranking input",
        "Step 16 detail report score context",
        "no_return_feedback_to_scores",
    )
    for phrase in required_phrases:
        assert phrase in doc
