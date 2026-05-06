from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_adoption_candidate_review_packets.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_adoption_candidate_review_packets", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def selector_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "selector_version": "v0_3_rule_first_selector_0_1",
        "selector_run_id": "selector_test",
        "candidate_id": "sc:test",
        "candidate_version": "v0.3.0",
        "evidence_id": "ee:test",
        "metric_subject_type": "strategy_candidate",
        "metric_subject_id": "sc:test",
        "candidate_metric_match": True,
        "candidate_metric_match_reason": "candidate_id_matches_candidate_level_evaluation_evidence",
        "hard_gate_status": "pass",
        "hard_gate_reason": "passed_hard_exclusion",
        "minimum_gate_status": "pass",
        "minimum_gate_reason": "passed_minimum_evidence_gate",
        "rule_score": 75.0,
        "ml_selector_score": None,
        "final_selector_score": 75.0,
        "selector_score_source": "rule_only",
        "selector_rank": 1,
        "review_priority": "top_review_candidate",
        "actual_metric_source": "approved_evaluation_evidence",
        "actual_metric_role": "candidate_specific",
        "actual_total_return": 0.18,
        "actual_max_drawdown": -0.08,
        "actual_sharpe": 1.1,
        "actual_turnover": 0.35,
        "actual_volatility": 0.2,
        "proxy_return": 0.13,
        "excess_return_vs_proxy": 0.05,
        "failure_flags": [],
        "adoption_candidate_boundary": "review_input_only_not_adoption_decision",
        "no_feedback_check": "rule_first_selector_must_not_feed_runtime_ranking_reports_backtests_trading_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    row.update(overrides)
    return row


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_rule_only_selector_row_becomes_adoption_candidate_review_packet() -> None:
    packets = builder.build_packets([selector_row()], selector_input_ref=Path("selector.jsonl"), run_id="packet_test")

    assert len(packets) == 1
    packet = packets[0]
    assert packet["candidate_id"] == "sc:test"
    assert packet["source_evidence_id"] == "ee:test"
    assert packet["selector_score_source"] == "rule_only"
    assert packet["selector_score"] == 75.0
    assert packet["selector_rank"] == 1
    assert packet["review_priority"] == "top_review_candidate"
    assert packet["status"] == "activation_blocked"
    assert "supervised_ml_blocked_or_not_available_rule_only_selector_used" in packet["limitation_summary"]
    assert packet["benchmark_or_proxy_reference_summary"]["generic_proxy_not_used_as_label_or_selector_score"] is True
    assert packet["benchmark_or_proxy_reference_summary"]["proxy_return"] == 0.13


def test_hybrid_selector_source_is_preserved() -> None:
    packets = builder.build_packets(
        [
            selector_row(
                selector_score_source="hybrid_ml_rule",
                ml_selector_score=80.0,
                final_selector_score=76.5,
            )
        ],
        selector_input_ref=Path("selector.jsonl"),
        run_id="packet_test",
    )

    packet = packets[0]
    assert packet["selector_score_source"] == "hybrid_ml_rule"
    assert packet["selector_score"] == 76.5
    assert "hybrid_ml_rule_selector_review" in packet["reason_codes"]
    assert "hybrid_score_depends_on_available_ml_selector_score" in packet["limitation_summary"]


def test_hard_excluded_and_blocked_rows_do_not_become_packets() -> None:
    rows = [
        selector_row(),
        selector_row(
            candidate_id="sc:missing",
            evidence_id=None,
            metric_subject_type=None,
            metric_subject_id=None,
            candidate_metric_match=False,
            hard_gate_status="excluded",
            hard_gate_reason="missing_candidate_level_evidence",
            minimum_gate_status="blocked",
            rule_score=None,
            final_selector_score=None,
            selector_rank=None,
            selector_score_source="blocked_no_candidate_level_evidence",
        ),
        selector_row(
            candidate_id="sc:proxy",
            metric_subject_type="generic_proxy",
            metric_subject_id="generic_momentum_proxy",
            candidate_metric_match=False,
            hard_gate_status="excluded",
            hard_gate_reason="generic_proxy_only",
            minimum_gate_status="blocked",
            rule_score=None,
            final_selector_score=None,
            selector_rank=None,
            selector_score_source="blocked_insufficient_labels",
        ),
    ]

    packets = builder.build_packets(rows, selector_input_ref=Path("selector.jsonl"), run_id="packet_test")
    manifest = builder.build_manifest(rows, packets, run_id="packet_test", selector_input_ref=Path("selector.jsonl"))

    assert [packet["candidate_id"] for packet in packets] == ["sc:test"]
    assert manifest["review_packet_count"] == 1
    assert manifest["blocked_or_excluded_reason_counts"]["missing_candidate_level_evidence"] == 1
    assert manifest["blocked_or_excluded_reason_counts"]["generic_proxy_only"] == 1


def test_dry_run_cli_outputs_manifest_without_writing(tmp_path: Path, capsys) -> None:
    selector_input = tmp_path / "selector.jsonl"
    output_dir = tmp_path / "packets"
    write_jsonl(selector_input, [selector_row()])

    exit_code = builder.main(
        [
            "--selector-input",
            str(selector_input),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "dry_run_test",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert not output_dir.exists()
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "dry_run"
    assert result["packet_count"] == 1
    assert result["manifest"]["selector_score_source_counts"]["rule_only"] == 1
