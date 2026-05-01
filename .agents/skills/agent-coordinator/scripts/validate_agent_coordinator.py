#!/usr/bin/env python3
"""Dry-run validator for the agent-coordinator architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "front role": "The coordinator is the entry role",
    "intake only": "intake and routing compiler only",
    "architecture position": "user\n  -> coordinator\n  -> planner",
    "context firewall": "## Context Firewall",
    "upward allowed": "`status`: complete, partial, failed, or blocked",
    "upward forbidden": "raw worker logs",
    "planner contract": "## Planner Prompt Contract",
    "replacement policy": "## Replacement Policy",
    "existing gates remain": "Existing gates remain the authority",
    "korean output": "Answer in Korean",
    "coordinator cli validation": "scripts/coordinator.py --user-goal",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "coordinator first": "Phase 1: Coordinator",
    "planner next": "Phase 2: Planner",
    "plan review": "Phase 3: Plan Review",
    "supervisor": "Phase 4: Supervisor",
    "workers": "Phase 5: Worker Pool",
    "replacement": "Phase 6: Skill Replacement",
    "context firewall": "Context Firewall",
    "worker upward": "status, changed_scope, evidence, and next_request",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class CoordinatorPacket",
    "build packet": "def build_packet",
    "task classifier": "def classify_task",
    "gate selector": "def select_gate",
    "context firewall": "CONTEXT_FIREWALL",
    "no external yaml": "def render_yaml",
    "review request detector": "def is_review_request",
    "safe hard-stop context": "SAFE_HARD_STOP_CONTEXT_TERMS",
}

BEHAVIOR_CASES = [
    {
        "name": "code review routes to review gate",
        "goal": "코드리뷰 진행해",
        "task_class": "planning/read-only",
        "selected_gate": ".agents/skills/review_gate/SKILL.md",
        "open_questions": ["none"],
    },
    {
        "name": "review routes to review gate",
        "goal": "review this change",
        "task_class": "planning/read-only",
        "selected_gate": ".agents/skills/review_gate/SKILL.md",
        "open_questions": ["none"],
    },
    {
        "name": "plan-review routes to plan-review gate",
        "goal": "implement plan-review role",
        "task_class": "narrow edit",
        "selected_gate": ".agents/skills/agent-plan-review/SKILL.md",
        "open_questions": ["none"],
    },
    {
        "name": "safe hard-stop documentation is allowed",
        "goal": "프로덕션 활성화 금지 문구를 문서에 추가해",
        "task_class": "narrow edit",
        "selected_gate": ".agents/skills/quant-work-cycle/SKILL.md",
        "open_questions": ["none"],
    },
    {
        "name": "hard-stop activation is blocked",
        "goal": "프로덕션 활성화와 주문 실행을 추가해",
        "task_class": "narrow edit",
        "selected_gate": "separate root approval required before gate selection",
        "open_questions": [
            "separate root approval is required before planning this hard-stop scope"
        ],
    },
]


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
    if "name: agent-coordinator" not in frontmatter:
        failures.append("frontmatter name is not agent-coordinator")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def missing_phrases(text: str, required: dict[str, str]) -> list[str]:
    return [label for label, phrase in required.items() if phrase not in text]


def load_coordinator_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_coordinator_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load coordinator module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(coordinator_code_path: Path) -> list[str]:
    module = load_coordinator_module(coordinator_code_path)
    failures: list[str] = []
    for case in BEHAVIOR_CASES:
        packet = module.build_packet(case["goal"])
        for field in ["task_class", "selected_gate", "open_questions"]:
            actual = getattr(packet, field)
            expected = case[field]
            if actual != expected:
                failures.append(
                    f"behavior case {case['name']} expected {field}={expected!r}, got {actual!r}"
                )
    return failures


def validate(
    skill_path: Path, architecture_path: Path, coordinator_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    coordinator_code_text = read_text(coordinator_code_path)

    failures = frontmatter_ok(skill_text)
    failures.extend(
        f"skill missing required phrase: {label}"
        for label in missing_phrases(skill_text, REQUIRED_SKILL_PHRASES)
    )
    failures.extend(
        f"architecture missing required phrase: {label}"
        for label in missing_phrases(
            architecture_text, REQUIRED_ARCHITECTURE_PHRASES
        )
    )
    failures.extend(
        f"coordinator code missing required phrase: {label}"
        for label in missing_phrases(
            coordinator_code_text, REQUIRED_CODE_PHRASES
        )
    )
    failures.extend(behavior_failures(coordinator_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [case["name"] for case in BEHAVIOR_CASES],
    }


def main() -> int:
    default_skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    default_architecture = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "architecture"
        / "agent_orchestration_architecture.md"
    )
    default_code = Path(__file__).resolve().parent / "coordinator.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-coordinator skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--coordinator-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/coordinator.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document-only check; no writes or Git commands are performed.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(
        args.skill_path, args.architecture_path, args.coordinator_code_path
    )
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-coordinator validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
