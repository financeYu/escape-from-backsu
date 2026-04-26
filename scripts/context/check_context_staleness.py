from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_CURRENT_CONTEXT_CHARS = 8_000
NEGATION_MARKERS = (
    "must not",
    "do not",
    "does not",
    "not complete",
    "not started",
    "not an authority",
    "forbidden",
    "before validation",
    "before the active step closes",
    "금지",
)


@dataclass(frozen=True)
class StalenessWarning:
    code: str
    source: str
    message: str


def check_staleness(project_root: Path) -> tuple[StalenessWarning, ...]:
    root = project_root.resolve()
    roadmap_path = root / "docs/roadmap_status.md"
    checklist_path = root / "docs/project_checklist.md"
    roadmap = _read_optional(roadmap_path)
    checklist = _read_optional(checklist_path)
    warnings: list[StalenessWarning] = []

    roadmap_statuses = _extract_step_statuses(roadmap)
    checklist_statuses = _extract_step_statuses(checklist)
    warnings.extend(
        _compare_statuses(
            roadmap_statuses,
            checklist_statuses,
            left_name="docs/roadmap_status.md",
            right_name="docs/project_checklist.md",
        )
    )

    current_context_path = root / "docs/context/current_context.md"
    if current_context_path.exists():
        current_text = _read_optional(current_context_path)
        if len(current_text) > MAX_CURRENT_CONTEXT_CHARS:
            warnings.append(
                StalenessWarning(
                    code="current_context_too_large",
                    source="docs/context/current_context.md",
                    message=(
                        f"current context is {len(current_text)} characters; "
                        f"limit is {MAX_CURRENT_CONTEXT_CHARS}."
                    ),
                )
            )
        current_statuses = _extract_step_statuses(current_text)
        warnings.extend(
            _compare_statuses(
                roadmap_statuses,
                current_statuses,
                left_name="docs/roadmap_status.md",
                right_name="docs/context/current_context.md",
            )
        )

    generated_dir = root / "docs/context/generated"
    packet_paths: list[Path] = []
    if generated_dir.exists():
        packet_paths.extend(sorted(generated_dir.glob("*.md")))

    active_step20_packet = root / "docs/context/active_step20_packet.md"
    if active_step20_packet.exists():
        packet_paths.append(active_step20_packet)

    for packet_path in packet_paths:
        packet_text = _read_optional(packet_path)
        packet_statuses = _extract_step_statuses(packet_text)
        warnings.extend(
            _compare_statuses(
                roadmap_statuses,
                packet_statuses,
                left_name="docs/roadmap_status.md",
                right_name=_display_path(root, packet_path),
            )
        )
        warnings.extend(_check_packet_stage(root, packet_path, roadmap_statuses))
        warnings.extend(_check_packet_authority_notice(root, packet_path, packet_text))

    return tuple(warnings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Warn about stale context routing files.")
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    args = parser.parse_args(argv)

    warnings = check_staleness(Path(args.project_root))
    if not warnings:
        print("No context staleness warnings.")
        return 0

    for warning in warnings:
        print(f"[{warning.code}] {warning.source}: {warning.message}")
    return 0


def _extract_step_statuses(text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    in_status_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\|\s*Step\s*\|\s*Status\s*\|", stripped, flags=re.IGNORECASE):
            in_status_table = True
            continue
        if in_status_table and re.match(r"^\|\s*-+", stripped):
            continue
        if in_status_table and not stripped.startswith("|"):
            in_status_table = False

        table_match = re.match(r"^\|\s*(Step\s+\d+)\s*\|\s*([^|]+?)\s*\|", stripped, flags=re.IGNORECASE)
        if in_status_table and table_match:
            statuses[table_match.group(1).title()] = _normalize_status(table_match.group(2))
            continue

        bullet_match = re.match(r"^[-*]\s*(Step\s+\d+)\s*=\s*([^,\n]+)", stripped, flags=re.IGNORECASE)
        if bullet_match:
            statuses[bullet_match.group(1).title()] = _normalize_status(bullet_match.group(2))
            continue

        inline_match = re.search(r"\b(Step\s+\d+)\s*=\s*([^,\n|]+)", line, flags=re.IGNORECASE)
        if inline_match:
            statuses.setdefault(inline_match.group(1).title(), _normalize_status(inline_match.group(2)))
    return {step: status for step, status in statuses.items() if status}


def _normalize_status(value: str) -> str:
    value = value.strip().lower()
    if "partially complete" in value:
        return "PARTIALLY COMPLETE"
    if "needs fix" in value:
        return "NEEDS FIX"
    if "complete" in value:
        return "COMPLETE"
    if "deferred" in value:
        return "DEFERRED"
    if "waiting" in value or "not started" in value:
        return "WAITING"
    if "next" in value:
        return "NEXT"
    return value.upper()


def _compare_statuses(
    left: dict[str, str],
    right: dict[str, str],
    *,
    left_name: str,
    right_name: str,
) -> list[StalenessWarning]:
    warnings: list[StalenessWarning] = []
    for step in sorted(set(left) & set(right), key=_step_sort_key):
        if left[step] != right[step]:
            warnings.append(
                StalenessWarning(
                    code="step_status_mismatch",
                    source=right_name,
                    message=f"{step} is `{right[step]}` but {left_name} says `{left[step]}`.",
                )
            )
    return warnings


def _check_packet_stage(
    root: Path,
    packet_path: Path,
    roadmap_statuses: dict[str, str],
) -> list[StalenessWarning]:
    text = _read_optional(packet_path)
    warnings: list[StalenessWarning] = []
    for step, status in roadmap_statuses.items():
        if status != "WAITING":
            continue
        for line in text.splitlines():
            if _is_negated(line):
                continue
            if re.search(rf"{re.escape(step)}.*\bCOMPLETE\b", line, flags=re.IGNORECASE):
                warnings.append(
                    StalenessWarning(
                        code="packet_status_contradiction",
                        source=_display_path(root, packet_path),
                        message=f"packet claims {step} complete while roadmap says WAITING.",
                    )
                )
    return warnings


def _check_packet_authority_notice(root: Path, packet_path: Path, text: str) -> list[StalenessWarning]:
    lower = text.lower()
    has_routing_aid = "routing aid" in lower or "routing aids" in lower
    has_not_authority = "not an authority document" in lower or "not authority documents" in lower
    if has_routing_aid and has_not_authority:
        return []
    return [
        StalenessWarning(
            code="packet_missing_authority_notice",
            source=_display_path(root, packet_path),
            message="packet should clearly say it is a routing aid, not an authority document.",
        )
    ]


def _is_negated(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in NEGATION_MARKERS)


def _step_sort_key(step: str) -> int:
    match = re.search(r"\d+", step)
    return int(match.group(0)) if match else 0


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
