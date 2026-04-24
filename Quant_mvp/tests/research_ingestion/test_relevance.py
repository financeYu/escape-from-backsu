from __future__ import annotations

from research_ingestion.relevance import apply_collection_relevance_gate, assess_collection_relevance


QUERY_SET = {
    "keywords": ["momentum", "daily returns", "technical analysis"],
    "exclude_keywords": ["crypto", "options", "intraday", "order book"],
}

GROUPED_QUERY_SET = {
    "keywords": ["momentum", "stock returns", "daily returns", "technical analysis"],
    "exclude_keywords": ["crypto", "options", "intraday", "order book"],
    "required_keyword_groups": [
        {"name": "signal", "keywords": ["momentum", "relative strength"]},
        {"name": "market_context", "keywords": ["stock", "equity", "returns", "technical analysis"]},
    ],
}

BACKTEST_QUERY_SET = {
    "keywords": ["backtest", "backtesting", "walk forward", "out of sample", "data snooping", "transaction costs"],
    "exclude_keywords": ["intraday", "order book", "crypto"],
    "required_keyword_groups": [
        {"name": "backtest_method", "keywords": ["backtest", "backtesting", "walk forward", "out of sample"]},
        {"name": "validation_risk", "keywords": ["data snooping", "transaction costs", "survivorship bias"]},
    ],
}


def test_relevance_accepts_matching_quant_metadata(sample_paper):
    paper = sample_paper(
        title="Momentum and daily returns in equity markets",
        abstract="We study technical analysis signals for stock momentum.",
    )

    result = assess_collection_relevance(paper, QUERY_SET)

    assert result["status"] == "accepted"
    assert "momentum" in result["positive_keyword_hits"]
    assert result["manual_review_required"] is False


def test_relevance_rejects_excluded_domains(sample_paper):
    paper = sample_paper(
        title="Crypto options order book momentum",
        abstract="Intraday order book prediction for crypto options.",
    )

    result = assess_collection_relevance(paper, QUERY_SET)

    assert result["status"] == "rejected"
    assert "crypto" in result["exclude_keyword_hits"]
    assert result["manual_review_required"] is True


def test_relevance_rejects_unrelated_metadata(sample_paper):
    paper = sample_paper(
        title="Neural protein folding benchmark",
        abstract="A biology benchmark with no market metadata.",
        topics=[],
        fields_of_study=[],
    )

    result = assess_collection_relevance(paper, QUERY_SET)

    assert result["status"] == "rejected"
    assert result["positive_keyword_hits"] == []


def test_relevance_marks_missing_abstract_for_manual_review(sample_paper):
    paper = sample_paper(
        title="Daily returns and momentum in equities",
        abstract=None,
    )

    accepted, rejected = apply_collection_relevance_gate([paper], QUERY_SET)

    assert not rejected
    assert accepted[0]["manual_review_required"] is True
    assert accepted[0]["collection_relevance"]["abstract_available"] is False


def test_relevance_required_groups_reject_single_word_momentum_false_positive(sample_paper):
    paper = sample_paper(
        title="Momentum conservation in finite volume schemes",
        abstract="We study momentum fields in incompressible flow simulations.",
        topics=[],
        fields_of_study=[],
    )

    result = assess_collection_relevance(paper, GROUPED_QUERY_SET)

    assert result["status"] == "rejected"
    assert result["required_keyword_group_hits"]["signal"] == ["momentum"]
    assert result["required_keyword_group_hits"]["market_context"] == []


def test_relevance_required_groups_accept_finance_momentum_context(sample_paper):
    paper = sample_paper(
        title="Momentum and stock returns",
        abstract="We study momentum effects in equity returns using daily data.",
    )

    result = assess_collection_relevance(paper, GROUPED_QUERY_SET)

    assert result["status"] == "accepted"
    assert result["required_keyword_group_hits"]["signal"] == ["momentum"]
    assert "returns" in result["required_keyword_group_hits"]["market_context"]


def test_relevance_accepts_backtest_methodology_lane(sample_paper):
    paper = sample_paper(
        title="Backtesting trading strategies under transaction costs",
        abstract="We study walk forward out of sample validation and data snooping risk in equity strategy evaluation.",
    )

    result = assess_collection_relevance(paper, BACKTEST_QUERY_SET)

    assert result["status"] == "accepted"
    assert "backtesting" in result["required_keyword_group_hits"]["backtest_method"]
    assert "data snooping" in result["required_keyword_group_hits"]["validation_risk"]


def test_relevance_rejects_algorithm_only_paper_from_backtest_lane(sample_paper):
    paper = sample_paper(
        title="A new momentum indicator for stock returns",
        abstract="We define a technical analysis signal using daily prices and volume.",
    )

    result = assess_collection_relevance(paper, BACKTEST_QUERY_SET)

    assert result["status"] == "rejected"
    assert "backtest_method" in result["reason_ko"]
