from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.step19_pipeline import load_pipeline_config  # noqa: E402
from src.validation.step19_pipeline_guardrails import (  # noqa: E402
    find_step19_forbidden_language,
    validate_step19_generated_output_path,
    validate_step19_pipeline_config,
    validate_step19_pipeline_summary,
)


def base_config() -> dict[str, object]:
    return {
        "step19": {
            "default_run_mode": "dry_run",
            "network_allowed": False,
            "secrets_allowed": False,
            "local_cache_required": False,
        },
        "boundary": {
            "no_semantics_changed": True,
            "valuation_fundamental_scoring_activation": False,
            "technical_composite_score_integration": False,
            "final_composite_score_activation": False,
            "kosdaq150_expansion": False,
            "futures_expansion": False,
            "options_expansion": False,
            "external_data_ingestion": False,
            "step20_final_validation": False,
        },
        "stages": {
            "preflight": {
                "order": 10,
                "enabled": True,
                "implementation_ref": "src.pipeline.step19_pipeline",
                "input_refs": ["AGENTS.md"],
                "output_refs": ["reports/pipeline/generated/preflight.json"],
            },
            "latest_ranking": {
                "order": 20,
                "enabled": True,
                "implementation_ref": "src.scanner.latest_ranking",
                "input_refs": ["normalized_technical_score_frame"],
                "output_refs": ["Step 15 latest ranking snapshot"],
            },
            "security_detail_reports": {
                "order": 30,
                "enabled": True,
                "implementation_ref": "src.reports.security_detail_report",
                "input_refs": ["Step 15 latest ranking snapshot"],
                "output_refs": ["reports/security/generated/security.json"],
            },
            "conservative_backtest_optional": {
                "order": 40,
                "enabled": False,
                "optional": True,
                "implementation_ref": "Quant_mvp.backtest_mvp.engine",
                "input_refs": ["Step 15 latest ranking snapshot"],
                "output_refs": ["reports/backtest/generated/backtest.json"],
            },
        },
    }


def test_default_pipeline_config_passes_guardrails() -> None:
    config = load_pipeline_config(PROJECT_ROOT / "config/step19_pipeline.toml")

    result = validate_step19_pipeline_config(config)

    assert result.is_valid


def test_forbidden_valuation_and_fundamental_activation_is_caught() -> None:
    config = base_config()
    config["boundary"]["valuation_fundamental_scoring_activation"] = True
    config["stages"]["latest_ranking"]["output_fields"] = ["valuation_score"]

    with pytest.raises(ValueError, match="valuation_fundamental_scoring_activation"):
        validate_step19_pipeline_config(config)

    result = validate_step19_pipeline_config(config, raise_on_error=False)
    assert "valuation_score" in result.forbidden_fields


def test_backtest_output_feedback_loop_is_caught() -> None:
    config = base_config()
    config["stages"]["latest_ranking"]["input_refs"] = [
        "reports/backtest/generated/backtest.json"
    ]

    with pytest.raises(ValueError, match="feeds Step 17 outputs back upstream"):
        validate_step19_pipeline_config(config)


def test_backtest_generated_directory_feedback_loop_is_caught() -> None:
    config = base_config()
    config["stages"]["conservative_backtest_optional"]["output_refs"] = [
        "reports/backtest/generated/"
    ]
    config["stages"]["latest_ranking"]["input_refs"] = [
        "reports/backtest/generated/monthly_result.json"
    ]

    with pytest.raises(ValueError, match="feeds Step 17 outputs back upstream"):
        validate_step19_pipeline_config(config)


def test_return_feedback_field_is_caught_in_upstream_inputs() -> None:
    config = base_config()
    config["stages"]["raw_scores"] = {
        "order": 15,
        "enabled": True,
        "implementation_ref": "src.scores.technical_scores",
        "input_fields": ["backtest_period_return"],
        "output_refs": ["raw_technical_score_frame"],
    }

    with pytest.raises(ValueError, match="return/evaluation fields upstream"):
        validate_step19_pipeline_config(config)


def test_report_output_feedback_into_ranking_is_caught() -> None:
    config = base_config()
    config["stages"]["latest_ranking"]["input_refs"] = [
        "reports/security/generated/security.json"
    ]

    with pytest.raises(ValueError, match="Step 16 report output back into scoring/ranking"):
        validate_step19_pipeline_config(config)


def test_forbidden_trading_and_alpha_language_is_caught() -> None:
    summary = {
        "run_mode": "dry_run",
        "generated_at": "2026-04-26T00:00:00+00:00",
        "stages": [
            {
                "stage_name": "final_summary",
                "status": "completed",
                "input_refs": [],
                "output_refs": [],
                "warnings": ["buy recommendation and alpha proven"],
                "errors": [],
                "boundary_notes": [],
                "validation_status": "passed",
            }
        ],
        "overall_status": "completed",
        "validation_summary": {},
        "forbidden_scope_check": {},
        "no_semantics_changed_notice": "unchanged",
    }

    with pytest.raises(ValueError, match="forbidden language"):
        validate_step19_pipeline_summary(summary)
    assert find_step19_forbidden_language("not a buy recommendation") == []


def test_generated_output_path_boundary_blocks_data_cache_pollution() -> None:
    validate_step19_generated_output_path("reports/pipeline/generated/manifest.json")

    with pytest.raises(ValueError, match="forbidden data/cache/report area"):
        validate_step19_generated_output_path("chart_mvp/outputs/pipeline.json")

    with pytest.raises(ValueError, match="reports/\\*/generated"):
        validate_step19_generated_output_path("reports/pipeline/manifest.json")


def test_step20_completion_claims_are_rejected() -> None:
    summary = {
        "run_mode": "dry_run",
        "generated_at": "2026-04-26T00:00:00+00:00",
        "stages": [],
        "overall_status": "completed",
        "validation_summary": {},
        "forbidden_scope_check": {},
        "no_semantics_changed_notice": "Step 20 final validation complete",
    }

    with pytest.raises(ValueError, match="Step 20 completion claim"):
        validate_step19_pipeline_summary(summary)


def test_network_dependency_is_rejected() -> None:
    config = base_config()
    config["step19"]["network_allowed"] = True
    config["stages"]["preflight"]["network_required"] = True

    with pytest.raises(ValueError, match="network"):
        validate_step19_pipeline_config(config)
