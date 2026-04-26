from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "context" / "check_context_staleness.py"
SPEC = importlib.util.spec_from_file_location("check_context_staleness", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_staleness_checker_detects_simple_status_mismatch(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/roadmap_status.md").write_text(
        "| Step | Status |\n| --- | --- |\n| Step 18 | COMPLETE |\n| Step 19 | WAITING / not started |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/project_checklist.md").write_text(
        "- Step 18 = DEFERRED / waiting for valuation expansion\n",
        encoding="utf-8",
    )

    warnings = module.check_staleness(tmp_path)

    assert any(warning.code == "step_status_mismatch" for warning in warnings)
    assert any("Step 18" in warning.message for warning in warnings)


def test_staleness_checker_detects_generated_packet_contradiction(tmp_path: Path) -> None:
    (tmp_path / "docs/context/generated").mkdir(parents=True)
    (tmp_path / "docs/roadmap_status.md").write_text(
        "| Step | Status |\n| --- | --- |\n| Step 19 | WAITING / not started |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/project_checklist.md").write_text("- Step 19 = WAITING / not started\n", encoding="utf-8")
    (tmp_path / "docs/context/generated/packet.md").write_text("Step 19 = COMPLETE\n", encoding="utf-8")

    warnings = module.check_staleness(tmp_path)

    assert any(warning.code == "step_status_mismatch" for warning in warnings)
    assert any(warning.code == "packet_status_contradiction" for warning in warnings)


def test_staleness_checker_returns_no_warning_for_matching_status(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/roadmap_status.md").write_text(
        "| Step | Status |\n| --- | --- |\n| Step 18 | COMPLETE |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/project_checklist.md").write_text("- Step 18 = COMPLETE\n", encoding="utf-8")

    warnings = module.check_staleness(tmp_path)

    assert warnings == ()
