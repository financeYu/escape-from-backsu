from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY
from src.reports.security_detail_report import build_security_detail_report_records
from src.validation.step16_detail_report_guardrails import (
    validate_step16_detail_report_output,
    validate_step16_report_boundary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def step15_snapshot() -> pd.DataFrame:
    spec = next(iter(DEFAULT_COMPOSITE_INPUT_REGISTRY))
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 1,
                "expected_score_count": 1,
                "review_routed_score_count": 0,
                "final_score_policy": "technical_only_no_valuation",
                spec.normalized_column: 0.75,
                spec.status_column: "adequate",
                spec.quality_flag_column: "valid",
                spec.count_column: 190,
                f"{spec.family}_family_score": 0.75,
            }
        ]
    )


def worker_a_report_record() -> dict[str, object]:
    return build_security_detail_report_records(
        step15_snapshot(),
        "005930",
        report_date="2026-04-25",
    )[0]


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


def test_worker_a_report_output_passes_worker_b_guardrails() -> None:
    result = validate_step16_report_boundary(step15_snapshot(), worker_a_report_record())

    assert result.is_valid
    assert "rank" in result.read_only_fields


def test_worker_b_guardrails_reject_worker_a_report_without_notice() -> None:
    record = worker_a_report_record()
    record.pop("boundary_notice")

    with pytest.raises(ValueError, match="missing required notice"):
        validate_step16_detail_report_output(record)


@pytest.mark.parametrize(
    "text",
    (
        "This is a buy setup.",
        "This is a sell setup.",
        "A backtest supports this report.",
        "This looks cheap.",
        "The security is undervalued.",
        "forward_return supports the view.",
    ),
)
def test_worker_b_guardrails_reject_forbidden_text_in_worker_a_shape(text: str) -> None:
    record = worker_a_report_record()
    record["explanations"] = (text,)

    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step16_detail_report_output(record)


def test_worker_b_guardrails_reject_nested_forbidden_text_in_worker_a_shape() -> None:
    record = worker_a_report_record()
    record["score_breakdown"] = (
        {
            **record["score_breakdown"][0],
            "explanation": "A backtest supports this report.",
        },
    )

    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step16_detail_report_output(record)


def test_worker_b_guardrails_reject_changed_worker_a_readonly_rank() -> None:
    record = worker_a_report_record()
    record["readonly_rank_fields"] = {**record["readonly_rank_fields"], "rank": 2}

    with pytest.raises(ValueError, match="read-only Step 15 input rank"):
        validate_step16_report_boundary(step15_snapshot(), record)
