from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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
    assert "`docs/context/active_step20_packet.md` - FOUND" in text
    assert "`docs/context/current_context.md` - FOUND" in text
    assert "`docs/context/context_usage_policy.md` - FOUND" in text
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


def _write_minimal_context_project(tmp_path: Path, *, include_missing_route: bool = False) -> None:
    (tmp_path / "docs/context/domain").mkdir(parents=True)
    (tmp_path / "docs/context/generated").mkdir(parents=True)
    (tmp_path / "docs/context/active_step20_packet.md").write_text("active", encoding="utf-8")
    (tmp_path / "docs/context/current_context.md").write_text("current", encoding="utf-8")
    (tmp_path / "docs/context/context_usage_policy.md").write_text("usage", encoding="utf-8")
    (tmp_path / "docs/context/decision_log.md").write_text("decision", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("agents", encoding="utf-8")
    (tmp_path / "WORKSPACE_MANIFEST.md").write_text("manifest", encoding="utf-8")
    (tmp_path / "docs/project_checklist.md").write_text("checklist", encoding="utf-8")
    (tmp_path / "docs/roadmap_status.md").write_text("roadmap", encoding="utf-8")
    (tmp_path / "docs/context/context_index.md").write_text("index", encoding="utf-8")
    (tmp_path / "docs/context/context_budget_policy.md").write_text("budget", encoding="utf-8")
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
