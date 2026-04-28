from __future__ import annotations

from pathlib import Path

import pytest

from research_ingestion.config import find_project_root, get_query_set, get_source_config, load_research_config, load_toml, validate_pdf_policy, validate_policy


def test_config_loading_from_project_root():
    config = load_research_config(Path(__file__).resolve().parents[2])
    validate_policy(config)
    assert get_source_config(config, "arxiv")["min_interval_seconds"] >= 3.0
    assert get_source_config(config, "openalex")["anonymous_allowed"] is False
    assert get_source_config(config, "nber")["pdf_download_enabled"] is False
    assert "nber" in config["policy"]["refresh_policy"]["default_sources"]
    assert config["policy"]["license_policy"]["allow_noncommercial_licenses"] is True
    technical_query = get_query_set(config, "technical_momentum")
    assert technical_query["queries"]
    assert technical_query["management_lane"] == "quant_algorithm"
    backtest_query = get_query_set(config, "backtest_methodology")
    assert backtest_query["branch_hint"] == "diagnostic"
    assert backtest_query["management_lane"] == "backtest_methodology"
    assert "backtest_methodology" in config["policy"]["refresh_policy"]["default_query_sets"]
    assert "isRetracted" in get_source_config(config, "semantic_scholar")["fields"]
    assert config["policy"]["guardrails"]["pdf_download_default"] is False
    assert config["policy"]["pdf_policy"]["allow_pdf"] is True
    assert config["policy"]["pdf_policy"]["max_downloads_per_run"] == 3
    assert config["policy"]["pdf_policy"]["allowed_manifest_categories"] == ["auto_cc", "noncommercial_cc"]
    assert config["policy"]["license_policy"]["fulltext_download_remains_disabled"] is False
    assert config["policy"]["license_policy"]["allowed_pdf_license_tokens"] == [
        "cc-by",
        "cc-by-sa",
        "cc-by-nd",
        "cc-by-nc",
        "cc-by-nc-sa",
        "cc-by-nc-nd",
    ]
    assert "elsevier-tdm" in config["policy"]["license_policy"]["blocked_fulltext_license_tokens"]
    assert "login_required_pdf" in config["policy"]["fulltext_access_policy"]["blocked_source_types"]
    assert config["policy"]["local_data_policy"]["generated_raw_fulltext_git_tracked_allowed"] is False


def test_expanded_query_sets_have_routing_metadata():
    config = load_research_config(Path(__file__).resolve().parents[2])
    expected_routes = {
        "technical_trend_efficiency": ("technical", "technical_score_architect"),
        "technical_time_series_momentum": ("technical", "technical_score_architect"),
        "technical_cross_sectional_momentum": ("technical", "technical_score_architect"),
        "technical_mean_reversion_extended": ("technical", "technical_score_architect"),
        "technical_oscillator_divergence": ("technical", "technical_score_architect"),
        "technical_breakout_confirmation": ("technical", "technical_score_architect"),
        "technical_volatility_regime": ("diagnostic", "diagnostic_backlog"),
        "technical_range_position": ("technical", "technical_score_architect"),
        "technical_liquidity_proxy_daily": ("diagnostic", "diagnostic_backlog"),
        "technical_volume_price_confirmation": ("technical", "technical_score_architect"),
        "technical_correlation_redundancy": ("diagnostic", "diagnostic_backlog"),
        "technical_rank_stability_diagnostics": ("diagnostic", "diagnostic_backlog"),
        "technical_turnover_cost_diagnostics": ("diagnostic", "diagnostic_backlog"),
        "methodology_multiple_testing": ("diagnostic", "diagnostic_backlog"),
        "methodology_survivorship_lookahead": ("diagnostic", "diagnostic_backlog"),
        "methodology_publication_bias": ("diagnostic", "diagnostic_backlog"),
        "korea_kospi_expanded": ("technical", "technical_score_architect"),
        "asia_pacific_equity_context": ("diagnostic", "diagnostic_backlog"),
        "emerging_market_equity_anomalies": ("diagnostic", "diagnostic_backlog"),
        "hybrid_technical_valuation_split": ("hybrid", "hybrid_split_required"),
    }

    for query_set_name, (branch, route) in expected_routes.items():
        query_set = get_query_set(config, query_set_name)
        assert query_set["name"] == query_set_name
        assert query_set["branch_hint"] == branch
        assert query_set["downstream_route"] == route
        assert query_set["allowed_sources"] == ["arxiv", "openalex", "crossref", "semantic_scholar", "nber"]
        assert query_set["region_scope"]
        assert query_set["required_input_policy"]
        assert query_set["refresh_cadence_days"] >= 14
        assert query_set["precision_mode"] in {"balanced", "high_precision"}
        assert query_set["notes"]

    assert "technical_cross_sectional_momentum" in config["policy"]["refresh_policy"]["default_query_sets"]
    assert "hybrid_technical_valuation_split" not in config["policy"]["refresh_policy"]["default_query_sets"]


def test_core_query_sets_have_routing_metadata_for_handoff():
    config = load_research_config(Path(__file__).resolve().parents[2])
    expected_routes = {
        "technical_momentum": ("technical", "technical_score_architect"),
        "technical_mean_reversion": ("technical", "technical_score_architect"),
        "technical_breakout": ("technical", "technical_score_architect"),
        "technical_volatility_liquidity": ("technical", "technical_score_architect"),
        "methodology_diagnostics": ("diagnostic", "diagnostic_backlog"),
        "backtest_methodology": ("diagnostic", "diagnostic_backlog"),
        "fundamental_valuation": ("valuation", "valuation_agent_handoff"),
        "korea_kospi_context": ("technical", "technical_score_architect"),
    }

    for query_set_name, (branch, route) in expected_routes.items():
        query_set = get_query_set(config, query_set_name)
        assert query_set["branch_hint"] == branch
        assert query_set["downstream_route"] == route
        assert query_set["allowed_sources"]
        assert query_set["region_scope"]
        assert query_set["required_input_policy"]
        assert query_set["refresh_cadence_days"] >= 14
        assert query_set["precision_mode"]
        assert query_set["notes"]


def test_refresh_profiles_split_operational_modes_and_keep_valuation_opt_in():
    config = load_research_config(Path(__file__).resolve().parents[2])
    profiles = config["policy"]["refresh_profiles"]

    assert config["policy"]["refresh_policy"]["default_profile"] == "fast_refresh"
    assert profiles["fast_refresh"]["sources"] == ["openalex"]
    assert 5 <= len(profiles["fast_refresh"]["query_sets"]) <= 6
    assert len(profiles["full_refresh"]["query_sets"]) == 26
    assert "nber" in profiles["full_refresh"]["sources"]
    assert "nber" in profiles["diagnostic_refresh"]["sources"]
    assert "fundamental_valuation" not in profiles["full_refresh"]["query_sets"]
    assert "technical_correlation_redundancy" in profiles["diagnostic_refresh"]["query_sets"]
    assert "methodology_publication_bias" in profiles["diagnostic_refresh"]["query_sets"]
    assert profiles["regional_refresh"]["query_sets"] == [
        "korea_kospi_context",
        "korea_kospi_expanded",
        "asia_pacific_equity_context",
        "emerging_market_equity_anomalies",
    ]
    assert profiles["valuation_fundamental_opt_in"]["valuation_fundamental"] == "requires_cli_include_valuation"


def test_find_project_root_from_master_workspace():
    master_root = Path(__file__).resolve().parents[3]
    research_root = Path(__file__).resolve().parents[2]

    assert find_project_root(master_root) == research_root


def test_missing_config_handling(workspace_tmp_path):
    missing = workspace_tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError):
        load_toml(missing)


def test_pdf_enabled_policy_still_requires_explicit_confirmation():
    config = load_research_config(Path(__file__).resolve().parents[2])
    validate_pdf_policy(config, allow_pdf=False, confirmed=False)
    with pytest.raises(ValueError):
        validate_pdf_policy(config, allow_pdf=True, confirmed=False)
    validate_pdf_policy(config, allow_pdf=True, confirmed=True)
