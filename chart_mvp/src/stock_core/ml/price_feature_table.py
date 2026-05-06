"""Build ML-oriented price feature tables from standardized OHLCV data."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from preprocess.price_data_validator import PriceValidationConfig, validate_price_frame
from preprocess.schema_validator import infer_ticker_from_price_path


ML_PRICE_FEATURE_TABLE_SCHEMA_VERSION = "v0_3_kospi200_price_ml_feature_table_0_1"
ML_PRICE_FEATURE_TABLE_KIND = "kospi200_price_ml_feature_table"
ROW_BOUNDARY = (
    "ML-useful processed price feature row for candidate/evidence review only; "
    "not a runtime ranking input, trading signal, backtest feedback input, or "
    "automatic production activation."
)
MASTER_MVP_CONTEXT_MARKER = "master_mvp_ml_useful_processed_price_table"
SPLIT_POLICY = "time_order_required_before_training"
LABEL_SOURCE_ADJUSTED_CLOSE = "adjusted_close"
LABEL_SOURCE_MISSING_ADJUSTED_CLOSE = "missing_adjusted_close"
CACHE_PRICE_COLUMN_ALIASES = {
    "\ub0a0\uc9dc": "date",
    "\uc2dc\uac00": "open",
    "\uace0\uac00": "high",
    "\uc800\uac00": "low",
    "\uc885\uac00": "close",
    "\uac70\ub798\ub7c9": "volume",
}


@dataclass(frozen=True)
class MlPriceFeatureConfig:
    """Configuration for ML price feature table construction."""

    label_horizon_days: int = 1
    min_history_length: int = 20
    source_universe: str = "KOSPI200_candidate_only"
    source_project: str = "chart_mvp"
    owner_route: str = "master_mvp_v0_3_strategy_adoption"
    generated_output_boundary: str = "chart_mvp/outputs/ml_ready_price_features/"


def _require_supported_label_horizon(label_horizon_days: int) -> None:
    if label_horizon_days != 1:
        raise ValueError("label_horizon_days must be 1 while label columns use the 1d contract")


def _validate_source_frame(frame: pd.DataFrame, config: MlPriceFeatureConfig) -> pd.DataFrame:
    validation_config = PriceValidationConfig(
        min_history_length=config.min_history_length,
        warmup_min_history_length=min(config.min_history_length, 20),
    )
    issues, _, normalized = validate_price_frame(frame, dataset_name="ml_price_feature_source", config=validation_config)
    error_issues = issues[issues["severity"] == "error"] if not issues.empty else pd.DataFrame()
    if not error_issues.empty:
        checks = sorted(str(item) for item in error_issues["check"].unique())
        raise ValueError(f"source price data failed ML feature table validation: {checks}")
    return normalized


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain.divide(avg_loss.where(avg_loss != 0))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return rsi


def _next_date(group: pd.DataFrame, horizon: int) -> pd.Series:
    return group["date"].shift(-horizon).dt.strftime("%Y-%m-%d")


def _build_group_features(group: pd.DataFrame, config: MlPriceFeatureConfig) -> pd.DataFrame:
    result = group.sort_values("date").copy()
    close = _numeric_column(result, "close")
    volume = _numeric_column(result, "volume")
    adjusted_close_available = "adjusted_close" in result.columns and result["adjusted_close"].notna().any()
    label_base = _numeric_column(result, "adjusted_close") if adjusted_close_available else close

    result["return_1d"] = close.pct_change(fill_method=None)
    result["return_5d"] = close.pct_change(periods=5, fill_method=None)
    result["return_20d"] = close.pct_change(periods=20, fill_method=None)
    result["ma5"] = close.rolling(window=5).mean()
    result["ma20"] = close.rolling(window=20).mean()
    result["close_to_ma5"] = close.divide(result["ma5"]) - 1
    result["close_to_ma20"] = close.divide(result["ma20"]) - 1
    result["volatility_20d"] = result["return_1d"].rolling(window=20).std()
    result["volume_ma20"] = volume.rolling(window=20).mean()
    result["volume_to_ma20"] = volume.divide(result["volume_ma20"]) - 1
    result["rsi14"] = _rsi(close)

    forward_base = label_base.shift(-config.label_horizon_days)
    raw_forward_return = forward_base.divide(label_base) - 1
    if adjusted_close_available:
        result["label_forward_return_1d"] = raw_forward_return
        result["label_up_1d"] = raw_forward_return > 0
    else:
        result["label_forward_return_1d"] = pd.NA
        result["label_up_1d"] = pd.NA
    result["label_source"] = (
        LABEL_SOURCE_ADJUSTED_CLOSE if adjusted_close_available else LABEL_SOURCE_MISSING_ADJUSTED_CLOSE
    )
    result["supervised_label_eligible"] = bool(adjusted_close_available)
    result["label_start_date"] = _next_date(result, 1)
    result["label_end_date"] = _next_date(result, config.label_horizon_days)
    return result


def _string_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def build_ml_price_feature_table(
    frame: pd.DataFrame,
    *,
    config: MlPriceFeatureConfig | None = None,
    generated_at_utc: str | None = None,
) -> pd.DataFrame:
    """Return one ML feature row per ticker-date from standardized OHLCV data."""

    config = config or MlPriceFeatureConfig()
    _require_supported_label_horizon(config.label_horizon_days)
    normalized = _validate_source_frame(frame, config)
    normalized = normalized.copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        normalized[column] = _numeric_column(normalized, column)
    if "adjusted_close" in frame.columns and "adjusted_close" not in normalized.columns:
        normalized["adjusted_close"] = pd.to_numeric(frame["adjusted_close"], errors="coerce")

    feature_groups = [
        _build_group_features(group, config)
        for _, group in normalized.groupby("ticker", sort=True, dropna=False)
    ]
    if not feature_groups:
        return pd.DataFrame()

    generated_at = generated_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result = pd.concat(feature_groups, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
    result["schema_version"] = ML_PRICE_FEATURE_TABLE_SCHEMA_VERSION
    result["feature_table_kind"] = ML_PRICE_FEATURE_TABLE_KIND
    result["master_mvp_context_marker"] = MASTER_MVP_CONTEXT_MARKER
    result["row_boundary"] = ROW_BOUNDARY
    result["source_project"] = config.source_project
    result["source_universe"] = config.source_universe
    result["owner_route"] = config.owner_route
    result["feature_as_of_date"] = _string_date(result["date"])
    result["label_horizon_days"] = config.label_horizon_days
    result["split_policy"] = SPLIT_POLICY
    result["split_name"] = None
    result["random_split_allowed"] = False
    result["no_lookahead_check"] = "features_use_only_values_available_on_or_before_feature_as_of_date"
    result["no_feedback_check"] = "ml_price_features_must_not_feed_runtime_scores_rankings_reports_backtests_trading_or_auto_adoption"
    result["activation_boundary"] = "production_activation_requires_later_root_approved_gate"
    result["generated_output_boundary"] = config.generated_output_boundary
    result["table_generated_at_utc"] = generated_at

    columns = [
        "schema_version",
        "feature_table_kind",
        "master_mvp_context_marker",
        "row_boundary",
        "source_project",
        "source_universe",
        "owner_route",
        "ticker",
        "feature_as_of_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "return_1d",
        "return_5d",
        "return_20d",
        "ma5",
        "ma20",
        "close_to_ma5",
        "close_to_ma20",
        "volatility_20d",
        "volume_ma20",
        "volume_to_ma20",
        "rsi14",
        "label_horizon_days",
        "label_start_date",
        "label_end_date",
        "label_forward_return_1d",
        "label_up_1d",
        "label_source",
        "supervised_label_eligible",
        "split_policy",
        "split_name",
        "random_split_allowed",
        "no_lookahead_check",
        "no_feedback_check",
        "activation_boundary",
        "generated_output_boundary",
        "table_generated_at_utc",
    ]
    return result.loc[:, columns]


def write_ml_price_feature_table(table: pd.DataFrame, output_path: str | Path) -> Path:
    """Write an ML price feature table to CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False, encoding="utf-8")
    return path


def _read_price_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ticker": str, "code": str})
    frame = frame.rename(columns={column: CACHE_PRICE_COLUMN_ALIASES.get(column, column) for column in frame.columns})
    if "ticker" not in frame.columns and "code" not in frame.columns:
        frame["ticker"] = infer_ticker_from_price_path(path)
    if "source" not in frame.columns:
        frame["source"] = "cache"
    return frame


def read_price_csv(path: str | Path) -> pd.DataFrame:
    """Read one cached daily-price CSV using the ML feature-table aliases."""

    return _read_price_csv(Path(path))


def _read_input_csvs(paths: Iterable[Path]) -> pd.DataFrame:
    frames = [_read_price_csv(path) for path in paths]
    if not frames:
        raise ValueError("at least one input CSV is required")
    return pd.concat(frames, ignore_index=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, help="Input price CSV path.")
    parser.add_argument("--output", type=Path, required=True, help="Output ML feature table CSV path.")
    parser.add_argument("--label-horizon-days", type=int, default=1)
    parser.add_argument("--min-history-length", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    frame = _read_input_csvs(args.input)
    config = MlPriceFeatureConfig(
        label_horizon_days=args.label_horizon_days,
        min_history_length=args.min_history_length,
    )
    table = build_ml_price_feature_table(frame, config=config)
    result = {
        "schema_version": ML_PRICE_FEATURE_TABLE_SCHEMA_VERSION,
        "feature_table_kind": ML_PRICE_FEATURE_TABLE_KIND,
        "master_mvp_context_marker": MASTER_MVP_CONTEXT_MARKER,
        "row_count": int(len(table)),
        "output": str(args.output),
        "dry_run": bool(args.dry_run),
    }
    if not args.dry_run:
        write_ml_price_feature_table(table, args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
