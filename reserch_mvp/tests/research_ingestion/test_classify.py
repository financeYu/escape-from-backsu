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
    assert "classify_required_inputs_boundary" in result["rule_names"]


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
    assert "classify_methodology_diagnostic" in result["rule_names"]


def test_required_fundamental_inputs_never_route_to_technical(sample_paper):
    paper = sample_paper(
        title="Momentum with PER PBR and ROE filters",
        abstract="We define a daily momentum signal combined with PER, PBR, ROE, earnings, and book value inputs.",
        required_inputs=["daily_ohlcv", "PER", "PBR", "ROE", "earnings", "book value"],
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "hybrid"
    assert result["downstream_route"] == "hybrid_split_required"
    assert result["main_score_branch_candidate"] == "unavailable"
    assert result["candidate_idea"]["point_in_time_fundamentals_required"] is True


def test_diagnostic_query_hint_overrides_technical_terms(sample_paper):
    paper = sample_paper(
        title="Rank stability for momentum stock ranking",
        abstract="We define rank stability diagnostics for momentum and turnover without creating a trading signal.",
        research_query_set="technical_rank_stability_diagnostics",
        research_query_sets=["technical_rank_stability_diagnostics"],
        research_branch_hint="diagnostic",
        research_branch_hints=["diagnostic"],
        research_management_lane="technical_diagnostics",
        research_management_lanes=["technical_diagnostics"],
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "diagnostic"
    assert result["downstream_route"] == "diagnostic_backlog"
    assert result["main_score_branch_candidate"] == "diagnostic"


def test_market_context_without_formula_routes_to_diagnostic(sample_paper):
    paper = sample_paper(
        title="KOSPI market context for stock returns",
        abstract="Korean equity market context.",
        research_query_set="korea_kospi_expanded",
        research_query_sets=["korea_kospi_expanded"],
        research_branch_hint="technical",
        research_branch_hints=["technical"],
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "diagnostic"
    assert result["downstream_route"] == "diagnostic_backlog"
    assert result["manual_review_required"] is True
    assert "classify_market_context_transfer_risk" in result["rule_names"]


def test_forbidden_valuation_language_on_price_only_technical_is_rejected(sample_paper):
    paper = sample_paper(
        title="Cheap RSI reversal with daily returns",
        abstract="We define an RSI reversal signal from daily OHLCV and describe the oversold stock as cheap.",
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "out_of_scope"
    assert result["downstream_route"] == "reject_log"
    assert result["guardrail_violations"] == ["language_guardrail_violation"]
    assert "classify_forbidden_valuation_language" in result["rule_names"]


def test_forbidden_valuation_language_rejected_even_with_diagnostic_hint(sample_paper):
    paper = sample_paper(
        title="Cheap RSI reversal diagnostics",
        abstract="We define a daily RSI reversal signal from daily OHLCV and call the oversold stock cheap.",
        research_query_set="technical_rank_stability_diagnostics",
        research_query_sets=["technical_rank_stability_diagnostics"],
        research_branch_hint="diagnostic",
        research_branch_hints=["diagnostic"],
        research_management_lane="technical_diagnostics",
        research_management_lanes=["technical_diagnostics"],
        topics=[],
        fields_of_study=[],
    )
    result = classify_paper(paper, *_config())
    assert result["research_branch"] == "out_of_scope"
    assert result["downstream_route"] == "reject_log"
    assert result["guardrail_violations"] == ["language_guardrail_violation"]
    assert "classify_forbidden_valuation_language" in result["rule_names"]


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
    assert result["paper_reported_backtest_treatment"] == "diagnostic_note_only"


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
