from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_step16_report_boundary_docs_define_safe_downstream_use() -> None:
    text = (
        PROJECT_ROOT / "docs" / "architecture" / "step16_report_backtest_boundary.md"
    ).read_text(encoding="utf-8")

    assert "Step 16 reports are explanatory artifacts." in text
    assert "Step 16 itself must not compute future returns" in text
    assert "must not introduce buy/sell/hold decisions" in text
    assert "must not introduce PER/PBR/ROE" in text
    assert "read-only snapshot information" in text


def test_reports_security_readme_defines_generated_output_boundary() -> None:
    text = (PROJECT_ROOT / "reports" / "security" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "reports/security/generated/" in text
    assert "technical-only detail report" in text
    assert "Generated report files are runtime artifacts." in text
    assert "No backtest" in text
    assert "No valuation" in text
