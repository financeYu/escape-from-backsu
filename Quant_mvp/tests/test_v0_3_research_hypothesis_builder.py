"""Tests for v0.3 ResearchHypothesis automation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_v0_3_research_hypotheses.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_research_hypotheses", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _card(**overrides):
    payload = {
        "evidence_card_id": "ecard:test",
        "parent_evidence_card_id": None,
        "source_run_id": "run",
        "source": {
            "source_query_set": "technical_momentum",
            "seed_origin_type": "metadata_api",
        },
        "paper": {
            "canonical_paper_id": "doi:10.1000/test",
            "doi": "10.1000/test",
            "arxiv_id": None,
            "title": "Daily momentum test",
            "publication_year": 2026,
            "publication_date": "2026-04-28",
            "venue": "Fixture Journal",
            "source_adapters": ["fixture"],
            "oa_status": "open",
            "license": "fixture",
            "is_retracted": False,
            "source_urls": ["https://example.test/paper"],
        },
        "classification": {
            "research_branch": "technical",
            "downstream_route": "technical_score_architect",
            "main_score_branch_candidate": "technical",
            "classification_confidence": "medium",
            "manual_review_required": False,
            "guardrail_violations": [],
        },
        "candidate_idea": {
            "candidate_name": "Daily momentum test",
            "idea_summary_ko": "candidate-only summary",
            "idea_summary_en": "candidate-only summary",
            "signal_family_candidate": "momentum",
            "formula_clarity": "partial",
            "implementation_readiness": 2,
            "required_inputs": ["daily_ohlcv"],
            "unavailable_inputs": [],
            "data_compatibility": ["daily_ohlcv"],
            "blocked_by_data": False,
            "point_in_time_fundamentals_required": False,
            "intraday_required": False,
            "order_book_required": False,
            "alternative_data_required": False,
            "universe_asset_class": "equity",
            "universe_frequency": "daily_or_unspecified",
        },
        "valuation_boundary": {
            "valuation_status": "not_applicable",
            "valuation_agent_required": False,
        },
        "extraction": {
            "evidence_status": "abstract_supported",
            "extraction_scope": "abstract_only",
            "abstract_available": True,
            "fulltext_used": False,
            "pdf_downloaded": False,
            "evidence_snippets_short": ["This must not be treated as verified performance."],
        },
        "backtest_context": {
            "paper_reported_backtest_present": False,
            "reproducibility_level": "not_reported",
            "transaction_costs_discussed": False,
            "lookahead_bias_discussed": False,
            "survivorship_bias_discussed": False,
        },
        "risks": {
            "project_internal_risk_readable": False,
            "data_snooping_risk_flag": True,
            "lookahead_risk_flag": False,
            "transaction_cost_missing_flag": True,
        },
        "guardrails": {
            "paper_claim_not_verified": True,
            "no_score_adopted": True,
            "no_backtest_performed": True,
            "valuation_not_inferred_from_price": True,
        },
    }

    for dotted_key, value in overrides.items():
        current = payload
        parts = dotted_key.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    return payload


def test_technical_card_converts_to_research_hypothesis_with_next_stage_input() -> None:
    record = builder.evidence_card_to_research_hypothesis_record(_card())
    hypothesis = record["research_hypothesis"]

    assert record["current_stage"] == "ResearchHypothesis"
    assert hypothesis["research_id"] == "rh:ecard:test"
    assert hypothesis["source_type"] == "paper"
    assert hypothesis["next_action"] == "convert_to_strategy_hypothesis"
    assert hypothesis["confidence_level"] == "medium"
    assert hypothesis["evidence_quality"] == "moderate"
    assert hypothesis["required_data"] == ["daily_ohlcv"]
    assert "정보 반영 지연" in hypothesis["market_mechanism"]
    assert record["next_stage_input"]["next_stage"] == "StrategyHypothesis"
    assert record["blocker"] == []
    assert record["main_risks"] == []
    assert "production ranking input" in record["research_boundary"]
    assert "trading recommendation" in record["research_boundary"]


def test_hybrid_or_data_blocked_card_needs_more_research() -> None:
    record = builder.evidence_card_to_research_hypothesis_record(
        _card(
            classification__research_branch="hybrid",
            classification__downstream_route="hybrid_split_required",
            classification__manual_review_required=True,
            candidate_idea__blocked_by_data=True,
            candidate_idea__point_in_time_fundamentals_required=True,
            candidate_idea__required_inputs=["daily_ohlcv", "point_in_time_fundamentals"],
        )
    )
    hypothesis = record["research_hypothesis"]

    assert hypothesis["next_action"] == "needs_more_research"
    assert hypothesis["implementation_difficulty"] == "high"
    assert record["next_stage_input"] is None
    assert "hybrid_split_required" in record["blocker"]
    assert any("point-in-time fundamentals" in item for item in record["minimal_fix"])


def test_rejected_card_stays_out_of_next_stage() -> None:
    record = builder.evidence_card_to_research_hypothesis_record(
        _card(
            classification__research_branch="out_of_scope",
            classification__downstream_route="reject_log",
            candidate_idea__required_inputs=[],
        )
    )

    assert record["research_hypothesis"]["next_action"] == "reject"
    assert record["research_hypothesis"]["required_data"] == ["not_applicable_rejected_or_out_of_scope"]
    assert record["next_stage_input"] is None
    assert "out_of_scope_or_rejected" in record["blocker"]


def test_build_research_hypotheses_writes_jsonl_csv_and_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "evidence_cards.jsonl"
    cards = [
        _card(evidence_card_id="ecard:convert"),
        _card(
            evidence_card_id="ecard:reject",
            classification__research_branch="out_of_scope",
            classification__downstream_route="reject_log",
        ),
    ]
    input_path.write_text(
        "".join(json.dumps(card, ensure_ascii=False) + "\n" for card in cards),
        encoding="utf-8",
    )

    paths = builder.build_research_hypotheses(input_path, tmp_path / "out", run_id="test_run")
    rows = [
        json.loads(line)
        for line in paths["jsonl"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert paths["csv"].exists()
    assert manifest["record_count"] == 2
    assert manifest["next_action_counts"]["convert_to_strategy_hypothesis"] == 1
    assert manifest["next_action_counts"]["reject"] == 1
    assert "not a score input" in manifest["research_boundary"]
