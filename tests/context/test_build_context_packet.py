from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "context" / "build_context_packet.py"
SPEC = importlib.util.spec_from_file_location("build_context_packet", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_packet_generation_for_step20_final_validation(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    output = tmp_path / "docs/context/generated/step20_final_validation_packet.md"
    config = module.PacketConfig(
        project_root=tmp_path,
        task="step20_final_validation",
        step="Step 20",
        stage="pre-start routing",
        output_path=output,
    )

    result = module.write_context_packet(config)

    text = output.read_text(encoding="utf-8")
    assert result.output_path == output
    assert "`step20_final_validation`" in text
    assert "`docs/context/MVP_V0_1_BASELINE.md` - FOUND" in text
    assert "`docs/context/active_step20_packet.md` - FOUND" in text
    assert "`docs/context/current_context.md` - FOUND" in text
    assert "`docs/context/context_usage_policy.md` - FOUND" in text
    assert "`docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml` - FOUND" in text
    assert "`docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md` - FOUND" not in text
    assert "Generated context packets are routing aids, not authority documents" in text
    assert "Step 20 final-validation routing" in text


def test_packet_generation_for_planning_only(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    config = module.PacketConfig(
        project_root=tmp_path,
        task="planning_only",
        step="Pre-Step20",
        stage="planning",
        output_path=tmp_path / "packet.md",
    )

    text = module.build_context_packet(config)

    assert "`planning_only`" in text
    assert "`docs/context/context_usage_policy.md` - FOUND" in text
    assert "`docs/context/CONTEXT_BUDGET_POLICY.md` - FOUND" not in text
    assert "no more than three context facts" in text


def test_missing_referenced_files_are_reported(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path, include_missing_route=True)
    config = module.PacketConfig(
        project_root=tmp_path,
        task="missing_reference_task",
        step="Pre-Step19",
        stage="missing-ref",
        output_path=tmp_path / "packet.md",
    )

    text = module.build_context_packet(config)

    assert "`docs/missing_context.md` - MISSING" in text
    assert "## Missing Referenced Files" in text
    assert "`docs/missing_context.md`" in text


def test_archive_files_are_not_embedded_by_default(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    archive = tmp_path / "docs/context/archive/step01_to_step19_summary.md"
    archive.parent.mkdir(parents=True)
    archive.write_text("OLD HISTORY SENTINEL SHOULD NOT APPEAR", encoding="utf-8")
    config = module.PacketConfig(
        project_root=tmp_path,
        task="step20_final_validation",
        step="Step 20",
        stage="pre-start routing",
        output_path=tmp_path / "packet.md",
    )

    text = module.build_context_packet(config)

    assert "OLD HISTORY SENTINEL SHOULD NOT APPEAR" not in text
    assert "`docs/context/archive/step01_to_step19_summary.md` - FOUND" not in text


def test_gpt_brief_mode_generates_route_only_context(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    (tmp_path / "docs/context/GPT_CONTEXT_GENERATION_RULES.md").write_text("rules", encoding="utf-8")
    (tmp_path / "docs/context/CONTEXT_ROUTING_INDEX.md").write_text("routes", encoding="utf-8")
    config = module.GptBriefConfig(
        project_root=tmp_path,
        request="Draft a GPT prompt.",
        output_path=tmp_path / "docs/context/generated/gpt_brief.md",
    )

    result = module.write_gpt_brief(config)

    text = result.output_path.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 80
    assert "Generated only after an explicit user request" in text
    assert "Draft a GPT prompt." in text
    assert "Post-MVP v0.3 research-to-strategy adoption is the active route." in text
    assert "Post-v1.0 v1.x staged release development is active" in text
    assert "v1.1-v1.5 are upstream evidence/status layers" in text
    assert "v0.2 `prob_up_1d_candidate` is archived/supporting compatibility only" in text
    assert "## North-Star Goal Memory" in text
    assert "review-preferred candidates with repeatable historical risk-adjusted support" in text
    assert "## Conditions And Gaps To Report" in text
    assert "valuation activation remains blocked" in text
    assert "Do not repeat completed Step history" in text
    assert "`docs/context/MVP_V0_1_BASELINE.md` - FOUND" in text
    assert "`docs/extension/v1_x_staged_release_plan.md` - FOUND" in text
    assert "`docs/extension/v1_6_confidence_robustness_review_priority.md` - FOUND" in text
    assert "GPT_CONTEXT_GENERATION_RULES.md" not in text
    assert "| Step 1 |" not in text


def test_gpt_brief_default_output_is_project_context_doc(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    output = module.DEFAULT_GPT_BRIEF_OUTPUT

    assert str(output).replace("\\", "/") == "docs/context/gpt/gpt_context_quant.md"


def test_request_only_cli_requires_explicit_gpt_brief_mode(tmp_path: Path, capsys) -> None:
    _write_minimal_context_project(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        module.main(["--project-root", str(tmp_path), "--request", "Draft a GPT prompt."])

    captured = capsys.readouterr()
    output = tmp_path / "docs/context/gpt/gpt_context_quant.md"
    assert exc_info.value.code == 2
    assert not output.exists()
    assert "--mode gpt-brief --user-requested --request" in captured.err


def test_gpt_brief_cli_requires_active_request_text(tmp_path: Path, capsys) -> None:
    _write_minimal_context_project(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        module.main(["--project-root", str(tmp_path), "--mode", "gpt-brief", "--user-requested"])

    captured = capsys.readouterr()
    output = tmp_path / "docs/context/gpt/gpt_context_quant.md"
    assert exc_info.value.code == 2
    assert not output.exists()
    assert "without --request" in captured.err


def test_gpt_brief_builder_rejects_blank_request(tmp_path: Path) -> None:
    _write_minimal_context_project(tmp_path)
    config = module.GptBriefConfig(
        project_root=tmp_path,
        request="  ",
        output_path=tmp_path / "docs/context/generated/gpt_brief.md",
    )

    with pytest.raises(ValueError, match="requires --request"):
        module.build_gpt_brief(config)


def test_explicit_gpt_brief_cli_writes_separate_context_path(tmp_path: Path, capsys) -> None:
    _write_minimal_context_project(tmp_path)

    exit_code = module.main(
        [
            "--project-root",
            str(tmp_path),
            "--mode",
            "gpt-brief",
            "--user-requested",
            "--request",
            "Draft a GPT prompt.",
        ]
    )

    captured = capsys.readouterr()
    output = tmp_path / "docs/context/gpt/gpt_context_quant.md"
    assert exit_code == 0
    assert output.exists()
    assert "Draft a GPT prompt." in output.read_text(encoding="utf-8")
    assert Path(json.loads(captured.out)["output_path"]) == output


def _write_minimal_context_project(tmp_path: Path, *, include_missing_route: bool = False) -> None:
    (tmp_path / "docs/context/domain").mkdir(parents=True)
    (tmp_path / "docs/context/generated").mkdir(parents=True)
    (tmp_path / "docs/context/active_step20_packet.md").write_text("active", encoding="utf-8")
    (tmp_path / "docs/context/MVP_V0_1_BASELINE.md").write_text("baseline", encoding="utf-8")
    (tmp_path / "docs/context/EXTENSION_REGISTRY.toml").write_text("status = \"test\"", encoding="utf-8")
    (tmp_path / "docs/extension").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/extension/v1_x_staged_release_plan.md").write_text("v1.x", encoding="utf-8")
    (tmp_path / "docs/extension/v1_1_net_profitability_evidence_runner.md").write_text("v1.1", encoding="utf-8")
    (tmp_path / "docs/extension/v1_2_baseline_ml_selector_application.md").write_text("v1.2", encoding="utf-8")
    (tmp_path / "docs/extension/v1_3_cost_turnover_liquidity_reliability_layer.md").write_text("v1.3", encoding="utf-8")
    (tmp_path / "docs/extension/v1_4_revision_layer.md").write_text("v1.4", encoding="utf-8")
    (tmp_path / "docs/extension/v1_5_valuation_quality_profitability_layer.md").write_text("v1.5", encoding="utf-8")
    (tmp_path / "docs/extension/v1_6_confidence_robustness_review_priority.md").write_text("v1.6", encoding="utf-8")
    (tmp_path / "docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml").write_text("status = \"routing_only\"", encoding="utf-8")
    (tmp_path / "docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md").write_text("active", encoding="utf-8")
    (tmp_path / "docs/context/current_context.md").write_text("current", encoding="utf-8")
    (tmp_path / "docs/context/context_usage_policy.md").write_text("usage", encoding="utf-8")
    (tmp_path / "docs/context/decision_log.md").write_text("decision", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("agents", encoding="utf-8")
    (tmp_path / "WORKSPACE_MANIFEST.md").write_text("manifest", encoding="utf-8")
    (tmp_path / "docs/project_checklist.md").write_text("checklist", encoding="utf-8")
    (tmp_path / "docs/roadmap_status.md").write_text("roadmap", encoding="utf-8")
    (tmp_path / "docs/context/context_index.md").write_text("index", encoding="utf-8")
    (tmp_path / "docs/context/CONTEXT_BUDGET_POLICY.md").write_text("budget", encoding="utf-8")
    (tmp_path / "docs/workspace_parallel_work_policy.md").write_text("policy", encoding="utf-8")
    (tmp_path / "docs/scope_audit_process.md").write_text("audit", encoding="utf-8")
    (tmp_path / "docs/cross_step_conflict_check.md").write_text("checkpoint", encoding="utf-8")
    routes = [
        "| Task type | required_context | optional_context | forbidden_or_do_not_read_unless_needed | allowed_scope | forbidden_scope | escalation_conditions | validation_expectations |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        "| `step20_final_validation` | `docs/context/active_step20_packet.md`, `docs/context/current_context.md`, `docs/context/context_usage_policy.md`, `docs/cross_step_conflict_check.md` | `docs/context/decision_log.md` | archives/history | Step 20 final-validation routing | implementation changes | missing evidence | final Step verdict |",
        "| `planning_only` | `docs/context/current_context.md`, `docs/context/context_usage_policy.md`, `docs/context/context_routing.md` | none | archives/history | no more than three context facts | repeating history | status contradiction | separate facts from reasoning |",
    ]
    if include_missing_route:
        routes.append(
            "| `missing_reference_task` | `docs/missing_context.md` | none | archive | docs only | runtime changes | missing contract | focused check |"
        )
    (tmp_path / "docs/context/context_routing.md").write_text("\n".join(routes), encoding="utf-8")
