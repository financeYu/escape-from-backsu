"""Prepare corporate-action event inputs for adjusted-close construction."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from stock_core.ml.price_feature_table import MASTER_MVP_CONTEXT_MARKER
from stock_core.ml.quant_local_price_inputs import (
    ACTIVATION_BOUNDARY,
    TARGET_QUANT_LOCAL_PRICE_INPUTS,
)
from stock_core.utils.paths import PROJECT_ROOT


EVENT_SCHEMA_VERSION = "v0_3_kospi200_corporate_action_events_0_1"
EVENT_TABLE_KIND = "kospi200_adjusted_close_event_inputs"
DEFAULT_EVENT_SOURCE = PROJECT_ROOT / "data" / "reference" / "kospi200_corporate_action_events.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT.parent / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
EVENT_TABLE_FILE = "corporate_action_events.csv"
EVENT_SUMMARY_FILE = "corporate_action_events_summary.json"
EVENT_BOUNDARY = (
    "candidate/evidence adjusted-close input only; not a trading signal or "
    "production activation"
)
EVENT_NO_LOOKAHEAD_CHECK = "event_date_is_public_event_or_listing_date; apply only to rows strictly before event date"
EVENT_NO_FEEDBACK_CHECK = "do_not_feed_adjusted_output_to_runtime_scores_rankings_reports_trading_or_auto_adoption"

REQUIRED_COLUMNS = [
    "schema_version",
    "event_table_kind",
    "master_mvp_context_marker",
    "target_quant_path",
    "owner_route",
    "ticker",
    "company_name",
    "event_id",
    "event_date",
    "listing_date",
    "event_type",
    "event_subtype",
    "event_name",
    "price_adjustment_factor_for_prior_rows",
    "share_adjustment_factor_for_prior_rows",
    "adjustment_factor_status",
    "adjustment_direction",
    "ratio_text",
    "source_name",
    "source_url",
    "source_as_of_date",
    "source_confidence",
    "notes",
    "boundary",
    "no_lookahead_check",
    "no_feedback_check",
    "activation_boundary",
]

SIMPLE_FACTOR_STATUSES = {
    "derived_from_reported_ratio",
    "derived_from_changed_shares_if_one_for_one",
    "derived_from_changed_shares_if_two_for_one",
}


@dataclass(frozen=True)
class CorporateActionEventConfig:
    """Configuration for exporting adjusted-close event inputs."""

    source_csv: Path = DEFAULT_EVENT_SOURCE
    output_dir: Path = DEFAULT_OUTPUT_DIR


def read_corporate_action_events(path: str | Path) -> pd.DataFrame:
    """Read event seed data with ticker and factor columns preserved."""

    frame = pd.read_csv(
        path,
        dtype={
            "ticker": str,
            "event_id": str,
            "price_adjustment_factor_for_prior_rows": str,
            "share_adjustment_factor_for_prior_rows": str,
        },
        keep_default_na=False,
    )
    return frame


def _missing_columns(columns: Iterable[str]) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in set(columns)]


def validate_corporate_action_events(events: pd.DataFrame) -> None:
    """Validate the event table contract before export."""

    missing = _missing_columns(events.columns)
    if missing:
        raise ValueError(f"missing required corporate-action event columns: {missing}")
    if events.empty:
        raise ValueError("corporate-action event table is empty")
    if events["event_id"].duplicated().any():
        duplicates = sorted(events.loc[events["event_id"].duplicated(), "event_id"].unique())
        raise ValueError(f"duplicate corporate-action event_id values: {duplicates}")

    expected_constants = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_table_kind": EVENT_TABLE_KIND,
        "master_mvp_context_marker": MASTER_MVP_CONTEXT_MARKER,
        "target_quant_path": TARGET_QUANT_LOCAL_PRICE_INPUTS,
        "boundary": EVENT_BOUNDARY,
        "no_lookahead_check": EVENT_NO_LOOKAHEAD_CHECK,
        "no_feedback_check": EVENT_NO_FEEDBACK_CHECK,
        "activation_boundary": ACTIVATION_BOUNDARY,
    }
    for column, expected in expected_constants.items():
        bad_values = sorted(str(value) for value in events.loc[events[column] != expected, column].unique())
        if bad_values:
            raise ValueError(f"{column} has values outside contract: {bad_values[:5]}")

    date_columns = ["event_date", "listing_date", "source_as_of_date"]
    for column in date_columns:
        parsed = pd.to_datetime(events[column], errors="coerce")
        if parsed.isna().any():
            bad = events.loc[parsed.isna(), ["event_id", column]].to_dict("records")
            raise ValueError(f"{column} contains invalid dates: {bad[:5]}")

    simple = events["adjustment_factor_status"].isin(SIMPLE_FACTOR_STATUSES)
    for column in ["price_adjustment_factor_for_prior_rows", "share_adjustment_factor_for_prior_rows"]:
        numeric = pd.to_numeric(events.loc[simple, column], errors="coerce")
        if numeric.isna().any() or (numeric <= 0).any():
            bad = events.loc[simple].loc[numeric.isna() | (numeric <= 0), ["event_id", column]]
            raise ValueError(f"{column} must be positive for simple factor events: {bad.to_dict('records')[:5]}")


def build_corporate_action_event_inputs(
    *,
    config: CorporateActionEventConfig,
    generated_at_utc: str | None = None,
) -> dict[str, object]:
    """Export corporate-action events beside Quant-local price inputs."""

    generated_at = generated_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    events = read_corporate_action_events(config.source_csv)
    validate_corporate_action_events(events)

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    event_path = output_dir / EVENT_TABLE_FILE
    events = events.sort_values(["ticker", "event_date", "event_id"]).reset_index(drop=True)
    events["table_generated_at_utc"] = generated_at
    events.to_csv(event_path, index=False, encoding="utf-8")

    simple = events["adjustment_factor_status"].isin(SIMPLE_FACTOR_STATUSES)
    needs_terms = events["adjustment_factor_status"].str.startswith("factor_requires")
    summary = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_table_kind": EVENT_TABLE_KIND,
        "target_quant_path": TARGET_QUANT_LOCAL_PRICE_INPUTS,
        "source_csv": str(config.source_csv),
        "event_table": str(event_path),
        "event_count": int(len(events)),
        "ticker_count": int(events["ticker"].nunique()),
        "simple_factor_event_count": int(simple.sum()),
        "official_terms_required_event_count": int(needs_terms.sum()),
        "event_types": {
            str(event_type): int(count)
            for event_type, count in events["event_type"].value_counts().sort_index().items()
        },
        "adjustment_factor_status": {
            str(status): int(count)
            for status, count in events["adjustment_factor_status"].value_counts().sort_index().items()
        },
        "master_mvp_context_marker": MASTER_MVP_CONTEXT_MARKER,
        "boundary": EVENT_BOUNDARY,
        "no_lookahead_check": EVENT_NO_LOOKAHEAD_CHECK,
        "no_feedback_check": EVENT_NO_FEEDBACK_CHECK,
        "activation_boundary": ACTIVATION_BOUNDARY,
        "adjusted_close_usage_note": (
            "Apply simple factors only to prior OHLCV rows after official terms are accepted; "
            "events marked factor_requires_* are flags for manual term completion."
        ),
        "generated_at_utc": generated_at,
    }
    summary_path = output_dir / EVENT_SUMMARY_FILE
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["summary"] = str(summary_path)
    _update_local_price_manifest(output_dir, summary, event_path, summary_path)
    _write_readme(output_dir)
    return summary


def _update_local_price_manifest(output_dir: Path, summary: dict[str, object], event_path: Path, summary_path: Path) -> None:
    manifest_path = output_dir / "local_price_input_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corporate_action_events"] = str(event_path)
    manifest["corporate_action_events_summary"] = str(summary_path)
    manifest["corporate_action_event_count"] = summary["event_count"]
    manifest["corporate_action_event_ticker_count"] = summary["ticker_count"]
    manifest["adjusted_close_event_usage_note"] = summary["adjusted_close_usage_note"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_readme(output_dir: Path) -> None:
    readme_path = output_dir / "README.generated.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Generated Local Price Input Tables",
                "",
                "`Quant_mvp/data/v0_3/local_price_inputs` now contains raw daily-price CSVs, aggregate price tables, and adjusted-close event inputs.",
                "",
                "- `quant_local_price_source_rows.csv`: normalized source OHLCV rows from every `*_daily_prices.csv` file.",
                "- `kospi200_price_ml_feature_table.csv`: ML-useful processed price feature table with Master MVP context marker.",
                "- `local_price_input_inventory.csv`: source file inventory.",
                "- `corporate_action_events.csv`: split, reverse split, capital reduction, bonus issue, paid issue, and demerger events needed to construct adjusted close.",
                "- `corporate_action_events_summary.json`: readiness counts for simple factors versus events needing official terms.",
                "- Shard files ending in `_forward.csv` and `_reverse.csv` were produced by parallel forward/reverse processing.",
                "",
                "Boundary: candidate/evidence use only; no runtime ranking, trading, valuation, or production activation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", type=Path, default=CorporateActionEventConfig.source_csv)
    parser.add_argument("--output-dir", type=Path, default=CorporateActionEventConfig.output_dir)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_corporate_action_event_inputs(
        config=CorporateActionEventConfig(source_csv=args.source_csv, output_dir=args.output_dir)
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
