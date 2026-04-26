from __future__ import annotations

import sys
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.contracts import PipelineRunMode, PipelineStageStatus  # noqa: E402
from src.pipeline.step19_pipeline import (  # noqa: E402
    DEFAULT_STEP19_PIPELINE_CONFIG,
    build_default_stage_contracts,
    run_step19_pipeline,
)
from src.validation.step18_valuation_fundamental_guardrails import (  # noqa: E402
    assert_step18_no_production_leakage,
    assert_step18_no_score_contamination,
)
from src.validation.step15_latest_ranking_guardrails import (  # noqa: E402
    validate_step15_output_columns,
)


def test_dry_run_plan_does_not_create_production_outputs() -> None:
    summary_path = PROJECT_ROOT / "reports/pipeline/generated/step19_pipeline_summary.json"
    preexisting_summary = summary_path.exists()

    summary = run_step19_pipeline(
        config_path=DEFAULT_STEP19_PIPELINE_CONFIG,
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=PROJECT_ROOT,
    )

    assert summary.run_mode == PipelineRunMode.DRY_RUN
    assert summary.overall_status == PipelineStageStatus.COMPLETED
    assert summary_path.exists() is preexisting_summary
    assert all(
        not result.output_refs
        for result in summary.stages
        if result.status == PipelineStageStatus.READY
    )
    assert summary.validation_summary["network_required"] is False
    assert summary.validation_summary["secrets_required"] is False


def test_stage_order_is_deterministic_and_selected_stage_aliases_are_supported() -> None:
    contracts = build_default_stage_contracts()
    assert [contract.order for contract in contracts] == sorted(
        contract.order for contract in contracts
    )

    summary = run_step19_pipeline(
        config_path=DEFAULT_STEP19_PIPELINE_CONFIG,
        selected_stages=["ranking"],
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=PROJECT_ROOT,
    )

    assert summary.selected_stages == (
        "preflight",
        "context_check",
        "latest_ranking",
        "output_validation",
        "final_summary",
    )
    latest = _stage(summary, "latest_ranking")
    assert latest.status == PipelineStageStatus.READY
    assert "Step 15" in " ".join(latest.boundary_notes)
    assert _stage(summary, "security_detail_reports").status == PipelineStageStatus.SKIPPED


def test_validate_only_mode_completes_validation_without_domain_execution() -> None:
    summary = run_step19_pipeline(
        config_path=DEFAULT_STEP19_PIPELINE_CONFIG,
        run_mode="validate_only",
        selected_stages=["validation_only"],
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=PROJECT_ROOT,
    )

    assert summary.run_mode == PipelineRunMode.VALIDATE_ONLY
    assert _stage(summary, "output_validation").status == PipelineStageStatus.COMPLETED
    assert "validate-only" in " ".join(_stage(summary, "output_validation").warnings)


def test_run_allowed_selected_stage_reports_contract_completion() -> None:
    summary = run_step19_pipeline(
        config_path=DEFAULT_STEP19_PIPELINE_CONFIG,
        run_mode="run_allowed_stages",
        selected_stages=["ranking"],
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=PROJECT_ROOT,
    )

    assert summary.run_mode == PipelineRunMode.RUN_ALLOWED_STAGES
    latest = _stage(summary, "latest_ranking")
    assert latest.status == PipelineStageStatus.COMPLETED
    assert latest.output_refs == ("Step 15 latest ranking snapshot",)
    assert any("semantics are unchanged" in warning for warning in latest.warnings)


def test_missing_required_input_is_blocked(tmp_path: Path) -> None:
    config_path = tmp_path / "missing_input_pipeline.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            [step19]
            default_run_mode = "dry_run"
            network_allowed = false
            secrets_allowed = false
            local_cache_required = false

            [boundary]
            no_semantics_changed = true
            valuation_fundamental_scoring_activation = false
            technical_composite_score_integration = false
            final_composite_score_activation = false
            kosdaq150_expansion = false
            futures_expansion = false
            options_expansion = false
            external_data_ingestion = false
            step20_final_validation = false

            [stages.preflight]
            order = 10
            enabled = true
            implementation_ref = "src.pipeline.step19_pipeline"
            required_input_paths = ["missing_required_input.csv"]
            output_refs = ["reports/pipeline/generated/missing_input_summary.json"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    summary = run_step19_pipeline(
        config_path=config_path,
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=tmp_path,
    )

    assert summary.overall_status == PipelineStageStatus.BLOCKED
    preflight = _stage(summary, "preflight")
    assert preflight.status == PipelineStageStatus.BLOCKED
    assert "missing_required_input.csv" in " ".join(preflight.errors)
    assert summary.forbidden_scope_check["status"] == "blocked"


def test_pipeline_summary_schema_is_stable() -> None:
    summary = run_step19_pipeline(
        config_path=DEFAULT_STEP19_PIPELINE_CONFIG,
        generated_at="2026-04-26T00:00:00+00:00",
        git_commit="test",
        project_root=PROJECT_ROOT,
    ).to_dict()

    assert tuple(summary.keys()) == (
        "run_mode",
        "generated_at",
        "git_commit",
        "selected_stages",
        "skipped_stages",
        "stages",
        "overall_status",
        "validation_summary",
        "forbidden_scope_check",
        "no_semantics_changed_notice",
        "boundary_notice",
    )
    assert {
        "stage_name",
        "status",
        "input_refs",
        "output_refs",
        "warnings",
        "errors",
        "boundary_notes",
        "validation_status",
    }.issubset(summary["stages"][0].keys())


def test_existing_step15_and_step18_boundaries_remain_available() -> None:
    validate_step15_output_columns(
        [
            "ticker",
            "date",
            "rank",
            "technical_composite_score",
            "final_composite_score",
            "coverage_metric",
            "data_quality_flag",
        ]
    )
    assert_step18_no_production_leakage(["ticker", "date", "rank"])
    assert_step18_no_score_contamination(["technical_composite_score", "final_composite_score"])


def _stage(summary, stage_name: str):
    for result in summary.stages:
        if result.stage_name == stage_name:
            return result
    raise AssertionError(f"missing stage: {stage_name}")
