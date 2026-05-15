"""v1.6 confidence, robustness, and manual review priority runner.

The runner consumes v1.1-v1.5 evidence/status rows and emits conservative
manual-review-only diagnostics. It never consumes or creates valuation scores,
production ranks, execution instructions, or future-return claims.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import re
import tomllib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Quant_mvp.backtest_mvp.confidence_review_priority_v1_6 import (
    ALLOWED_INPUT_STATUS_VALUES,
    ALLOWED_REASON_CODES,
    CONTRACT_VERSION,
    DEFAULT_OUTPUT_DIR,
    EVIDENCE_ONLY_NOTICE,
    FORBIDDEN_COLUMN_NAMES,
    GENERATED_OUTPUT_PATHS,
    MANUAL_REVIEW_ONLY_NOTICE,
    READINESS_VERDICTS,
    THRESHOLD_CONFIG_CANDIDATES,
    validate_v1_6_columns,
)


REQUIRED_IDENTITY_COLUMNS = ("candidate_id", "ticker", "evaluation_date")
COMPONENT_COLUMNS = ("coverage", "data_quality", "stability")
OPTIONAL_LINEAGE_COLUMNS = ("source_artifact", "lineage_ref")
FORBIDDEN_LANGUAGE_PATTERNS = (
    "production ranking",
    "trading recommendation",
    "order instruction",
    "rebalance instruction",
)
FORBIDDEN_RUNTIME_WORDS = (
    "valuation_score",
    "fundamental_score",
    "technical_composite_score",
    "final_composite_score",
    "forward_return",
    "future_return",
    "expected_return",
    "alpha",
    "signal",
)
STATUS_COLUMNS = (
    "evidence_status",
    "candidate_overall_readiness_status",
    "incremental_evidence_status",
    "overall_valuation_status",
    "overall_quality_profitability_status",
    "price_to_earnings_canonical_formula_status",
    "price_to_book_canonical_formula_status",
    "price_to_earnings_vendor_reference_status",
    "price_to_book_vendor_reference_status",
)


class V16InputError(ValueError):
    """Raised when v1.6 input would cross the manual-review contract."""


def run_v1_6_confidence_review_priority(
    input_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    config_path: str | Path | None = None,
    input_mode: str = "project_artifacts",
) -> dict[str, Any]:
    """Run the v1.6 manual review priority packet generator."""

    rows = _read_csv_rows(Path(input_path))
    _validate_input(rows)
    thresholds, threshold_source, config_status = _load_thresholds(config_path)

    confidence_rows = _build_confidence_rows(rows, thresholds, config_status)
    horizon_rows = _build_horizon_rows(rows, confidence_rows, thresholds, config_status)
    split_rows = _build_split_rows(rows, thresholds, config_status)
    layer_rows = _build_layer_rows(rows, thresholds, threshold_source, config_status)
    composite_rows = _build_composite_rows(
        rows,
        confidence_rows,
        horizon_rows,
        split_rows,
        layer_rows,
        config_status,
    )
    readiness_packet = _build_readiness_packet(
        rows,
        composite_rows,
        horizon_rows,
        split_rows,
        layer_rows,
        threshold_source,
        config_status,
        input_mode,
    )

    output_base = Path(output_dir)
    output_base.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "confidence": output_base / "v1_6_confidence_score_manifest_latest.csv",
        "horizon": output_base / "v1_6_horizon_stability_report_latest.csv",
        "split": output_base / "v1_6_split_stability_report_latest.csv",
        "layer": output_base / "v1_6_layer_redundancy_report_latest.csv",
        "composite": output_base / "v1_6_composite_review_priority_manifest_latest.csv",
        "readiness": output_base / "v1_6_v2_0_readiness_packet_latest.json",
        "readiness_md": output_base / "v1_6_v2_0_readiness_packet_latest.md",
        "guardrail_report": output_base
        / "v1_6_integration_guardrail_lineage_packet_test_report_latest.json",
    }
    readiness_packet["output_file_names"] = [str(path) for path in output_paths.values()]
    _write_csv(output_paths["confidence"], confidence_rows)
    _write_csv(output_paths["horizon"], horizon_rows)
    _write_csv(output_paths["split"], split_rows)
    _write_csv(output_paths["layer"], layer_rows)
    _write_csv(output_paths["composite"], composite_rows)
    _write_json(output_paths["readiness"], readiness_packet)
    _write_text(output_paths["readiness_md"], _readiness_markdown(readiness_packet))
    _write_json(
        output_paths["guardrail_report"],
        _guardrail_lineage_report(
            {
                key: path
                for key, path in output_paths.items()
                if key != "guardrail_report"
            },
            composite_rows,
            readiness_packet,
        ),
    )
    _validate_output_files(output_paths)
    return {
        "output_paths": {key: str(path) for key, path in output_paths.items()},
        "readiness_verdict": readiness_packet["readiness_verdict"],
        "missing_dependencies": readiness_packet["missing_dependencies"],
    }


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise V16InputError("v1.6 input CSV has no header")
        validate_v1_6_columns(reader.fieldnames)
        _reject_forbidden_runtime_language(reader.fieldnames, context="input header")
        return [dict(row) for row in reader]


def _validate_input(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise V16InputError("v1.6 input CSV has no rows")
    columns = set(rows[0])
    missing = [column for column in REQUIRED_IDENTITY_COLUMNS if column not in columns]
    if missing:
        raise V16InputError(f"missing required identity columns: {', '.join(missing)}")
    status_values: set[str] = set()
    for row in rows:
        for value in row.values():
            _reject_forbidden_runtime_language([value], context="input value")
        for column in _status_columns_in_row(row):
            value = _clean(row.get(column))
            if value:
                status_values.add(value)
    unknown_statuses = sorted(status_values.difference(ALLOWED_INPUT_STATUS_VALUES))
    if unknown_statuses:
        raise V16InputError(f"unknown v1.6 status values: {', '.join(unknown_statuses)}")


def _load_thresholds(config_path: str | Path | None) -> tuple[dict[str, float], str, str]:
    candidates = [Path(config_path)] if config_path else [Path(path) for path in THRESHOLD_CONFIG_CANDIDATES]
    for path in candidates:
        if not path.exists():
            continue
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
        thresholds = {
            "coverage_warn": _toml_float(payload, "coverage", "warn_score_coverage"),
            "coverage_min": _toml_float(payload, "coverage", "min_score_coverage"),
            "stability_warn": _toml_float(payload, "stability", "rank_stability_warn_floor"),
            "spearman_warn": _toml_float(payload, "redundancy", "spearman_warn"),
            "spearman_block": _toml_float(payload, "redundancy", "spearman_block"),
        }
        if all(value is not None for value in thresholds.values()):
            return {key: float(value) for key, value in thresholds.items()}, str(path), "config_present"
    return {}, "missing_threshold_config", "config_missing"


def _toml_float(payload: dict[str, Any], section: str, key: str) -> float | None:
    value = payload.get(section, {}).get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _build_confidence_rows(
    rows: list[dict[str, str]],
    thresholds: dict[str, float],
    config_status: str,
) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        components = {column: _parse_unit_interval(row.get(column)) for column in COMPONENT_COLUMNS}
        missing_components = [key for key, value in components.items() if value is None]
        confidence_score = round(sum(value or 0.0 for value in components.values()) / len(COMPONENT_COLUMNS), 6)
        status_values = _row_status_values(row)
        reason_codes = _base_reason_codes(status_values)
        if config_status == "config_missing":
            support_status = "config_missing"
            reason_codes.add("config_missing")
        elif missing_components:
            support_status = "insufficient_data"
            reason_codes.add("limited_quality_evidence")
        elif (
            components["coverage"] >= thresholds["coverage_min"]
            and components["data_quality"] >= thresholds["coverage_min"]
            and components["stability"] >= thresholds["stability_warn"]
        ):
            support_status = "diagnostic_ready"
            reason_codes.add("strong_multi_layer_coverage")
        else:
            support_status = "partial_diagnostic_ready"
            reason_codes.add("limited_quality_evidence")
        reason_codes.add("manual_review_only")
        output.append(
            {
                "schema_version": "v1_6",
                "candidate_id": row["candidate_id"],
                "ticker": row["ticker"],
                "evaluation_date": row["evaluation_date"],
                "confidence_score": f"{confidence_score:.6f}",
                "confidence_support_status": support_status,
                "coverage_component": _format_component(components["coverage"]),
                "data_quality_component": _format_component(components["data_quality"]),
                "stability_component": _format_component(components["stability"]),
                "reason_codes": _join_codes(reason_codes),
                "source_artifact": _clean(row.get("source_artifact")),
                "lineage_ref": _clean(row.get("lineage_ref")),
                "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            }
        )
    return output


def _build_horizon_rows(
    rows: list[dict[str, str]],
    confidence_rows: list[dict[str, Any]],
    thresholds: dict[str, float],
    config_status: str,
) -> list[dict[str, Any]]:
    by_candidate = _group_by_candidate(rows)
    confidence_by_key = {
        (row["candidate_id"], row["ticker"], row["evaluation_date"]): row for row in confidence_rows
    }
    output = []
    for key, candidate_rows in by_candidate.items():
        horizons = sorted({_clean(row.get("horizon_id")) for row in candidate_rows if _clean(row.get("horizon_id"))})
        reason_codes = {"manual_review_only"}
        if len(horizons) < 2:
            status = "insufficient_horizon_coverage"
            reason_codes.add("limited_quality_evidence")
        elif config_status == "config_missing":
            status = "config_missing"
            reason_codes.add("config_missing")
        else:
            stability_values = [_parse_unit_interval(row.get("stability")) for row in candidate_rows]
            valid_stability = [value for value in stability_values if value is not None]
            if len(valid_stability) < len(horizons):
                status = "insufficient_horizon_coverage"
                reason_codes.add("limited_quality_evidence")
            elif min(valid_stability) >= thresholds["stability_warn"]:
                status = "stable_across_horizons"
                reason_codes.add("stable_across_horizons")
            else:
                status = "partial_diagnostic_ready"
                reason_codes.add("limited_quality_evidence")
        base = confidence_by_key[key]
        output.append(
            {
                "schema_version": "v1_6",
                "candidate_id": key[0],
                "ticker": key[1],
                "evaluation_date": key[2],
                "horizon_count": str(len(horizons)),
                "horizon_ids": ";".join(horizons),
                "horizon_stability_status": status,
                "reason_codes": _join_codes(reason_codes),
                "source_artifact": base["source_artifact"],
                "lineage_ref": base["lineage_ref"],
                "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            }
        )
    return output


def _build_split_rows(
    rows: list[dict[str, str]],
    thresholds: dict[str, float],
    config_status: str,
) -> list[dict[str, Any]]:
    output = []
    for key, candidate_rows in _group_by_candidate(rows).items():
        split_ids = sorted({_clean(row.get("split_id")) for row in candidate_rows if _clean(row.get("split_id"))})
        seed_ids = sorted({_clean(row.get("seed")) for row in candidate_rows if _clean(row.get("seed"))})
        coverage_count = max(len(split_ids), len(seed_ids))
        reason_codes = {"manual_review_only"}
        if coverage_count < 2:
            status = "insufficient_split_or_seed_coverage"
            reason_codes.add("limited_quality_evidence")
        elif config_status == "config_missing":
            status = "config_missing"
            reason_codes.add("config_missing")
        else:
            stability_values = [_parse_unit_interval(row.get("stability")) for row in candidate_rows]
            valid_stability = [value for value in stability_values if value is not None]
            if len(valid_stability) < coverage_count:
                status = "insufficient_split_or_seed_coverage"
                reason_codes.add("limited_quality_evidence")
            elif min(valid_stability) >= thresholds["stability_warn"]:
                status = "stable_across_splits"
                reason_codes.add("stable_across_splits")
            else:
                status = "partial_diagnostic_ready"
                reason_codes.add("limited_quality_evidence")
        source_artifacts, lineage_refs = _collect_lineage(candidate_rows)
        output.append(
            {
                "schema_version": "v1_6",
                "candidate_id": key[0],
                "ticker": key[1],
                "evaluation_date": key[2],
                "split_seed_count": str(coverage_count),
                "split_ids": ";".join(split_ids),
                "seed_ids": ";".join(seed_ids),
                "split_stability_status": status,
                "reason_codes": _join_codes(reason_codes),
                "source_artifact": source_artifacts,
                "lineage_ref": lineage_refs,
                "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            }
        )
    return output


def _build_layer_rows(
    rows: list[dict[str, str]],
    thresholds: dict[str, float],
    threshold_source: str,
    config_status: str,
) -> list[dict[str, Any]]:
    if not {"layer_id", "evidence_value"}.issubset(rows[0]):
        return [_layer_gap_row(rows, "insufficient_data", "missing layer_id or evidence_value")]
    layer_ids = sorted({_clean(row.get("layer_id")) for row in rows if _clean(row.get("layer_id"))})
    if len(layer_ids) < 2:
        return [_layer_gap_row(rows, "insufficient_data", "fewer than two layers")]
    if config_status == "config_missing":
        row = _layer_gap_row(rows, "config_missing", "missing redundancy threshold config")
        row["threshold_source"] = threshold_source
        row["reason_codes"] = _join_codes({"config_missing", "manual_review_only"})
        return [row]

    by_layer: dict[str, dict[tuple[str, str, str], float]] = defaultdict(dict)
    for row in rows:
        layer_id = _clean(row.get("layer_id"))
        value = _parse_float(row.get("evidence_value"))
        if layer_id and value is not None:
            by_layer[layer_id][_candidate_key(row)] = value
    output = []
    for layer_a, layer_b in itertools.combinations(layer_ids, 2):
        shared = sorted(set(by_layer[layer_a]).intersection(by_layer[layer_b]))
        if len(shared) < 3:
            status = "insufficient_data"
            correlation = ""
            reason_codes = {"limited_quality_evidence", "manual_review_only"}
        else:
            values_a = [by_layer[layer_a][key] for key in shared]
            values_b = [by_layer[layer_b][key] for key in shared]
            rho = _spearman(values_a, values_b)
            correlation = f"{rho:.6f}"
            if abs(rho) >= thresholds["spearman_block"]:
                status = "redundant_layer_block"
                reason_codes = {"redundant_layer_warning", "manual_review_only"}
            elif abs(rho) >= thresholds["spearman_warn"]:
                status = "redundant_layer_warning"
                reason_codes = {"redundant_layer_warning", "manual_review_only"}
            else:
                status = "diagnostic_ready"
                reason_codes = {"manual_review_only"}
        output.append(
            {
                "schema_version": "v1_6",
                "layer_id_a": layer_a,
                "layer_id_b": layer_b,
                "candidate_count": str(len(shared)),
                "spearman_correlation": correlation,
                "redundancy_status": status,
                "threshold_source": threshold_source,
                "reason_codes": _join_codes(reason_codes),
                "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            }
        )
    return output or [_layer_gap_row(rows, "insufficient_data", "no comparable layer pairs")]


def _build_composite_rows(
    rows: list[dict[str, str]],
    confidence_rows: list[dict[str, Any]],
    horizon_rows: list[dict[str, Any]],
    split_rows: list[dict[str, Any]],
    layer_rows: list[dict[str, Any]],
    config_status: str,
) -> list[dict[str, Any]]:
    confidence_by_key = {_row_key(row): row for row in confidence_rows}
    horizon_by_key = {_row_key(row): row for row in horizon_rows}
    split_by_key = {_row_key(row): row for row in split_rows}
    redundancy_summary = _redundancy_summary(layer_rows)
    output = []
    for key, candidate_rows in _group_by_candidate(rows).items():
        confidence = confidence_by_key[key]
        horizon = horizon_by_key[key]
        split = split_by_key[key]
        reason_codes = _split_codes(confidence["reason_codes"])
        reason_codes.update(_split_codes(horizon["reason_codes"]))
        reason_codes.update(_split_codes(split["reason_codes"]))
        if redundancy_summary == "redundant_layer_warning":
            reason_codes.add("redundant_layer_warning")
        status_values = _row_status_values(candidate_rows[0])
        reason_codes.update(_base_reason_codes(status_values))
        priority = _manual_review_priority(
            confidence,
            horizon,
            split,
            redundancy_summary,
            config_status,
            reason_codes,
        )
        source_artifacts, lineage_refs = _collect_lineage(candidate_rows)
        output.append(
            {
                "schema_version": "v1_6",
                "candidate_id": key[0],
                "ticker": key[1],
                "evaluation_date": key[2],
                "manual_review_priority": priority,
                "confidence_score": confidence["confidence_score"],
                "confidence_support_status": confidence["confidence_support_status"],
                "horizon_stability_status": horizon["horizon_stability_status"],
                "split_stability_status": split["split_stability_status"],
                "redundancy_status_summary": redundancy_summary,
                "reason_codes": _join_codes(reason_codes),
                "source_artifact_refs": source_artifacts,
                "lineage_refs": lineage_refs,
                "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            }
        )
    return output


def _build_readiness_packet(
    rows: list[dict[str, str]],
    composite_rows: list[dict[str, Any]],
    horizon_rows: list[dict[str, Any]],
    split_rows: list[dict[str, Any]],
    layer_rows: list[dict[str, Any]],
    threshold_source: str,
    config_status: str,
    input_mode: str,
) -> dict[str, Any]:
    missing_dependencies = _missing_dependencies(rows, horizon_rows, split_rows, layer_rows, config_status)
    priorities = {row["manual_review_priority"] for row in composite_rows}
    if missing_dependencies or "blocked_manual_review" in priorities:
        verdict = "V2_0_NOT_READY"
    elif "limited_manual_review" in priorities:
        verdict = "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY"
    else:
        verdict = "V2_0_READY_FOR_LIMITED_REVIEW"
    if verdict not in READINESS_VERDICTS:
        raise AssertionError(f"internal invalid readiness verdict: {verdict}")
    source_artifacts, lineage_refs = _collect_lineage(rows)
    if not source_artifacts:
        missing_dependencies.append("missing_source_artifact_refs")
        source_artifacts = "missing_source_artifact"
    if not lineage_refs:
        missing_dependencies.append("missing_lineage_refs")
        lineage_refs = "missing_lineage_ref"
    return {
        "schema_version": "v1_6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_version": CONTRACT_VERSION,
        "input_mode": input_mode,
        "readiness_verdict": verdict,
        "manual_review_only": True,
        "valuation_scoring_activation_allowed": False,
        "automatic_action_allowed": False,
        "threshold_source": threshold_source,
        "config_status": config_status,
        "candidate_count": len(_group_by_candidate(rows)),
        "manual_review_priority_summary": _count_values(
            row["manual_review_priority"] for row in composite_rows
        ),
        "blocking_reason_codes": sorted(
            {
                code
                for row in composite_rows
                for code in _split_codes(row["reason_codes"])
                if code in {"blocked_by_upstream_reconciliation", "insufficient_baseline_artifact", "config_missing"}
            }
        ),
        "carry_forward_limitations": _collect_limitations(rows, missing_dependencies),
        "missing_dependencies": missing_dependencies,
        "source_artifact_refs": source_artifacts,
        "lineage_refs": lineage_refs,
        "output_file_names": list(GENERATED_OUTPUT_PATHS.values()),
        "guardrail_summary": {
            "manual_review_only": True,
            "valuation_scoring_activation_allowed": False,
            "automatic_action_allowed": False,
            "forbidden_column_policy": "reject_input_and_output_columns",
            "forbidden_language_policy": "reject_input_and_generated_output_language",
        },
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _manual_review_priority(
    confidence: dict[str, Any],
    horizon: dict[str, Any],
    split: dict[str, Any],
    redundancy_summary: str,
    config_status: str,
    reason_codes: set[str],
) -> str:
    reason_codes.add("manual_review_only")
    if {
        "blocked_by_upstream_reconciliation",
        "insufficient_baseline_artifact",
        "missing_artifact",
        "config_missing",
    }.intersection(reason_codes):
        return "blocked_manual_review"
    if (
        config_status == "config_present"
        and confidence["confidence_support_status"] == "diagnostic_ready"
        and horizon["horizon_stability_status"] == "stable_across_horizons"
        and split["split_stability_status"] == "stable_across_splits"
        and redundancy_summary != "redundant_layer_warning"
    ):
        return "review_preferred"
    return "limited_manual_review"


def _base_reason_codes(status_values: set[str]) -> set[str]:
    reason_codes: set[str] = set()
    if "blocked_by_reconciliation" in status_values or "block" in status_values:
        reason_codes.add("blocked_by_upstream_reconciliation")
    if {"skipped_missing_baseline_artifacts", "missing_artifact"}.intersection(status_values):
        reason_codes.add("insufficient_baseline_artifact")
    if {"insufficient_data", "partial_diagnostic_ready", "vendor_reference_only"}.intersection(status_values):
        reason_codes.add("limited_quality_evidence")
    return reason_codes


def _missing_dependencies(
    rows: list[dict[str, str]],
    horizon_rows: list[dict[str, Any]],
    split_rows: list[dict[str, Any]],
    layer_rows: list[dict[str, Any]],
    config_status: str,
) -> list[str]:
    missing = set()
    columns = set(rows[0])
    for column in COMPONENT_COLUMNS:
        if column not in columns:
            missing.add(f"missing_input_column:{column}")
    if config_status == "config_missing":
        missing.add("missing_threshold_config")
    if any(row["horizon_stability_status"] == "insufficient_horizon_coverage" for row in horizon_rows):
        missing.add("insufficient_horizon_coverage")
    if any(row["split_stability_status"] == "insufficient_split_or_seed_coverage" for row in split_rows):
        missing.add("insufficient_split_or_seed_coverage")
    if any(row["redundancy_status"] in {"insufficient_data", "config_missing"} for row in layer_rows):
        missing.add("insufficient_layer_redundancy_evidence")
    return sorted(missing)


def _layer_gap_row(rows: list[dict[str, str]], status: str, note: str) -> dict[str, Any]:
    reason_codes = {"limited_quality_evidence", "manual_review_only"}
    if status == "config_missing":
        reason_codes = {"config_missing", "manual_review_only"}
    return {
        "schema_version": "v1_6",
        "layer_id_a": "",
        "layer_id_b": "",
        "candidate_count": "0",
        "spearman_correlation": "",
        "redundancy_status": status,
        "threshold_source": "",
        "gap_note": note,
        "reason_codes": _join_codes(reason_codes),
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
    }


def _redundancy_summary(layer_rows: list[dict[str, Any]]) -> str:
    statuses = {row["redundancy_status"] for row in layer_rows}
    if "redundant_layer_block" in statuses:
        return "redundant_layer_block"
    if "redundant_layer_warning" in statuses:
        return "redundant_layer_warning"
    if "config_missing" in statuses:
        return "config_missing"
    if "insufficient_data" in statuses:
        return "insufficient_data"
    return "diagnostic_ready"


def _status_columns_in_row(row: dict[str, str]) -> list[str]:
    return [column for column in row if column in STATUS_COLUMNS or column.endswith("_status")]


def _row_status_values(row: dict[str, str]) -> set[str]:
    return {_clean(row.get(column)) for column in _status_columns_in_row(row) if _clean(row.get(column))}


def _group_by_candidate(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[_candidate_key(row)].append(row)
    return dict(grouped)


def _candidate_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row["candidate_id"], row["ticker"], row["evaluation_date"])


def _row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (row["candidate_id"], row["ticker"], row["evaluation_date"])


def _collect_lineage(rows: list[dict[str, str]]) -> tuple[str, str]:
    source_artifacts = sorted({_clean(row.get("source_artifact")) for row in rows if _clean(row.get("source_artifact"))})
    lineage_refs = sorted({_clean(row.get("lineage_ref")) for row in rows if _clean(row.get("lineage_ref"))})
    return ";".join(source_artifacts), ";".join(lineage_refs)


def _collect_limitations(rows: list[dict[str, str]], missing_dependencies: list[str]) -> list[str]:
    limitations = {
        _clean(row.get("limitations"))
        for row in rows
        if "limitations" in row and _clean(row.get("limitations"))
    }
    limitations.update(missing_dependencies)
    return sorted(limitations)


def _parse_unit_interval(value: str | None) -> float | None:
    parsed = _parse_float(value)
    if parsed is None:
        return None
    if parsed < 0.0 or parsed > 1.0:
        return None
    return parsed


def _parse_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _format_component(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def _spearman(values_a: list[float], values_b: list[float]) -> float:
    ranks_a = _average_ranks(values_a)
    ranks_b = _average_ranks(values_b)
    mean_a = sum(ranks_a) / len(ranks_a)
    mean_b = sum(ranks_b) / len(ranks_b)
    numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(ranks_a, ranks_b))
    denom_a = math.sqrt(sum((a - mean_a) ** 2 for a in ranks_a))
    denom_b = math.sqrt(sum((b - mean_b) ** 2 for b in ranks_b))
    if denom_a == 0.0 or denom_b == 0.0:
        return 0.0
    return numerator / (denom_a * denom_b)


def _average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[position][1]:
            end += 1
        rank = (position + end + 2) / 2.0
        for index in range(position, end + 1):
            ranks[indexed[index][0]] = rank
        position = end + 1
    return ranks


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _join_codes(reason_codes: set[str]) -> str:
    unknown = sorted(reason_codes.difference(ALLOWED_REASON_CODES))
    if unknown:
        raise AssertionError(f"internal unknown v1.6 reason codes: {', '.join(unknown)}")
    return ";".join(sorted(reason_codes))


def _split_codes(value: str) -> set[str]:
    return {item for item in value.split(";") if item}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _reject_forbidden_runtime_language(values: Any, context: str) -> None:
    for value in values:
        text = _clean(value).lower()
        if not text:
            continue
        for pattern in FORBIDDEN_LANGUAGE_PATTERNS:
            if pattern in text:
                raise V16InputError(f"forbidden v1.6 language in {context}: {pattern}")
        for word in FORBIDDEN_RUNTIME_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", text):
                raise V16InputError(f"forbidden v1.6 term in {context}: {word}")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise AssertionError(f"no rows to write: {path}")
    validate_v1_6_columns(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    validate_v1_6_columns(payload.keys())
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _validate_output_files(output_paths: dict[str, Path]) -> None:
    for path in output_paths.values():
        text = path.read_text(encoding="utf-8").lower()
        for pattern in FORBIDDEN_LANGUAGE_PATTERNS:
            if pattern in text:
                raise AssertionError(f"forbidden v1.6 output language in {path}: {pattern}")


def _readiness_markdown(packet: dict[str, Any]) -> str:
    limitations = packet.get("carry_forward_limitations") or ["none"]
    missing = packet.get("missing_dependencies") or ["none"]
    return "\n".join(
        [
            "# v1.6 v2.0 Readiness Packet",
            "",
            f"- readiness_verdict: `{packet['readiness_verdict']}`",
            f"- manual_review_only: `{packet['manual_review_only']}`",
            f"- valuation_scoring_activation_allowed: `{packet['valuation_scoring_activation_allowed']}`",
            f"- automatic_action_allowed: `{packet['automatic_action_allowed']}`",
            f"- config_status: `{packet['config_status']}`",
            "",
            "## Missing Dependencies",
            *[f"- `{item}`" for item in missing],
            "",
            "## Carry-Forward Limitations",
            *[f"- `{item}`" for item in limitations],
            "",
            "## Notice",
            MANUAL_REVIEW_ONLY_NOTICE,
            "",
        ]
    )


def _guardrail_lineage_report(
    output_paths: dict[str, Path],
    composite_rows: list[dict[str, Any]],
    readiness_packet: dict[str, Any],
) -> dict[str, Any]:
    forbidden_columns_by_file: dict[str, list[str]] = {}
    manual_review_notice_by_file: dict[str, bool] = {}
    forbidden_language_by_file: dict[str, list[str]] = {}
    for path in output_paths.values():
        text = path.read_text(encoding="utf-8")
        lower_text = text.lower()
        forbidden_language_by_file[path.name] = [
            pattern for pattern in FORBIDDEN_LANGUAGE_PATTERNS if pattern in lower_text
        ]
        manual_review_notice_by_file[path.name] = "manual_review" in lower_text
        if path.suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                forbidden_columns_by_file[path.name] = sorted(
                    set(reader.fieldnames or []).intersection(FORBIDDEN_COLUMN_NAMES)
                )
        elif path.suffix == ".json":
            payload = json.loads(text)
            forbidden_columns_by_file[path.name] = sorted(
                set(payload.keys()).intersection(FORBIDDEN_COLUMN_NAMES)
            )
        else:
            forbidden_columns_by_file[path.name] = []
    top_reason_code_check = all(row.get("reason_codes") for row in composite_rows)
    lineage_present = bool(readiness_packet.get("source_artifact_refs")) or bool(
        readiness_packet.get("lineage_refs")
    )
    return {
        "schema_version": "v1_6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_version": CONTRACT_VERSION,
        "manual_review_only_confirmed": all(manual_review_notice_by_file.values()),
        "forbidden_columns_by_file": forbidden_columns_by_file,
        "forbidden_language_by_file": forbidden_language_by_file,
        "forbidden_columns_absent": all(not values for values in forbidden_columns_by_file.values()),
        "forbidden_language_absent": all(not values for values in forbidden_language_by_file.values()),
        "top_review_priority_reason_codes_present": top_reason_code_check,
        "lineage_or_source_refs_present": lineage_present,
        "readiness_verdict": readiness_packet.get("readiness_verdict"),
        "readiness_verdict_conservative": readiness_packet.get("readiness_verdict")
        in {
            "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY",
            "V2_0_NOT_READY",
        },
        "carry_forward_limitations_visible": bool(readiness_packet.get("carry_forward_limitations")),
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build v1.6 manual review priority outputs.")
    parser.add_argument("--input", required=True, help="Merged v1.1-v1.5 evidence/status CSV")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--config", default=None, help="Optional threshold config TOML")
    parser.add_argument(
        "--input-mode",
        default="project_artifacts",
        choices=("project_artifacts", "fixture"),
        help="Input mode label for lineage diagnostics",
    )
    args = parser.parse_args(argv)
    result = run_v1_6_confidence_review_priority(
        input_path=args.input,
        output_dir=args.output_dir,
        config_path=args.config,
        input_mode=args.input_mode,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
