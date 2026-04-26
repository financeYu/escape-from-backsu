"""Inventory-only validation for financial statement collector output."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


FISCAL_PERIOD_PATTERN = re.compile(r"\d{4}[/.-](?:\d{2}|Q[1-4])(?:\(E\))?")
POINT_IN_TIME_DATE_COLUMNS = {
    "disclosure_date",
    "availability_date",
    "available_at",
    "filing_date",
}
OBSERVATION_DATE_COLUMNS = {"collected_at"}
EXPECTED_FINANCIAL_COLUMNS = ["code", "table_index", "metric", "period", "value"]


@dataclass(frozen=True)
class FinancialValidationResult:
    """Financial data validation result without valuation scoring."""

    issues: pd.DataFrame
    column_inventory: pd.DataFrame
    point_in_time_status: str
    future_valuation_safety: str


def _expected_column_issues(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {
            "check": f"available_column:{column}",
            "severity": "info" if column in frame.columns else "warning",
            "rows_affected": 0,
            "message": "present" if column in frame.columns else "missing",
        }
        for column in EXPECTED_FINANCIAL_COLUMNS
    ]


def _fiscal_period_issue(frame: pd.DataFrame, column: str) -> dict[str, object]:
    parsed = frame[column].astype(str).str.strip().map(lambda value: bool(FISCAL_PERIOD_PATTERN.search(value))).astype(bool)
    invalid_count = int((~parsed & frame[column].notna()).sum())
    return {
        "check": f"fiscal_period_column:{column}",
        "severity": "warning" if invalid_count else "info",
        "rows_affected": invalid_count,
        "message": "Fiscal period column detected.",
    }


def _fiscal_period_issues(frame: pd.DataFrame) -> list[dict[str, object]]:
    period_columns = [column for column in frame.columns if "period" in column.lower() or "fiscal" in column.lower()]
    if period_columns:
        return [_fiscal_period_issue(frame, column) for column in period_columns]

    return [
        {
            "check": "fiscal_period_columns",
            "severity": "warning",
            "rows_affected": len(frame),
            "message": "No fiscal period column detected.",
        }
    ]


def _evaluate_point_in_time_columns(frame: pd.DataFrame) -> tuple[list[str], list[str], pd.Series, int, str, str]:
    pit_columns = sorted(POINT_IN_TIME_DATE_COLUMNS.intersection(set(frame.columns)))
    observation_columns = sorted(OBSERVATION_DATE_COLUMNS.intersection(set(frame.columns)))
    valid_pit_rows = pd.Series(False, index=frame.index)
    invalid_pit_values = 0

    for column in pit_columns:
        raw_values = frame[column].astype(str).str.strip()
        populated = frame[column].notna() & raw_values.ne("")
        parsed = pd.to_datetime(frame[column], errors="coerce")
        valid_pit_rows = valid_pit_rows | (populated & parsed.notna())
        invalid_pit_values += int((populated & parsed.isna()).sum())

    if pit_columns and bool(valid_pit_rows.all()) and invalid_pit_values == 0:
        point_in_time_status = "verified"
        future_valuation_safety = "safe_with_disclosure_dates"
    elif pit_columns and bool(valid_pit_rows.any()):
        point_in_time_status = "partially_verified"
        future_valuation_safety = "partial_requires_row_level_filter"
    else:
        point_in_time_status = "unverified"
        future_valuation_safety = "unsafe_without_availability_dates"

    return (
        pit_columns,
        observation_columns,
        valid_pit_rows,
        invalid_pit_values,
        point_in_time_status,
        future_valuation_safety,
    )


def _point_in_time_issues(
    frame: pd.DataFrame,
    pit_columns: list[str],
    observation_columns: list[str],
    valid_pit_rows: pd.Series,
    invalid_pit_values: int,
    point_in_time_status: str,
    future_valuation_safety: str,
) -> list[dict[str, object]]:
    issues = [_pit_presence_issue(frame, pit_columns, valid_pit_rows)]

    if observation_columns:
        issues.append(_collection_timestamp_issue(observation_columns))

    if pit_columns:
        issues.extend(_pit_parseability_issues(frame, valid_pit_rows, invalid_pit_values, point_in_time_status))
    elif observation_columns:
        issues.append(_collection_timestamp_not_pit_issue(frame))

    issues.extend(_pit_status_issues(frame, point_in_time_status, future_valuation_safety))
    return issues


def _pit_presence_issue(
    frame: pd.DataFrame,
    pit_columns: list[str],
    valid_pit_rows: pd.Series,
) -> dict[str, object]:
    return {
        "check": "disclosure_or_availability_date_presence",
        "severity": "info" if pit_columns else "warning",
        "rows_affected": int(len(frame) - valid_pit_rows.sum()) if pit_columns else len(frame),
        "message": ";".join(pit_columns) if pit_columns else "No disclosure date or availability date column present.",
    }


def _collection_timestamp_issue(observation_columns: list[str]) -> dict[str, object]:
    return {
        "check": "collection_timestamp_presence",
        "severity": "info",
        "rows_affected": 0,
        "message": ";".join(observation_columns),
    }


def _pit_parseability_issues(
    frame: pd.DataFrame,
    valid_pit_rows: pd.Series,
    invalid_pit_values: int,
    point_in_time_status: str,
) -> list[dict[str, object]]:
    return [
        {
            "check": "point_in_time_date_parseability",
            "severity": "warning" if invalid_pit_values else "info",
            "rows_affected": invalid_pit_values,
            "message": "invalid PIT date values found" if invalid_pit_values else "all populated PIT date values are parseable",
        },
        {
            "check": "point_in_time_row_coverage",
            "severity": "warning" if point_in_time_status != "verified" else "info",
            "rows_affected": int(len(frame) - valid_pit_rows.sum()),
            "message": f"{int(valid_pit_rows.sum())}/{len(frame)} rows have parseable PIT dates",
        },
    ]


def _collection_timestamp_not_pit_issue(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "check": "collection_timestamp_is_not_pit",
        "severity": "warning",
        "rows_affected": len(frame),
        "message": "collected_at records observation time only and does not verify historical availability.",
    }


def _pit_status_issues(
    frame: pd.DataFrame,
    point_in_time_status: str,
    future_valuation_safety: str,
) -> list[dict[str, object]]:
    return [
        {
            "check": "point_in_time_status",
            "severity": "info",
            "rows_affected": len(frame),
            "message": point_in_time_status,
        },
        {
            "check": "future_valuation_safety",
            "severity": "info" if point_in_time_status == "verified" else "warning",
            "rows_affected": len(frame),
            "message": future_valuation_safety,
        },
    ]


def _build_column_inventory(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "column": column,
                "dtype": str(frame[column].dtype),
                "non_null_rows": int(frame[column].notna().sum()),
                "sample_values": "; ".join(frame[column].dropna().astype(str).head(3).tolist()),
            }
            for column in frame.columns
        ],
        columns=["column", "dtype", "non_null_rows", "sample_values"],
    )


def validate_financial_frame(frame: pd.DataFrame) -> FinancialValidationResult:
    """Validate financial statement data only for schema and point-in-time safety."""

    issues = _expected_column_issues(frame)
    issues.extend(_fiscal_period_issues(frame))
    (
        pit_columns,
        observation_columns,
        valid_pit_rows,
        invalid_pit_values,
        point_in_time_status,
        future_valuation_safety,
    ) = _evaluate_point_in_time_columns(frame)
    issues.extend(
        _point_in_time_issues(
            frame,
            pit_columns,
            observation_columns,
            valid_pit_rows,
            invalid_pit_values,
            point_in_time_status,
            future_valuation_safety,
        )
    )

    return FinancialValidationResult(
        issues=pd.DataFrame(issues, columns=["check", "severity", "rows_affected", "message"]),
        column_inventory=_build_column_inventory(frame),
        point_in_time_status=point_in_time_status,
        future_valuation_safety=future_valuation_safety,
    )
