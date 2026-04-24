"""Quality checks for standardized price collector output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from preprocess.schema_validator import (
    REQUIRED_PRICE_COLUMNS,
    infer_ticker_from_price_path,
    is_valid_ticker,
    normalize_price_columns,
)


@dataclass(frozen=True)
class PriceValidationConfig:
    """Configurable thresholds for price data validation."""

    min_history_length: int = 120
    warmup_min_history_length: int = 60
    suspicious_return_threshold: float = 0.30
    flat_pattern_window: int = 5
    latest_coverage_lag_days: int = 10


def _issue(
    issues: list[dict[str, object]],
    *,
    check: str,
    severity: str,
    message: str,
    ticker: str = "",
    date: object = "",
    rows_affected: int = 0,
) -> None:
    issues.append(
        {
            "check": check,
            "severity": severity,
            "ticker": ticker,
            "date": "" if pd.isna(date) else str(date),
            "rows_affected": rows_affected,
            "message": message,
        }
    )


def load_standard_price_csv(path: str | Path, *, source: str = "cache") -> pd.DataFrame:
    """Load one cached price CSV into the standard price schema."""

    csv_path = Path(path)
    frame = pd.read_csv(csv_path, dtype={"종목코드": str, "ticker": str, "code": str})
    return normalize_price_columns(frame, ticker=infer_ticker_from_price_path(csv_path), source=source)


def validate_price_frame(
    frame: pd.DataFrame,
    *,
    dataset_name: str = "price",
    config: PriceValidationConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Validate a standard or alias-compatible price DataFrame.

    Returns ``(issues, per_ticker_summary, normalized_frame)``.
    """

    config = config or PriceValidationConfig()
    normalized = normalize_price_columns(frame)
    issues: list[dict[str, object]] = []

    missing_columns = [column for column in REQUIRED_PRICE_COLUMNS if column not in normalized.columns]
    if missing_columns:
        for column in missing_columns:
            _issue(
                issues,
                check="required_column_existence",
                severity="error",
                message=f"Missing required column: {column}",
            )
        return pd.DataFrame(issues), pd.DataFrame(), normalized

    normalized = normalized.copy()
    normalized["ticker"] = normalized["ticker"].astype(str).str.strip()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")

    invalid_ticker_mask = ~normalized["ticker"].map(is_valid_ticker)
    if invalid_ticker_mask.any():
        _issue(
            issues,
            check="ticker_format",
            severity="error",
            message="Ticker must match six alphanumeric characters.",
            rows_affected=int(invalid_ticker_mask.sum()),
        )

    invalid_dates = normalized["date"].isna()
    if invalid_dates.any():
        _issue(
            issues,
            check="date_parseability",
            severity="error",
            message="Date values could not be parsed.",
            rows_affected=int(invalid_dates.sum()),
        )

    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        invalid_numeric = normalized[column].isna()
        if invalid_numeric.any():
            severity = "error" if column in {"close", "volume"} else "warning"
            _issue(
                issues,
                check=f"numeric_type:{column}",
                severity=severity,
                message=f"{column} contains missing or non-numeric values.",
                rows_affected=int(invalid_numeric.sum()),
            )

    duplicates = normalized.duplicated(subset=["ticker", "date"], keep=False)
    if duplicates.any():
        _issue(
            issues,
            check="duplicate_ticker_date",
            severity="error",
            message="Duplicate ticker-date rows found.",
            rows_affected=int(duplicates.sum()),
        )

    for ticker, group in normalized.groupby("ticker", dropna=False, sort=False):
        ticker_text = str(ticker)
        dates = group["date"]
        if dates.notna().any() and not dates.dropna().is_monotonic_increasing:
            _issue(
                issues,
                check="per_ticker_date_ordering",
                severity="warning",
                message="Dates are not monotonic increasing within ticker.",
                ticker=ticker_text,
            )

        row_count = int(len(group))
        if row_count < config.min_history_length:
            _issue(
                issues,
                check="minimum_history_length",
                severity="warning",
                message=f"History length {row_count} is below minimum {config.min_history_length}.",
                ticker=ticker_text,
                rows_affected=row_count,
            )
        if row_count < config.warmup_min_history_length:
            _issue(
                issues,
                check="warmup_eligibility",
                severity="warning",
                message=f"History length {row_count} is below warmup minimum {config.warmup_min_history_length}.",
                ticker=ticker_text,
                rows_affected=row_count,
            )

        valid_dates = dates.dropna()
        if not valid_dates.empty:
            latest_date = valid_dates.max()
            global_latest = normalized["date"].max()
            if pd.notna(global_latest) and (global_latest - latest_date).days > config.latest_coverage_lag_days:
                _issue(
                    issues,
                    check="latest_date_coverage",
                    severity="warning",
                    message=f"Latest date {latest_date.date()} lags global latest {global_latest.date()}.",
                    ticker=ticker_text,
                    date=latest_date.date(),
                )

        returns = group.sort_values("date")["close"].pct_change(fill_method=None).abs()
        suspicious_jumps = returns > config.suspicious_return_threshold
        if suspicious_jumps.any():
            _issue(
                issues,
                check="suspicious_large_return_jumps",
                severity="warning",
                message=f"Absolute close-to-close return exceeds {config.suspicious_return_threshold:.0%}.",
                ticker=ticker_text,
                rows_affected=int(suspicious_jumps.sum()),
            )

        zero_volume = group["volume"] == 0
        if zero_volume.any():
            _issue(
                issues,
                check="suspended_like_zero_volume",
                severity="info",
                message="Rows with zero volume may indicate halted or stale trading.",
                ticker=ticker_text,
                rows_affected=int(zero_volume.sum()),
            )

        flat_ohlc = group[["open", "high", "low", "close"]].nunique(axis=1) == 1
        repeated_flat = flat_ohlc.rolling(config.flat_pattern_window, min_periods=config.flat_pattern_window).sum()
        if (repeated_flat >= config.flat_pattern_window).any():
            _issue(
                issues,
                check="suspended_like_repeated_flat_ohlc",
                severity="info",
                message=f"Repeated flat OHLC pattern reaches {config.flat_pattern_window} consecutive rows.",
                ticker=ticker_text,
            )

    row_checks = [
        ("non_positive_open", normalized["open"] <= 0),
        ("non_positive_high", normalized["high"] <= 0),
        ("non_positive_low", normalized["low"] <= 0),
        ("non_positive_close", normalized["close"] <= 0),
        ("negative_volume", normalized["volume"] < 0),
        ("high_less_than_low", normalized["high"] < normalized["low"]),
        ("high_less_than_open", normalized["high"] < normalized["open"]),
        ("high_less_than_close", normalized["high"] < normalized["close"]),
        ("low_greater_than_open", normalized["low"] > normalized["open"]),
        ("low_greater_than_close", normalized["low"] > normalized["close"]),
        ("missing_close", normalized["close"].isna()),
        ("missing_volume", normalized["volume"].isna()),
    ]
    for check, mask in row_checks:
        if mask.any():
            _issue(
                issues,
                check=check,
                severity="error" if check.startswith("missing") else "warning",
                message=f"{check} rows found.",
                rows_affected=int(mask.sum()),
            )

    summary = (
        normalized.groupby("ticker", dropna=False)
        .agg(
            rows=("date", "size"),
            first_date=("date", "min"),
            latest_date=("date", "max"),
            missing_close=("close", lambda series: int(series.isna().sum())),
            missing_volume=("volume", lambda series: int(series.isna().sum())),
            zero_volume_rows=("volume", lambda series: int((series == 0).sum())),
        )
        .reset_index()
    )
    summary["warmup_eligible"] = summary["rows"] >= config.warmup_min_history_length
    summary["history_length_ok"] = summary["rows"] >= config.min_history_length
    summary["dataset"] = dataset_name

    issue_frame = pd.DataFrame(
        issues,
        columns=["check", "severity", "ticker", "date", "rows_affected", "message"],
    )
    return issue_frame, summary, normalized


def validate_price_csvs(
    paths: list[str | Path],
    *,
    config: PriceValidationConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Validate multiple cached price CSV files."""

    frames = [load_standard_price_csv(path) for path in paths]
    if not frames:
        empty = pd.DataFrame()
        return empty, empty, empty
    return validate_price_frame(pd.concat(frames, ignore_index=True), dataset_name="price_cache", config=config)
