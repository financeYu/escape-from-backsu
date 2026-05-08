"""Build v0.5 PersonalDecisionSupportPacket artifacts.

The builder consumes v0.3/v0.4 review artifacts as read-only inputs and emits
private decision-support packets. Packets are evidence/risk/checklist summaries
only; they do not create transaction instructions or production activation.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_ML_READY_INPUT = Path(
    "Quant_mvp/data/v0_3/ml_ready_candidate_inputs/v0_3_ml_ready_candidate_input.jsonl"
)
DEFAULT_ADOPTION_PACKETS = Path(
    "Quant_mvp/data/v0_3/adoption_candidate_review_packets/v0_3_adoption_candidate_review_packets.jsonl"
)
DEFAULT_RANKING_ROWS = Path("Quant_mvp/data/v0_4/selector_scores/v0_4_1_selector_ml_score_ranking.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_5/personal_decision_support")
DEFAULT_JSONL_NAME = "v0_5_personal_decision_support_packets.jsonl"
DEFAULT_CSV_NAME = "v0_5_personal_decision_support_packets.csv"
DEFAULT_MANIFEST_NAME = "v0_5_personal_decision_support_manifest.json"
SCHEMA_VERSION = "v0_5_personal_decision_support_packet_v1_0"
MANIFEST_SCHEMA_VERSION = "v0_5_personal_decision_support_manifest_v1_0"
ROUTE_REF = "docs/extension/v0_5_personal_decision_support_route.md"

FORBIDDEN_ACTION_TERMS = (
    "buy",
    "sell",
    "hold",
    "rebalance",
    "move_to_cash",
    "target_price",
    "expected_return",
    "profit_expected",
    "position_size",
    "order",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ml-ready-input", type=Path, default=DEFAULT_ML_READY_INPUT)
    parser.add_argument("--adoption-packets", type=Path, default=DEFAULT_ADOPTION_PACKETS)
    parser.add_argument("--ranking-rows", type=Path, default=DEFAULT_RANKING_ROWS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--jsonl-name", default=DEFAULT_JSONL_NAME)
    parser.add_argument("--csv-name", default=DEFAULT_CSV_NAME)
    parser.add_argument("--manifest-name", default=DEFAULT_MANIFEST_NAME)
    parser.add_argument(
        "--current-condition-status",
        default="blocked_missing_current_condition",
        choices=("blocked_missing_current_condition", "not_checked", "snapshot_available"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _by_candidate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("candidate_id")): row for row in rows if row.get("candidate_id")}


def _packet_status(row: dict[str, Any], current_condition_status: str) -> str:
    if current_condition_status != "snapshot_available":
        return "blocked_missing_current_condition"
    if row.get("evaluation_status") == "needs_more_evidence":
        return "needs_more_evidence"
    if row.get("evaluation_status") != "evidence_recorded":
        return "blocked_validation_incomplete"
    if row.get("adoption_review_eligible") is True:
        return "evidence_supported_review"
    return "blocked_validation_incomplete"


def _manual_checklist(row: dict[str, Any], adoption: dict[str, Any] | None) -> list[str]:
    checklist = [
        "confirm_current_kospi200_boundary_snapshot",
        "review_evaluation_evidence_source_packet",
        "review_cost_sensitivity_flags",
        "review_drawdown_volatility_turnover_flags",
        "confirm_no_order_or_position_instruction_is_generated",
    ]
    if row.get("evaluation_status") != "evidence_recorded":
        checklist.insert(1, "obtain_candidate_level_evaluation_evidence_before_use")
    if adoption and adoption.get("diagnostic_references"):
        checklist.append("treat_ml_ranking_manifest_as_reference_only")
    return checklist


def _risk_flags(row: dict[str, Any], adoption: dict[str, Any] | None) -> list[str]:
    flags: list[str] = []
    if row.get("evaluation_failure_flags"):
        flags.extend(str(item) for item in row.get("evaluation_failure_flags") or [])
    if row.get("risk_flag_count"):
        flags.append(f"research_risk_flag_count_{row['risk_flag_count']}")
    if row.get("actual_max_drawdown") is not None:
        flags.append("drawdown_metric_available")
    if adoption:
        risk_summary = adoption.get("risk_summary") if isinstance(adoption.get("risk_summary"), dict) else {}
        if risk_summary.get("failure_flags"):
            flags.extend(str(item) for item in risk_summary["failure_flags"])
    return sorted(set(flags))


def _coverage_gaps(row: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if row.get("evaluation_status") == "needs_more_evidence":
        gaps.append("candidate_level_metric_missing")
    if row.get("actual_metric_summary_available") is not True:
        gaps.append("actual_metric_summary_unavailable")
    if row.get("adoption_required_checks_ready") is not True:
        gaps.append("adoption_required_checks_not_ready")
    if row.get("actual_oos_stability") in (None, "", "not_available_needs_more_evidence"):
        gaps.append("oos_stability_not_confirmed")
    return sorted(set(gaps))


def _cost_flags(row: dict[str, Any]) -> list[str]:
    flags = []
    profile = row.get("benchmark_cost_profile_id")
    market = row.get("benchmark_cost_market")
    if profile:
        flags.append(f"cost_profile_{profile}")
    if market:
        flags.append(f"cost_market_{market}")
    if row.get("benchmark_cost_total_adjustment") is not None:
        flags.append("cost_adjustment_available_for_audit")
    return flags


def build_packet(
    row: dict[str, Any],
    *,
    adoption: dict[str, Any] | None,
    ranking: dict[str, Any] | None,
    current_condition_status: str,
    generated_at: str,
) -> dict[str, Any]:
    candidate_id = str(row["candidate_id"])
    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": "pds_v0_5_" + candidate_id.replace(":", "_"),
        "candidate_id": candidate_id,
        "candidate_version": row.get("candidate_version"),
        "support_scope": "private_personal_decision_support_only",
        "packet_status": _packet_status(row, current_condition_status),
        "generated_at_utc": generated_at,
        "route_ref": ROUTE_REF,
        "input_artifact_refs": [
            str(row.get("registry_ref")),
            str(row.get("evaluation_evidence_ref")),
            DEFAULT_ML_READY_INPUT.as_posix(),
            DEFAULT_ADOPTION_PACKETS.as_posix(),
            DEFAULT_RANKING_ROWS.as_posix(),
        ],
        "evidence_status": row.get("evaluation_status"),
        "evidence_summary": {
            "evaluation_id": row.get("evaluation_id"),
            "actual_metric_summary_available": row.get("actual_metric_summary_available"),
            "actual_total_return": row.get("actual_total_return"),
            "actual_max_drawdown": row.get("actual_max_drawdown"),
            "actual_sharpe": row.get("actual_sharpe"),
            "actual_oos_stability": row.get("actual_oos_stability"),
        },
        "selector_diagnostic_refs": {
            "adoption_packet_id": adoption.get("adoption_candidate_id") if adoption else None,
            "selector_score_source": adoption.get("selector_score_source") if adoption else None,
            "selector_rank": adoption.get("selector_rank") if adoption else None,
            "ml_ranking_reference_only": bool(ranking),
            "ml_ranking_evaluation_mode": ranking.get("evaluation_mode") if ranking else None,
            "rf_reference_only": True,
        },
        "current_condition_status": current_condition_status,
        "risk_flags": _risk_flags(row, adoption),
        "cost_sensitivity_flags": _cost_flags(row),
        "coverage_gaps": _coverage_gaps(row),
        "manual_review_checklist": _manual_checklist(row, adoption),
        "decision_boundary": (
            "manual_judgment_support_only_no_transaction_instruction_no_prediction_claim"
        ),
        "no_order_generation_check": "pass_no_order_generation",
        "no_position_sizing_check": "pass_no_position_sizing",
        "no_prediction_claim_check": "pass_no_future_return_prediction_claim",
        "no_production_activation_check": "pass_no_production_activation",
        "forbidden_action_terms": list(FORBIDDEN_ACTION_TERMS),
    }
    return packet


def _assert_packet_guardrails(packet: dict[str, Any]) -> None:
    text = json.dumps(packet, ensure_ascii=False).lower()
    for term in FORBIDDEN_ACTION_TERMS:
        if f"{term} recommendation" in text or f"{term} instruction" in text:
            raise ValueError(f"forbidden action framing found: {term}")
    if packet["no_order_generation_check"] != "pass_no_order_generation":
        raise ValueError("packet failed no_order_generation_check")
    if packet["no_prediction_claim_check"] != "pass_no_future_return_prediction_claim":
        raise ValueError("packet failed no_prediction_claim_check")


def build_packets(
    *,
    ml_ready_input: Path,
    adoption_packets: Path,
    ranking_rows: Path,
    output_dir: Path,
    jsonl_name: str,
    csv_name: str,
    manifest_name: str,
    current_condition_status: str,
    dry_run: bool,
) -> dict[str, Any]:
    ml_rows = read_jsonl(ml_ready_input)
    adoption_by_candidate = _by_candidate(read_jsonl(adoption_packets))
    ranking_by_candidate = _by_candidate(read_jsonl(ranking_rows))
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    eligible_rows = [
        row for row in ml_rows if row.get("evaluation_status") in {"evidence_recorded", "needs_more_evidence"}
    ]
    packets = [
        build_packet(
            row,
            adoption=adoption_by_candidate.get(str(row["candidate_id"])),
            ranking=ranking_by_candidate.get(str(row["candidate_id"])),
            current_condition_status=current_condition_status,
            generated_at=generated_at,
        )
        for row in eligible_rows
    ]
    for packet in packets:
        _assert_packet_guardrails(packet)

    jsonl_path = output_dir / jsonl_name
    csv_path = output_dir / csv_name
    manifest_path = output_dir / manifest_name
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "route_ref": ROUTE_REF,
        "generated_at_utc": generated_at,
        "mode": "dry_run" if dry_run else "write",
        "packet_count": len(packets),
        "packet_status_counts": dict(sorted(Counter(packet["packet_status"] for packet in packets).items())),
        "evidence_status_counts": dict(sorted(Counter(packet["evidence_status"] for packet in packets).items())),
        "current_condition_status": current_condition_status,
        "input_refs": {
            "ml_ready_input": _relative(ml_ready_input),
            "adoption_packets": _relative(adoption_packets),
            "ranking_rows": _relative(ranking_rows),
        },
        "output_refs": {
            "jsonl": _relative(jsonl_path),
            "csv": _relative(csv_path),
            "manifest": _relative(manifest_path),
        },
        "guardrails": {
            "private_personal_decision_support_only": True,
            "order_generation_allowed": False,
            "position_sizing_allowed": False,
            "future_return_prediction_allowed": False,
            "production_activation_allowed": False,
            "new_market_data_ingestion_allowed": False,
            "universe_expansion_allowed": False,
        },
    }

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path.write_text(
            "\n".join(json.dumps(packet, ensure_ascii=False, sort_keys=True) for packet in packets) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "packet_id",
                "candidate_id",
                "candidate_version",
                "packet_status",
                "evidence_status",
                "current_condition_status",
                "risk_flags",
                "coverage_gaps",
                "manual_review_checklist",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for packet in packets:
                writer.writerow(
                    {
                        key: json.dumps(packet[key], ensure_ascii=False) if isinstance(packet[key], list) else packet[key]
                        for key in fieldnames
                    }
                )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_packets(
        ml_ready_input=args.ml_ready_input,
        adoption_packets=args.adoption_packets,
        ranking_rows=args.ranking_rows,
        output_dir=args.output_dir,
        jsonl_name=args.jsonl_name,
        csv_name=args.csv_name,
        manifest_name=args.manifest_name,
        current_condition_status=args.current_condition_status,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
