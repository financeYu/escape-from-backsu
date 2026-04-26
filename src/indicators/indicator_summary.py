"""Step 7 indicator summary and validation report builders."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .indicator_config import IndicatorWindows
from .indicator_engine import OUTPUT_METADATA_COLUMNS, REQUIRED_OHLCV_COLUMNS


def build_indicator_summary(
    indicators: pd.DataFrame,
    *,
    input_path: str,
    output_path: str,
    windows: IndicatorWindows,
) -> dict[str, object]:
    """Build a compact summary for Step 7 indicator output."""

    indicator_columns = [
        column
        for column in indicators.columns
        if column not in REQUIRED_OHLCV_COLUMNS and column not in OUTPUT_METADATA_COLUMNS
    ]
    warmup_counts = indicators["warmup_state"].value_counts(dropna=False).to_dict()
    return {
        "step": "Step 7",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "input_path": input_path,
        "output_path": output_path,
        "row_count": int(len(indicators)),
        "ticker_count": int(indicators["ticker"].nunique()) if not indicators.empty else 0,
        "date_range_start": str(indicators["date"].min().date()) if not indicators.empty else "",
        "date_range_end": str(indicators["date"].max().date()) if not indicators.empty else "",
        "indicator_column_count": len(indicator_columns),
        "indicator_columns": ", ".join(indicator_columns),
        "metadata_columns": ", ".join(OUTPUT_METADATA_COLUMNS),
        "ready_rows": int(warmup_counts.get("ready", 0)),
        "warmup_rows": int(warmup_counts.get("warmup", 0)),
        "insufficient_history_rows": int(warmup_counts.get("insufficient_history", 0)),
        "return_windows": ", ".join(str(value) for value in windows.returns.values()),
        "volatility_windows": ", ".join(str(value) for value in windows.volatility.values()),
        "indicator_windows": ", ".join(str(value) for value in windows.indicators.values()),
        "statistics_windows": ", ".join(str(value) for value in windows.statistics.values()),
        "score_implementation": "not_performed",
        "ranking_generation": "not_performed",
        "composite_generation": "not_performed",
        "backtest": "not_performed",
        "valuation_or_fundamental_scoring": "not_performed",
    }


def indicator_validation_summary_frame(summary: dict[str, object]) -> pd.DataFrame:
    """Return the Step 7 summary as a simple validation status table."""

    rows = []
    for metric, value in summary.items():
        status = "pass" if metric.endswith(("implementation", "generation", "backtest", "scoring")) else "info"
        rows.append({"metric": metric, "value": value, "status": status})
    return pd.DataFrame(rows, columns=["metric", "value", "status"])


def write_indicator_summary_report(summary: dict[str, object], path: Path) -> None:
    """Write the Korean-facing Step 7 indicator summary report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Step 7 Indicator Summary",
        "",
        "이 보고서는 일봉 OHLCV 기반 technical indicator 계산 결과만 요약합니다.",
        "score 구현, ranking 생성, composite 생성, adoption decision, backtest는 수행하지 않았습니다.",
        "가격 기반 technical indicator는 valuation evidence가 아닙니다.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- 모든 지표는 Step 6 canonical OHLCV 입력에 의존합니다.",
            "- `history_count`, `minimum_history_required`, `warmup_state`로 warmup/insufficient history 상태를 표시합니다.",
            "- warmup 구간의 NaN은 보수적으로 유지합니다.",
            "- as-of date 이후의 future date 입력은 거부합니다.",
            "- Step 8 normalization protocol 전까지 0-100 normalized score를 생성하지 않습니다.",
            "- Step 9 전까지 candidate score formula를 구현하지 않습니다.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "build_indicator_summary",
    "indicator_validation_summary_frame",
    "write_indicator_summary_report",
]
