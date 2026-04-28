"""Check v0.2 probability report wording guardrails."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.reports.v0_2_probability_wording import (  # noqa: E402
    V0_2_PROBABILITY_REPORT_DISCLAIMER,
    validate_v0_2_probability_report_wording,
)


def main() -> int:
    valid = (
        "final_composite_score는 1영업일 뒤 adjusted_close 상승확률 추정값입니다. "
        "상승확률 기반 순위이며 v0.2 확률형 최종 스코어입니다. "
        f"{V0_2_PROBABILITY_REPORT_DISCLAIMER}"
    )
    validate_v0_2_probability_report_wording(valid)

    for forbidden in (
        "매수",
        "매도",
        "보유",
        "추천",
        "기대수익률",
        "proven alpha",
        "guaranteed return",
        "expected return",
        "buy",
        "sell",
        "hold",
    ):
        try:
            validate_v0_2_probability_report_wording(f"{valid} {forbidden}")
        except ValueError:
            continue
        raise AssertionError(f"forbidden wording was not rejected: {forbidden}")

    print("PASS: v0.2 probability report wording guardrail is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
