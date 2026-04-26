from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_ROUTING_PATH = Path("docs/context/context_routing.md")
DEFAULT_OUTPUT_DIR = Path("docs/context/generated")
DEFAULT_GPT_BRIEF_OUTPUT = Path("docs/context/gpt/gpt_context_quant.md")
GPT_BRIEF_ROUTE_REFS = (
    "docs/context/MVP_V0_1_BASELINE.md",
)
ALWAYS_READ_REFS = (
    "docs/context/current_context.md",
    "docs/context/MVP_V0_1_BASELINE.md",
    "docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml",
)
AUTHORITY_WARNING = (
    "Generated context packets are routing aids, not authority documents. They do not override "
    "`AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`, "
    "the active `WORKSPACE_MANIFEST.md`, or the user's latest instruction."
)


@dataclass(frozen=True)
class ContextRoute:
    task: str
    required_context: str
    optional_context: str
    forbidden_or_do_not_read_unless_needed: str
    allowed_scope: str
    forbidden_scope: str
    escalation_conditions: str
    validation_expectations: str


@dataclass(frozen=True)
class PacketConfig:
    project_root: Path
    task: str
    step: str
    stage: str
    output_path: Path
    routing_path: Path = DEFAULT_ROUTING_PATH


@dataclass(frozen=True)
class GptBriefConfig:
    project_root: Path
    request: str
    output_path: Path


@dataclass(frozen=True)
class PacketResult:
    output_path: Path
    missing_references: tuple[str, ...]
    char_count: int


def build_context_packet(config: PacketConfig) -> str:
    root = config.project_root.resolve()
    routes = load_routes(root, config.routing_path)
    task = config.task.strip()
    if task not in routes:
        known = ", ".join(sorted(routes)) or "none"
        raise ValueError(f"Unknown context task `{task}`. Known tasks: {known}")

    route = routes[task]
    required_refs = tuple(dict.fromkeys((*ALWAYS_READ_REFS, *_extract_path_refs(route.required_context))))
    optional_refs = _extract_path_refs(route.optional_context)
    missing_required = _missing_refs(root, required_refs)
    missing_optional = _missing_refs(root, optional_refs)
    missing_refs = tuple(dict.fromkeys((*missing_required, *missing_optional)))

    sections = [
        "# Context Packet",
        "",
        f"Generated at: {_now()}",
        "",
        "## Authority Warning",
        "",
        AUTHORITY_WARNING,
        "",
        "## Task",
        "",
        f"- task: `{route.task}`",
        f"- step: {config.step}",
        f"- stage: {config.stage}",
        "",
        "## Required Context Files",
        "",
        _format_ref_list(root, required_refs),
        "",
        "## Required Context Notes",
        "",
        _format_notes(route.required_context, required_refs),
        "",
        "## Optional Context Files",
        "",
        _format_ref_list(root, optional_refs),
        "",
        "## Optional Context Notes",
        "",
        _format_notes(route.optional_context, optional_refs),
        "",
        "## Do Not Read Unless Needed",
        "",
        _format_single_bullet(route.forbidden_or_do_not_read_unless_needed),
        "",
        "## Allowed Scope",
        "",
        _format_single_bullet(route.allowed_scope),
        "",
        "## Forbidden Scope",
        "",
        _format_single_bullet(route.forbidden_scope),
        "",
        "## Escalation Conditions",
        "",
        _format_single_bullet(route.escalation_conditions),
        "",
        "## Validation Expectations",
        "",
        _format_single_bullet(route.validation_expectations),
        "",
        "## Missing Referenced Files",
        "",
        _format_missing_refs(missing_refs),
        "",
        "## Packet Boundary",
        "",
        "- This packet lists context paths and routing rules only.",
        "- It does not embed source files, generated data, caches, secrets, images, or raw reports.",
    ]
    return "\n".join(sections).rstrip() + "\n"


def write_context_packet(config: PacketConfig) -> PacketResult:
    text = build_context_packet(config)
    output_path = _root_path(config.project_root.resolve(), config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    missing = tuple(_extract_missing_refs_from_packet(text))
    return PacketResult(output_path=output_path, missing_references=missing, char_count=len(text))


def build_gpt_brief(config: GptBriefConfig) -> str:
    root = config.project_root.resolve()
    request = config.request.strip() or "Replace this placeholder with the active user request."
    missing_refs = _missing_refs(root, GPT_BRIEF_ROUTE_REFS)
    sections = [
        "# GPT Context Quant",
        "",
        "Status: routing aid, not an authority document.",
        "",
        "## Confirmed Context",
        "",
        "- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.",
        "- MVP v0.1 is KOSPI200-only and technical-only.",
        "- Valuation/fundamental scoring, KOSDAQ150, futures/options, Nasdaq, and trading recommendation work remain outside the baseline unless a later routed task opens them.",
        "",
        "## Current Request",
        "",
        f"- Task: {request}",
        "- Decision needed: focus on the current request, not old roadmap narration.",
        "",
        "## Do Not Repeat",
        "",
        "Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.",
        "",
        "## Boundaries",
        "",
        "- No quant logic, score formula, ranking behavior, report behavior, backtest behavior, valuation/fundamental activation, data ingestion, or trading language changes unless explicitly requested and allowed.",
        "- Do not implement KOSDAQ150, futures/options, or Nasdaq from this brief.",
        "- Completed Step 1-20 history is archive-only. Full validation logs are archive-only. Full score catalog is not default context.",
        "- Internal generation rules, budget policy, and routing index are not GPT prompt inputs.",
        "",
        "## Route-Only References",
        "",
        _format_ref_list(root, GPT_BRIEF_ROUTE_REFS),
        "- add task-specific file paths only when needed",
        "",
        "## Missing Referenced Files",
        "",
        _format_missing_refs(missing_refs),
    ]
    text = "\n".join(sections).rstrip() + "\n"
    line_count = len(text.splitlines())
    if line_count > 80:
        raise ValueError(f"Generated GPT brief is {line_count} lines; limit is 80.")
    return text


def write_gpt_brief(config: GptBriefConfig) -> PacketResult:
    text = build_gpt_brief(config)
    output_path = _root_path(config.project_root.resolve(), config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    missing = tuple(_extract_missing_refs_from_packet(text))
    return PacketResult(output_path=output_path, missing_references=missing, char_count=len(text))


def load_routes(project_root: Path, routing_path: Path = DEFAULT_ROUTING_PATH) -> dict[str, ContextRoute]:
    path = _root_path(project_root.resolve(), routing_path)
    text = path.read_text(encoding="utf-8")
    routes: dict[str, ContextRoute] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `"):
            continue
        cells = _split_markdown_row(stripped)
        if len(cells) < 8:
            continue
        task = _strip_code(cells[0])
        routes[task] = ContextRoute(
            task=task,
            required_context=cells[1],
            optional_context=cells[2],
            forbidden_or_do_not_read_unless_needed=cells[3],
            allowed_scope=cells[4],
            forbidden_scope=cells[5],
            escalation_conditions=cells[6],
            validation_expectations=cells[7],
        )
    return routes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a compact context routing packet.")
    parser.add_argument(
        "--mode",
        choices=("packet", "gpt-brief"),
        default="packet",
        help="Build mode. Use --mode gpt-brief --user-requested only when a GPT submission brief is explicitly requested.",
    )
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--routing", default=str(DEFAULT_ROUTING_PATH), help="Root-relative routing matrix path.")
    parser.add_argument("--task", help="Context task type, for example step19_pipeline.")
    parser.add_argument("--step", help="Roadmap Step label.")
    parser.add_argument("--stage", help="Current stage label.")
    parser.add_argument("--request", help="Current request text for --mode gpt-brief.")
    parser.add_argument(
        "--user-requested",
        action="store_true",
        help="Required confirmation that the user explicitly requested a GPT brief refresh.",
    )
    parser.add_argument(
        "--output",
        help="Output path. Defaults to docs/context/generated/<task>_packet.md or docs/context/gpt/gpt_context_quant.md.",
    )
    args = parser.parse_args(argv)

    if args.mode != "gpt-brief" and args.request and not any((args.task, args.step, args.stage)):
        parser.error(
            "--request is for GPT submission briefs only when --mode gpt-brief is explicit. "
            "Use: --mode gpt-brief --user-requested --request \"...\""
        )

    try:
        if args.mode == "gpt-brief":
            if not args.user_requested:
                parser.error(
                    "Refusing to refresh GPT brief without --user-requested. "
                    "Run only after the user explicitly asks for this GPT context update."
                )
            output = Path(args.output) if args.output else DEFAULT_GPT_BRIEF_OUTPUT
            result = write_gpt_brief(
                GptBriefConfig(
                    project_root=Path(args.project_root),
                    request=args.request or "Replace this placeholder with the active user request.",
                    output_path=output,
                )
            )
        else:
            if not args.task or not args.step or not args.stage:
                parser.error("--task, --step, and --stage are required unless --mode gpt-brief is used.")
            output = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{args.task}_packet.md"
            result = write_context_packet(
                PacketConfig(
                    project_root=Path(args.project_root),
                    task=args.task,
                    step=args.step,
                    stage=args.stage,
                    output_path=output,
                    routing_path=Path(args.routing),
                )
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "missing_references": list(result.missing_references),
                "char_count": result.char_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _split_markdown_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def _strip_code(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def _extract_path_refs(value: str) -> tuple[str, ...]:
    refs: list[str] = []
    for raw in re.findall(r"`([^`]+)`", value):
        normalized = raw.replace("\\", "/").strip()
        if "/" not in normalized:
            continue
        if normalized.endswith((".md", ".py", ".toml", ".json", ".jsonl", ".csv")) or normalized.endswith("AGENTS.md"):
            refs.append(normalized)
    return tuple(dict.fromkeys(refs))


def _missing_refs(project_root: Path, refs: tuple[str, ...]) -> tuple[str, ...]:
    missing: list[str] = []
    for ref in refs:
        if "*" in ref:
            if not list(project_root.glob(ref)):
                missing.append(ref)
        elif not (project_root / ref).exists():
            missing.append(ref)
    return tuple(missing)


def _format_ref_list(project_root: Path, refs: tuple[str, ...]) -> str:
    if not refs:
        return "- none declared"
    lines = []
    for ref in refs:
        status = "MISSING" if ref in _missing_refs(project_root, (ref,)) else "FOUND"
        lines.append(f"- `{ref}` - {status}")
    return "\n".join(lines)


def _format_notes(value: str, refs: tuple[str, ...]) -> str:
    note = value
    for ref in refs:
        note = note.replace(f"`{ref}`", "").replace(ref, "")
    note = re.sub(r"\s*,\s*,", ",", note).strip(" ,")
    return _format_single_bullet(note) if note else "- none"


def _format_single_bullet(value: str) -> str:
    value = value.strip()
    return f"- {value}" if value else "- none"


def _format_missing_refs(missing_refs: tuple[str, ...]) -> str:
    if not missing_refs:
        return "- none"
    return "\n".join(f"- `{ref}`" for ref in missing_refs)


def _extract_missing_refs_from_packet(text: str) -> list[str]:
    marker = "## Missing Referenced Files"
    start = text.find(marker)
    if start < 0:
        return []
    section = text[start:].split("## ", 2)[1]
    return re.findall(r"`([^`]+)`", section)


def _root_path(project_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return project_root / path


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
