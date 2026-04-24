from __future__ import annotations

from pathlib import Path

from research_ingestion.classify import classify_paper
from research_ingestion.config import load_research_config


def _config():
    config = load_research_config(Path(__file__).resolve().parents[2])
    return config["classification"], config["policy"]


def test_classification_branch_and_route_technical(sample_paper):
    classification_config, policy = _config()
    result = classify_paper(sample_paper(), classification_config, policy)
    assert result["research_branch"] == "technical"
    assert result["downstream_route"] == "technical_score_architect"
    assert result["main_score_branch_candidate"] == "technical"


def test_classification_routes_valuation_to_handoff(sample_paper):
    paper = sample_paper(
        title="Book to market and earnings yield",
        abstract="Book to market requires point in time fundamentals.",
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "valuation"
    assert result["downstream_route"] == "valuation_agent_handoff"
    assert result["main_score_branch_candidate"] == "unavailable"
    assert result["candidate_idea"]["point_in_time_fundamentals_required"] is True


def test_classification_routes_hybrid_to_manual_review(sample_paper):
    paper = sample_paper(title="Momentum and book-to-market", abstract="Momentum and book to market combine technical and fundamental inputs.")
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "hybrid"
    assert result["downstream_route"] == "hybrid_split_required"
    assert result["manual_review_required"] is True


def test_diagnostic_kept_out_of_alpha_signal_route(sample_paper):
    paper = sample_paper(
        title="Backtest overfitting and transaction cost diagnostics",
        abstract="Data snooping and transaction cost diagnostics.",
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "diagnostic"
    assert result["downstream_route"] == "diagnostic_backlog"
