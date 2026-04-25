from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refresh_quant_project_context.py"
SPEC = importlib.util.spec_from_file_location("refresh_quant_project_context", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_refresh_context_keeps_only_latest_local_file() -> None:
    root = _new_tmp_dir("refresh")
    _write_minimal_project(root)
    current = root / "quant_project_reference_for_chatgpt_project_current.md"
    previous = root / "quant_project_reference_for_chatgpt_project_previous.md"
    previous.write_text("old context", encoding="utf-8")
    config = _config(root, current=current, previous=previous)

    result = module.refresh_context(config)

    assert result.output_path == current
    assert current.exists()
    assert not previous.exists()
    assert previous in result.removed_local_paths
    text = current.read_text(encoding="utf-8")
    assert "Quant Project Current Context" in text
    assert "Workspace: `repository root`" in text
    assert str(root) not in text
    assert "No paid API upload is performed" in text
    assert "Cross-Step Conflict Checkpoint" in text


def test_build_context_respects_max_chars() -> None:
    root = _new_tmp_dir("max_chars")
    _write_minimal_project(root, extra_roadmap_lines=200)
    current = root / "current.md"
    previous = root / "previous.md"
    config = _config(root, current=current, previous=previous, max_chars=900)

    text = module.build_context(config)

    assert len(text) <= 900
    assert "Context truncated" in text


def _config(
    root: Path,
    *,
    current: Path,
    previous: Path,
    max_chars: int = 14000,
) -> module.ContextConfig:
    return module.ContextConfig(
        project_root=root,
        output_path=current,
        obsolete_local_paths=(previous,),
        max_chars=max_chars,
        project_label="current_quant_project",
        context_key="quant_project_current_context",
        local_latest_only=True,
    )


def _write_minimal_project(root: Path, *, extra_roadmap_lines: int = 0) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "Quant_mvp/docs").mkdir(parents=True)
    (root / "docs/project_checklist.md").write_text(
        "# Checklist\n\n## 7. Hard Stop Rules\n\n- Step 17 전에는 backtest 금지.\n",
        encoding="utf-8",
    )
    extra = "\n".join(f"- extra roadmap line {index}" for index in range(extra_roadmap_lines))
    (root / "docs/roadmap_status.md").write_text(
        "# Roadmap\n\n"
        "## 현재 활성 단계\n\nStep 14 = Adoption Synthesis, NEXT / not started\n\n"
        "## 전체 Step 판정\n\n| Step | Status |\n| --- | --- |\n| Step 13 | COMPLETE |\n| Step 14 | NEXT / not started |\n\n"
        "## 최근 완료 Step 요약\n\n완료:\n\n- review contract implemented\n"
        f"{extra}\n\n"
        "## 상세 이력 위치\n\n- archived\n\n"
        "## Step 간 충돌 체크포인트\n\nRun checkpoint at important stage boundaries.\n\n"
        "## 밸류에이션 상태\n\n- deferred\n",
        encoding="utf-8",
    )
    (root / "Quant_mvp/AGENTS.md").write_text(
        "# AGENTS\n\n## Purpose\n\nQuant purpose.\n\n## Multi-agent operating model\n\nModel.\n\n"
        "## Adoption synthesis policy\n\nPolicy.\n\n### Suggested interpretation\n\nDetails.\n",
        encoding="utf-8",
    )
    (root / "Quant_mvp/docs/score_catalog.md").write_text(
        "| score | status |\n| --- | --- |\n| `score_a` | test |\n",
        encoding="utf-8",
    )
    (root / "Quant_mvp/docs/family_map.md").write_text(
        "| family | scores |\n| --- | --- |\n| `mean_reversion` | `score_a` |\n",
        encoding="utf-8",
    )


def _new_tmp_dir(label: str) -> Path:
    root = SCRIPT_PATH.parents[1] / "tests" / "_tmp" / "context_snapshot_unit"
    path = root / f"{label}_{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path
