#!/usr/bin/env python3
"""Dry-run validator for the agent-planner architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-planner",
    "planning only": "This skill is planning-only",
    "architecture position": "user\n  -> coordinator\n  -> planner",
    "required input": "The planner accepts only a compact `coordinator_packet`",
    "planner responsibilities": "The planner must produce:",
    "context firewall": "## Context Firewall",
    "planner contract": "## Planner Packet Contract",
    "replacement policy": "Existing project-local gates remain the authority",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "planner phase": "Phase 2: Planner",
    "planner code surface": "Planner Code Surface",
    "current migration": "Current state: Phase 3 plan-review introduced.",
    "next component": "Next component: supervisor.",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class PlannerPacket",
    "step dataclass": "class PlanStep",
    "build planner packet": "def build_planner_packet",
    "blocked gate": "def is_blocked",
    "ordered plan": "def build_ordered_plan",
    "validation plan": "def build_validation_plan",
    "required fields": "REQUIRED_COORDINATOR_FIELDS",
    "stdin support": "sys.stdin.read()",
}

READY_COORDINATOR_PACKET = {
    "user_goal": "coordinator 역할에 코드와 기능 해석을 덧붙여",
    "task_class": "narrow edit",
    "current_route": "post-MVP v0.3 research-to-strategy adoption route",
    "selected_gate": ".agents/skills/agent-coordinator/SKILL.md",
    "allowed_scope": [".agents/skills/agent-coordinator/"],
    "forbidden_scope": ["live trading, brokerage integration, order generation"],
    "planner_must_output": [
        "ordered plan",
        "scope lock",
        "validation plan",
        "handoff packet for plan-review",
    ],
    "validation_expectations": ["git diff --check"],
    "context_firewall": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
    "korean_final_report": True,
    "open_questions": ["none"],
}

BLOCKED_COORDINATOR_PACKET = {
    **READY_COORDINATOR_PACKET,
    "user_goal": "프로덕션 활성화와 주문 실행을 추가해",
    "selected_gate": "separate root approval required before gate selection",
    "allowed_scope": ["approval question only; no planning or file edits before root approval"],
    "validation_expectations": ["not_applicable until separate root approval is granted"],
    "open_questions": [
        "separate root approval is required before planning this hard-stop scope"
    ],
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"missing file: {path}") from None


def missing_phrases(text: str, required: dict[str, str]) -> list[str]:
    return [label for label, phrase in required.items() if phrase not in text]


def frontmatter_ok(text: str) -> list[str]:
    failures: list[str] = []
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return ["missing YAML frontmatter"]
    frontmatter = match.group(1)
    if "name: agent-planner" not in frontmatter:
        failures.append("frontmatter name is not agent-planner")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def load_planner_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_planner_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load planner module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(planner_code_path: Path) -> list[str]:
    module = load_planner_module(planner_code_path)
    failures: list[str] = []

    ready = module.build_planner_packet(READY_COORDINATOR_PACKET)
    if ready.plan_status != "ready_for_plan_review":
        failures.append("ready coordinator packet did not produce ready_for_plan_review")
    if ready.user_goal != READY_COORDINATOR_PACKET["user_goal"]:
        failures.append("ready planner packet did not preserve user_goal text")
    if ready.current_route != READY_COORDINATOR_PACKET["current_route"]:
        failures.append("ready planner packet did not preserve current_route")
    if ready.supervisor_handoff["ready"] is not False:
        failures.append("ready planner packet allowed supervisor before plan-review")
    if not any(step.id == "P4" for step in ready.ordered_plan):
        failures.append("ready planner packet is missing P4 handoff step")

    blocked = module.build_planner_packet(BLOCKED_COORDINATOR_PACKET)
    if blocked.plan_status != "blocked":
        failures.append("blocked coordinator packet did not produce blocked plan")
    if blocked.supervisor_handoff["ready"] is not False:
        failures.append("blocked planner packet incorrectly prepared supervisor handoff")
    if "approval" not in blocked.plan_review_handoff["approval_question"]:
        failures.append("blocked planner packet is missing approval question")

    try:
        module.unwrap_coordinator_packet({"coordinator_packet": {"user_goal": "missing"}})
        failures.append("missing coordinator fields did not raise ValueError")
    except ValueError:
        pass

    return failures


def validate(
    skill_path: Path, architecture_path: Path, planner_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    planner_code_text = read_text(planner_code_path)

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
        f"planner code missing required phrase: {label}"
        for label in missing_phrases(planner_code_text, REQUIRED_CODE_PHRASES)
    )
    failures.extend(behavior_failures(planner_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [
            "ready coordinator packet produces plan-review handoff",
            "blocked coordinator packet prevents supervisor handoff",
            "missing coordinator fields fail closed",
        ],
    }


def main() -> int:
    default_skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    default_architecture = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "architecture"
        / "agent_orchestration_architecture.md"
    )
    default_code = Path(__file__).resolve().parent / "planner.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-planner skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--planner-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/planner.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(args.skill_path, args.architecture_path, args.planner_code_path)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-planner validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
