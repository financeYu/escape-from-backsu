"""Tests for v0.3 StrategyCandidate registry automation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_v0_3_strategy_candidates.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_strategy_candidates", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _strategy_record(**overrides):
    payload = {
        "schema_version": "v0_3_strategy_hypothesis_output_0_1",
        "current_stage": "StrategyHypothesis",
        "strategy_boundary": "candidate-only strategy structure with no trading recommendation",
        "linked_research_hypothesis": {
            "research_id": "rh:ecard:test",
            "title": "Daily momentum test",
            "next_action": "convert_to_strategy_hypothesis",
            "evidence_quality": "moderate",
            "confidence_level": "medium",
        },
        "strategy_hypothesis": {
            "strategy_hypothesis_id": "sh:ecard:test",
            "linked_research_id": "rh:ecard:test",
            "title": "Daily momentum test",
            "strategy_type": "momentum",
            "signal_definition": "Cross-sectional percentile rank of 20-trading-day return.",
            "signal_calculation_window": "20 trading days.",
            "entry_rule": "Include securities with signal_percentile >= 0.80.",
            "exit_rule": "Remove after 20 trading days or when signal_percentile < 0.50.",
            "holding_period": "20 trading days.",
            "rebalance_rule": "Every 20 trading days using prior close data.",
            "universe_filter": "approved KOSPI200 daily OHLCV universe",
            "position_sizing": "Equal-weight evidence-only basket.",
            "risk_control": "No-lookahead and cost checks required.",
            "transaction_cost_assumption": "10 bps per side.",
            "benchmark": "Equal-weight approved KOSPI200 universe.",
            "primary_metric": "Information ratio versus benchmark after costs.",
            "secondary_metrics": ["max_drawdown", "turnover"],
            "null_hypothesis": "No advantage versus benchmark after costs.",
            "expected_positive_pattern": "Top signal bucket separates from benchmark after costs.",
            "expected_failure_case": "No stable quantile separation after costs.",
            "data_requirements": ["daily_ohlcv"],
            "implementation_notes": ["Candidate-only."],
            "conversion_status": "ready_for_candidate_registry",
            "reason_for_status": "Ready for registry.",
        },
        "testable_rules": {},
        "evaluation_plan": {},
        "failure_definition": "No stable quantile separation after costs.",
        "next_stage_input": {"next_stage": "StrategyCandidate"},
        "blocker": [],
        "minimal_fix": [],
        "no_feedback_check": "strategy_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    for dotted_key, value in overrides.items():
        current = payload
        parts = dotted_key.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    return payload


def test_ready_strategy_hypothesis_becomes_ready_candidate() -> None:
    record = builder.strategy_record_to_candidate_record(_strategy_record())
    candidate = record["strategy_candidate"]

    assert record["current_stage"] == "StrategyCandidate"
    assert candidate["candidate_id"] == "sc:ecard:test"
    assert candidate["candidate_version"] == "v0.3.0"
    assert candidate["status"] == "ready_for_eval"
    assert candidate["next_action"] == "create_evaluation_evidence"
    assert candidate["blocking_issues"] == []
    assert "daily_ohlcv" in candidate["data_requirements"]
    assert "signal_percentile_or_bucket" in candidate["feature_requirements"]
    assert record["next_stage_input"]["next_stage"] == "EvaluationEvidence"
    assert "trading recommendation" in record["candidate_boundary"]


def test_refinement_strategy_hypothesis_becomes_proposed_candidate() -> None:
    record = builder.strategy_record_to_candidate_record(
        _strategy_record(
            strategy_hypothesis__conversion_status="needs_refinement",
            next_stage_input=None,
            blocker=["strategy_definition_not_specific_enough"],
            minimal_fix=["Refine signal."],
        )
    )
    candidate = record["strategy_candidate"]

    assert candidate["status"] == "proposed"
    assert candidate["next_action"] == "refine_strategy_hypothesis"
    assert record["next_stage_input"] is None
    assert "strategy_definition_not_specific_enough" in candidate["blocking_issues"]


def test_blocked_strategy_hypothesis_becomes_rejected_candidate() -> None:
    record = builder.strategy_record_to_candidate_record(
        _strategy_record(
            strategy_hypothesis__conversion_status="blocked",
            next_stage_input=None,
            blocker=["out_of_scope_or_rejected"],
            minimal_fix=["Do not evaluate."],
        )
    )
    candidate = record["strategy_candidate"]

    assert candidate["status"] == "rejected"
    assert candidate["next_action"] == "reject"
    assert record["next_stage_input"] is None
    assert "out_of_scope_or_rejected" in candidate["blocking_issues"]


def test_build_strategy_candidates_writes_outputs_and_groups(tmp_path: Path) -> None:
    input_path = tmp_path / "strategy_hypotheses.jsonl"
    records = [
        _strategy_record(strategy_hypothesis__strategy_hypothesis_id="sh:ecard:ready"),
        _strategy_record(
            strategy_hypothesis__strategy_hypothesis_id="sh:ecard:proposed",
            strategy_hypothesis__conversion_status="needs_refinement",
            next_stage_input=None,
            blocker=["strategy_definition_not_specific_enough"],
            minimal_fix=["Refine signal."],
        ),
    ]
    input_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    paths = builder.build_strategy_candidates(input_path, tmp_path / "out", run_id="test_run")
    rows = [
        json.loads(line)
        for line in paths["jsonl"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    groups = json.loads(paths["groups"].read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert paths["csv"].exists()
    assert manifest["record_count"] == 2
    assert manifest["candidate_status_counts"]["ready_for_eval"] == 1
    assert manifest["candidate_status_counts"]["proposed"] == 1
    assert groups["groups"]["momentum"]["status_counts"]["ready_for_eval"] == 1
    assert groups["groups"]["momentum"]["status_counts"]["proposed"] == 1
