"""Validation helpers for Step 18 candidate valuation/fundamental data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import math
import re
from typing import Any

import pandas as pd

from src.scores.schema import find_missing_columns, find_valuation_fundamental_columns
from src.valuation.contracts import (
    STEP18_CANDIDATE_SCHEMA_COLUMNS,
    STEP18_CANDIDATE_SOURCE_ID_COLUMNS,
    STEP18_OPTIONAL_CANDIDATE_COLUMNS,
    MetricCategory,
    ValuationCandidateRecord,
)
from src.valuation.registry import (
    DEFAULT_STEP18_METRIC_REGISTRY,
    MetricSpec,
    metric_registry_by_name,
)


STEP18_AVAILABILITY_DATE_COLUMNS = ("availability_date", "available_date", "as_of_date")
STEP18_MAX_REPORTING_LAG_DAYS = 120
STEP18_MAX_STALE_AGE_DAYS = 540
STEP18_REQUIRED_REPORT_COLUMNS = (
    *STEP18_CANDIDATE_SCHEMA_COLUMNS,
    "step18_candidate_only_notice",
)

STEP18_UNSAFE_IMPUTATION_FLAGS = frozenset(
    {
        "future_filled",
        "backfilled",
        "cross_sectional_imputed",
        "peer_imputed",
        "optimistic_fill",
        "filled_from_future",
        "unsafe_imputation",
        "missing_available_date",
    }
)

STEP18_UNSAFE_IMPUTATION_COLUMNS = frozenset(
    {
        "imputation_method",
        "fill_method",
        "filled_from_future",
        "cross_sectional_fill",
        "backfilled",
        "future_filled",
    }
)

STEP18_PRODUCTION_PROTECTED_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "backtest_period_return",
        "realized_holding_return",
        "evaluation_return",
    }
)

STEP18_CANDIDATE_ONLY_SCORE_COLUMNS = frozenset(
    {
        "valuation_candidate_score",
        "fundamental_candidate_score",
    }
)

STEP18_FINANCIAL_EXACT_COLUMNS = frozenset(
    {
        "per",
        "pbr",
        "psr",
        "pcr",
        "dividend_yield",
        "roe",
        "roa",
        "operating_margin",
        "net_margin",
        "debt_to_equity",
        "current_ratio",
        "revenue_growth_yoy",
        "operating_income_growth_yoy",
        "eps_growth_yoy",
        "eps",
        "bps",
        "book_value",
        "earnings",
        "net_income",
        "revenue",
        "sales",
        "operating_income",
        "cash_flow",
        "free_cash_flow",
        "market_cap",
        "shares_outstanding",
        "source_report_id",
        "disclosure_id",
        "source_vendor",
        "filing_date",
        "availability_date",
        "available_date",
        "as_of_date",
        "period",
        "fiscal_period",
        "metric",
        "metric_name",
        "value",
        "metric_value",
        "metric_unit",
        "metric_category",
    }
)

STEP18_FINANCIAL_PREFIXES = (
    "valuation_",
    "fundamental_",
    "financial_",
    "earnings_",
    "revenue_",
    "sales_",
    "cash_flow_",
    "dividend_",
    "market_cap_",
)


def validate_candidate_records(
    records: pd.DataFrame | Mapping[str, Any] | Iterable[Mapping[str, Any] | ValuationCandidateRecord],
    *,
    evaluation_date: object | None = None,
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> tuple[ValuationCandidateRecord, ...]:
    """Validate and return Step 18 candidate records.

    Records are rejected when they are not point-in-time usable for the supplied
    evaluation date. This function never creates a score or ranking output.
    """

    registry_by_name = metric_registry_by_name(registry)
    evaluation_ts = _optional_date(evaluation_date, field_name="evaluation_date")
    return tuple(
        _coerce_record(row, registry_by_name=registry_by_name, evaluation_ts=evaluation_ts)
        for row in _record_iter(records)
    )


def candidate_records_to_frame(
    records: Iterable[ValuationCandidateRecord],
) -> pd.DataFrame:
    """Convert validated records into a candidate-only DataFrame."""

    return pd.DataFrame([record.to_dict() for record in records])


def find_step18_candidate_columns(columns: Iterable[str]) -> list[str]:
    """Return columns that are valuation/fundamental candidate fields."""

    flagged: set[str] = set(find_valuation_fundamental_columns(columns))
    for column in columns:
        normalized = str(column).strip().lower()
        if (
            normalized in STEP18_FINANCIAL_EXACT_COLUMNS
            or normalized in STEP18_CANDIDATE_ONLY_SCORE_COLUMNS
            or normalized.startswith(STEP18_FINANCIAL_PREFIXES)
        ):
            flagged.add(str(column))
    return sorted(flagged)


def assert_no_step18_score_contamination(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 18 score boundary",
) -> None:
    """Reject valuation/fundamental fields near protected score/ranking outputs."""

    column_names = _column_names(columns)
    candidate_columns = find_step18_candidate_columns(column_names)
    protected = sorted(
        column for column in column_names if column.lower() in STEP18_PRODUCTION_PROTECTED_COLUMNS
    )
    if candidate_columns and protected:
        raise ValueError(
            f"{context} has valuation/fundamental fields beside protected production "
            f"columns ({', '.join(protected)}): {', '.join(candidate_columns)}"
        )


def assert_no_step18_production_leakage(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 18 production boundary",
) -> None:
    """Reject candidate-only valuation/fundamental columns in production outputs."""

    column_names = _column_names(columns)
    candidate_columns = find_step18_candidate_columns(column_names)
    if candidate_columns:
        raise ValueError(
            f"{context} contains Step 18 candidate-only valuation/fundamental columns: "
            f"{', '.join(candidate_columns)}"
        )
    candidate_scores = sorted(
        column
        for column in column_names
        if column.lower() in STEP18_CANDIDATE_ONLY_SCORE_COLUMNS
    )
    if candidate_scores:
        raise ValueError(
            f"{context} contains candidate-only score placeholders: "
            f"{', '.join(candidate_scores)}"
        )


def validate_step18_candidate_report_frame(
    frame: pd.DataFrame,
    *,
    context: str = "Step 18 candidate report",
) -> None:
    """Validate candidate-only report tables without accepting ranking fields."""

    missing = find_missing_columns(frame.columns, STEP18_REQUIRED_REPORT_COLUMNS)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")
    protected = sorted(
        column for column in frame.columns if column.lower() in STEP18_PRODUCTION_PROTECTED_COLUMNS
    )
    if protected:
        raise ValueError(
            f"{context} must remain separate from production ranking/backtest fields: "
            f"{', '.join(protected)}"
        )
    validate_candidate_records(frame.drop(columns=["step18_candidate_only_notice"]))


def validate_candidate_backtest_availability(
    records: pd.DataFrame | Mapping[str, Any] | Iterable[Mapping[str, Any] | ValuationCandidateRecord],
    *,
    decision_date: object,
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> tuple[ValuationCandidateRecord, ...]:
    """Reject candidate records that are unavailable for a backtest decision date."""

    return validate_candidate_records(records, evaluation_date=decision_date, registry=registry)


def _record_iter(
    records: pd.DataFrame | Mapping[str, Any] | Iterable[Mapping[str, Any] | ValuationCandidateRecord],
) -> tuple[Mapping[str, Any] | ValuationCandidateRecord, ...]:
    if isinstance(records, pd.DataFrame):
        return tuple(records.to_dict(orient="records"))
    if isinstance(records, Mapping):
        return (records,)
    return tuple(records)


def _coerce_record(
    record: Mapping[str, Any] | ValuationCandidateRecord,
    *,
    registry_by_name: Mapping[str, MetricSpec],
    evaluation_ts: pd.Timestamp | None,
) -> ValuationCandidateRecord:
    if isinstance(record, ValuationCandidateRecord):
        payload = record.to_dict()
    else:
        payload = dict(record)

    _assert_required_candidate_fields(payload)
    _assert_safe_imputation(payload)

    ticker = _required_text_alias(payload, "ticker", aliases=("symbol",))
    _assert_safe_ticker(ticker)
    company_name = _resolve_company_name(payload)
    metric = _required_text_alias(payload, "metric", aliases=("metric_name",)).lower()
    spec = registry_by_name.get(metric)
    if spec is None:
        raise ValueError(f"Step 18 candidate metric is outside the allowed registry: {metric}")

    metric_category = _required_text(payload, "metric_category").lower()
    if metric_category not in {category.value for category in MetricCategory}:
        raise ValueError(f"Step 18 candidate metric_category is unsupported: {metric_category}")
    if metric_category != spec.metric_category:
        raise ValueError(
            "Step 18 candidate metric_category does not match registry for "
            f"{metric}: {metric_category} != {spec.metric_category}"
        )
    metric_unit = _required_text(payload, "metric_unit").lower()
    if metric_unit != spec.metric_unit:
        raise ValueError(
            "Step 18 candidate metric_unit does not match registry for "
            f"{metric}: {metric_unit} != {spec.metric_unit}"
        )

    value = _required_numeric_alias(payload, "value", aliases=("metric_value",))
    available_ts = _required_availability_date(payload)
    filing_ts = _required_date(payload.get("filing_date"), field_name="filing_date")
    collected_ts = _required_date(payload.get("collected_at"), field_name="collected_at")
    report_ts = _optional_date(payload.get("report_date"), field_name="report_date")
    universe_ts = _optional_date(payload.get("universe_date"), field_name="universe_date")
    _assert_reporting_lag_policy(filing_ts, available_ts)

    if evaluation_ts is not None:
        future_fields: list[str] = []
        if available_ts > evaluation_ts:
            future_fields.append("availability_date/available_date/as_of_date")
        if filing_ts > evaluation_ts:
            future_fields.append("filing_date")
        if report_ts is not None and report_ts > evaluation_ts:
            future_fields.append("report_date")
        if universe_ts is not None and universe_ts > evaluation_ts:
            future_fields.append("universe_date")
        if future_fields:
            raise ValueError(
                "Step 18 candidate record is not available for evaluation_date "
                f"{evaluation_ts.date().isoformat()}: {', '.join(future_fields)}"
            )
        _assert_stale_data_policy(available_ts, evaluation_ts)

    source_report_id = _optional_text(payload.get("source_report_id"))
    disclosure_id = _optional_text(payload.get("disclosure_id"))
    if source_report_id is None and disclosure_id is None:
        raise ValueError("Step 18 candidate source_report_id or disclosure_id is required.")

    return ValuationCandidateRecord(
        ticker=ticker,
        company_name=company_name,
        metric=metric,
        value=value,
        metric_unit=metric_unit,
        metric_category=metric_category,
        period=_required_text_alias(payload, "period", aliases=("fiscal_period",)),
        filing_date=_date_string(filing_ts),
        availability_date=_date_string(available_ts),
        source_vendor=_required_text(payload, "source_vendor"),
        collected_at=_date_string(collected_ts),
        quality_flags=_quality_flags(payload.get("quality_flags")),
        disclosure_id=disclosure_id,
        source_report_id=source_report_id,
        report_date=_optional_date_string(report_ts),
        universe_date=_optional_date_string(universe_ts),
        source=_optional_text(payload.get("source")),
        notes=_optional_text(payload.get("notes")),
    )


def _assert_required_candidate_fields(payload: Mapping[str, Any]) -> None:
    missing = [
        field
        for field in STEP18_CANDIDATE_SCHEMA_COLUMNS
        if field not in payload
        and field
        not in {
            "ticker",
            "metric",
            "value",
            "period",
            "availability_date",
            "company_name",
        }
    ]
    if "ticker" not in payload and "symbol" not in payload:
        missing.append("ticker/symbol")
    if "metric" not in payload and "metric_name" not in payload:
        missing.append("metric/metric_name")
    if "value" not in payload and "metric_value" not in payload:
        missing.append("value/metric_value")
    if "period" not in payload and "fiscal_period" not in payload:
        missing.append("period/fiscal_period")
    if not any(column in payload for column in STEP18_AVAILABILITY_DATE_COLUMNS):
        missing.append("availability_date/available_date/as_of_date")
    if "company_name" not in payload and "name" not in payload:
        missing.append("company_name/name")
    if not any(column in payload for column in STEP18_CANDIDATE_SOURCE_ID_COLUMNS):
        missing.append("source_report_id or disclosure_id")
    if missing:
        raise ValueError(f"Step 18 candidate record missing required fields: {', '.join(missing)}")


def _assert_safe_ticker(ticker: str) -> None:
    if not re.fullmatch(r"\d{6}", ticker):
        raise ValueError("Step 18 candidate ticker must preserve a six-digit KOSPI code string.")


def _assert_safe_imputation(payload: Mapping[str, Any]) -> None:
    flags = set(flag.lower() for flag in _quality_flags(payload.get("quality_flags")))
    unsafe_flags = sorted(flags.intersection(STEP18_UNSAFE_IMPUTATION_FLAGS))
    if unsafe_flags:
        raise ValueError(
            "Step 18 candidate record contains unsafe imputation quality_flags: "
            f"{', '.join(unsafe_flags)}"
        )
    for column in STEP18_UNSAFE_IMPUTATION_COLUMNS:
        if column not in payload:
            continue
        value = payload[column]
        if value in (None, "", False, "none", "None", "NONE"):
            continue
        raise ValueError(f"Step 18 candidate record contains unsafe imputation field: {column}")


def _required_text(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if value is None or value is pd.NA:
        raise ValueError(f"Step 18 candidate {field_name} is required.")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Step 18 candidate {field_name} is required.")
    return text


def _required_text_alias(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    aliases: Sequence[str] = (),
) -> str:
    value = _first_present_value(payload, (field_name, *aliases))
    return _required_text({field_name: value}, field_name)


def _optional_text(value: object) -> str | None:
    if value is None or value is pd.NA:
        return None
    text = str(value).strip()
    return text or None


def _resolve_company_name(payload: Mapping[str, Any]) -> str:
    value = payload.get("company_name", payload.get("name"))
    if value is None or value is pd.NA or str(value).strip() == "":
        raise ValueError("Step 18 candidate company_name/name is required.")
    return str(value).strip()


def _required_numeric(value: object, *, field_name: str) -> float:
    if value is None or value is pd.NA:
        raise ValueError(f"Step 18 candidate {field_name} must be numeric and present.")
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        raise ValueError(f"Step 18 candidate {field_name} must be numeric.")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        raise ValueError(f"Step 18 candidate {field_name} must be numeric.") from None
    if math.isnan(parsed) or math.isinf(parsed):
        raise ValueError(f"Step 18 candidate {field_name} must be finite.")
    return parsed


def _required_numeric_alias(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    aliases: Sequence[str] = (),
) -> float:
    value = _first_present_value(payload, (field_name, *aliases))
    return _required_numeric(value, field_name=f"{field_name}/{'/'.join(aliases)}" if aliases else field_name)


def _required_availability_date(payload: Mapping[str, Any]) -> pd.Timestamp:
    value = _first_present_value(payload, STEP18_AVAILABILITY_DATE_COLUMNS)
    if value is None or value is pd.NA or str(value).strip() == "":
        raise ValueError("Step 18 candidate availability_date/available_date/as_of_date is required.")
    return _required_date(value, field_name="availability_date/available_date/as_of_date")


def _required_date(value: object, *, field_name: str) -> pd.Timestamp:
    timestamp = _optional_date(value, field_name=field_name)
    if timestamp is None:
        raise ValueError(f"Step 18 candidate {field_name} is required.")
    return timestamp


def _optional_date(value: object, *, field_name: str) -> pd.Timestamp | None:
    if value is None or value is pd.NA or str(value).strip() == "":
        return None
    try:
        timestamp = pd.Timestamp(pd.to_datetime(value, errors="raise")).normalize()
    except (TypeError, ValueError):
        raise ValueError(f"Step 18 candidate {field_name} must be a valid date.") from None
    if pd.isna(timestamp):
        return None
    return timestamp


def _first_present_value(payload: Mapping[str, Any], field_names: Sequence[str]) -> object:
    for field_name in field_names:
        value = payload.get(field_name)
        if value is None or value is pd.NA:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def _assert_reporting_lag_policy(filing_ts: pd.Timestamp, availability_ts: pd.Timestamp) -> None:
    lag_days = (availability_ts - filing_ts).days
    if lag_days < 0:
        raise ValueError("Step 18 candidate availability_date cannot be before filing_date.")
    if lag_days > STEP18_MAX_REPORTING_LAG_DAYS:
        raise ValueError(
            "Step 18 candidate reporting lag exceeds policy: "
            f"{lag_days} days > {STEP18_MAX_REPORTING_LAG_DAYS} days"
        )


def _assert_stale_data_policy(availability_ts: pd.Timestamp, evaluation_ts: pd.Timestamp) -> None:
    stale_days = (evaluation_ts - availability_ts).days
    if stale_days > STEP18_MAX_STALE_AGE_DAYS:
        raise ValueError(
            "Step 18 candidate availability_date is stale for evaluation_date: "
            f"{stale_days} days > {STEP18_MAX_STALE_AGE_DAYS} days"
        )


def _date_string(timestamp: pd.Timestamp) -> str:
    return timestamp.date().isoformat()


def _optional_date_string(timestamp: pd.Timestamp | None) -> str | None:
    return None if timestamp is None else _date_string(timestamp)


def _quality_flags(value: object) -> tuple[str, ...]:
    if value is None or value is pd.NA:
        return ()
    if isinstance(value, str):
        raw_flags = value.split(",") if "," in value else value.split("|")
    elif isinstance(value, Iterable):
        raw_flags = [str(flag) for flag in value]
    else:
        raw_flags = [str(value)]
    return tuple(dict.fromkeys(flag.strip() for flag in raw_flags if flag and flag.strip()))


def _column_names(columns: pd.DataFrame | Iterable[str]) -> tuple[str, ...]:
    if isinstance(columns, pd.DataFrame):
        return tuple(str(column) for column in columns.columns)
    return tuple(str(column) for column in columns)


__all__ = (
    "STEP18_AVAILABILITY_DATE_COLUMNS",
    "STEP18_CANDIDATE_ONLY_SCORE_COLUMNS",
    "STEP18_MAX_REPORTING_LAG_DAYS",
    "STEP18_MAX_STALE_AGE_DAYS",
    "STEP18_REQUIRED_REPORT_COLUMNS",
    "STEP18_UNSAFE_IMPUTATION_FLAGS",
    "assert_no_step18_production_leakage",
    "assert_no_step18_score_contamination",
    "candidate_records_to_frame",
    "find_step18_candidate_columns",
    "validate_candidate_backtest_availability",
    "validate_candidate_records",
    "validate_step18_candidate_report_frame",
)
