from __future__ import annotations

from pathlib import Path

from research_ingestion.classify import classify_paper
from research_ingestion.config import load_research_config
from research_ingestion.evidence import generate_evidence_card, validate_evidence_card


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
