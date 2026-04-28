"""Tests for v0.2 probability report wording."""

from __future__ import annotations

import pytest

from src.reports.v0_2_probability_wording import (
    V0_2_PROBABILITY_REPORT_DISCLAIMER,
    validate_v0_2_probability_report_wording,
)


def _allowed_text() -> str:
    return (
        "final_composite_score는 1영업일 뒤 adjusted_close 상승확률 추정값입니다. "
        "상승확률 기반 순위이며 v0.2 확률형 최종 스코어입니다. "
        f"{V0_2_PROBABILITY_REPORT_DISCLAIMER}"
    )


def test_v0_2_probability_report_allowed_wording_passes() -> None:
    validate_v0_2_probability_report_wording(_allowed_text())


@pytest.mark.parametrize(
    "forbidden",
    (
        "매수",
        "매도",
        "보유",
        "추천",
        "투자 조언",
        "확정 상승",
        "수익 보장",
        "기대수익률",
        "초과수익",
        "검증된 알파",
        "proven alpha",
        "guaranteed return",
        "expected return",
        "buy",
        "sell",
        "hold",
    ),
)
def test_v0_2_probability_report_forbidden_wording_fails(forbidden: str) -> None:
    with pytest.raises(ValueError):
        validate_v0_2_probability_report_wording(f"{_allowed_text()} {forbidden}")
