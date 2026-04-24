from __future__ import annotations

from pathlib import Path

from research_ingestion.classify import classify_paper
from research_ingestion.cli import _write_evidence_outputs
from research_ingestion.config import ProjectPaths
from research_ingestion.config import load_research_config
from research_ingestion.evidence import generate_evidence_card, validate_evidence_card
from research_ingestion.persistence import read_jsonl


def test_evidence_card_schema_and_hard_guardrails(sample_paper):
    paper = sample_paper()
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "20260424_000000")
    validate_evidence_card(card)
    assert card["guardrails"]["paper_claim_not_verified"] is True
    assert card["guardrails"]["no_score_adopted"] is True
    assert card["guardrails"]["no_backtest_performed"] is True
    assert card["guardrails"]["valuation_not_inferred_from_price"] is True


def test_scholar_snippet_is_not_used_as_evidence(sample_paper):
    paper = dict(sample_paper())
    paper["scholar_snippet"] = "This Scholar-only snippet must not appear."
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "run")
    assert "Scholar-only" not in str(card["extraction"]["evidence_snippets_short"])


def test_retracted_item_is_flagged_conservatively(sample_paper):
    paper = sample_paper(is_retracted=True)
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "run")
    assert card["classification"]["manual_review_required"] is True
    assert card["classification"]["downstream_route"] == "reject_log"


def test_backtest_methodology_cards_are_written_to_separate_lane(sample_paper, workspace_tmp_path):
    paper = sample_paper(
        title="Backtesting momentum trading strategies",
        abstract="Walk forward out of sample validation and data snooping checks for equity strategies.",
        research_query_set="backtest_methodology",
        research_query_sets=["backtest_methodology"],
        research_management_lane="backtest_methodology",
        research_management_lanes=["backtest_methodology"],
        topics=[],
        fields_of_study=[],
    )
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "bt_run")

    _write_evidence_outputs(
        ProjectPaths(workspace_tmp_path),
        [card],
        run_id="bt_run",
        management_lane="backtest_methodology",
    )

    evidence_dir = workspace_tmp_path / "data" / "research" / "evidence"
    assert read_jsonl(evidence_dir / "bt_run_backtest_methodology_items.jsonl") == [card]
    assert read_jsonl(evidence_dir / "backtest_methodology_items.jsonl") == [card]
    assert not (evidence_dir / "technical_candidates.jsonl").exists()
