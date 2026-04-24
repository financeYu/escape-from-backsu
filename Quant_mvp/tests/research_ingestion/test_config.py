from __future__ import annotations

from pathlib import Path

import pytest

from research_ingestion.config import find_project_root, get_query_set, get_source_config, load_research_config, load_toml, validate_pdf_policy, validate_policy


def test_config_loading_from_project_root():
    config = load_research_config(Path(__file__).resolve().parents[2])
    validate_policy(config)
    assert get_source_config(config, "arxiv")["min_interval_seconds"] >= 3.0
    assert get_source_config(config, "openalex")["anonymous_allowed"] is False
    technical_query = get_query_set(config, "technical_momentum")
    assert technical_query["queries"]
    assert technical_query["management_lane"] == "quant_algorithm"
    backtest_query = get_query_set(config, "backtest_methodology")
    assert backtest_query["branch_hint"] == "diagnostic"
    assert backtest_query["management_lane"] == "backtest_methodology"
    assert "backtest_methodology" in config["policy"]["refresh_policy"]["default_query_sets"]
    assert "isRetracted" in get_source_config(config, "semantic_scholar")["fields"]
    assert config["policy"]["guardrails"]["pdf_download_default"] is False


def test_find_project_root_from_master_workspace():
    master_root = Path(__file__).resolve().parents[3]
    quant_root = Path(__file__).resolve().parents[2]

    assert find_project_root(master_root) == quant_root


def test_missing_config_handling(workspace_tmp_path):
    missing = workspace_tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError):
        load_toml(missing)


def test_pdf_disabled_by_default_and_allow_pdf_requires_policy():
    config = load_research_config(Path(__file__).resolve().parents[2])
    validate_pdf_policy(config, allow_pdf=False, confirmed=False)
    with pytest.raises(ValueError):
        validate_pdf_policy(config, allow_pdf=True, confirmed=True)
