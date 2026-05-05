#!/usr/bin/env python3
"""Dry-run validator for the agent-replacement architecture skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-replacement",
    "phase 7": "Agent Replacement is the Phase 7 gate",
    "active compatibility": "Status: `active_compatibility_mode`",
    "domain authorities": "Existing project-local gates remain domain authorities",
    "replacement rules": "## Replacement Rules",
    "migration map": "## Migration Map",
    "migration status": "## Migration Status",
    "validation": "validate_agent_replacement.py --dry-run",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "activation state": "## Replacement Activation State",
    "active compatibility": "Status: `active_compatibility_mode`",
    "replacement owner": "`agent-replacement` governs migration",
    "migration map": "## Migration Map",
    "phase 7 completed": "Phase 7 skill replacement completed",
}

REQUIRED_ROUTER_PHRASES = {
    "architecture first": "route through the active agent architecture first",
    "replacement skill": ".agents/skills/agent-replacement/SKILL.md",
    "domain compatibility": "compatibility targets selected and bounded",
}

REQUIRED_ROOT_PHRASES = {
    "architecture authority": "The active agent architecture skill chain",
    "replacement governs": "`agent-replacement` governing migration",
    "domain targets": "compatibility targets selected and bounded",
}

REQUIRED_ROADMAP_PHRASES = {
    "root orchestration": "Current active root orchestration",
    "replacement skill": ".agents/skills/agent-replacement/SKILL.md",
    "default process": "default root work process",
}

REQUIRED_STATUS_PHRASES = {
    "status title": "# Agent Replacement Migration Status",
    "root task intake complete": "| 1 | Root task intake | `agent-coordinator` | selected domain gate | `COMPLETE` |",
    "manual planning complete": "| 2 | Manual planning | `agent-planner` | selected validation plan | `COMPLETE` |",
    "plan review complete": "| 3 | Plan review | `agent-plan-review` | selected hard-stop/scope checks | `COMPLETE` |",
    "root orchestration complete": "| 4 | Root orchestration | `agent-supervisor` | `quant-work-cycle` for implementation | `COMPLETE` |",
    "direct implementation complete": "| 5 | Direct implementation | `agent-worker-pool` `coder` | approved file operations | `COMPLETE` |",
    "direct validation complete": "| 6 | Direct validation | `agent-worker-pool` `validator` | assigned validator commands | `COMPLETE` |",
    "workflow status complete": "| 7 | Workflow status | `agent-worker-pool` `tracker` | compact state transitions | `COMPLETE` |",
    "final reporting complete": "| 8 | Final reporting | `agent-reporter` | compact Korean report | `COMPLETE` |",
    "next target": "Next replacement target: `none`.",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"missing file: {path}") from None


def frontmatter_ok(text: str) -> list[str]:
    failures: list[str] = []
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return ["missing YAML frontmatter"]
    frontmatter = match.group(1)
    if "name: agent-replacement" not in frontmatter:
        failures.append("frontmatter name is not agent-replacement")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def missing_phrases(text: str, required: dict[str, str]) -> list[str]:
    return [label for label, phrase in required.items() if phrase not in text]


def validate(
    skill_path: Path,
    architecture_path: Path,
    agents_path: Path,
    root_hard_stops_path: Path,
    roadmap_status_path: Path,
    migration_status_path: Path,
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    agents_text = read_text(agents_path)
    root_text = read_text(root_hard_stops_path)
    roadmap_text = read_text(roadmap_status_path)
    migration_status_text = read_text(migration_status_path)

    failures = frontmatter_ok(skill_text)
    failures.extend(
        f"skill missing required phrase: {label}"
        for label in missing_phrases(skill_text, REQUIRED_SKILL_PHRASES)
    )
    failures.extend(
        f"architecture missing required phrase: {label}"
        for label in missing_phrases(architecture_text, REQUIRED_ARCHITECTURE_PHRASES)
    )
    failures.extend(
        f"AGENTS missing required phrase: {label}"
        for label in missing_phrases(agents_text, REQUIRED_ROUTER_PHRASES)
    )
    failures.extend(
        f"root hard stops missing required phrase: {label}"
        for label in missing_phrases(root_text, REQUIRED_ROOT_PHRASES)
    )
    failures.extend(
        f"roadmap status missing required phrase: {label}"
        for label in missing_phrases(roadmap_text, REQUIRED_ROADMAP_PHRASES)
    )
    failures.extend(
        f"migration status missing required phrase: {label}"
        for label in missing_phrases(migration_status_text, REQUIRED_STATUS_PHRASES)
    )

    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_router_phrases": sorted(REQUIRED_ROUTER_PHRASES),
        "checked_root_phrases": sorted(REQUIRED_ROOT_PHRASES),
        "checked_roadmap_phrases": sorted(REQUIRED_ROADMAP_PHRASES),
        "checked_status_phrases": sorted(REQUIRED_STATUS_PHRASES),
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[4]
    default_skill = Path(__file__).resolve().parents[1] / "SKILL.md"

    parser = argparse.ArgumentParser(
        description="Validate the agent-replacement skill and activation docs."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=project_root / "docs" / "architecture" / "agent_orchestration_architecture.md",
        type=Path,
    )
    parser.add_argument("--agents-path", default=project_root / "AGENTS.md", type=Path)
    parser.add_argument(
        "--root-hard-stops-path",
        default=project_root / "docs" / "root_hard_stops.md",
        type=Path,
    )
    parser.add_argument(
        "--roadmap-status-path",
        default=project_root / "docs" / "roadmap_status.md",
        type=Path,
    )
    parser.add_argument(
        "--migration-status-path",
        default=project_root
        / ".agents"
        / "skills"
        / "agent-replacement"
        / "MIGRATION_STATUS.md",
        type=Path,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and activation checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(
        args.skill_path,
        args.architecture_path,
        args.agents_path,
        args.root_hard_stops_path,
        args.roadmap_status_path,
        args.migration_status_path,
    )
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-replacement validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
