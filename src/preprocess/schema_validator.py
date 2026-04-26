"""Canonical schema definitions and validators for Step 3 cleanup.

This module is intentionally limited to schema/report checks. It does not load
market data, implement scores, generate rankings, or run backtests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from numbers import Number
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


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

@dataclass(frozen=True)
class SymbolPolicy:
    """Validation policy for instrument identifiers.

    The default remains the KOSPI200/Naver six-character stock-code contract.
    Future extension work can pass a different policy without weakening the MVP
    guard.
    """

    policy_id: str
    valid_pattern: str
    normalize_numeric_width: int | None = 6
    leading_zero_check_enabled: bool = True
    display_rule: str = "six-character uppercase alphanumeric string format"

    def is_valid(self, value: object) -> bool:
        return bool(re.fullmatch(self.valid_pattern, str(value).strip().upper()))

    def normalize(self, value: object) -> str:
        return str(value).strip().upper()

    def leading_zero_loss_candidates(self, values: pd.Series) -> int:
        if not self.leading_zero_check_enabled or self.normalize_numeric_width is None:
            return 0
        ticker_text = values.astype(str).str.strip()
        non_null = values.notna()
        short_digit_tickers = (
            non_null
            & ticker_text.str.isdigit()
            & (ticker_text.str.len() < self.normalize_numeric_width)
        )
        return int(short_digit_tickers.sum()) if short_digit_tickers.any() else 0


KOSPI200_SYMBOL_POLICY = SymbolPolicy(
    policy_id="kospi200_korean_equity_6",
    valid_pattern=r"^[0-9A-Z]{6}$",
    normalize_numeric_width=6,
    leading_zero_check_enabled=True,
    display_rule="six-character uppercase alphanumeric string format",
)

GENERIC_EXCHANGE_SYMBOL_POLICY = SymbolPolicy(
    policy_id="generic_exchange_symbol",
    valid_pattern=r"^[0-9A-Z][0-9A-Z._-]{0,31}$",
    normalize_numeric_width=None,
    leading_zero_check_enabled=False,
    display_rule="configured exchange symbol format",
)

TICKER_PATTERN = re.compile(KOSPI200_SYMBOL_POLICY.valid_pattern)
PLAIN_NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
COMMA_NUMERIC_PATTERN = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d*)?$")


@dataclass(frozen=True)
class SchemaCheck:
    """One report-friendly schema validation result row."""

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
    data_vendor: str | None = "naver_finance",
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
    *,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> tuple[bool, int, int]:
    ticker_text = ticker_values.astype(str).str.strip()
    non_null = ticker_values.notna()
    numeric_dtype = pd.api.types.is_numeric_dtype(ticker_values)
    invalid_format = non_null & ~ticker_text.map(lambda value: is_valid_ticker(value, symbol_policy=symbol_policy))

    format_failures = int(invalid_format.sum())
    leading_zero_loss_candidates = symbol_policy.leading_zero_loss_candidates(ticker_values)
    if numeric_dtype:
        leading_zero_loss_candidates = (
            max(leading_zero_loss_candidates, int(non_null.sum()))
            if symbol_policy.leading_zero_check_enabled
            else 0
        )
    return numeric_dtype, format_failures, leading_zero_loss_candidates


def validate_ticker_column(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
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
        return [SchemaCheck(dataset=dataset, check="date_parseable", status="fail", details="missing date column")]

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


def _as_date(value: date | datetime | pd.Timestamp | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def validate_future_dates_absent(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    as_of_date: date | datetime | pd.Timestamp | None = None,
) -> list[SchemaCheck]:
    """Validate that parsed dates do not exceed the as-of date."""

    normalized = normalize_price_columns(frame)
    if "date" not in normalized.columns:
        return [SchemaCheck(dataset=dataset, check="future_dates_absent", status="fail", details="missing date column")]

    parsed_dates = pd.to_datetime(normalized["date"], errors="coerce")
    cutoff = pd.Timestamp(_as_date(as_of_date))
    future_dates = parsed_dates.notna() & (parsed_dates > cutoff)
    future_count = int(future_dates.sum())
    return [
        SchemaCheck(
            dataset=dataset,
            check="future_dates_absent",
            status="fail" if future_count else "pass",
            details=f"future_rows={future_count};as_of_date={cutoff.date().isoformat()}",
        )
    ]


def is_safe_numeric_value(value: object) -> bool:
    """Return whether a value can be converted without stripping unknown text."""

    if pd.isna(value) or isinstance(value, bool):
        return False
    if isinstance(value, Number):
        return True

    text = str(value).strip()
    if not text:
        return False
    return bool(PLAIN_NUMERIC_PATTERN.fullmatch(text) or COMMA_NUMERIC_PATTERN.fullmatch(text))


def to_safe_numeric(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Convert safe numeric values and return ``(converted, invalid_mask)``."""

    valid_mask = series.map(is_safe_numeric_value)
    normalized = series.astype(str).str.strip().str.replace(",", "", regex=False)
    converted = pd.to_numeric(normalized.where(valid_mask), errors="coerce")
    invalid_mask = series.notna() & ~valid_mask
    return converted, invalid_mask


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
        _, invalid_numeric = to_safe_numeric(values)
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


def validate_non_negative_volume(frame: pd.DataFrame, *, dataset: str = "price") -> list[SchemaCheck]:
    """Validate that volume is convertible and not negative."""

    normalized = normalize_price_columns(frame)
    if "volume" not in normalized.columns:
        return [SchemaCheck(dataset=dataset, check="non_negative_volume", status="fail", details="missing column")]

    converted, invalid_numeric = to_safe_numeric(normalized["volume"])
    negative_volume = converted.notna() & (converted < 0)
    negative_count = int(negative_volume.sum())
    invalid_count = int(invalid_numeric.sum())
    status = "fail" if negative_count or invalid_count else "pass"
    return [
        SchemaCheck(
            dataset=dataset,
            check="non_negative_volume",
            status=status,
            details=f"negative_rows={negative_count};invalid_numeric_rows={invalid_count}",
        )
    ]


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
    as_of_date: date | datetime | pd.Timestamp | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
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
    checks.extend(validate_future_dates_absent(normalized, dataset=dataset, as_of_date=as_of_date))
    checks.extend(validate_numeric_columns_convertible(normalized, dataset=dataset))
    checks.extend(validate_non_negative_volume(normalized, dataset=dataset))
    checks.extend(validate_duplicate_ticker_date_absent(normalized, dataset=dataset))
    return append_schema_validation_summary(checks, dataset=dataset)


def validate_standard_ohlcv_schema(
    frame: pd.DataFrame,
    *,
    dataset: str = "price",
    as_of_date: date | datetime | pd.Timestamp | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> list[SchemaCheck]:
    """Validate the canonical OHLCV schema without requiring runtime source metadata."""

    normalized = normalize_price_columns(frame)
    checks = validate_required_columns(normalized, CANONICAL_OHLCV_COLUMNS, dataset=dataset)
    checks.extend(validate_ticker_column(normalized, dataset=dataset, symbol_policy=symbol_policy))
    checks.extend(validate_date_parseability(normalized, dataset=dataset))
    checks.extend(validate_future_dates_absent(normalized, dataset=dataset, as_of_date=as_of_date))
    checks.extend(validate_numeric_columns_convertible(normalized, dataset=dataset))
    checks.extend(validate_non_negative_volume(normalized, dataset=dataset))
    checks.extend(validate_duplicate_ticker_date_absent(normalized, dataset=dataset))
    return append_schema_validation_summary(checks, dataset=dataset)


def schema_checks_to_frame(checks: Iterable[SchemaCheck]) -> pd.DataFrame:
    """Convert schema checks to a report-friendly DataFrame."""

    return pd.DataFrame([check.__dict__ for check in checks], columns=["dataset", "check", "status", "details"])


def infer_ticker_from_price_path(path: str | Path) -> str:
    """Infer a ticker from the current cache file convention."""

    name = Path(path).name
    suffix = "_daily_prices.csv"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return Path(path).stem


def is_valid_ticker(
    value: object,
    *,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> bool:
    """Return whether a value matches the configured ticker convention."""

    return symbol_policy.is_valid(value)
