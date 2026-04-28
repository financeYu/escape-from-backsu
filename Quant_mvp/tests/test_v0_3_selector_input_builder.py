"""Tests for v0.3 candidate-only selector input automation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_v0_3_selector_inputs.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_selector_inputs", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _card(**overrides):
    payload = {
        "evidence_card_id": "ecard:test",
        "parent_evidence_card_id": None,
        "source_run_id": "run",
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
            "evidence_snippets_short": ["This must not be exported as a selector field."],
        },
        "backtest_context": {
            "paper_reported_backtest_present": False,
            "reproducibility_level": "not_reported",
            "transaction_costs_discussed": False,
            "lookahead_bias_discussed": False,
            "survivorship_bias_discussed": False,
        },
        "risks": {
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


def test_technical_daily_ohlcv_card_is_selector_eligible() -> None:
    record = builder.evidence_card_to_selector_record(_card())

    assert record["ml_use_status"] == "eligible_for_candidate_selector_review"
    assert record["paper_claim_language_present"] is False
    assert record["risk_flags"] == ["data_snooping_risk_flag", "transaction_cost_missing_flag"]
    assert record["blocked_reasons"] == []
    assert record["no_feedback_check"] == "must_not_feed_scores_rankings_reports_models_or_auto_adoption"
    assert "idea_summary_en" not in record
    assert "evidence_snippets_short" not in record
    assert "source_urls" not in record
    assert "final_composite_score" not in record
    assert "technical_composite_score" not in record


@pytest.mark.parametrize(
    ("branch", "route", "expected"),
    (
        ("valuation", "valuation_agent_handoff", "excluded_valuation_lane"),
        ("hybrid", "hybrid_split_required", "needs_hybrid_split"),
        ("diagnostic", "diagnostic_backlog", "diagnostic_context_only"),
        ("out_of_scope", "reject_log", "excluded_rejected_or_out_of_scope"),
    ),
)
def test_non_technical_cards_are_kept_with_review_status(branch: str, route: str, expected: str) -> None:
    record = builder.evidence_card_to_selector_record(
        _card(
            classification__research_branch=branch,
            classification__downstream_route=route,
        )
    )

    assert record["ml_use_status"] == expected
    assert record["blocked_reasons"]


def test_selector_record_requires_research_guardrails() -> None:
    with pytest.raises(ValueError, match="no_score_adopted"):
        builder.evidence_card_to_selector_record(_card(guardrails__no_score_adopted=False))


def test_paper_claim_language_is_reduced_to_boolean_flag() -> None:
    record = builder.evidence_card_to_selector_record(
        _card(
            candidate_idea__idea_summary_en=(
                "The paper reports a profitable trading strategy with strong performance."
            )
        )
    )

    assert record["paper_claim_language_present"] is True
    assert "profitable trading strategy" not in json.dumps(record)


def test_build_selector_inputs_writes_jsonl_csv_and_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "evidence_cards.jsonl"
    cards = [
        _card(evidence_card_id="ecard:eligible"),
        _card(
            evidence_card_id="ecard:valuation",
            classification__research_branch="valuation",
            classification__downstream_route="valuation_agent_handoff",
        ),
    ]
    input_path.write_text(
        "".join(json.dumps(card, ensure_ascii=False) + "\n" for card in cards),
        encoding="utf-8",
    )

    paths = builder.build_selector_inputs(input_path, tmp_path / "out", run_id="test_run")

    rows = [
        json.loads(line)
        for line in paths["jsonl"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert paths["csv"].exists()
    assert manifest["record_count"] == 2
    assert manifest["ml_use_status_counts"]["eligible_for_candidate_selector_review"] == 1
    assert manifest["ml_use_status_counts"]["excluded_valuation_lane"] == 1
    assert "production ranking input" in manifest["selector_input_boundary"]
