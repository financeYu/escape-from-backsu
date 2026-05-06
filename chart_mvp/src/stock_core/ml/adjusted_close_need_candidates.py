"""Build adjusted-close need triage tables from Quant-local price inputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from stock_core.ml.quant_local_price_inputs import (
    ACTIVATION_BOUNDARY,
    NO_FEEDBACK_CHECK,
    NO_LOOKAHEAD_CHECK,
    TARGET_QUANT_LOCAL_PRICE_INPUTS,
)
from stock_core.utils.paths import PROJECT_ROOT


ADJUSTED_CLOSE_NEED_SCHEMA_VERSION = "v0_3_adjusted_close_need_candidates_0_2"
ADJUSTED_CLOSE_NEED_KIND = "adjusted_close_need_triage"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT.parent / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
DEFAULT_SOURCE_TABLE = DEFAULT_OUTPUT_DIR / "quant_local_price_source_rows.csv"
DEFAULT_FEATURE_TABLE = DEFAULT_OUTPUT_DIR / "kospi200_price_ml_feature_table.csv"
DEFAULT_EVENT_TABLE = DEFAULT_OUTPUT_DIR / "corporate_action_events.csv"
DEFAULT_OUTPUT_CSV = DEFAULT_OUTPUT_DIR / "adjusted_close_need_candidates.csv"
DEFAULT_SUMMARY_JSON = DEFAULT_OUTPUT_DIR / "adjusted_close_need_summary.json"
ROW_BOUNDARY = (
    "candidate/evidence adjusted-close need triage only; not a trading signal, "
    "valuation input, runtime ranking input, or production activation"
)
SIMPLE_FACTOR_STATUSES = {
    "derived_from_reported_ratio",
    "derived_from_changed_shares_if_one_for_one",
    "derived_from_changed_shares_if_two_for_one",
}


@dataclass(frozen=True)
class AdjustedCloseNeedConfig:
    """Configuration for adjusted-close need triage."""

    source_table: Path = DEFAULT_SOURCE_TABLE
    feature_table: Path = DEFAULT_FEATURE_TABLE
    event_table: Path = DEFAULT_EVENT_TABLE
    output_csv: Path = DEFAULT_OUTPUT_CSV
    summary_json: Path = DEFAULT_SUMMARY_JSON
    high_threshold: float = 0.30
    medium_threshold: float = 0.20


def _join_unique(values: pd.Series) -> str:
    cleaned = sorted({str(value) for value in values.dropna() if str(value)})
    return "|".join(cleaned)


def _bool_any(values: pd.Series) -> bool:
    return any(str(value).lower() == "true" for value in values.dropna())


def _safe_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _source_triage(source: pd.DataFrame, config: AdjustedCloseNeedConfig) -> pd.DataFrame:
    frame = source.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ["open", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    rows: list[dict[str, object]] = []
    for ticker, group in frame.sort_values(["ticker", "date"]).groupby("ticker", sort=True):
        close_return = group["close"].pct_change(fill_method=None)
        open_gap = group["open"].divide(group["close"].shift(1)) - 1
        abs_close_return = close_return.abs()
        abs_open_gap = open_gap.abs()
        close_idx = abs_close_return.idxmax() if abs_close_return.notna().any() else None
        gap_idx = abs_open_gap.idxmax() if abs_open_gap.notna().any() else None
        high_count = int((abs_close_return >= config.high_threshold).sum() + (abs_open_gap >= config.high_threshold).sum())
        medium_count = int(
            (abs_close_return >= config.medium_threshold).sum() + (abs_open_gap >= config.medium_threshold).sum()
        )
        priority = "high" if high_count else ("medium" if medium_count else "baseline")
        rows.append(
            {
                "ticker": ticker,
                "row_count": int(len(group)),
                "first_date": group["date"].min().strftime("%Y-%m-%d"),
                "last_date": group["date"].max().strftime("%Y-%m-%d"),
                "max_abs_close_return": _safe_float(abs_close_return.loc[close_idx]) if close_idx is not None else None,
                "max_close_return": _safe_float(close_return.loc[close_idx]) if close_idx is not None else None,
                "max_close_return_date": group.loc[close_idx, "date"].strftime("%Y-%m-%d") if close_idx is not None else "",
                "max_abs_open_gap": _safe_float(abs_open_gap.loc[gap_idx]) if gap_idx is not None else None,
                "max_open_gap": _safe_float(open_gap.loc[gap_idx]) if gap_idx is not None else None,
                "max_open_gap_date": group.loc[gap_idx, "date"].strftime("%Y-%m-%d") if gap_idx is not None else "",
                "abs_close_return_ge_30pct_count": int((abs_close_return >= config.high_threshold).sum()),
                "abs_open_gap_ge_30pct_count": int((abs_open_gap >= config.high_threshold).sum()),
                "abs_close_return_ge_20pct_count": int((abs_close_return >= config.medium_threshold).sum()),
                "abs_open_gap_ge_20pct_count": int((abs_open_gap >= config.medium_threshold).sum()),
                "priority": priority,
            }
        )
    return pd.DataFrame(rows)


def _feature_triage(feature_table: pd.DataFrame) -> pd.DataFrame:
    return (
        feature_table.groupby("ticker", sort=True)
        .agg(
            label_source_values=("label_source", _join_unique),
            supervised_label_ready=("supervised_label_eligible", _bool_any),
        )
        .reset_index()
    )


def _event_triage(event_table: pd.DataFrame) -> pd.DataFrame:
    if event_table.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "event_count",
                "event_types",
                "factor_statuses",
                "simple_factor_count",
                "terms_required_count",
            ]
        )
    events = event_table.copy()
    events["simple_factor_ready"] = events["adjustment_factor_status"].isin(SIMPLE_FACTOR_STATUSES)
    events["terms_required"] = events["adjustment_factor_status"].astype(str).str.startswith("factor_requires")
    return (
        events.groupby("ticker", sort=True)
        .agg(
            event_count=("event_id", "count"),
            event_types=("event_type", _join_unique),
            factor_statuses=("adjustment_factor_status", _join_unique),
            simple_factor_count=("simple_factor_ready", "sum"),
            terms_required_count=("terms_required", "sum"),
        )
        .reset_index()
    )


def _review_bucket(row: pd.Series) -> str:
    if int(row["event_count"]) > 0 and int(row["terms_required_count"]) > 0:
        return "official_terms_required_before_adjustment"
    if int(row["event_count"]) > 0 and int(row["simple_factor_count"]) > 0:
        return "simple_factor_adjustment_candidate"
    if row["priority"] == "high":
        return "corporate_action_or_source_quality_investigation"
    if row["priority"] == "medium":
        return "medium_jump_source_quality_review"
    return "baseline_adjusted_close_needed_for_supervised_labels"


def build_adjusted_close_need_candidates(
    *,
    config: AdjustedCloseNeedConfig,
    generated_at_utc: str | None = None,
) -> dict[str, object]:
    """Write adjusted-close need candidates and a compact summary."""

    source = pd.read_csv(
        config.source_table,
        usecols=["ticker", "date", "open", "close", "volume"],
        dtype={"ticker": str, "date": str},
    )
    features = pd.read_csv(
        config.feature_table,
        usecols=["ticker", "label_source", "supervised_label_eligible"],
        dtype={"ticker": str, "label_source": str},
    )
    events = (
        pd.read_csv(config.event_table, dtype={"ticker": str}, keep_default_na=False)
        if config.event_table.exists()
        else pd.DataFrame()
    )

    generated_at = generated_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candidates = _source_triage(source, config)
    candidates = candidates.merge(_feature_triage(features), on="ticker", how="left")
    candidates = candidates.merge(_event_triage(events), on="ticker", how="left")
    for column in ["event_count", "simple_factor_count", "terms_required_count"]:
        candidates[column] = candidates[column].fillna(0).astype(int)
    for column in ["event_types", "factor_statuses", "label_source_values"]:
        candidates[column] = candidates[column].fillna("")
    candidates["adjusted_close_needed"] = True
    candidates["supervised_label_ready"] = candidates["supervised_label_ready"].fillna(False).astype(bool)
    candidates["review_bucket"] = candidates.apply(_review_bucket, axis=1)
    candidates["boundary"] = ROW_BOUNDARY
    candidates["no_lookahead_check"] = NO_LOOKAHEAD_CHECK
    candidates["no_feedback_check"] = NO_FEEDBACK_CHECK
    candidates["activation_boundary"] = ACTIVATION_BOUNDARY
    candidates["target_quant_path"] = TARGET_QUANT_LOCAL_PRICE_INPUTS
    candidates["schema_version"] = ADJUSTED_CLOSE_NEED_SCHEMA_VERSION
    candidates["candidate_table_kind"] = ADJUSTED_CLOSE_NEED_KIND
    candidates["table_generated_at_utc"] = generated_at

    priority_order = {"high": 0, "medium": 1, "baseline": 2}
    candidates["_priority_order"] = candidates["priority"].map(priority_order).fillna(9)
    candidates = candidates.sort_values(
        ["_priority_order", "event_count", "max_abs_close_return", "ticker"],
        ascending=[True, False, False, True],
    ).drop(columns=["_priority_order"])

    output_csv = config.output_csv
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(output_csv, index=False, encoding="utf-8")

    summary = {
        "schema_version": ADJUSTED_CLOSE_NEED_SCHEMA_VERSION,
        "candidate_table_kind": ADJUSTED_CLOSE_NEED_KIND,
        "target_quant_path": TARGET_QUANT_LOCAL_PRICE_INPUTS,
        "source_table": str(config.source_table),
        "feature_table": str(config.feature_table),
        "event_table": str(config.event_table),
        "output_csv": str(output_csv),
        "unique_tickers": int(candidates["ticker"].nunique()),
        "all_tickers_need_adjusted_close_for_supervised_labels": bool(candidates["adjusted_close_needed"].all()),
        "supervised_label_ready_tickers": int(candidates["supervised_label_ready"].sum()),
        "high_priority_count": int((candidates["priority"] == "high").sum()),
        "medium_priority_count": int((candidates["priority"] == "medium").sum()),
        "baseline_required_count": int((candidates["priority"] == "baseline").sum()),
        "event_matched_ticker_count": int((candidates["event_count"] > 0).sum()),
        "high_without_event_count": int(((candidates["priority"] == "high") & (candidates["event_count"] == 0)).sum()),
        "medium_without_event_count": int(
            ((candidates["priority"] == "medium") & (candidates["event_count"] == 0)).sum()
        ),
        "simple_factor_candidate_ticker_count": int((candidates["simple_factor_count"] > 0).sum()),
        "official_terms_required_ticker_count": int((candidates["terms_required_count"] > 0).sum()),
        "review_buckets": {
            str(bucket): int(count)
            for bucket, count in candidates["review_bucket"].value_counts().sort_index().items()
        },
        "thresholds": {
            "high": f"abs(close_return) >= {config.high_threshold:.0%} or abs(open_gap) >= {config.high_threshold:.0%}",
            "medium": (
                f"abs(close_return) >= {config.medium_threshold:.0%} or "
                f"abs(open_gap) >= {config.medium_threshold:.0%}"
            ),
        },
        "boundary": ROW_BOUNDARY,
        "no_lookahead_check": NO_LOOKAHEAD_CHECK,
        "no_feedback_check": NO_FEEDBACK_CHECK,
        "activation_boundary": ACTIVATION_BOUNDARY,
        "generated_at_utc": generated_at,
    }
    config.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _update_local_price_manifest(output_csv.parent, summary)
    return summary


def _update_local_price_manifest(output_dir: Path, summary: dict[str, object]) -> None:
    manifest_path = output_dir / "local_price_input_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["adjusted_close_need_candidates"] = summary["output_csv"]
    manifest["adjusted_close_need_summary"] = str(output_dir / "adjusted_close_need_summary.json")
    manifest["adjusted_close_need_unique_tickers"] = summary["unique_tickers"]
    manifest["adjusted_close_need_review_buckets"] = summary["review_buckets"]
    manifest["adjusted_close_need_generated_at_utc"] = summary["generated_at_utc"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-table", type=Path, default=DEFAULT_SOURCE_TABLE)
    parser.add_argument("--feature-table", type=Path, default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--event-table", type=Path, default=DEFAULT_EVENT_TABLE)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--high-threshold", type=float, default=0.30)
    parser.add_argument("--medium-threshold", type=float, default=0.20)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_adjusted_close_need_candidates(
        config=AdjustedCloseNeedConfig(
            source_table=args.source_table,
            feature_table=args.feature_table,
            event_table=args.event_table,
            output_csv=args.output_csv,
            summary_json=args.summary_json,
            high_threshold=args.high_threshold,
            medium_threshold=args.medium_threshold,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
