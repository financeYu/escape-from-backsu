"""Build v0.3 AdoptionCandidate review packets from selector output.

The packets are candidate-only review artifacts. They do not adopt a strategy,
activate production behavior, train a model, or create trading instructions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.artifact_io import read_jsonl, write_csv, write_jsonl

DEFAULT_SELECTOR_INPUT = Path("Quant_mvp/data/v0_3/rule_first_selector/v0_3_rule_first_selector.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/adoption_candidate_review_packets")
DEFAULT_JSONL_NAME = "v0_3_adoption_candidate_review_packets.jsonl"
DEFAULT_CSV_NAME = "v0_3_adoption_candidate_review_packets.csv"
DEFAULT_MANIFEST_NAME = "v0_3_adoption_candidate_review_packets_manifest.json"
DEFAULT_DIAGNOSTIC_RANKING_MANIFEST = Path(
    "Quant_mvp/data/v0_4/selector_scores/v0_4_1_selector_ml_score_ranking_manifest.json"
)

SCHEMA_VERSION = "v0_3_adoption_candidate_review_packet_0_1"
MANIFEST_SCHEMA_VERSION = "v0_3_adoption_candidate_review_packet_manifest_0_1"
ACTIVATION_GATE_REF = "docs/extension/v0_3_production_activation_decision_gate.md"
SELECTOR_GATE_REF = "docs/extension/v0_3_adoption_candidate_selector_gate.md"
GENERIC_PROXY_ROLE = "generic_momentum_proxy"

REVIEWABLE_SOURCES = {"rule_only", "hybrid_ml_rule", "ml_model"}
REQUIRED_PACKET_FIELDS = [
    "schema_version",
    "adoption_candidate_id",
    "candidate_id",
    "candidate_version",
    "source_evidence_id",
    "selector_version",
    "selector_run_id",
    "selector_input_refs",
    "selector_score_source",
    "selector_score",
    "selector_score_candidate",
    "selector_rank",
    "relative_review_rank",
    "review_priority",
    "confidence",
    "reason_codes",
    "evidence_summary",
    "benchmark_or_proxy_reference_summary",
    "risk_summary",
    "limitation_summary",
    "limitations",
    "blocked_or_excluded_reason",
    "required_review",
    "status",
    "no_feedback_check",
    "activation_gate_ref",
    "production_boundary_check",
    "diagnostic_references",
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "unknown")).strip("_").lower()
    return text[:80] or "unknown"


def _is_reviewable_selector_row(row: dict[str, Any]) -> bool:
    return (
        row.get("hard_gate_status") == "pass"
        and row.get("minimum_gate_status") == "pass"
        and row.get("selector_score_source") in REVIEWABLE_SOURCES
        and row.get("final_selector_score") is not None
        and row.get("selector_rank") is not None
    )


def _blocked_or_excluded_reason(row: dict[str, Any]) -> str | None:
    if _is_reviewable_selector_row(row):
        return None
    if row.get("hard_gate_status") != "pass":
        return str(row.get("hard_gate_reason") or "hard_gate_blocked")
    if row.get("minimum_gate_status") != "pass":
        return str(row.get("minimum_gate_reason") or "minimum_gate_blocked")
    return str(row.get("selector_score_source") or "selector_not_reviewable")


def _confidence(selector_score: float | None, score_source: str) -> str:
    if score_source == "hybrid_ml_rule" and selector_score is not None and selector_score >= 80.0:
        return "medium"
    return "low"


def _reason_codes(row: dict[str, Any]) -> list[str]:
    codes = [
        "evidence_complete_enough_for_review",
        "historical_performance_summary_documented",
        "risk_metrics_documented",
        "limitations_explicit",
        "no_feedback_boundary_passed",
    ]
    if row.get("selector_score_source") == "rule_only":
        codes.append("rule_only_selector_review")
    if row.get("selector_score_source") == "hybrid_ml_rule":
        codes.append("hybrid_ml_rule_selector_review")
    return codes


def _limitation_summary(row: dict[str, Any]) -> list[str]:
    limitations = [
        "adoption_candidate_review_only_not_activation",
        "production_activation_requires_separate_root_gate",
    ]
    source = row.get("selector_score_source")
    if source == "rule_only":
        limitations.append("supervised_ml_blocked_or_not_available_rule_only_selector_used")
    elif source == "hybrid_ml_rule":
        limitations.append("hybrid_score_depends_on_available_ml_selector_score")
    elif source == "ml_model":
        limitations.append("ml_score_present_without_rule_component_requires_manual_review")
    if row.get("ml_selector_score") is None:
        limitations.append("ml_selector_score_absent")
    return limitations


def _diagnostic_references(ranking_manifest_ref: Path | None) -> dict[str, Any]:
    if ranking_manifest_ref is None:
        return {
            "ml_score_ranking_manifest_path": None,
            "evaluation_mode": "diagnostic_ranking_only",
            "reference_only": True,
            "selector_score_source_unchanged": True,
            "ranking_result_changes_selector_score": False,
            "ranking_result_changes_selector_rank": False,
            "performance_claim_allowed": False,
            "trading_signal_allowed": False,
            "adoption_auto_decision_allowed": False,
        }
    return {
        "ml_score_ranking_manifest_path": str(ranking_manifest_ref),
        "evaluation_mode": "diagnostic_ranking_only",
        "reference_only": True,
        "selector_score_source_unchanged": True,
        "ranking_result_changes_selector_score": False,
        "ranking_result_changes_selector_rank": False,
        "performance_claim_allowed": False,
        "trading_signal_allowed": False,
        "adoption_auto_decision_allowed": False,
    }


def selector_row_to_packet(
    row: dict[str, Any],
    *,
    selector_input_ref: Path,
    run_id: str,
    diagnostic_ranking_manifest_ref: Path | None = DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
) -> dict[str, Any] | None:
    if not _is_reviewable_selector_row(row):
        return None
    candidate_id = row.get("candidate_id")
    source_evidence_id = row.get("evidence_id")
    selector_score = _as_float(row.get("final_selector_score"))
    score_source = str(row.get("selector_score_source"))
    limitations = _limitation_summary(row)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "adoption_candidate_id": f"ac_v0_3_{_slug(run_id)}_{_slug(candidate_id)}",
        "candidate_id": candidate_id,
        "candidate_version": row.get("candidate_version"),
        "source_evidence_id": source_evidence_id,
        "selector_version": row.get("selector_version"),
        "selector_run_id": row.get("selector_run_id") or run_id,
        "selector_input_refs": [str(selector_input_ref), str(source_evidence_id)],
        "diagnostic_references": _diagnostic_references(diagnostic_ranking_manifest_ref),
        "selector_score_source": score_source,
        "selector_score": selector_score,
        "selector_score_candidate": selector_score,
        "selector_rank": row.get("selector_rank"),
        "relative_review_rank": row.get("selector_rank"),
        "review_priority": row.get("review_priority"),
        "confidence": _confidence(selector_score, score_source),
        "reason_codes": _reason_codes(row),
        "evidence_summary": {
            "source_evidence_id": source_evidence_id,
            "metric_subject_type": row.get("metric_subject_type"),
            "metric_subject_id": row.get("metric_subject_id"),
            "candidate_metric_match": row.get("candidate_metric_match"),
            "actual_metric_source": row.get("actual_metric_source"),
            "actual_metric_role": row.get("actual_metric_role"),
            "total_return": row.get("actual_total_return"),
        },
        "benchmark_or_proxy_reference_summary": {
            "generic_momentum_proxy_role": "benchmark_reference_context_only",
            "generic_proxy_not_used_as_label_or_selector_score": True,
            "benchmark_return": row.get("benchmark_return") or row.get("actual_benchmark_return"),
            "proxy_return": row.get("proxy_return") or row.get("actual_proxy_return"),
            "excess_return_vs_proxy": row.get("excess_return_vs_proxy")
            or row.get("actual_excess_return_vs_proxy"),
            "reference_context_available": any(
                row.get(column) is not None
                for column in (
                    "benchmark_return",
                    "actual_benchmark_return",
                    "proxy_return",
                    "actual_proxy_return",
                    "excess_return_vs_proxy",
                    "actual_excess_return_vs_proxy",
                )
            ),
        },
        "risk_summary": {
            "max_drawdown": row.get("actual_max_drawdown"),
            "sharpe": row.get("actual_sharpe"),
            "turnover": row.get("actual_turnover"),
            "volatility": row.get("actual_volatility"),
            "failure_flags": _as_list(row.get("failure_flags")),
        },
        "limitation_summary": limitations,
        "limitations": limitations,
        "blocked_or_excluded_reason": None,
        "required_review": [
            "root_governance_review",
            "quant_strategy_adoption_gate_review",
            "production_activation_decision_gate_required",
        ],
        "status": "activation_blocked",
        "no_feedback_check": "adoption_candidate_review_packet_must_not_feed_runtime_ranking_trading_or_auto_activation",
        "activation_gate_ref": ACTIVATION_GATE_REF,
        "selector_gate_ref": SELECTOR_GATE_REF,
        "production_boundary_check": "no_automatic_production_activation_claim",
    }
    validate_packet(packet)
    return packet


def build_packets(
    selector_rows: list[dict[str, Any]],
    *,
    selector_input_ref: Path,
    run_id: str,
    diagnostic_ranking_manifest_ref: Path | None = DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
) -> list[dict[str, Any]]:
    packets = [
        packet
        for row in selector_rows
        if (
            packet := selector_row_to_packet(
                row,
                selector_input_ref=selector_input_ref,
                run_id=run_id,
                diagnostic_ranking_manifest_ref=diagnostic_ranking_manifest_ref,
            )
        )
        is not None
    ]
    validate_packets(packets)
    return packets


def validate_packet(packet: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_PACKET_FIELDS if field not in packet]
    if missing:
        raise ValueError(f"adoption packet missing fields: {missing}")
    if packet.get("status") not in {"proposed", "review_required", "rejected", "activation_blocked"}:
        raise ValueError(f"invalid AdoptionCandidate status: {packet.get('status')}")
    if packet.get("activation_gate_ref") != ACTIVATION_GATE_REF:
        raise ValueError("activation gate reference is required")
    if packet.get("selector_score_source") not in REVIEWABLE_SOURCES:
        raise ValueError("packet selector_score_source must be reviewable")
    if packet.get("selector_score") is None or packet.get("selector_rank") is None:
        raise ValueError("packet requires selector_score and selector_rank")
    if packet.get("blocked_or_excluded_reason") is not None:
        raise ValueError("blocked or excluded selector rows must not become AdoptionCandidate packets")
    if "production_activation_decision_gate_required" not in _as_list(packet.get("required_review")):
        raise ValueError("production activation decision gate review is required")
    reference_summary = packet.get("benchmark_or_proxy_reference_summary")
    if not isinstance(reference_summary, dict):
        raise ValueError("benchmark_or_proxy_reference_summary must be an object")
    if reference_summary.get("generic_proxy_not_used_as_label_or_selector_score") is not True:
        raise ValueError("generic proxy must remain reference context only")
    diagnostic_references = packet.get("diagnostic_references")
    if not isinstance(diagnostic_references, dict):
        raise ValueError("diagnostic_references must be an object")
    if diagnostic_references.get("reference_only") is not True:
        raise ValueError("diagnostic references must remain reference-only")
    if diagnostic_references.get("evaluation_mode") != "diagnostic_ranking_only":
        raise ValueError("diagnostic ranking reference must use diagnostic_ranking_only")
    if diagnostic_references.get("selector_score_source_unchanged") is not True:
        raise ValueError("diagnostic ranking must not change selector_score_source")
    if diagnostic_references.get("ranking_result_changes_selector_score") is not False:
        raise ValueError("diagnostic ranking must not change selector_score")
    if diagnostic_references.get("ranking_result_changes_selector_rank") is not False:
        raise ValueError("diagnostic ranking must not change selector_rank")
    if diagnostic_references.get("performance_claim_allowed") is not False:
        raise ValueError("diagnostic ranking must not allow performance claims")
    if diagnostic_references.get("trading_signal_allowed") is not False:
        raise ValueError("diagnostic ranking must not allow trading signal claims")


def validate_packets(packets: list[dict[str, Any]]) -> None:
    ids = [str(packet.get("adoption_candidate_id")) for packet in packets]
    duplicates = [packet_id for packet_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate adoption_candidate_id values: {sorted(duplicates)}")
    for packet in packets:
        validate_packet(packet)


def build_manifest(
    selector_rows: list[dict[str, Any]],
    packets: list[dict[str, Any]],
    *,
    run_id: str,
    selector_input_ref: Path,
    diagnostic_ranking_manifest_ref: Path | None = DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
) -> dict[str, Any]:
    blocked_reasons = Counter(
        reason for row in selector_rows if (reason := _blocked_or_excluded_reason(row)) is not None
    )
    source_counts = Counter(str(packet.get("selector_score_source")) for packet in packets)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "selector_input_ref": str(selector_input_ref),
        "selector_row_count": len(selector_rows),
        "review_packet_count": len(packets),
        "selector_score_source_counts": dict(sorted(source_counts.items())),
        "blocked_or_excluded_selector_row_count": sum(blocked_reasons.values()),
        "blocked_or_excluded_reason_counts": dict(sorted(blocked_reasons.items())),
        "generic_proxy_policy": "generic_momentum_proxy_is_benchmark_reference_context_only",
        "supervised_ml_limitation_policy": "rule_only_packets_record_ml_blocked_or_absent_in_limitation_summary",
        "selection_status": (
            "adoption_candidate_review_packets_available"
            if packets
            else "selection_unavailable_evidence_insufficient"
        ),
        "required_packet_fields": list(REQUIRED_PACKET_FIELDS),
        "diagnostic_ranking_manifest_ref": (
            str(diagnostic_ranking_manifest_ref) if diagnostic_ranking_manifest_ref is not None else None
        ),
        "diagnostic_reference_policy": (
            "ml_score_ranking_manifest_reference_only_not_selector_input_or_adoption_decision"
        ),
        "activation_gate_ref": ACTIVATION_GATE_REF,
        "no_feedback_check": "adoption_candidate_review_packets_must_not_feed_runtime_ranking_trading_or_auto_activation",
    }


def build_adoption_candidate_review_packets(
    selector_input: Path,
    output_dir: Path,
    *,
    run_id: str,
    diagnostic_ranking_manifest_ref: Path | None = DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    selector_rows = read_jsonl(selector_input)
    packets = build_packets(
        selector_rows,
        selector_input_ref=selector_input,
        run_id=run_id,
        diagnostic_ranking_manifest_ref=diagnostic_ranking_manifest_ref,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    write_jsonl(jsonl_path, packets)
    manifest = build_manifest(
        selector_rows,
        packets,
        run_id=run_id,
        selector_input_ref=selector_input,
        diagnostic_ranking_manifest_ref=diagnostic_ranking_manifest_ref,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths = {"jsonl": jsonl_path, "manifest": manifest_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        write_csv(csv_path, packets, list_style="json")
        paths["csv"] = csv_path
    return paths


def dry_run_adoption_candidate_review_packets(
    selector_input: Path,
    *,
    run_id: str,
    diagnostic_ranking_manifest_ref: Path | None = DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
) -> dict[str, Any]:
    selector_rows = read_jsonl(selector_input)
    packets = build_packets(
        selector_rows,
        selector_input_ref=selector_input,
        run_id=run_id,
        diagnostic_ranking_manifest_ref=diagnostic_ranking_manifest_ref,
    )
    return {
        "mode": "dry_run",
        "output_written": False,
        "packet_count": len(packets),
        "manifest": build_manifest(
            selector_rows,
            packets,
            run_id=run_id,
            selector_input_ref=selector_input,
            diagnostic_ranking_manifest_ref=diagnostic_ranking_manifest_ref,
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-input", type=Path, default=DEFAULT_SELECTOR_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("adoption_candidate_review_packets_%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate review packets, then print the manifest without writing outputs.",
    )
    parser.add_argument(
        "--diagnostic-ranking-manifest",
        type=Path,
        default=DEFAULT_DIAGNOSTIC_RANKING_MANIFEST,
        help="Reference-only v0.4.1 ML score ranking manifest path to link in packets.",
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        result = dry_run_adoption_candidate_review_packets(
            args.selector_input,
            run_id=args.run_id,
            diagnostic_ranking_manifest_ref=args.diagnostic_ranking_manifest,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    paths = build_adoption_candidate_review_packets(
        args.selector_input,
        args.output_dir,
        run_id=args.run_id,
        diagnostic_ranking_manifest_ref=args.diagnostic_ranking_manifest,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
