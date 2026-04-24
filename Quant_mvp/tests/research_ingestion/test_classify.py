from __future__ import annotations

from pathlib import Path

from research_ingestion.classify import classify_paper
from research_ingestion.config import load_research_config
from research_ingestion.dedupe import deduplicate_papers


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


def test_backtest_methodology_lane_overrides_algorithm_terms(sample_paper):
    paper = sample_paper(
        title="Backtesting momentum trading strategies",
        abstract="Walk forward out of sample validation for equity momentum strategies.",
        research_query_set="backtest_methodology",
        research_query_sets=["backtest_methodology"],
        research_management_lane="backtest_methodology",
        research_management_lanes=["backtest_methodology"],
        topics=[],
        fields_of_study=[],
    )

    result = classify_paper(paper, *_config())

    assert result["research_branch"] == "diagnostic"
    assert result["downstream_route"] == "diagnostic_backlog"
    assert result["main_score_branch_candidate"] == "diagnostic"
    assert result["management_lane"] == "backtest_methodology"
    assert result["candidate_idea"]["signal_family_candidate"] is None


def test_backtest_methodology_lane_survives_dedupe_with_technical_primary(sample_paper):
    technical_paper = sample_paper(
        doi="10.1000/backtest-shared",
        title="Backtesting momentum trading strategies",
        abstract="Walk forward out of sample validation for equity momentum strategies.",
        research_query_set="technical_momentum",
        research_query_sets=["technical_momentum"],
        research_management_lane="quant_algorithm",
        research_management_lanes=["quant_algorithm"],
        topics=[],
        fields_of_study=[],
    )
    backtest_paper = sample_paper(
        doi="10.1000/backtest-shared",
        title="Backtesting momentum trading strategies",
        abstract="Walk forward out of sample validation for equity momentum strategies.",
        research_query_set="backtest_methodology",
        research_query_sets=["backtest_methodology"],
        research_management_lane="backtest_methodology",
        research_management_lanes=["backtest_methodology"],
        topics=[],
        fields_of_study=[],
    )

    merged = deduplicate_papers([technical_paper, backtest_paper])
    assert len(merged) == 1
    merged_paper = next(iter(merged))
    result = classify_paper(merged_paper, *_config())

    assert merged_paper["research_management_lanes"] == ["quant_algorithm", "backtest_methodology"]
    assert result["research_branch"] == "diagnostic"
    assert result["downstream_route"] == "diagnostic_backlog"
    assert result["management_lane"] == "backtest_methodology"
