#!/usr/bin/env python3
"""Dry-run validator for the subproject-delegation skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter": "name: subproject-delegation",
    "purpose": "Keep root orchestration thin",
    "delegation principle": "Root should delegate subproject-contained exploration",
    "duplicate write rule": "One writer per path at a time.",
    "context firewall": "Subproject workers may return only",
    "handoff packet": "subproject_handoff:",
    "architecture integration": "## Architecture Integration",
}

REQUIRED_ROUTING_PHRASES = {
    "AGENTS skill reference": ".agents/skills/subproject-delegation/SKILL.md",
    "coordinator route": "subproject-delegation/SKILL.md",
    "coordinator terms": "SUBPROJECT_DELEGATION_TERMS",
    "planner check": "subproject delegation",
    "supervisor mention": "subproject delegation",
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
    if "name: subproject-delegation" not in frontmatter:
        failures.append("frontmatter name is not subproject-delegation")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def missing_phrases(text: str, required: dict[str, str]) -> list[str]:
    return [label for label, phrase in required.items() if phrase not in text]


def validate(project_root: Path) -> dict[str, object]:
    skill = read_text(project_root / ".agents/skills/subproject-delegation/SKILL.md")
    agents = read_text(project_root / "AGENTS.md")
    coordinator_skill = read_text(project_root / ".agents/skills/agent-coordinator/SKILL.md")
    coordinator_script = read_text(project_root / ".agents/skills/agent-coordinator/scripts/coordinator.py")
    planner_skill = read_text(project_root / ".agents/skills/agent-planner/SKILL.md")
    supervisor_skill = read_text(project_root / ".agents/skills/agent-supervisor/SKILL.md")

    failures = frontmatter_ok(skill)
    failures.extend(
        f"skill missing required phrase: {label}"
        for label in missing_phrases(skill, REQUIRED_SKILL_PHRASES)
    )
    routing_text = "\n".join(
        [agents, coordinator_skill, coordinator_script, planner_skill, supervisor_skill]
    )
    failures.extend(
        f"routing missing required phrase: {label}"
        for label in missing_phrases(routing_text, REQUIRED_ROUTING_PHRASES)
    )
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_routing_phrases": sorted(REQUIRED_ROUTING_PHRASES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate subproject delegation controls.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[4], type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.project_root.resolve())
    result["dry_run"] = bool(args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"subproject-delegation validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
