from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_CONFIG_PATH = Path("Quant_mvp/config/context_snapshot.toml")


@dataclass(frozen=True)
class ContextConfig:
    project_root: Path
    output_path: Path
    obsolete_local_paths: tuple[Path, ...]
    max_chars: int
    project_label: str
    context_key: str
    local_latest_only: bool


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    removed_local_paths: tuple[Path, ...]
    char_count: int


def load_config(project_root: Path, config_path: Path) -> ContextConfig:
    resolved_root = project_root.resolve()
    raw = tomllib.loads((resolved_root / config_path).read_text(encoding="utf-8"))
    context = raw["context"]
    return ContextConfig(
        project_root=resolved_root,
        output_path=_root_path(resolved_root, context["output_path"]),
        obsolete_local_paths=tuple(_root_path(resolved_root, path) for path in context.get("obsolete_local_paths", [])),
        max_chars=int(context.get("max_chars", 14000)),
        project_label=str(context["project_label"]),
        context_key=str(context["context_key"]),
        local_latest_only=bool(context.get("local_latest_only", True)),
    )


def refresh_context(config: ContextConfig) -> ExportResult:
    text = build_context(config)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(text, encoding="utf-8", newline="\n")

    removed: list[Path] = []
    if config.local_latest_only:
        for obsolete_path in config.obsolete_local_paths:
            if obsolete_path.exists():
                obsolete_path.unlink()
                removed.append(obsolete_path)

    return ExportResult(output_path=config.output_path, removed_local_paths=tuple(removed), char_count=len(text))


def build_context(config: ContextConfig) -> str:
    roadmap = _read_optional(config.project_root / "docs/roadmap_status.md")
    checklist = _read_optional(config.project_root / "docs/project_checklist.md")
    quant_agents = _read_optional(config.project_root / "Quant_mvp/AGENTS.md")
    score_catalog = _read_optional(config.project_root / "Quant_mvp/docs/score_catalog.md")
    family_map = _read_optional(config.project_root / "Quant_mvp/docs/family_map.md")

    sections = [
        "# Quant Project Current Context",
        "",
        f"Generated at: {_now()}",
        "Workspace: `repository root`",
        f"Project target: `{config.project_label}`",
        f"Context key: `{config.context_key}`",
        "",
        "This file is the only local context snapshot kept by the master workspace.",
        "Older local snapshots managed by this script are removed during refresh.",
        "No paid API upload is performed by this local-only workflow.",
        "",
        "## Authority Order",
        "",
        "1. User's latest explicit instruction",
        "2. Root `AGENTS.md`",
        "3. `docs/project_checklist.md`",
        "4. `docs/roadmap_status.md`",
        "5. Related source, tests, docs, and config",
        "",
        "## Current Roadmap Position",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 현재 활성 단계", "## 전체 Step 판정", 12),
                ("## 현재 활성 단계", "## 현재 판정", 12),
            ),
        ),
        "",
        "## Roadmap Verdicts",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 전체 Step 판정", "## 최근 완료 Step 요약", 28),
                ("## 현재 판정", "## Step 13 통합 완료 상태", 24),
            ),
        ),
        "",
        "## Most Recent Completed Step",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 최근 완료 Step 요약", "## 상세 이력 위치", 32),
                ("## Step 13 통합 완료 상태", "## Step 11 통합 상태", 40),
            ),
        ),
        "",
        "## Cross-Step Conflict Checkpoint",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## Step 간 충돌 체크포인트", "## 밸류에이션 상태", 24),
            ),
        ),
        "",
        "## Active Guardrails",
        "",
        _compact_section(checklist, "## 7. Hard Stop Rules", next_heading=None, max_lines=18),
        "",
        "## Quant Agent Scope",
        "",
        _compact_section(quant_agents, "## Purpose", next_heading="## Multi-agent operating model", max_lines=28),
        "",
        "## Quant Adoption Synthesis Policy",
        "",
        _compact_section(quant_agents, "## Adoption synthesis policy", next_heading="### Suggested interpretation", max_lines=18),
        "",
        "## Score Catalog Snapshot",
        "",
        _compact_lines(score_catalog, include_markers=("| `",), max_lines=24),
        "",
        "## Family Map Snapshot",
        "",
        _compact_lines(family_map, include_markers=("| `", "| Volatility", "| Trend", "| Mean"), max_lines=20),
        "",
        "## Git Snapshot",
        "",
        _git_snapshot(config.project_root),
        "",
        "## Step-End Context Policy",
        "",
        "- Refresh this file after Step-end validation, review, required fixes, rerun, and commit.",
        "- Keep latest-only local retention: remove obsolete local context files listed in config.",
        "- Do not include `.env`, API keys, local runtime caches, chart images, generated data caches, or secrets.",
        "",
        "## Next Allowed Work",
        "",
        _infer_next_allowed_work(roadmap),
        "",
    ]
    text = "\n".join(part for part in sections if part is not None)
    return _truncate_context(text, max_chars=config.max_chars)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the latest local Quant project context snapshot.")
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Root-relative config path.")
    args = parser.parse_args(argv)

    config = load_config(Path(args.project_root), Path(args.config))
    result = refresh_context(config)
    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "removed_local_paths": [str(path) for path in result.removed_local_paths],
                "char_count": result.char_count,
                "mode": "local_only_no_paid_upload",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _root_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _compact_section(text: str, heading: str, *, next_heading: str | None, max_lines: int) -> str:
    if not text:
        return "- unavailable"
    start = text.find(heading)
    if start < 0:
        return "- unavailable"
    end = len(text)
    if next_heading:
        next_start = text.find(next_heading, start + len(heading))
        if next_start >= 0:
            end = next_start
    section_lines = text[start:end].splitlines()[1:]
    return _format_limited_lines(section_lines, max_lines=max_lines)


def _compact_first_section(text: str, specs: tuple[tuple[str, str | None, int], ...]) -> str:
    for heading, next_heading, max_lines in specs:
        section = _compact_section(text, heading, next_heading=next_heading, max_lines=max_lines)
        if section != "- unavailable":
            return section
    return "- unavailable"


def _compact_lines(text: str, *, include_markers: tuple[str, ...], max_lines: int) -> str:
    if not text:
        return "- unavailable"
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and any(marker in stripped for marker in include_markers):
            lines.append(stripped)
    return _format_limited_lines(lines, max_lines=max_lines)


def _format_limited_lines(lines: list[str], *, max_lines: int) -> str:
    cleaned = [line.rstrip() for line in lines if line.strip()]
    limited = cleaned[:max_lines]
    if len(cleaned) > max_lines:
        limited.append(f"- omitted {len(cleaned) - max_lines} additional lines for compact context")
    return "\n".join(limited) if limited else "- unavailable"


def _git_snapshot(project_root: Path) -> str:
    branch = _run_git(project_root, "branch", "--show-current") or "unknown"
    commit = _run_git(project_root, "rev-parse", "--short", "HEAD") or "unknown"
    status = _run_git(project_root, "status", "--short") or "clean"
    status_lines = status.splitlines()
    if len(status_lines) > 40:
        status = "\n".join(status_lines[:40] + [f"... omitted {len(status_lines) - 40} additional status lines"])
    return f"- branch: `{branch}`\n- commit: `{commit}`\n- status:\n```text\n{status}\n```"


def _run_git(project_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _infer_next_allowed_work(roadmap: str) -> str:
    if "Step 14 = Adoption Synthesis" in roadmap:
        return (
            "- Step 14 Adoption Synthesis is the next active roadmap step.\n"
            "- Step 15 ranking, Step 17 backtest, and Step 18 valuation/fundamental scoring remain gated."
        )
    return "- Follow `docs/roadmap_status.md` and `docs/project_checklist.md` before starting the next Step."


def _truncate_context(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker = "\n\n[Context truncated by `max_chars`; consult repository docs for full detail.]\n"
    if max_chars <= len(marker):
        return marker[-max_chars:]
    return text[: max_chars - len(marker)].rstrip() + marker


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
