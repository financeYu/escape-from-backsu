"""Config-driven Step 6 preprocessing for daily OHLCV data.

This module prepares canonical daily price data for later research stages. It
does not compute indicators, scores, rankings, composites, or backtests.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import tomllib
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from .schema_validator import (
    CANONICAL_OHLCV_COLUMNS,
    NUMERIC_PRICE_COLUMNS,
    infer_ticker_from_price_path,
    is_valid_ticker,
    normalize_price_columns,
    schema_checks_to_frame,
    to_safe_numeric,
    validate_standard_ohlcv_schema,
)


DEFAULT_INPUT_GLOB = "chart_mvp/data/*_daily_prices.csv"
DEFAULT_OUTPUT_PATH = "data/processed/daily_ohlcv.csv"
DEFAULT_SUMMARY_REPORT_PATH = "reports/preprocess/preprocess_summary.md"
DEFAULT_VALIDATION_REPORT_PATH = "reports/preprocess/preprocess_validation_summary.csv"
DEFAULT_INVALID_ROWS_REPORT_PATH = "reports/preprocess/preprocess_invalid_rows.csv"
DEFAULT_FINANCIAL_DATA_STATUS = "valuation_deferred"
SUPPORTED_ROW_POLICIES = frozenset({"reject_and_report"})
SUPPORTED_FINANCIAL_DATA_STATUSES = frozenset({DEFAULT_FINANCIAL_DATA_STATUS})


@dataclass(frozen=True)
class PreprocessConfig:
    """Config-derived paths and conservative validation policies."""

    input_glob: str
    output_path: str
    summary_report_path: str
    validation_summary_path: str
    invalid_rows_report_path: str
    timezone: str = "Asia/Seoul"
    future_date_policy: str = "reject_and_report"
    invalid_row_policy: str = "reject_and_report"
    financial_data_status: str = DEFAULT_FINANCIAL_DATA_STATUS


@dataclass(frozen=True)
class PreprocessResult:
    """Preprocessing outputs and report metrics."""

    processed: pd.DataFrame
    invalid_rows: pd.DataFrame
    validation_summary: pd.DataFrame
    summary: dict[str, object]
    output_path: Path
    summary_report_path: Path
    validation_summary_path: Path
    invalid_rows_report_path: Path


def load_preprocess_config(config_path: str | Path = "config/data.toml") -> PreprocessConfig:
    """Load Step 6 preprocessing settings from ``config/data.toml``."""

    path = Path(config_path)
    with path.open("rb") as handle:
        config = tomllib.load(handle)

    preprocess = config.get("preprocess", {})
    global_settings = _load_global_settings(path.parent.parent)

    preprocess_config = PreprocessConfig(
        input_glob=str(preprocess.get("raw_price_input_glob", DEFAULT_INPUT_GLOB)),
        output_path=str(preprocess.get("processed_price_output_path", DEFAULT_OUTPUT_PATH)),
        summary_report_path=str(preprocess.get("summary_report_path", DEFAULT_SUMMARY_REPORT_PATH)),
        validation_summary_path=str(
            preprocess.get("validation_summary_path", DEFAULT_VALIDATION_REPORT_PATH)
        ),
        invalid_rows_report_path=str(
            preprocess.get("invalid_rows_report_path", DEFAULT_INVALID_ROWS_REPORT_PATH)
        ),
        timezone=str(preprocess.get("timezone", global_settings.get("timezone", "Asia/Seoul"))),
        future_date_policy=str(preprocess.get("future_date_policy", "reject_and_report")),
        invalid_row_policy=str(preprocess.get("invalid_row_policy", "reject_and_report")),
        financial_data_status=str(
            preprocess.get(
                "financial_data_status",
                config.get("financial_data", {}).get("status", DEFAULT_FINANCIAL_DATA_STATUS),
            )
        ),
    )
    _validate_preprocess_config(preprocess_config)
    return preprocess_config


def load_raw_price_data(input_glob: str, *, project_root: str | Path = ".") -> pd.DataFrame:
    """Load raw or cached daily price CSVs into the canonical alias-aware shape."""

    root = Path(project_root)
    paths = sorted(root.glob(input_glob))
    if not paths:
        raise FileNotFoundError(f"No price input files matched: {input_glob}")

    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_csv(
            path,
            dtype={"ticker": "string", "code": "string", "종목코드": "string"},
            keep_default_na=False,
        )
        normalized = normalize_price_columns(
            frame,
            ticker=infer_ticker_from_price_path(path),
            source="cache",
        )
        normalized["_input_file"] = str(path.relative_to(root))
        frames.append(normalized)

    return pd.concat(frames, ignore_index=True)


def preprocess_ohlcv_frame(
    frame: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | None = None,
    input_path: str = "",
    output_path: str = "",
    financial_data_status: str = DEFAULT_FINANCIAL_DATA_STATUS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Validate, reject invalid rows, and return clean canonical OHLCV output."""

    normalized = normalize_price_columns(frame).copy()
    if "_input_file" in frame.columns and "_input_file" not in normalized.columns:
        normalized["_input_file"] = frame["_input_file"]

    cutoff = _as_timestamp(as_of_date)
    row_count_before = int(len(normalized))
    missing_columns = [column for column in CANONICAL_OHLCV_COLUMNS if column not in normalized.columns]

    if missing_columns:
        invalid_rows = normalized.copy()
        invalid_rows["validation_status"] = "invalid"
        invalid_rows["invalid_reason"] = "missing_required_columns:" + ",".join(missing_columns)
        processed = _empty_processed_frame()
        summary = _build_summary(
            input_path=input_path,
            output_path=output_path,
            row_count_before=row_count_before,
            processed=processed,
            duplicate_count=0,
            invalid_numeric_count=0,
            invalid_date_count=0,
            missing_required_value_count=row_count_before * len(missing_columns),
            future_date_count=0,
            negative_volume_count=0,
            invalid_ticker_count=row_count_before,
            input_file_count=_input_file_count(normalized),
            financial_data_status=financial_data_status,
        )
        validation_summary = _validation_summary_frame(summary)
        return processed, invalid_rows, validation_summary, summary

    reasons = pd.Series([""] * len(normalized), index=normalized.index, dtype="string")

    ticker_values = normalized["ticker"]
    ticker_text = ticker_values.astype("string").str.strip()
    ticker_numeric_dtype = pd.api.types.is_numeric_dtype(ticker_values)
    invalid_ticker = (
        ticker_values.isna() | ticker_text.eq("").fillna(True) | ~ticker_text.map(is_valid_ticker)
    ).fillna(True)
    leading_zero_loss = (ticker_text.str.isdigit() & ticker_text.str.len().lt(6)).fillna(False)
    if ticker_numeric_dtype:
        invalid_ticker = invalid_ticker | ticker_values.notna()
        leading_zero_loss = leading_zero_loss | ticker_values.notna()
    _add_reason(reasons, invalid_ticker, "invalid_ticker")
    _add_reason(reasons, leading_zero_loss, "ticker_leading_zero_loss_candidate")

    missing_required_values = _missing_required_values(normalized)
    missing_required_rows = missing_required_values.any(axis=1)
    _add_reason(reasons, missing_required_rows, "missing_required_value")

    parsed_dates = pd.to_datetime(normalized["date"], errors="coerce")
    date_text = normalized["date"].astype("string").str.strip()
    invalid_dates = (normalized["date"].notna() & date_text.ne("").fillna(False) & parsed_dates.isna()).fillna(False)
    _add_reason(reasons, invalid_dates, "invalid_date")

    future_dates = (parsed_dates.notna() & (parsed_dates > cutoff)).fillna(False)
    _add_reason(reasons, future_dates, "future_date")

    converted_numeric: dict[str, pd.Series] = {}
    invalid_numeric_masks: list[pd.Series] = []
    for column in NUMERIC_PRICE_COLUMNS:
        converted, invalid_numeric = to_safe_numeric(normalized[column])
        converted_numeric[column] = converted
        invalid_numeric_masks.append(invalid_numeric)
        _add_reason(reasons, invalid_numeric, f"invalid_numeric:{column}")

    negative_volume = (converted_numeric["volume"].notna() & (converted_numeric["volume"] < 0)).fillna(False)
    _add_reason(reasons, negative_volume, "negative_volume")

    duplicate_keys = _duplicate_ticker_date_mask(ticker_text, parsed_dates, invalid_ticker, invalid_dates)
    _add_reason(reasons, duplicate_keys, "duplicate_ticker_date")

    valid_rows = reasons.str.len().eq(0)
    processed = pd.DataFrame(
        {
            "ticker": ticker_text[valid_rows].astype("string"),
            "date": parsed_dates[valid_rows].dt.strftime("%Y-%m-%d"),
            "open": converted_numeric["open"][valid_rows],
            "high": converted_numeric["high"][valid_rows],
            "low": converted_numeric["low"][valid_rows],
            "close": converted_numeric["close"][valid_rows],
            "volume": converted_numeric["volume"][valid_rows],
        }
    )
    processed = processed.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    invalid_rows = normalized.loc[~valid_rows, [column for column in normalized.columns if column in CANONICAL_OHLCV_COLUMNS or column == "_input_file"]].copy()
    invalid_rows["validation_status"] = "invalid"
    invalid_rows["invalid_reason"] = reasons.loc[~valid_rows].str.strip(";")
    invalid_rows = invalid_rows.reset_index(drop=True)

    invalid_numeric_count = int(sum(mask.sum() for mask in invalid_numeric_masks))
    summary = _build_summary(
        input_path=input_path,
        output_path=output_path,
        row_count_before=row_count_before,
        processed=processed,
        duplicate_count=int(duplicate_keys.sum()),
        invalid_numeric_count=invalid_numeric_count,
        invalid_date_count=int(invalid_dates.sum()),
        missing_required_value_count=int(missing_required_values.sum().sum()),
        future_date_count=int(future_dates.sum()),
        negative_volume_count=int(negative_volume.sum()),
        invalid_ticker_count=int(invalid_ticker.sum()),
        input_file_count=_input_file_count(normalized),
        financial_data_status=financial_data_status,
    )
    validation_summary = _validation_summary_frame(summary)
    return processed, invalid_rows, validation_summary, summary


def run_preprocessing_from_config(
    *,
    config_path: str | Path = "config/data.toml",
    project_root: str | Path = ".",
    as_of_date: date | datetime | pd.Timestamp | None = None,
) -> PreprocessResult:
    """Run the Step 6 preprocessing pipeline and write configured artifacts."""

    root = Path(project_root)
    config = load_preprocess_config(root / config_path)
    output_path = _resolve_path(root, config.output_path)
    summary_report_path = _resolve_path(root, config.summary_report_path)
    validation_summary_path = _resolve_path(root, config.validation_summary_path)
    invalid_rows_report_path = _resolve_path(root, config.invalid_rows_report_path)

    cutoff = as_of_date or _today_in_timezone(config.timezone)
    raw = load_raw_price_data(config.input_glob, project_root=root)
    processed, invalid_rows, validation_summary, summary = preprocess_ohlcv_frame(
        raw,
        as_of_date=cutoff,
        input_path=config.input_glob,
        output_path=config.output_path,
        financial_data_status=config.financial_data_status,
    )

    _write_csv(processed, output_path)
    _write_csv(validation_summary, validation_summary_path)
    _write_csv(invalid_rows, invalid_rows_report_path)
    _write_summary_report(
        summary,
        summary_report_path,
        validation_checks=schema_checks_to_frame(validate_standard_ohlcv_schema(raw, as_of_date=cutoff)),
    )

    return PreprocessResult(
        processed=processed,
        invalid_rows=invalid_rows,
        validation_summary=validation_summary,
        summary=summary,
        output_path=output_path,
        summary_report_path=summary_report_path,
        validation_summary_path=validation_summary_path,
        invalid_rows_report_path=invalid_rows_report_path,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Step 6 daily OHLCV preprocessing.")
    parser.add_argument("--config", default="config/data.toml")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--as-of-date", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)

    as_of = pd.to_datetime(args.as_of_date).date() if args.as_of_date else None
    result = run_preprocessing_from_config(
        config_path=args.config,
        project_root=args.project_root,
        as_of_date=as_of,
    )
    print(
        "Step 6 preprocessing complete: "
        f"rows_before={result.summary['row_count_before']}, "
        f"rows_after={result.summary['row_count_after']}, "
        f"output={result.output_path}"
    )
    return 0


def _load_global_settings(project_root: Path) -> dict[str, object]:
    global_path = project_root / "config" / "global.toml"
    if not global_path.exists():
        return {}
    with global_path.open("rb") as handle:
        config = tomllib.load(handle)
    return {
        "timezone": config.get("project", {}).get("timezone", "Asia/Seoul"),
    }


def _validate_preprocess_config(config: PreprocessConfig) -> None:
    _require_supported_value(
        "preprocess.future_date_policy",
        config.future_date_policy,
        SUPPORTED_ROW_POLICIES,
    )
    _require_supported_value(
        "preprocess.invalid_row_policy",
        config.invalid_row_policy,
        SUPPORTED_ROW_POLICIES,
    )
    _require_supported_value(
        "preprocess.financial_data_status",
        config.financial_data_status,
        SUPPORTED_FINANCIAL_DATA_STATUSES,
    )


def _require_supported_value(name: str, value: str, supported: frozenset[str]) -> None:
    if value in supported:
        return
    allowed = ", ".join(sorted(supported))
    raise ValueError(f"Unsupported {name}: {value!r}. Supported values: {allowed}.")


def _today_in_timezone(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date()


def _as_timestamp(value: date | datetime | pd.Timestamp | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp(date.today())
    if isinstance(value, pd.Timestamp):
        return pd.Timestamp(value.date())
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    return pd.Timestamp(value)


def _resolve_path(root: Path, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _empty_processed_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_OHLCV_COLUMNS)


def _add_reason(reasons: pd.Series, mask: pd.Series, reason: str) -> None:
    if not mask.any():
        return
    existing = reasons.loc[mask].fillna("")
    separator = existing.where(existing.eq(""), existing + ";")
    reasons.loc[mask] = separator + reason


def _missing_required_values(frame: pd.DataFrame) -> pd.DataFrame:
    missing = pd.DataFrame(False, index=frame.index, columns=CANONICAL_OHLCV_COLUMNS)
    for column in CANONICAL_OHLCV_COLUMNS:
        values = frame[column]
        missing[column] = values.isna() | values.astype("string").str.strip().eq("")
    return missing


def _duplicate_ticker_date_mask(
    ticker_text: pd.Series,
    parsed_dates: pd.Series,
    invalid_ticker: pd.Series,
    invalid_dates: pd.Series,
) -> pd.Series:
    key_frame = pd.DataFrame(
        {
            "ticker": ticker_text,
            "date": parsed_dates.dt.strftime("%Y-%m-%d"),
        },
        index=ticker_text.index,
    )
    key_valid = ~invalid_ticker & ~invalid_dates & key_frame["date"].notna()
    duplicates = key_frame.loc[key_valid].duplicated(["ticker", "date"], keep=False)
    mask = pd.Series(False, index=ticker_text.index)
    mask.loc[duplicates.index] = duplicates
    return mask


def _input_file_count(frame: pd.DataFrame) -> int:
    if "_input_file" not in frame.columns:
        return 0
    return int(frame["_input_file"].nunique(dropna=True))


def _build_summary(
    *,
    input_path: str,
    output_path: str,
    row_count_before: int,
    processed: pd.DataFrame,
    duplicate_count: int,
    invalid_numeric_count: int,
    invalid_date_count: int,
    missing_required_value_count: int,
    future_date_count: int,
    negative_volume_count: int,
    invalid_ticker_count: int,
    input_file_count: int,
    financial_data_status: str,
) -> dict[str, object]:
    if processed.empty:
        start_date = ""
        end_date = ""
        ticker_count = 0
    else:
        start_date = str(processed["date"].min())
        end_date = str(processed["date"].max())
        ticker_count = int(processed["ticker"].nunique())

    return {
        "input_path": input_path,
        "output_path": output_path,
        "row_count_before": row_count_before,
        "row_count_after": int(len(processed)),
        "ticker_count": ticker_count,
        "date_range_start": start_date,
        "date_range_end": end_date,
        "duplicate_count": duplicate_count,
        "invalid_numeric_count": invalid_numeric_count,
        "invalid_date_count": invalid_date_count,
        "missing_required_value_count": missing_required_value_count,
        "future_date_count": future_date_count,
        "negative_volume_count": negative_volume_count,
        "invalid_ticker_count": invalid_ticker_count,
        "input_file_count": input_file_count,
        "financial_data_status": financial_data_status,
    }


def _validation_summary_frame(summary: dict[str, object]) -> pd.DataFrame:
    error_metrics = {
        "duplicate_count",
        "invalid_numeric_count",
        "invalid_date_count",
        "missing_required_value_count",
        "future_date_count",
        "negative_volume_count",
        "invalid_ticker_count",
    }
    rows = []
    for metric, value in summary.items():
        if metric in error_metrics:
            status = "pass" if int(value) == 0 else "fail"
        else:
            status = "info"
        rows.append({"metric": metric, "value": value, "status": status})
    return pd.DataFrame(rows, columns=["metric", "value", "status"])


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def _write_summary_report(summary: dict[str, object], path: Path, *, validation_checks: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Step 6 Preprocessing Summary",
        "",
        "This report is validation/preprocessing output only. It does not include indicators, scores, rankings, composites, or backtests.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Schema Checks",
            "",
            "| dataset | check | status | details |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in validation_checks.to_dict("records"):
        lines.append(f"| {row['dataset']} | {row['check']} | {row['status']} | {row['details']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
