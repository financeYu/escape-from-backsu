from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "context" / "refresh_gpt_references.py"
SPEC = importlib.util.spec_from_file_location("refresh_gpt_references", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_refresh_gpt_references_updates_both_gpt_files(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)

    result = module.refresh_gpt_references(
        module.RefreshGptReferencesConfig(
            project_root=tmp_path,
            request="Prepare a focused GPT reference for the candidate ML gate.",
        )
    )

    project_reference = tmp_path / "docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md"
    gpt_brief = tmp_path / "docs/context/gpt/gpt_context_quant.md"
    assert result.project_reference_path == project_reference
    assert result.gpt_brief_path == gpt_brief
    assert project_reference.exists()
    assert gpt_brief.exists()

    project_text = project_reference.read_text(encoding="utf-8")
    brief_text = gpt_brief.read_text(encoding="utf-8")
    assert "Quant Project Current Context" in project_text
    assert "Refresh only when the user explicitly requests this ChatGPT reference update." in project_text
    assert "GPT Context Quant" in brief_text
    assert "Prepare a focused GPT reference for the candidate ML gate." in brief_text
    assert len(brief_text.splitlines()) <= 80


def test_refresh_gpt_references_cli_requires_explicit_user_request(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)

    exit_code = module.main(
        [
            "--project-root",
            str(tmp_path),
            "--request",
            "Prepare a focused GPT reference.",
        ]
    )

    assert exit_code == 2
    assert not (tmp_path / "docs/context/gpt/gpt_context_quant.md").exists()


def test_refresh_gpt_references_cli_requires_request_text(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)

    exit_code = module.main(["--project-root", str(tmp_path), "--user-requested"])

    assert exit_code == 2
    assert not (tmp_path / "docs/context/gpt/gpt_context_quant.md").exists()


def _write_minimal_project(root: Path) -> None:
    (root / "Quant_mvp/config").mkdir(parents=True, exist_ok=True)
    (root / "docs/context/gpt").mkdir(parents=True, exist_ok=True)
    (root / "Quant_mvp/config/context_snapshot.toml").write_text(
        "[context]\n"
        "project_label = \"current_quant_project\"\n"
        "context_key = \"quant_project_current_context\"\n"
        "output_path = \"docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md\"\n"
        "obsolete_local_paths = []\n"
        "max_chars = 5000\n"
        "local_latest_only = true\n",
        encoding="utf-8",
    )
    (root / "docs/root_hard_stops.md").write_text(
        "# Root Hard Stops\n\n"
        "## Forbidden Scope Without Explicit Approval\n\n"
        "- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.\n"
        "- Trading recommendations, buy/sell/hold, proven-alpha, or expected-return wording.\n\n"
        "## Context Boundary\n\n"
        "- compact context only.\n",
        encoding="utf-8",
    )
    (root / "docs/roadmap_status.md").write_text(
        "# 로드맵 상태\n\n"
        "## 현재 로드맵 상태\n\n"
        "Post-MVP `v0.2 predictive probability score route` is active.\n\n"
        "## 컨텍스트 운영 상태\n\n"
        "- latest-only.\n\n"
        "## 현재 Baseline 핵심\n\n"
        "- MVP universe는 KOSPI200 only다.\n"
        "- `technical_composite_score`는 technical-only이다.\n\n"
        "## Research Ingestion 상태\n\n"
        "- diagnostic only.\n",
        encoding="utf-8",
    )
    (root / "docs/context/MVP_V0_1_BASELINE.md").write_text("baseline", encoding="utf-8")
