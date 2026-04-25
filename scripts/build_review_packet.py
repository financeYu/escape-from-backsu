from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_OUTPUT_PATH = Path("docs/current_review_packet.md")
DEFAULT_MAX_CHARS = 12000


@dataclass(frozen=True)
class ReviewPacketConfig:
    project_root: Path
    output_path: Path
    step: str
    stage: str
    owner: str
    reason: str
    changed_files: tuple[str, ...]
    max_status_lines: int = 60
    max_chars: int = DEFAULT_MAX_CHARS


@dataclass(frozen=True)
class ReviewPacketResult:
    output_path: Path
    char_count: int
    changed_file_count: int


def build_review_packet(config: ReviewPacketConfig) -> str:
    root = config.project_root.resolve()
    roadmap = _read_optional(root / "docs/roadmap_status.md")
    checklist = _read_optional(root / "docs/project_checklist.md")
    changed_files = config.changed_files or tuple(_git_status_lines(root, max_lines=config.max_status_lines))

    protected_sections = [
        "# Current Review Packet",
        "",
        f"Generated at: {_now()}",
        "Workspace: `repository root`",
        "",
        "## Scope",
        "",
        f"- Step: {config.step}",
        f"- Stage: {config.stage}",
        f"- Owner: {config.owner}",
        f"- Reason: {config.reason}",
        "",
        "## Review Input Policy",
        "",
        "- Keep review output findings-first: concrete findings, missing evidence, and required follow-up only.",
        "- For normal reviews, report at most 5 findings ordered by blocking risk.",
        "- Do not restate passed checklist items unless a full gate record is explicitly required.",
        "- Use this packet plus the diff as the default review input.",
        "- Do not re-open completed Step implementation history unless the current diff touches it, consumes it downstream, or appears to violate a hard stop.",
        "- Consult `docs/roadmap_archive/` only for historical Step-end evidence.",
        "",
    ]
    variable_sections = [
        "## Current Roadmap Snapshot",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 현재 활성 단계", "## 전체 Step 판정", 12),
                ("## 현재 활성 단계", "## 현재 판정", 12),
            ),
        ),
        "",
        "## Step Verdicts",
        "",
        _compact_first_section(
            roadmap,
            (
                ("## 전체 Step 판정", "## 최근 완료 Step 요약", 28),
                ("## 현재 판정", "## Step 13 통합 완료 상태", 28),
            ),
        ),
        "",
        "## Active Guardrails",
        "",
        _compact_first_section(
            checklist,
            (
                ("## 7. Hard Stop Rules", None, 18),
            ),
        ),
        "",
        "## Changed Files",
        "",
        _format_list(changed_files),
        "",
        "## Cross-Step Conflict Checkpoint",
        "",
        "- Trigger:",
        f"  - important stage ended: `{config.stage}`",
        "- Roadmap/order:",
        "  - pending",
        "- Hard stops:",
        "  - pending",
        "- Score/composite boundary:",
        "  - pending",
        "- Valuation boundary:",
        "  - pending",
        "- Diagnostics boundary:",
        "  - pending",
        "- Handoff consistency:",
        "  - pending",
        "- Generated-output boundary:",
        "  - pending",
        "- Dirty worktree isolation:",
        "  - pending",
        "- Verdict: NEEDS_CLARIFICATION until reviewed",
        "- Required follow-up:",
        "  - complete this checkpoint before Step-end code review or downstream handoff consumption",
        "",
    ]
    return _truncate_text(
        "\n".join(variable_sections),
        max_chars=config.max_chars,
        protected_prefix="\n".join(protected_sections),
    )


def write_review_packet(config: ReviewPacketConfig) -> ReviewPacketResult:
    text = build_review_packet(config)
    output_path = _root_path(config.project_root.resolve(), config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    changed_files = config.changed_files or tuple(_git_status_lines(config.project_root.resolve(), max_lines=config.max_status_lines))
    return ReviewPacketResult(
        output_path=output_path,
        char_count=len(text),
        changed_file_count=len(changed_files),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a compact review packet for cross-step conflict checks.")
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output path, relative to project root unless absolute.")
    parser.add_argument("--step", required=True, help='Active roadmap Step, for example "Step 14".')
    parser.add_argument("--stage", required=True, help="Important in-Step stage that just ended.")
    parser.add_argument("--owner", default="root master agent", help="Owner of this review packet.")
    parser.add_argument("--reason", default="cross-step conflict checkpoint", help="Reason for packet generation.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file to include. May be repeated.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Maximum packet length in characters. Defaults to 12000.",
    )
    args = parser.parse_args(argv)

    config = ReviewPacketConfig(
        project_root=Path(args.project_root),
        output_path=Path(args.output),
        step=args.step,
        stage=args.stage,
        owner=args.owner,
        reason=args.reason,
        changed_files=tuple(args.changed_file),
        max_chars=args.max_chars,
    )
    result = write_review_packet(config)
    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "char_count": result.char_count,
                "changed_file_count": result.changed_file_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _compact_first_section(text: str, specs: tuple[tuple[str, str | None, int], ...]) -> str:
    for heading, next_heading, max_lines in specs:
        section = _compact_section(text, heading, next_heading=next_heading, max_lines=max_lines)
        if section != "- unavailable":
            return section
    return "- unavailable"


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
    lines = [line.rstrip() for line in text[start:end].splitlines()[1:] if line.strip()]
    limited = lines[:max_lines]
    if len(lines) > max_lines:
        limited.append(f"- omitted {len(lines) - max_lines} additional lines for compact review")
    return "\n".join(limited) if limited else "- unavailable"


def _format_list(lines: tuple[str, ...]) -> str:
    if not lines:
        return "- clean or unavailable"
    return "\n".join(f"- `{line}`" for line in lines)


def _git_status_lines(project_root: Path, *, max_lines: int) -> list[str]:
    status = _run_git(project_root, "status", "--short")
    if not status:
        return []
    lines = status.splitlines()
    if len(lines) > max_lines:
        return lines[:max_lines] + [f"... omitted {len(lines) - max_lines} additional status lines"]
    return lines


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


def _root_path(project_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return project_root / path


def _truncate_text(text: str, *, max_chars: int, protected_prefix: str = "") -> str:
    protected_prefix = protected_prefix.rstrip()
    text = text.lstrip() if protected_prefix else text
    combined = "\n\n".join(part for part in (protected_prefix, text) if part)
    if max_chars <= 0 or len(combined) <= max_chars:
        return combined
    marker = "\n\n[Review packet truncated by `max_chars`; use the diff for exact changed lines.]\n"
    if max_chars <= len(marker):
        return marker[-max_chars:]
    available = max_chars - len(marker)
    if not protected_prefix:
        return text[:available].rstrip() + marker
    if len(protected_prefix) >= available:
        return protected_prefix[:available].rstrip() + marker
    separator = "\n\n"
    variable_budget = available - len(protected_prefix) - len(separator)
    if variable_budget <= 0:
        return protected_prefix[:available].rstrip() + marker
    return protected_prefix + separator + text[:variable_budget].rstrip() + marker


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
