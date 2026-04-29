from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
    output_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    output_paths: tuple[Path, ...]
    removed_local_paths: tuple[Path, ...]
    char_count: int


def load_config(project_root: Path, config_path: Path) -> ContextConfig:
    resolved_root = project_root.resolve()
    raw = tomllib.loads((resolved_root / config_path).read_text(encoding="utf-8"))
    context = raw["context"]
    output_path = _root_path(resolved_root, context["output_path"])
    output_paths = tuple(
        _root_path(resolved_root, path)
        for path in context.get("output_paths", [context["output_path"]])
    )
    if output_path not in output_paths:
        output_paths = (output_path, *output_paths)
    return ContextConfig(
        project_root=resolved_root,
        output_path=output_path,
        output_paths=tuple(dict.fromkeys(output_paths)),
        obsolete_local_paths=tuple(_root_path(resolved_root, path) for path in context.get("obsolete_local_paths", [])),
        max_chars=int(context.get("max_chars", 14000)),
        project_label=str(context["project_label"]),
        context_key=str(context["context_key"]),
        local_latest_only=bool(context.get("local_latest_only", True)),
    )


def refresh_context(config: ContextConfig) -> ExportResult:
    text = build_context(config)
    output_paths = config.output_paths or (config.output_path,)
    for output_path in output_paths:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8", newline="\n")

    removed: list[Path] = []
    if config.local_latest_only:
        for obsolete_path in config.obsolete_local_paths:
            if obsolete_path.exists():
                obsolete_path.unlink()
                removed.append(obsolete_path)

    return ExportResult(
        output_path=config.output_path,
        output_paths=output_paths,
        removed_local_paths=tuple(removed),
        char_count=len(text),
    )


def build_context(config: ContextConfig) -> str:
    hard_stops = _read_optional(config.project_root / "docs/root_hard_stops.md")
    roadmap = _read_optional(config.project_root / "docs/roadmap_status.md")
    sections = [
        *_context_header_sections(config),
        *_roadmap_context_sections(roadmap),
        *_guardrail_context_sections(hard_stops),
        *_route_reference_sections(),
    ]
    text = "\n".join(part for part in sections if part is not None)
    return _truncate_context(text, max_chars=config.max_chars)


def _context_header_sections(config: ContextConfig) -> list[str]:
    return [
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
        "## User-Requested Context Policy",
        "",
        "- Refresh only when the user explicitly requests this ChatGPT reference update.",
        "- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.",
        "",
        "## Authority Order",
        "",
        "1. User's latest explicit instruction",
        "2. Root `AGENTS.md`",
        "3. `docs/root_hard_stops.md`",
        "4. `docs/roadmap_status.md`",
        "5. `docs/project_checklist.md` for targeted root authority lookup",
        "6. Related source, tests, docs, and config",
        "",
    ]


def _roadmap_context_sections(roadmap: str) -> list[str]:
    return [
        "## Current Roadmap Position",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 현재 로드맵 상태", "## 컨텍스트 운영 상태", 12),
                ("## 현재 활성 단계", "## 전체 Step 판정", 12),
                ("## 현재 활성 단계", "## 현재 판정", 12),
            ),
        ),
        "",
        "## Current Baseline",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 현재 Baseline 핵심", "## Research Ingestion 상태", 6),
                ("## 최근 완료 Step 요약", "## 상세 이력 위치", 8),
            ),
        ),
        "",
    ]


def _guardrail_context_sections(hard_stops: str) -> list[str]:
    return [
        "## Cross-Step Conflict Checkpoint",
        "",
        "- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.",
        "- Use `scripts/build_review_packet.py` for compact review input.",
        "",
        "## Active Guardrails",
        "",
        _compact_section(
            hard_stops,
            "## Forbidden Scope Without Explicit Approval",
            next_heading="## Context Boundary",
            max_lines=14,
        ),
        "",
    ]


def _route_reference_sections() -> list[str]:
    return [
        "## Route-Only References",
        "",
        "- Root compact hard stops: `docs/root_hard_stops.md`.",
        "- Current roadmap status: `docs/roadmap_status.md`.",
        "- MVP baseline: `docs/context/MVP_V0_1_BASELINE.md`.",
        "- MVP contracts: `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`.",
        "- Extension registry: `docs/context/EXTENSION_REGISTRY.toml`.",
        "- Candidate ML gate skill: `.agents/skills/quant-candidate-ml-gate/SKILL.md`.",
        "- Candidate ML gate validator: `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`.",
        "- Candidate ML score contract: `Quant_mvp/docs/v0_2_candidate_ml_score_contract.md`.",
        "- Candidate ML implementation gate: `Quant_mvp/docs/v0_2_candidate_ml_implementation_gate_1.md`.",
        "- Candidate ML config: `Quant_mvp/config/v0_2_candidate_ml_score.toml`.",
        "- Quant agent scope: `Quant_mvp/AGENTS.md`.",
        "- Score catalog: `Quant_mvp/docs/score_catalog.md` (on-demand only; not embedded).",
        "- Archive lookup: `docs/context/ARCHIVE_INDEX.md`.",
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the latest local Quant project context snapshot.")
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Root-relative config path.")
    parser.add_argument(
        "--user-requested",
        action="store_true",
        help="Required confirmation that the user explicitly requested this ChatGPT reference refresh.",
    )
    args = parser.parse_args(argv)

    if not args.user_requested:
        print(
            "Refusing to refresh ChatGPT reference without --user-requested. "
            "Run only after the user explicitly asks for this reference update.",
            file=sys.stderr,
        )
        return 2

    config = load_config(Path(args.project_root), Path(args.config))
    result = refresh_context(config)
    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "output_paths": [str(path) for path in result.output_paths],
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


def _format_limited_lines(lines: list[str], *, max_lines: int) -> str:
    cleaned = [line.rstrip() for line in lines if line.strip()]
    limited = cleaned[:max_lines]
    if len(cleaned) > max_lines:
        limited.append(f"- omitted {len(cleaned) - max_lines} additional lines for compact context")
    return "\n".join(limited) if limited else "- unavailable"


def _truncate_context(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker = "\n\n[Context truncated by `max_chars`; consult repository docs for full detail.]\n"
    if max_chars <= len(marker):
        return marker[-max_chars:]
    cutoff = text[: max_chars - len(marker)].rstrip()
    last_newline = cutoff.rfind("\n")
    if last_newline > max_chars // 2:
        cutoff = cutoff[:last_newline].rstrip()
    return cutoff + marker


def _now() -> str:
    try:
        tz = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        tz = timezone(timedelta(hours=9))
    return datetime.now(tz).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
