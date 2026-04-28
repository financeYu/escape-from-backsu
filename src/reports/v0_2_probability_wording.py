"""v0.2 probability report wording contract."""

from __future__ import annotations

from src.validation.text_guardrails import find_forbidden_terms


ALLOWED_V0_2_PROBABILITY_REPORT_WORDING = (
    "1영업일 뒤 adjusted_close 상승확률 추정값",
    "상승확률 기반 순위",
    "v0.2 확률형 최종 스코어",
    "확률형 최종 스코어",
    "상승확률 기반 점수",
)

V0_2_PROBABILITY_REPORT_DISCLAIMER = (
    "This score is a model-estimated probability signal for research/scanning "
    "use and is not investment advice."
)

FORBIDDEN_V0_2_PROBABILITY_REPORT_WORDING = frozenset(
    {
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
        "investment advice",
        "buy",
        "sell",
        "hold",
    }
)


def validate_v0_2_probability_report_wording(text: str) -> None:
    """Reject v0.2 report wording that implies trading or return claims."""

    screened_text = text.replace(V0_2_PROBABILITY_REPORT_DISCLAIMER, "")
    forbidden = find_forbidden_terms(screened_text, FORBIDDEN_V0_2_PROBABILITY_REPORT_WORDING)
    if forbidden:
        raise ValueError(f"v0.2 probability report wording contains forbidden terms: {', '.join(forbidden)}")
    if not any(phrase in text for phrase in ALLOWED_V0_2_PROBABILITY_REPORT_WORDING):
        raise ValueError("v0.2 probability report wording must include an allowed probability-score expression.")
    if V0_2_PROBABILITY_REPORT_DISCLAIMER not in text:
        raise ValueError("v0.2 probability report wording must include the required user-facing disclaimer.")


__all__ = (
    "ALLOWED_V0_2_PROBABILITY_REPORT_WORDING",
    "FORBIDDEN_V0_2_PROBABILITY_REPORT_WORDING",
    "V0_2_PROBABILITY_REPORT_DISCLAIMER",
    "validate_v0_2_probability_report_wording",
)
