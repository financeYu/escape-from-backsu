"""Dynamic v1.5 collection candidate selection.

This module ranks the current pending handoff rows before live data collection.
It only chooses diagnostic collection targets; it never promotes valuation
scoring or runtime ranking behavior.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


SCHEMA_VERSION = "v1_5_dynamic_collection_candidate_selection_v1_0"
SELECTION_POLICY = "v1_5_dynamic_collection_candidate_selection_policy_v1"
PER_PBR_FIELDS = {"price_to_earnings", "price_to_book"}
QUALITY_PROFITABILITY_FIELDS = {"debt_ratio", "net_margin", "operating_margin", "roe"}
DIVIDEND_FIELDS = {"dividend_yield"}

SELECTION_COLUMNS = [
    "ticker",
    "selection_source",
    "selection_purpose",
    "candidate_count",
    "per_pbr_field_count",
    "quality_profitability_field_count",
    "dividend_field_count",
    "source_file_count",
    "krx_metadata_row_count",
    "source_rank_slot_best",
    "source_average_traded_value_max",
    "source_market_cap_proxy_max",
    "source_candidate_priority_score",
    "latest_evaluation_date",
    "collection_priority_score",
    "collection_target_status",
    "collection_target_reason",
    "selection_score",
    "selection_status",
    "selection_reason",
    "scoring_activation_allowed",
]


@dataclass(frozen=True)
class V15CollectionCandidateSelectionConfig:
    pending_handoff_path: Path
    output_csv_path: Path
    output_manifest_path: Path
    selection_purpose: str
    max_codes: int = 1
    require_per_pbr_need: bool = False
    source_candidate_handoff_path: Path | None = None


def build_v1_5_collection_candidate_selection(
    config: V15CollectionCandidateSelectionConfig,
) -> dict[str, object]:
    """Write a ranked collection target list and return selected tickers."""

    rows = build_v1_5_collection_candidate_selection_rows(
        config.pending_handoff_path,
        selection_purpose=config.selection_purpose,
        max_codes=config.max_codes,
        require_per_pbr_need=config.require_per_pbr_need,
        source_candidate_handoff_path=config.source_candidate_handoff_path,
    )
    selected_codes = [row["ticker"] for row in rows if row["collection_target_status"] == "selected"]
    config.output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(config.output_csv_path, rows)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "selection_policy": SELECTION_POLICY,
        "selection_purpose": config.selection_purpose,
        "selection_source": str(config.pending_handoff_path),
        "source_candidate_handoff_path": str(config.source_candidate_handoff_path or ""),
        "output_csv": str(config.output_csv_path),
        "max_codes": config.max_codes,
        "hardcoded_tickers_used": False,
        "candidate_generation_mode": "runtime_from_pending_handoff",
        "candidate_selection_mode": "ranked_best_fit",
        "krx_preference_rule": "prefer_rows_with_krx_sector_or_industry_metadata",
        "row_count": len(rows),
        "selected_count": len(selected_codes),
        "selected_codes": selected_codes,
        "candidate_codes": selected_codes,
        "candidate_code_pool": [row["ticker"] for row in rows],
        "scoring_activation_allowed": False,
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "rows": rows,
    }
    config.output_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "rows": rows,
        "selected_codes": selected_codes,
        "output_csv": str(config.output_csv_path),
        "output_manifest": str(config.output_manifest_path),
        "manifest": manifest,
    }


def build_v1_5_collection_candidate_selection_rows(
    pending_handoff_path: Path,
    *,
    selection_purpose: str,
    max_codes: int = 1,
    require_per_pbr_need: bool = False,
    source_candidate_handoff_path: Path | None = None,
) -> list[dict[str, str]]:
    with pending_handoff_path.open(encoding="utf-8-sig", newline="") as handle:
        pending_rows = list(csv.DictReader(handle))
    source_candidate_by_ticker = (
        _source_candidate_rows_by_ticker(source_candidate_handoff_path)
        if source_candidate_handoff_path and source_candidate_handoff_path.exists()
        else {}
    )

    grouped: dict[str, dict[str, object]] = {}
    for row in pending_rows:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        entry = grouped.setdefault(
            ticker,
            {
                "ticker": ticker,
                "candidate_ids": set(),
                "per_pbr_field_count": 0,
                "quality_profitability_field_count": 0,
                "dividend_field_count": 0,
                "source_files": set(),
                "krx_metadata_row_count": 0,
                "latest_evaluation_date": "",
            },
        )
        _as_string_set(entry["candidate_ids"]).add(str(row.get("candidate_id", "")).strip())
        field_name = str(row.get("field_name", "")).strip()
        if field_name in PER_PBR_FIELDS:
            entry["per_pbr_field_count"] = int(entry["per_pbr_field_count"]) + 1
        if field_name in QUALITY_PROFITABILITY_FIELDS:
            entry["quality_profitability_field_count"] = int(entry["quality_profitability_field_count"]) + 1
        if field_name in DIVIDEND_FIELDS:
            entry["dividend_field_count"] = int(entry["dividend_field_count"]) + 1
        source_path = str(row.get("source_financial_cache_path") or "").strip()
        if source_path:
            _as_string_set(entry["source_files"]).add(source_path)
        if str(row.get("sector_id") or row.get("industry_name") or "").strip():
            entry["krx_metadata_row_count"] = int(entry["krx_metadata_row_count"]) + 1
        evaluation_date = str(row.get("evaluation_date") or "").strip()
        if evaluation_date > str(entry["latest_evaluation_date"]):
            entry["latest_evaluation_date"] = evaluation_date

    ranked = []
    for entry in grouped.values():
        candidate_count = len(_as_string_set(entry["candidate_ids"]))
        per_pbr_count = int(entry["per_pbr_field_count"])
        quality_count = int(entry["quality_profitability_field_count"])
        dividend_count = int(entry["dividend_field_count"])
        source_count = len(_as_string_set(entry["source_files"]))
        krx_count = int(entry["krx_metadata_row_count"])
        source_candidate = source_candidate_by_ticker.get(str(entry["ticker"]), {})
        rank_slot = _safe_int(source_candidate.get("rank_slot"), default=0)
        average_traded_value = _safe_float(source_candidate.get("average_traded_value"), default=0.0)
        market_cap_proxy = _safe_float(source_candidate.get("market_cap_proxy"), default=0.0)
        source_candidate_priority_score = max(0, 60 - rank_slot) if rank_slot > 0 else 0
        collection_need_score = (
            per_pbr_count * 30
            + quality_count * 10
            + dividend_count * 8
            + source_count * 5
            + min(krx_count, 7) * 3
            + source_candidate_priority_score
        )
        collection_priority_score = collection_need_score + candidate_count
        if require_per_pbr_need and per_pbr_count == 0:
            collection_target_status = "not_selected_no_per_pbr_need"
            collection_target_reason = "per_pbr_policy_collection_requires_per_or_pbr_pending_field"
        elif collection_need_score <= 0:
            collection_target_status = "not_selected_no_collection_need"
            collection_target_reason = "no_pending_collection_need_detected"
        else:
            collection_target_status = "eligible"
            collection_target_reason = "runtime_candidate_handoff_best_fit_not_hardcoded"
        ranked.append(
            {
                "ticker": str(entry["ticker"]),
                "selection_source": str(pending_handoff_path),
                "selection_purpose": selection_purpose,
                "candidate_count": str(candidate_count),
                "per_pbr_field_count": str(per_pbr_count),
                "quality_profitability_field_count": str(quality_count),
                "dividend_field_count": str(dividend_count),
                "source_file_count": str(source_count),
                "krx_metadata_row_count": str(krx_count),
                "source_rank_slot_best": str(rank_slot) if rank_slot else "",
                "source_average_traded_value_max": _format_float(average_traded_value),
                "source_market_cap_proxy_max": _format_float(market_cap_proxy),
                "source_candidate_priority_score": str(source_candidate_priority_score),
                "latest_evaluation_date": str(entry["latest_evaluation_date"]),
                "collection_priority_score": str(collection_priority_score),
                "collection_target_status": collection_target_status,
                "collection_target_reason": collection_target_reason,
                "selection_score": str(collection_priority_score),
                "selection_status": collection_target_status,
                "selection_reason": collection_target_reason,
                "scoring_activation_allowed": "false",
            }
        )

    ranked.sort(key=lambda row: (-int(row["collection_priority_score"]), row["ticker"]))
    limit = max_codes if max_codes > 0 else len(ranked)
    selected = 0
    for row in ranked:
        if row["collection_target_status"] == "eligible" and selected < limit:
            row["collection_target_status"] = "selected"
            row["selection_status"] = "selected"
            row["selection_reason"] = "selected_by_runtime_best_fit_candidate_generation"
            selected += 1
        elif row["collection_target_status"] == "eligible":
            row["collection_target_status"] = "not_selected_limit"
            row["selection_status"] = "not_selected_limit"
            row["selection_reason"] = "eligible_but_lower_ranked_than_runtime_selection_limit"
    return ranked


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SELECTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _as_string_set(value: object) -> set[str]:
    return value if isinstance(value, set) else set()


def _source_candidate_rows_by_ticker(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = str(row.get("candidate_ticker") or row.get("ticker") or "").strip()
        if not ticker:
            continue
        current = result.get(ticker)
        if current is None or _source_candidate_sort_key(row) < _source_candidate_sort_key(current):
            result[ticker] = row
    return result


def _source_candidate_sort_key(row: dict[str, str]) -> tuple[int, float, str]:
    rank_slot = _safe_int(row.get("rank_slot"), default=999999)
    average_traded_value = _safe_float(row.get("average_traded_value"), default=0.0)
    ticker = str(row.get("candidate_ticker") or row.get("ticker") or "")
    return (rank_slot, -average_traded_value, ticker)


def _safe_int(value: object, *, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, *, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _format_float(value: float) -> str:
    return f"{value:.6f}" if value else ""
