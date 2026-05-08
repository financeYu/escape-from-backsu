from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_5_personal_decision_support_packets.py"
SPEC = importlib.util.spec_from_file_location("build_v0_5_personal_decision_support_packets", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def ml_row(candidate_id: str, status: str = "evidence_recorded", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "candidate_version": "v0.3.0",
        "registry_ref": "registry.jsonl",
        "evaluation_evidence_ref": "evidence.md",
        "evaluation_id": "ee_" + candidate_id.replace(":", "_"),
        "evaluation_status": status,
        "actual_metric_summary_available": status == "evidence_recorded",
        "adoption_review_eligible": status == "evidence_recorded",
        "adoption_required_checks_ready": status == "evidence_recorded",
        "actual_total_return": 0.1 if status == "evidence_recorded" else None,
        "actual_max_drawdown": -0.05 if status == "evidence_recorded" else None,
        "actual_sharpe": 0.3 if status == "evidence_recorded" else None,
        "actual_oos_stability": "walk_forward_pass" if status == "evidence_recorded" else None,
        "benchmark_cost_profile_id": "kospi_product_purchase_cost_v1",
        "benchmark_cost_market": "KOSPI",
        "benchmark_cost_total_adjustment": 0.002,
        "evaluation_failure_flags": [],
        "risk_flag_count": 1,
    }
    row.update(overrides)
    return row


def test_v0_5_builder_emits_fail_closed_personal_support_packets(tmp_path: Path) -> None:
    ml_ready = tmp_path / "ml_ready.jsonl"
    adoption = tmp_path / "adoption.jsonl"
    ranking = tmp_path / "ranking.jsonl"
    write_jsonl(
        ml_ready,
        [
            ml_row("sc:recorded"),
            ml_row(
                "sc:needs_more",
                status="needs_more_evidence",
                evaluation_failure_flags=["candidate_level_metric_missing"],
                adoption_required_checks_ready=False,
            ),
            ml_row("sc:missing", status="missing_evaluation_evidence"),
        ],
    )
    write_jsonl(
        adoption,
        [
            {
                "candidate_id": "sc:recorded",
                "adoption_candidate_id": "ac_recorded",
                "selector_score_source": "rule_only",
                "selector_rank": 1,
                "diagnostic_references": {"reference_only": True},
            }
        ],
    )
    write_jsonl(
        ranking,
        [{"candidate_id": "sc:recorded", "evaluation_mode": "diagnostic_ranking_only"}],
    )

    manifest = builder.build_packets(
        ml_ready_input=ml_ready,
        adoption_packets=adoption,
        ranking_rows=ranking,
        output_dir=tmp_path / "out",
        jsonl_name="packets.jsonl",
        csv_name="packets.csv",
        manifest_name="manifest.json",
        current_condition_status="blocked_missing_current_condition",
        dry_run=False,
    )

    packets = [
        json.loads(line)
        for line in (tmp_path / "out" / "packets.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert manifest["packet_count"] == 2
    assert manifest["guardrails"]["order_generation_allowed"] is False
    assert manifest["guardrails"]["position_sizing_allowed"] is False
    assert {packet["packet_status"] for packet in packets} == {"blocked_missing_current_condition"}
    assert {packet["evidence_status"] for packet in packets} == {"evidence_recorded", "needs_more_evidence"}
    needs_more = next(packet for packet in packets if packet["candidate_id"] == "sc:needs_more")
    assert "candidate_level_metric_missing" in needs_more["coverage_gaps"]
    assert needs_more["no_order_generation_check"] == "pass_no_order_generation"


def test_v0_5_packet_guardrail_rejects_action_instruction_text() -> None:
    packet = {
        "no_order_generation_check": "pass_no_order_generation",
        "no_prediction_claim_check": "pass_no_future_return_prediction_claim",
        "note": "buy instruction",
    }

    try:
        builder._assert_packet_guardrails(packet)
    except ValueError as exc:
        assert "forbidden action framing" in str(exc)
    else:
        raise AssertionError("expected forbidden action framing to fail")
