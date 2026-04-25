from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_review_packet.py"
SPEC = importlib.util.spec_from_file_location("build_review_packet", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_build_review_packet_includes_cross_step_checkpoint() -> None:
    root = _new_tmp_dir("build")
    _write_minimal_project(root)
    config = _config(root, output_path=root / "packet.md")

    text = module.build_review_packet(config)

    assert "Current Review Packet" in text
    assert "Step 14" in text
    assert "contract lock" in text
    assert "Cross-Step Conflict Checkpoint" in text
    assert "Roadmap/order" in text
    assert "Step 17 전에는 backtest 금지" in text


def test_write_review_packet_writes_output() -> None:
    root = _new_tmp_dir("write")
    _write_minimal_project(root)
    output_path = root / "docs" / "current_review_packet.md"
    config = _config(root, output_path=output_path, changed_files=("docs/roadmap_status.md",))

    result = module.write_review_packet(config)

    assert result.output_path == output_path
    assert result.changed_file_count == 1
    assert output_path.exists()
    assert "`docs/roadmap_status.md`" in output_path.read_text(encoding="utf-8")


def test_build_review_packet_respects_max_chars() -> None:
    root = _new_tmp_dir("truncate")
    _write_minimal_project(root)
    config = _config(root, output_path=root / "packet.md", max_chars=1200)

    text = module.build_review_packet(config)

    assert len(text) <= 1200
    assert "Keep review output findings-first" in text
    assert "Review packet truncated" in text


def _config(
    root: Path,
    *,
    output_path: Path,
    changed_files: tuple[str, ...] = (),
    max_chars: int = module.DEFAULT_MAX_CHARS,
) -> module.ReviewPacketConfig:
    return module.ReviewPacketConfig(
        project_root=root,
        output_path=output_path,
        step="Step 14",
        stage="contract lock",
        owner="test owner",
        reason="unit test",
        changed_files=changed_files,
        max_chars=max_chars,
    )


def _write_minimal_project(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs/project_checklist.md").write_text(
        "# Checklist\n\n## 7. Hard Stop Rules\n\n- Step 17 전에는 backtest 금지.\n",
        encoding="utf-8",
    )
    (root / "docs/roadmap_status.md").write_text(
        "# 로드맵 상태\n\n"
        "## 현재 활성 단계\n\nStep 14 = Adoption Synthesis, NEXT / not started\n\n"
        "## 전체 Step 판정\n\n| Step | Status |\n| --- | --- |\n| Step 14 | NEXT |\n\n"
        "## 최근 완료 Step 요약\n\n- Step 13 complete.\n",
        encoding="utf-8",
    )


def _new_tmp_dir(label: str) -> Path:
    root = SCRIPT_PATH.parents[1] / "tests" / "_tmp" / "review_packet_unit"
    path = root / f"{label}_{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path
