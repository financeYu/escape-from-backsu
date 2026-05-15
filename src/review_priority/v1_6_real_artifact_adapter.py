"""Build a narrow real-artifact input CSV for the v1.6 runner."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACTS = {
    "v1_3_liquidity": Path("chart_mvp/data/v1_3_liquidity/v1_3_candidate_liquidity_handoff_records_latest.csv"),
    "v1_4_revision": Path("chart_mvp/data/v1_4_revision/v1_4_candidate_revision_diagnostic_handoff_latest.csv"),
    "v1_5_feature_readiness": Path("chart_mvp/data/v1_5_valuation/v1_5_feature_level_readiness_latest.csv"),
    "v1_5_to_v1_6_handoff": Path(
        "chart_mvp/data/v1_5_valuation/v1_6_readiness_status_handoff_from_v1_5_latest.csv"
    ),
    "v1_5_incremental_comparison": Path(
        "chart_mvp/data/v1_5_valuation/v1_5_incremental_valuation_real_comparison_latest.csv"
    ),
}
MISSING_ARTIFACTS = {
    "v1_1_net_profitability": "latest v1.1 net profitability project output not found",
    "v1_2_baseline_ml_selector": "latest v1.2 baseline ML selector project output not found",
}


def build_real_available_v1_6_input(
    output_csv: str | Path,
    dependency_report: str | Path,
    artifacts: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Create a v1.6 runner input from real artifacts when join keys are clear."""

    artifact_paths = artifacts or DEFAULT_ARTIFACTS
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    dependency_notes = dict(MISSING_ARTIFACTS)
    found_artifacts: dict[str, str] = {}

    handoff_path = artifact_paths["v1_5_to_v1_6_handoff"]
    if not handoff_path.exists():
        raise FileNotFoundError(f"required v1.5-to-v1.6 handoff missing: {handoff_path}")
    found_artifacts["v1_5_to_v1_6_handoff"] = str(handoff_path)
    for row in _read_csv(handoff_path):
        key = (row["candidate_id"], row["ticker"], row["evaluation_date"])
        rows_by_key[key] = {
            "candidate_id": row["candidate_id"],
            "ticker": row["ticker"],
            "evaluation_date": row["evaluation_date"],
            "evidence_status": row.get("candidate_overall_readiness_status", ""),
            "overall_valuation_status": row.get("overall_valuation_status", ""),
            "overall_quality_profitability_status": row.get("overall_quality_profitability_status", ""),
            "price_to_earnings_canonical_formula_status": row.get(
                "price_to_earnings_canonical_formula_status", ""
            ),
            "price_to_book_canonical_formula_status": row.get(
                "price_to_book_canonical_formula_status", ""
            ),
            "price_to_earnings_vendor_reference_status": row.get(
                "price_to_earnings_vendor_reference_status", ""
            ),
            "price_to_book_vendor_reference_status": row.get(
                "price_to_book_vendor_reference_status", ""
            ),
            "dividend_yield_status": row.get("dividend_yield_status", ""),
            "incremental_evidence_status": row.get("incremental_evidence_status", ""),
            "candidate_overall_readiness_status": row.get("candidate_overall_readiness_status", ""),
            "limitations": row.get("limitations", ""),
            "manual_review_required": row.get("manual_review_required", ""),
            "source_artifact": str(handoff_path),
            "lineage_ref": "v1_5_to_v1_6_handoff",
        }

    _merge_v1_3(rows_by_key, artifact_paths, found_artifacts, dependency_notes)
    _merge_v1_4(rows_by_key, artifact_paths, found_artifacts, dependency_notes)
    _merge_v1_5_feature_readiness(rows_by_key, artifact_paths, found_artifacts, dependency_notes)
    _merge_v1_5_incremental(rows_by_key, artifact_paths, found_artifacts, dependency_notes)

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate_id",
        "ticker",
        "evaluation_date",
        "horizon_id",
        "evidence_status",
        "overall_valuation_status",
        "overall_quality_profitability_status",
        "price_to_earnings_canonical_formula_status",
        "price_to_book_canonical_formula_status",
        "price_to_earnings_vendor_reference_status",
        "price_to_book_vendor_reference_status",
        "dividend_yield_status",
        "incremental_evidence_status",
        "candidate_overall_readiness_status",
        "revision_diagnostic_status",
        "technical_ml_baseline_status",
        "comparison_status",
        "limitations",
        "manual_review_required",
        "source_artifact",
        "lineage_ref",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_by_key.values():
            writer.writerow({field: row.get(field, "") for field in fieldnames})

    report = {
        "schema_version": "v1_6_real_artifact_adapter_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "join_keys": ["candidate_id", "ticker", "evaluation_date"],
        "horizon_join_key_available": False,
        "merged_row_count": len(rows_by_key),
        "found_artifacts": found_artifacts,
        "missing_or_limited_artifacts": dependency_notes,
        "output_csv": str(output_path),
        "adapter_policy": (
            "No valuation scores are consumed. Status/readiness flags and lineage only are merged. "
            "Missing coverage/data_quality/stability remain missing for the v1.6 runner."
        ),
    }
    report_path = Path(dependency_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _merge_v1_3(
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]],
    artifacts: dict[str, Path],
    found: dict[str, str],
    notes: dict[str, str],
) -> None:
    path = artifacts["v1_3_liquidity"]
    if not path.exists():
        notes["v1_3_liquidity"] = "artifact missing"
        return
    found["v1_3_liquidity"] = str(path)
    lookup = {
        (row["candidate_id"], row["candidate_ticker"], row["as_of_date"]): row
        for row in _read_csv(path)
    }
    _append_lineage(rows_by_key, lookup, path, "v1_3_liquidity", "liquidity_proxy_source_ref")


def _merge_v1_4(
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]],
    artifacts: dict[str, Path],
    found: dict[str, str],
    notes: dict[str, str],
) -> None:
    path = artifacts["v1_4_revision"]
    if not path.exists():
        notes["v1_4_revision"] = "artifact missing"
        return
    found["v1_4_revision"] = str(path)
    lookup = {
        (row["candidate_id"], row["source_ticker"], row["selection_reference_date"]): row
        for row in _read_csv(path)
    }
    for key, base in rows_by_key.items():
        row = lookup.get(key)
        if not row:
            notes[f"v1_4_revision_missing_join:{key[0]}"] = "candidate join key not found"
            continue
        base["revision_diagnostic_status"] = _map_revision_status(row.get("diagnostic_status", ""))
        _append_value(base, "limitations", row.get("diagnostic_status", ""))
        _append_value(base, "limitations", row.get("diagnostic_reason_codes", ""))
        _append_value(base, "source_artifact", str(path))
        _append_value(base, "lineage_ref", row.get("revision_source_ref", "") or "v1_4_revision")


def _merge_v1_5_feature_readiness(
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]],
    artifacts: dict[str, Path],
    found: dict[str, str],
    notes: dict[str, str],
) -> None:
    path = artifacts["v1_5_feature_readiness"]
    if not path.exists():
        notes["v1_5_feature_readiness"] = "artifact missing"
        return
    found["v1_5_feature_readiness"] = str(path)
    by_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in _read_csv(path):
        by_key[(row["candidate_id"], row["ticker"], row["evaluation_date"])].append(
            f"{row.get('field_name', '')}:{row.get('feature_readiness_status', '')}"
        )
    for key, base in rows_by_key.items():
        values = by_key.get(key)
        if values:
            _append_value(base, "limitations", "feature_readiness=" + ";".join(values))
            _append_value(base, "source_artifact", str(path))
            _append_value(base, "lineage_ref", "v1_5_feature_level_readiness")


def _merge_v1_5_incremental(
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]],
    artifacts: dict[str, Path],
    found: dict[str, str],
    notes: dict[str, str],
) -> None:
    path = artifacts["v1_5_incremental_comparison"]
    if not path.exists():
        notes["v1_5_incremental_comparison"] = "artifact missing"
        return
    found["v1_5_incremental_comparison"] = str(path)
    lookup = {
        (row["candidate_id"], row["ticker"], row["evaluation_date"]): row
        for row in _read_csv(path)
    }
    for key, base in rows_by_key.items():
        row = lookup.get(key)
        if not row:
            continue
        base["horizon_id"] = row.get("horizon_id", "")
        base["technical_ml_baseline_status"] = _map_incremental_status(
            row.get("technical_ml_baseline_status", "")
        )
        base["comparison_status"] = row.get("comparison_status", "")
        _append_value(base, "limitations", row.get("technical_ml_baseline_status", ""))
        _append_value(base, "limitations", row.get("reason_code", ""))
        _append_value(base, "source_artifact", str(path))
        _append_value(base, "lineage_ref", row.get("evidence_id", "") or "v1_5_incremental")


def _append_lineage(
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]],
    lookup: dict[tuple[str, str, str], dict[str, str]],
    path: Path,
    fallback_ref: str,
    lineage_column: str,
) -> None:
    for key, base in rows_by_key.items():
        row = lookup.get(key)
        if not row:
            continue
        _append_value(base, "source_artifact", str(path))
        _append_value(base, "lineage_ref", row.get(lineage_column, "") or fallback_ref)


def _append_value(row: dict[str, Any], column: str, value: str) -> None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return
    existing = str(row.get(column, "") or "").strip()
    if not existing:
        row[column] = cleaned
    elif cleaned not in existing.split("|"):
        row[column] = existing + "|" + cleaned


def _map_revision_status(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned == "diagnostic_ready":
        return "diagnostic_ready"
    if cleaned:
        return "insufficient_data"
    return ""


def _map_incremental_status(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned in {"diagnostic_ready", "partial_diagnostic_ready", "skipped_missing_baseline_artifacts"}:
        return cleaned
    if cleaned.startswith("skipped_") or cleaned:
        return "skipped_missing_baseline_artifacts"
    return ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build real available v1.6 runner input.")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--dependency-report", required=True)
    args = parser.parse_args(argv)
    report = build_real_available_v1_6_input(args.output_csv, args.dependency_report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
