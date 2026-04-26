"""Shared schema definitions and validators for collected market data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from stock_core.utils.market_specs import KOREAN_EQUITY_SYMBOL_POLICY, NAVER_PRICE_PROVIDER_SPEC, SymbolPolicy


CANONICAL_OHLCV_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]
NUMERIC_PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]
REQUIRED_PRICE_COLUMNS = [*CANONICAL_OHLCV_COLUMNS, "source"]
OPTIONAL_PRICE_COLUMNS = ["name", "market", "data_vendor", "collected_at"]
STANDARD_PRICE_COLUMNS = [*REQUIRED_PRICE_COLUMNS, *OPTIONAL_PRICE_COLUMNS]

PRICE_COLUMN_ALIASES = {
    "ticker": ("ticker", "code", "종목코드"),
    "date": ("date", "날짜", "일자"),
    "open": ("open", "시가"),
    "high": ("high", "고가"),
    "low": ("low", "저가"),
    "close": ("close", "종가"),
    "volume": ("volume", "거래량"),
    "source": ("source", "data_source"),
    "name": ("name", "종목명"),
    "market": ("market",),
    "data_vendor": ("data_vendor", "vendor"),
    "collected_at": ("collected_at",),
}

TICKER_PATTERN = re.compile(KOREAN_EQUITY_SYMBOL_POLICY.valid_pattern)


@dataclass(frozen=True)
class SchemaCheck:
    """One schema validation result row."""

    dataset: str
    check: str
    status: str
    details: str = ""


def find_column(frame: pd.DataFrame, logical_name: str) -> str | None:
    """Return the first matching physical column for a logical schema name."""

    aliases = PRICE_COLUMN_ALIASES.get(logical_name, (logical_name,))
    for alias in aliases:
        if alias in frame.columns:
            return alias
    return None


def normalize_price_columns(
    frame: pd.DataFrame,
    *,
    ticker: str | None = None,
    source: str | None = None,
    data_vendor: str | None = NAVER_PRICE_PROVIDER_SPEC.data_vendor,
) -> pd.DataFrame:
    """Return a copy with standard price schema column names when aliases exist."""

    normalized = pd.DataFrame(index=frame.index)
    for logical_name in STANDARD_PRICE_COLUMNS:
        physical_name = find_column(frame, logical_name)
        if physical_name is not None:
            normalized[logical_name] = frame[physical_name]

    if ticker is not None and "ticker" not in normalized:
        normalized["ticker"] = ticker
    if source is not None and "source" not in normalized:
        normalized["source"] = source
    if data_vendor is not None and "data_vendor" not in normalized:
        normalized["data_vendor"] = data_vendor

    return normalized


def validate_required_columns(
    frame: pd.DataFrame,
    required_columns: Iterable[str],
    *,
    dataset: str,
) -> list[SchemaCheck]:
    """Check whether a DataFrame contains all required columns."""

    checks: list[SchemaCheck] = []
    for column in required_columns:
        status = "pass" if column in frame.columns else "fail"
        checks.append(SchemaCheck(dataset=dataset, check=f"required_column:{column}", status=status))
    return checks


def _missing_ticker_checks(dataset: str) -> list[SchemaCheck]:
    return [
        SchemaCheck(dataset=dataset, check="ticker_string_like", status="fail", details="missing ticker column"),
        SchemaCheck(dataset=dataset, check="ticker_six_char_format", status="fail", details="missing ticker column"),
        SchemaCheck(
            dataset=dataset,
            check="ticker_leading_zero_preserved",
            status="fail",
            details="missing ticker column",
        ),
    ]


def _ticker_quality_counts(
    ticker_values: pd.Series,
    symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY,
) -> tuple[bool, int, int]:
    ticker_text = ticker_values.astype(str).str.strip()
    non_null = ticker_values.notna()
    numeric_dtype = pd.api.types.is_numeric_dtype(ticker_values)
    invalid_format = non_null & ~ticker_text.map(lambda value: is_valid_ticker(value, symbol_policy=symbol_policy))

    format_failures = int(invalid_format.sum())
    leading_zero_loss_candidates = symbol_policy.leading_zero_loss_candidates(ticker_values)
    if numeric_dtype:
        leading_zero_loss_candidates = max(leading_zero_loss_candidates, int(non_null.sum()))
    return numeric_dtype, format_failures, leading_zero_loss_candidates


def validate_ticker_column(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY,
) -> list[SchemaCheck]:
    """Validate ticker dtype, configured format, and likely leading-zero loss."""

    normalized = normalize_price_columns(frame)
    if "ticker" not in normalized.columns:
        return _missing_ticker_checks(dataset)

    ticker_values = normalized["ticker"]
    numeric_dtype, format_failures, leading_zero_loss_candidates = _ticker_quality_counts(
        ticker_values,
        symbol_policy=symbol_policy,
    )

    return [
        SchemaCheck(
            dataset=dataset,
            check="ticker_string_like",
            status="fail" if numeric_dtype else "pass",
            details=f"dtype={ticker_values.dtype}",
        ),
        SchemaCheck(
            dataset=dataset,
            check="ticker_six_char_format",
            status="fail" if format_failures else "pass",
            details=f"invalid_rows={format_failures}",
        ),
        SchemaCheck(
            dataset=dataset,
            check="ticker_leading_zero_preserved",
            status="fail" if leading_zero_loss_candidates else "pass",
            details=f"loss_candidates={leading_zero_loss_candidates}",
        ),
    ]


def validate_date_parseability(frame: pd.DataFrame, *, dataset: str = "price") -> list[SchemaCheck]:
    """Validate that date values can be parsed without mutating the frame."""

    normalized = normalize_price_columns(frame)
    if "date" not in normalized.columns:
        return [
            SchemaCheck(
                dataset=dataset,
                check="date_parseable",
                status="fail",
                details="missing date column",
            )
        ]

    date_values = normalized["date"]
    parsed_dates = pd.to_datetime(date_values, errors="coerce")
    invalid_dates = date_values.notna() & parsed_dates.isna()
    invalid_count = int(invalid_dates.sum())
    return [
        SchemaCheck(
            dataset=dataset,
            check="date_parseable",
            status="fail" if invalid_count else "pass",
            details=f"invalid_rows={invalid_count}",
        )
    ]


def validate_numeric_columns_convertible(frame: pd.DataFrame, *, dataset: str = "price") -> list[SchemaCheck]:
    """Validate OHLCV numeric convertibility without silently coercing source data."""

    normalized = normalize_price_columns(frame)
    checks: list[SchemaCheck] = []
    for column in NUMERIC_PRICE_COLUMNS:
        if column not in normalized.columns:
            checks.append(
                SchemaCheck(
                    dataset=dataset,
                    check=f"numeric_columns_convertible:{column}",
                    status="fail",
                    details="missing column",
                )
            )
            continue

        values = normalized[column]
        converted = pd.to_numeric(values, errors="coerce")
        invalid_numeric = values.notna() & converted.isna()
        invalid_count = int(invalid_numeric.sum())
        checks.append(
            SchemaCheck(
                dataset=dataset,
                check=f"numeric_columns_convertible:{column}",
                status="fail" if invalid_count else "pass",
                details=f"invalid_rows={invalid_count}",
            )
        )
    return checks


def validate_duplicate_ticker_date_absent(frame: pd.DataFrame, *, dataset: str = "price") -> list[SchemaCheck]:
    """Validate that ticker-date rows are unique in the normalized schema."""

    normalized = normalize_price_columns(frame)
    if "ticker" not in normalized.columns or "date" not in normalized.columns:
        return [
            SchemaCheck(
                dataset=dataset,
                check="duplicate_ticker_date_absent",
                status="fail",
                details="missing ticker or date column",
            )
        ]

    duplicates = normalized.duplicated(["ticker", "date"], keep=False)
    duplicate_count = int(duplicates.sum())
    return [
        SchemaCheck(
            dataset=dataset,
            check="duplicate_ticker_date_absent",
            status="fail" if duplicate_count else "pass",
            details=f"duplicate_rows={duplicate_count}",
        )
    ]


def append_schema_validation_summary(checks: list[SchemaCheck], *, dataset: str = "price") -> list[SchemaCheck]:
    """Append a report-friendly summary row to schema validation checks."""

    fail_count = sum(1 for check in checks if check.status == "fail")
    pass_count = sum(1 for check in checks if check.status == "pass")
    info_count = sum(1 for check in checks if check.status == "info")
    return [
        *checks,
        SchemaCheck(
            dataset=dataset,
            check="schema_validation_summary",
            status="fail" if fail_count else "pass",
            details=f"pass={pass_count};fail={fail_count};info={info_count}",
        ),
    ]


def validate_standard_price_schema(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY,
) -> list[SchemaCheck]:
    """Validate standard price schema presence and Step 3 safety checks."""

    normalized = normalize_price_columns(frame)
    checks = validate_required_columns(normalized, REQUIRED_PRICE_COLUMNS, dataset=dataset)
    optional_present = sorted(column for column in OPTIONAL_PRICE_COLUMNS if column in normalized.columns)
    checks.append(
        SchemaCheck(
            dataset=dataset,
            check="optional_columns_present",
            status="info",
            details=";".join(optional_present) if optional_present else "none",
        )
    )
    checks.extend(validate_ticker_column(normalized, dataset=dataset, symbol_policy=symbol_policy))
    checks.extend(validate_date_parseability(normalized, dataset=dataset))
    checks.extend(validate_numeric_columns_convertible(normalized, dataset=dataset))
    checks.extend(validate_duplicate_ticker_date_absent(normalized, dataset=dataset))
    return append_schema_validation_summary(checks, dataset=dataset)


def validate_standard_ohlcv_schema(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY,
) -> list[SchemaCheck]:
    """Validate the canonical OHLCV schema without requiring runtime source metadata."""

    normalized = normalize_price_columns(frame)
    checks = validate_required_columns(normalized, CANONICAL_OHLCV_COLUMNS, dataset=dataset)
    checks.extend(validate_ticker_column(normalized, dataset=dataset, symbol_policy=symbol_policy))
    checks.extend(validate_date_parseability(normalized, dataset=dataset))
    checks.extend(validate_numeric_columns_convertible(normalized, dataset=dataset))
    checks.extend(validate_duplicate_ticker_date_absent(normalized, dataset=dataset))
    return append_schema_validation_summary(checks, dataset=dataset)


def schema_checks_to_frame(checks: Iterable[SchemaCheck]) -> pd.DataFrame:
    """Convert schema checks to a report-friendly DataFrame."""

    return pd.DataFrame([check.__dict__ for check in checks], columns=["dataset", "check", "status", "details"])


def infer_ticker_from_price_path(path: str | Path, *, price_suffix: str = "daily_prices") -> str:
    """Infer a ticker from the current cache file convention."""

    name = Path(path).name
    suffix = f"_{price_suffix}.csv"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return Path(path).stem


def is_valid_ticker(value: object, symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY) -> bool:
    """Return whether a value matches the configured ticker convention."""

    return symbol_policy.is_valid(value)
