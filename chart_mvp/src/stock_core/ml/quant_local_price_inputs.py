"""Prepare Quant-local price input tables from collected daily-price CSVs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from stock_core.ml.price_feature_table import (
    MASTER_MVP_CONTEXT_MARKER,
    MlPriceFeatureConfig,
    build_ml_price_feature_table,
    read_price_csv,
    write_ml_price_feature_table,
)
from stock_core.utils.paths import PROJECT_ROOT


SOURCE_TABLE_SCHEMA_VERSION = "v0_3_quant_local_price_input_source_rows_0_1"
SOURCE_TABLE_KIND = "quant_local_price_input_source_rows"
TARGET_QUANT_LOCAL_PRICE_INPUTS = "Quant_mvp/data/v0_3/local_price_inputs"
ROW_BOUNDARY = (
    "Quant-local daily price input row for v0.3 candidate/evidence work only; "
    "not a production scanner universe, ranking input, trading signal, valuation "
    "input, or automatic production activation."
)
NO_LOOKAHEAD_CHECK = "source_rows_are_historical_daily_bars_keyed_by_observed_trade_date"
NO_FEEDBACK_CHECK = "local_price_inputs_must_not_feed_runtime_scores_rankings_reports_trading_or_auto_adoption"
ACTIVATION_BOUNDARY = "production_activation_requires_later_root_approved_gate"


@dataclass(frozen=True)
class QuantLocalPriceInputConfig:
    """Configuration for building Quant-local price input tables."""

    input_dir: Path = PROJECT_ROOT / "data" / "historical_kospi200" / "prices"
    output_dir: Path = PROJECT_ROOT.parent / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    min_history_length: int = 20
    workers: int = 2
    sync_price_files: bool = True
    reuse_existing: bool = True


def discover_price_files(input_dir: str | Path) -> list[Path]:
    """Return source daily-price CSVs, excluding generated aggregate tables."""

    return sorted(Path(input_dir).glob("*_daily_prices.csv"))


def split_forward_reverse(paths: Iterable[Path]) -> dict[str, list[Path]]:
    """Split paths into forward and reverse shards for parallel processing."""

    ordered = sorted(paths)
    midpoint = (len(ordered) + 1) // 2
    return {
        "forward": ordered[:midpoint],
        "reverse": list(reversed(ordered[midpoint:])),
    }


def _standardize_source_rows(paths: list[Path], *, generated_at_utc: str) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = read_price_csv(path).copy()
        frame["source_file"] = str(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        combined[column] = pd.to_numeric(combined[column], errors="coerce")

    result = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    duplicate_count = int(result.duplicated(["ticker", "date"], keep="first").sum())
    if duplicate_count:
        result = result.drop_duplicates(["ticker", "date"], keep="first").reset_index(drop=True)
    result.attrs["duplicate_ticker_date_rows_removed"] = duplicate_count
    result["schema_version"] = SOURCE_TABLE_SCHEMA_VERSION
    result["input_table_kind"] = SOURCE_TABLE_KIND
    result["master_mvp_context_marker"] = MASTER_MVP_CONTEXT_MARKER
    result["row_boundary"] = ROW_BOUNDARY
    result["source_project"] = "chart_mvp"
    result["target_quant_path"] = TARGET_QUANT_LOCAL_PRICE_INPUTS
    result["owner_route"] = "master_mvp_v0_3_strategy_adoption"
    result["feature_as_of_date"] = result["date"].dt.strftime("%Y-%m-%d")
    result["date"] = result["feature_as_of_date"]
    if "source" not in result.columns:
        result["source"] = "quant_local_price_input_csv"
    result["no_lookahead_check"] = NO_LOOKAHEAD_CHECK
    result["no_feedback_check"] = NO_FEEDBACK_CHECK
    result["activation_boundary"] = ACTIVATION_BOUNDARY
    result["dedup_policy"] = "drop_duplicate_ticker_date_keep_first"
    result["duplicate_ticker_date_rows_removed_in_shard"] = duplicate_count
    result["table_generated_at_utc"] = generated_at_utc
    columns = [
        "schema_version",
        "input_table_kind",
        "master_mvp_context_marker",
        "row_boundary",
        "source_project",
        "target_quant_path",
        "owner_route",
        "ticker",
        "date",
        "feature_as_of_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "source_file",
        "no_lookahead_check",
        "no_feedback_check",
        "activation_boundary",
        "dedup_policy",
        "duplicate_ticker_date_rows_removed_in_shard",
        "table_generated_at_utc",
    ]
    return result.loc[:, columns]


def _write_frame(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sync_price_file(source_path: Path, output_dir: Path, *, reuse_existing: bool) -> dict[str, str | int]:
    target_path = output_dir / source_path.name
    if source_path.resolve() == target_path.resolve():
        return {"source_path": str(source_path), "target_path": str(target_path), "sync_status": "same_path"}

    status = "copied"
    if target_path.exists():
        if reuse_existing and source_path.stat().st_size == target_path.stat().st_size:
            if _file_digest(source_path) == _file_digest(target_path):
                status = "skipped_existing"
            else:
                shutil.copy2(source_path, target_path)
                status = "overwritten_changed"
        else:
            shutil.copy2(source_path, target_path)
            status = "overwritten"
    else:
        shutil.copy2(source_path, target_path)
    return {"source_path": str(source_path), "target_path": str(target_path), "sync_status": status}


def _sync_price_files(
    paths: list[Path],
    output_dir: Path,
    *,
    reuse_existing: bool,
) -> tuple[list[Path], list[dict[str, str | int]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [_sync_price_file(path, output_dir, reuse_existing=reuse_existing) for path in paths]
    return [Path(row["target_path"]) for row in rows], rows


def _build_shard(
    shard_name: str,
    paths: list[Path],
    output_dir: Path,
    min_history_length: int,
    generated_at_utc: str,
    sync_price_files: bool,
    reuse_existing: bool,
) -> dict[str, str | int]:
    if sync_price_files:
        working_paths, sync_rows = _sync_price_files(paths, output_dir, reuse_existing=reuse_existing)
    else:
        working_paths, sync_rows = paths, []
    source_rows = _standardize_source_rows(working_paths, generated_at_utc=generated_at_utc)
    duplicate_count = int(source_rows.attrs.get("duplicate_ticker_date_rows_removed", 0))
    source_path = output_dir / f"quant_local_price_source_rows_{shard_name}.csv"
    feature_path = output_dir / f"kospi200_price_ml_feature_table_{shard_name}.csv"
    _write_frame(source_rows, source_path)

    if source_rows.empty:
        feature_rows = pd.DataFrame()
    else:
        feature_rows = build_ml_price_feature_table(
            source_rows,
            config=MlPriceFeatureConfig(
                min_history_length=min_history_length,
                generated_output_boundary=f"{TARGET_QUANT_LOCAL_PRICE_INPUTS}/",
            ),
            generated_at_utc=generated_at_utc,
        )
    write_ml_price_feature_table(feature_rows, feature_path)
    return {
        "shard": shard_name,
        "file_count": len(paths),
        "source_rows": int(len(source_rows)),
        "feature_rows": int(len(feature_rows)),
        "duplicate_ticker_date_rows_removed": duplicate_count,
        "price_files_copied": sum(1 for row in sync_rows if row["sync_status"] == "copied"),
        "price_files_reused": sum(1 for row in sync_rows if row["sync_status"] in {"same_path", "skipped_existing"}),
        "price_files_overwritten": sum(1 for row in sync_rows if str(row["sync_status"]).startswith("overwritten")),
        "source_path": str(source_path),
        "feature_path": str(feature_path),
    }


def _inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        rows.append(
            {
                "source_file": str(path),
                "ticker": path.name.removesuffix("_daily_prices.csv"),
                "file_size_bytes": path.stat().st_size,
                "target_quant_path": TARGET_QUANT_LOCAL_PRICE_INPUTS,
            }
        )
    return pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)


def build_quant_local_price_input_tables(
    *,
    config: QuantLocalPriceInputConfig,
    generated_at_utc: str | None = None,
) -> dict[str, object]:
    """Build combined Quant-local source and ML feature tables."""

    paths = discover_price_files(config.input_dir)
    if not paths:
        raise ValueError(f"no *_daily_prices.csv files found under {config.input_dir}")

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = generated_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    shards = split_forward_reverse(paths)
    worker_count = max(1, min(config.workers, len([items for items in shards.values() if items])))
    shard_results: list[dict[str, str | int]] = []

    if worker_count == 1:
        for shard_name, shard_paths in shards.items():
            if shard_paths:
                shard_results.append(
                    _build_shard(
                        shard_name,
                        shard_paths,
                        output_dir,
                        config.min_history_length,
                        generated_at,
                        config.sync_price_files,
                        config.reuse_existing,
                    )
                )
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    _build_shard,
                    shard_name,
                    shard_paths,
                    output_dir,
                    config.min_history_length,
                    generated_at,
                    config.sync_price_files,
                    config.reuse_existing,
                )
                for shard_name, shard_paths in shards.items()
                if shard_paths
            ]
            for future in futures:
                shard_results.append(future.result())

    source_parts = [pd.read_csv(result["source_path"], dtype={"ticker": str}) for result in shard_results]
    feature_parts = [pd.read_csv(result["feature_path"], dtype={"ticker": str}) for result in shard_results]
    source_table = pd.concat(source_parts, ignore_index=True).sort_values(["ticker", "feature_as_of_date"])
    feature_table = pd.concat(feature_parts, ignore_index=True).sort_values(["ticker", "feature_as_of_date"])

    source_path = _write_frame(source_table, output_dir / "quant_local_price_source_rows.csv")
    feature_path = write_ml_price_feature_table(feature_table, output_dir / "kospi200_price_ml_feature_table.csv")
    inventory_path = _write_frame(_inventory(paths), output_dir / "local_price_input_inventory.csv")
    readme_path = output_dir / "README.generated.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Generated Local Price Input Tables",
                "",
                "`Quant_mvp/data/v0_3/local_price_inputs` now contains both raw daily-price CSVs and aggregate tables.",
                "",
                "- `quant_local_price_source_rows.csv`: normalized source OHLCV rows from every `*_daily_prices.csv` file.",
                "- `kospi200_price_ml_feature_table.csv`: ML-useful processed price feature table with Master MVP context marker.",
                "- `local_price_input_inventory.csv`: source file inventory.",
                "- Raw `*_daily_prices.csv` files are synchronized from chart_mvp collected prices when this builder is run from that source.",
                "- Shard files ending in `_forward.csv` and `_reverse.csv` were produced by parallel forward/reverse processing.",
                "",
                "Boundary: candidate/evidence use only; no runtime ranking, trading, valuation, or production activation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": SOURCE_TABLE_SCHEMA_VERSION,
        "target_quant_path": TARGET_QUANT_LOCAL_PRICE_INPUTS,
        "input_dir": str(config.input_dir),
        "output_dir": str(output_dir),
        "file_count": len(paths),
        "source_row_count": int(len(source_table)),
        "feature_row_count": int(len(feature_table)),
        "duplicate_ticker_date_rows_removed": int(
            sum(int(result.get("duplicate_ticker_date_rows_removed", 0)) for result in shard_results)
        ),
        "price_files_copied": int(sum(int(result.get("price_files_copied", 0)) for result in shard_results)),
        "price_files_reused": int(sum(int(result.get("price_files_reused", 0)) for result in shard_results)),
        "price_files_overwritten": int(sum(int(result.get("price_files_overwritten", 0)) for result in shard_results)),
        "source_table": str(source_path),
        "feature_table": str(feature_path),
        "inventory": str(inventory_path),
        "readme": str(readme_path),
        "parallel_policy": "forward_shard_and_reverse_shard",
        "shards": sorted(shard_results, key=lambda item: str(item["shard"])),
        "master_mvp_context_marker": MASTER_MVP_CONTEXT_MARKER,
        "row_boundary": ROW_BOUNDARY,
        "no_lookahead_check": NO_LOOKAHEAD_CHECK,
        "no_feedback_check": NO_FEEDBACK_CHECK,
        "activation_boundary": ACTIVATION_BOUNDARY,
        "generated_at_utc": generated_at,
    }
    manifest_path = output_dir / "local_price_input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=QuantLocalPriceInputConfig.input_dir)
    parser.add_argument("--output-dir", type=Path, default=QuantLocalPriceInputConfig.output_dir)
    parser.add_argument("--min-history-length", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--no-sync-price-files", action="store_true")
    parser.add_argument("--no-reuse-existing", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_quant_local_price_input_tables(
        config=QuantLocalPriceInputConfig(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            min_history_length=args.min_history_length,
            workers=args.workers,
            sync_price_files=not args.no_sync_price_files,
            reuse_existing=not args.no_reuse_existing,
        )
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
