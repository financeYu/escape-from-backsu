from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "ml" / "build_selector_labels.py"
SPEC = importlib.util.spec_from_file_location("build_selector_labels", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def registry_record(candidate_id: str = "sc:ecard:test") -> dict[str, object]:
    return {
        "strategy_candidate": {
            "candidate_id": candidate_id,
            "candidate_version": "v0.3.0",
            "linked_strategy_hypothesis_id": "sh:ecard:test",
            "status": "evaluable",
        }
    }


def evidence_packet(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evaluation_id": "ee_v0_3_test",
        "candidate_id": "sc:ecard:test",
        "candidate_version": "v0.3.0",
        "hypothesis_id": "sh:ecard:test",
        "status": "evidence_recorded",
        "created_at": "2026-05-06",
        "updated_at": "2026-05-06",
        "failure_flags": [],
        "required_evaluation_checks": {
            "no_lookahead": {"status": "recorded_boundary_check"},
            "oos_walk_forward_stability": {"status": "walk_forward_pass"},
        },
        "metric_summary": {
            "total_return": 0.2,
            "benchmark_return": 0.1,
            "sharpe_ratio": 1.1,
            "max_drawdown": -0.08,
            "oos_stability_status": "walk_forward_pass",
        },
    }
    payload.update(overrides)
    return payload


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_evidence(path: Path, packet: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# test evidence\n\n```json\n"
        + json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )


def test_contract_only_and_not_yet_run_remain_null() -> None:
    rules = builder._load_rules(PROJECT_ROOT / "Quant_mvp/config/v0_3_selector_label_rules.toml")
    row = builder.build_label_row(
        registry_record(),
        evidence_packet(status="contract_only", failure_flags=["not_yet_run"], metric_summary=None),
        rules=rules,
    )

    assert row["label_pass_minimum_gate"] is None
    assert row["label_review_preferred"] is None
    assert row["label_source"] is None
    assert row["label_null_reason"] == "evaluation_status_not_label_eligible:contract_only"


def test_recorded_metric_summary_can_set_review_preferred_label() -> None:
    rules = builder._load_rules(PROJECT_ROOT / "Quant_mvp/config/v0_3_selector_label_rules.toml")
    row = builder.build_label_row(registry_record(), evidence_packet(), rules=rules)

    assert row["label_pass_minimum_gate"] == 1
    assert row["label_review_preferred"] == 1
    assert row["label_source"] == "approved_evaluation_evidence_metric_summary"
    assert row["label_null_reason"] is None


def test_metric_failure_sets_zero_without_calling_missing_backtests_negative() -> None:
    rules = builder._load_rules(PROJECT_ROOT / "Quant_mvp/config/v0_3_selector_label_rules.toml")
    row = builder.build_label_row(
        registry_record(),
        evidence_packet(metric_summary={"total_return": 0.05, "benchmark_return": 0.1, "sharpe_ratio": 0.7, "max_drawdown": -0.2, "oos_stability_status": "walk_forward_pass"}),
        rules=rules,
    )

    assert row["label_pass_minimum_gate"] == 0
    assert row["label_review_preferred"] == 0


def test_oos_missing_keeps_review_preferred_null_after_minimum_gate_passes() -> None:
    rules = builder._load_rules(PROJECT_ROOT / "Quant_mvp/config/v0_3_selector_label_rules.toml")
    row = builder.build_label_row(
        registry_record(),
        evidence_packet(
            required_evaluation_checks={"no_lookahead": {"status": "recorded_boundary_check"}},
            metric_summary={
                "total_return": 0.2,
                "benchmark_relative_return": 0.1,
                "sharpe_ratio": 1.1,
                "max_drawdown": -0.08,
                "oos_stability_status": "not_available_single_pass_snapshot",
            },
        ),
        rules=rules,
    )

    assert row["label_pass_minimum_gate"] == 1
    assert row["label_review_preferred"] is None
    assert row["label_null_reason"] == "review_preferred_evidence_insufficient"


def test_dry_run_summary_reports_null_counts(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    evidence_dir = tmp_path / "evidence"
    rules = PROJECT_ROOT / "Quant_mvp/config/v0_3_selector_label_rules.toml"
    write_jsonl(registry, [registry_record(), registry_record("sc:ecard:missing")])
    write_evidence(evidence_dir / "ee_v0_3_test.md", evidence_packet())

    rows = builder.build_selector_label_rows(registry, evidence_dir, rules)
    summary = builder.build_dry_run_summary(
        rows,
        registry=registry,
        evidence_dir=evidence_dir,
        rules_path=rules,
    )

    assert summary["output_written"] is False
    assert summary["candidate_count"] == 2
    assert summary["label_review_preferred_counts"] == {"1": 1, "null": 1}
    assert summary["label_possible_count"] == 1
    assert summary["label_unavailable_count"] == 1
