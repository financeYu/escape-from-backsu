"""Tests for v0.3 StrategyHypothesis automation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_v0_3_strategy_hypotheses.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_strategy_hypotheses", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _entry_threshold_text() -> str:
    return f"{builder.OHLCV_ADAPTER_DEFAULT_CONFIG.entry_percentile_threshold:.2f}"


def _momentum_window_text() -> str:
    return f"{builder.OHLCV_ADAPTER_DEFAULT_CONFIG.momentum_window} trading days"


def _research_record(**overrides):
    payload = {
        "schema_version": "v0_3_research_hypothesis_output_0_1",
        "current_stage": "ResearchHypothesis",
        "research_boundary": "candidate-only research structure",
        "research_hypothesis": {
            "research_id": "rh:ecard:test",
            "title": "Daily momentum test",
            "source_type": "paper",
            "source_reference": {
                "evidence_card_id": "ecard:test",
                "source_query_set": "technical_momentum",
            },
            "core_claim": "Momentum can be tested as a candidate-only rule.",
            "market_mechanism": "Delayed information incorporation can create trend persistence.",
            "target_universe": "equity; daily_or_unspecified",
            "expected_signal": "momentum candidate signal from daily_ohlcv",
            "required_data": ["daily_ohlcv"],
            "assumptions": ["candidate-only"],
            "falsification_test": "Reject if quantile separation is not stable after costs.",
            "risk_or_failure_modes": ["transaction_cost_missing_flag"],
            "confidence_level": "medium",
            "evidence_quality": "moderate",
            "implementation_difficulty": "medium",
            "next_action": "convert_to_strategy_hypothesis",
            "reason_for_next_action": "Ready for StrategyHypothesis.",
        },
        "why_this_could_be_a_strategy": "It is measurable.",
        "validation_requirement": "Define features and costs.",
        "main_risks": ["transaction_cost_missing_flag"],
        "next_stage_input": {
            "next_stage": "StrategyHypothesis",
            "research_id": "rh:ecard:test",
            "candidate_name": "Daily momentum test",
            "signal_family_candidate": "momentum",
            "required_data": ["daily_ohlcv"],
        },
        "blocker": [],
        "minimal_fix": [],
        "no_feedback_check": "research_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    for dotted_key, value in overrides.items():
        current = payload
        parts = dotted_key.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    return payload


def test_ready_research_hypothesis_becomes_strategy_hypothesis() -> None:
    record = builder.research_record_to_strategy_record(_research_record())
    strategy = record["strategy_hypothesis"]

    assert record["current_stage"] == "StrategyHypothesis"
    assert strategy["strategy_hypothesis_id"] == "sh:ecard:test"
    assert strategy["linked_research_id"] == "rh:ecard:test"
    assert strategy["strategy_type"] == "momentum"
    assert strategy["conversion_status"] == "ready_for_candidate_registry"
    assert f"signal_percentile >= {_entry_threshold_text()}" in strategy["entry_rule"]
    assert _momentum_window_text() in strategy["holding_period"]
    assert "KOSPI200" in strategy["universe_filter"]
    assert record["next_stage_input"]["next_stage"] == "StrategyCandidate"
    assert record["blocker"] == []
    assert "trading recommendation" in record["strategy_boundary"]


def test_non_ready_research_hypothesis_is_not_candidate_registry_input() -> None:
    record = builder.research_record_to_strategy_record(
        _research_record(
            research_hypothesis__next_action="needs_more_research",
            research_hypothesis__reason_for_next_action="Needs signal details.",
            next_stage_input=None,
            blocker=["strategy_definition_not_specific_enough"],
            minimal_fix=["Define numeric signal."],
        )
    )

    assert record["strategy_hypothesis"]["conversion_status"] == "needs_refinement"
    assert record["next_stage_input"] is None
    assert record["blocker"] == ["strategy_definition_not_specific_enough"]


def test_manual_review_gap_promotion_is_tracked_and_bounded() -> None:
    research = _research_record(
        research_hypothesis__next_action="needs_more_research",
        research_hypothesis__reason_for_next_action="Manual review required.",
        next_stage_input=None,
        blocker=["manual_review_required"],
        minimal_fix=["Resolve manual review."],
    )
    promotion = {
        "rh:ecard:test": {
            "research_id": "rh:ecard:test",
            "candidate_id": "sc:ecard:test",
            "review_resolution": "Manual review resolved for candidate-only OHLCV evidence.",
        }
    }

    record = builder.research_record_to_strategy_record(
        research,
        manual_review_promotions=promotion,
    )
    strategy = record["strategy_hypothesis"]

    assert strategy["conversion_status"] == "ready_for_candidate_registry"
    assert "Manual review resolved" in strategy["reason_for_status"]
    assert f"signal_percentile >= {_entry_threshold_text()}" in strategy["entry_rule"]
    assert record["blocker"] == []
    assert record["minimal_fix"] == []
    assert record["next_stage_input"]["next_stage"] == "StrategyCandidate"


def test_manual_review_promotion_strategy_types_follow_ohlcv_adapter_policy() -> None:
    assert builder.PROMOTABLE_STRATEGY_TYPES == builder.OHLCV_ADAPTER_SUPPORTED_STRATEGY_TYPES


def test_rejected_research_hypothesis_is_blocked() -> None:
    record = builder.research_record_to_strategy_record(
        _research_record(
            research_hypothesis__next_action="reject",
            next_stage_input=None,
            blocker=["out_of_scope_or_rejected"],
            minimal_fix=["Do not register."],
        )
    )

    assert record["strategy_hypothesis"]["conversion_status"] == "blocked"
    assert record["next_stage_input"] is None
    assert "out_of_scope_or_rejected" in record["blocker"]


def test_build_strategy_hypotheses_writes_outputs_and_rule_groups(tmp_path: Path) -> None:
    input_path = tmp_path / "research_hypotheses.jsonl"
    records = [
        _research_record(research_hypothesis__research_id="rh:ecard:ready"),
        _research_record(
            research_hypothesis__research_id="rh:ecard:blocked",
            research_hypothesis__next_action="reject",
            next_stage_input=None,
            blocker=["out_of_scope_or_rejected"],
            minimal_fix=["Do not register."],
        ),
    ]
    input_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    paths = builder.build_strategy_hypotheses(input_path, tmp_path / "out", run_id="test_run")
    rows = [
        json.loads(line)
        for line in paths["jsonl"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    rule_groups = json.loads(paths["rule_groups"].read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert paths["csv"].exists()
    assert manifest["record_count"] == 2
    assert manifest["conversion_status_counts"]["ready_for_candidate_registry"] == 1
    assert manifest["conversion_status_counts"]["blocked"] == 1
    assert "momentum" in rule_groups["groups"]
    assert rule_groups["groups"]["momentum"]["ml_rule_family"]["label_horizon"] == "20 trading days."
