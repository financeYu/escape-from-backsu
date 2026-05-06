from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_rule_first_selector.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_rule_first_selector", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def ml_ready_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "sc:test",
        "candidate_version": "v0.3.0",
        "evaluation_id": "ee:test",
        "evaluation_status": "evidence_recorded",
        "metric_subject_type": "strategy_candidate",
        "metric_subject_id": "sc:test",
        "candidate_metric_match": True,
        "candidate_metric_match_reason": "candidate_id_matches_candidate_level_evaluation_evidence",
        "metric_source": "approved_evaluation_evidence",
        "metric_role": "candidate_specific",
        "actual_metric_summary_available": True,
        "has_benchmark_comparison": True,
        "actual_total_return": 0.18,
        "actual_max_drawdown": -0.08,
        "actual_sharpe": 1.1,
        "actual_turnover": 0.35,
        "actual_volatility": 0.2,
        "excess_return_vs_proxy": 0.05,
        "evaluation_failure_flags": [],
        "excluded_untradable": False,
        "excluded_failure": False,
        "label_decision": "positive",
    }
    row.update(overrides)
    return row


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_rule_only_selector_scores_candidate_level_evidence() -> None:
    rows = builder.build_selector_rows([ml_ready_row()], run_id="test_run")

    row = rows[0]
    assert row["hard_gate_status"] == "pass"
    assert row["minimum_gate_status"] == "pass"
    assert row["rule_score"] is not None
    assert row["ml_selector_score"] is None
    assert row["final_selector_score"] == row["rule_score"]
    assert row["selector_score_source"] == "rule_only"
    assert row["selector_rank"] == 1
    assert row["review_priority"] == "top_review_candidate"


def test_optional_ml_score_creates_hybrid_score_only_after_rule_pass() -> None:
    rows = builder.build_selector_rows([ml_ready_row(ml_selector_score=90.0)], run_id="test_run")

    row = rows[0]
    assert row["selector_score_source"] == "hybrid_ml_rule"
    assert row["ml_selector_score"] == 90.0
    assert row["rule_score"] is not None
    assert row["final_selector_score"] == round((0.70 * row["rule_score"]) + (0.30 * 90.0), 6)
    assert row["selector_rank"] == 1


def test_missing_evidence_rows_receive_no_score_or_rank() -> None:
    rows = builder.build_selector_rows(
        [
            ml_ready_row(
                evaluation_id=None,
                evaluation_status="missing_evaluation_evidence",
                metric_subject_type=None,
                metric_subject_id=None,
                candidate_metric_match=False,
                candidate_metric_match_reason="metric_summary_missing_or_unavailable",
                actual_metric_summary_available=False,
                has_benchmark_comparison=False,
                label_decision="null_missing_evidence",
            )
        ],
        run_id="test_run",
    )

    row = rows[0]
    assert row["hard_gate_status"] == "excluded"
    assert row["hard_gate_reason"] == "missing_candidate_level_evidence"
    assert row["rule_score"] is None
    assert row["final_selector_score"] is None
    assert row["selector_rank"] is None
    assert row["selector_score_source"] == "blocked_no_candidate_level_evidence"


def test_generic_proxy_rows_stay_reference_only_without_selector_score() -> None:
    rows = builder.build_selector_rows(
        [
            ml_ready_row(
                metric_subject_type="generic_proxy",
                metric_subject_id="generic_momentum_proxy",
                metric_role="generic_momentum_proxy",
                candidate_metric_match=False,
                candidate_metric_match_reason="generic_momentum_proxy_not_candidate_level",
                actual_metric_summary_available=True,
                label_decision="blocked_generic_proxy_not_candidate_level",
                ml_selector_score=99.0,
            )
        ],
        run_id="test_run",
    )

    row = rows[0]
    assert row["hard_gate_status"] == "excluded"
    assert row["hard_gate_reason"] == "generic_proxy_only"
    assert row["rule_score"] is None
    assert row["ml_selector_score"] is None
    assert row["final_selector_score"] is None
    assert row["selector_rank"] is None
    assert row["selector_score_source"] == "blocked_insufficient_labels"


def test_hard_exclusion_prevents_ranked_output() -> None:
    rows = builder.build_selector_rows(
        [
            ml_ready_row(candidate_id="sc:ok", metric_subject_id="sc:ok"),
            ml_ready_row(
                candidate_id="sc:excluded",
                metric_subject_id="sc:excluded",
                excluded_untradable=True,
            ),
        ],
        run_id="test_run",
    )

    ranked = [row for row in rows if row["selector_rank"] is not None]
    assert [row["candidate_id"] for row in ranked] == ["sc:ok"]
    excluded = next(row for row in rows if row["candidate_id"] == "sc:excluded")
    assert excluded["hard_gate_reason"] == "excluded_untradable"
    assert excluded["final_selector_score"] is None


def test_dry_run_cli_outputs_manifest_without_writing(tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "ml_ready.jsonl"
    output_dir = tmp_path / "rule_first_selector"
    write_jsonl(input_path, [ml_ready_row()])

    exit_code = builder.main(
        [
            "--input",
            str(input_path),
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
    assert result["output_written"] is False
    assert result["manifest"]["rule_scored_candidate_count"] == 1
    assert result["manifest"]["top_review_candidates_count"] == 1
