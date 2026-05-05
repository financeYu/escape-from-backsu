#!/usr/bin/env python3
"""Dry-run validator for the agent-plan-review architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-plan-review",
    "review only": "This skill is review-only",
    "architecture position": "user\n  -> coordinator\n  -> planner\n  <-> plan-review",
    "required input": "Plan Review accepts only a compact `planner_packet`",
    "review responsibilities": "Plan Review must check:",
    "user approval policy": "Do not require user approval for every clean plan.",
    "context firewall": "## Context Firewall",
    "packet contract": "## Plan Review Packet Contract",
    "replacement policy": "domain authorities as compatibility targets",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "plan review phase": "Phase 3: Plan Review",
    "plan review code surface": "Plan Review Code Surface",
    "current migration": (
        "Current state: Phase 7 skill replacement completed in active compatibility mode."
    ),
    "next component": "Next component: none",
    "approval policy": "Do not require user approval for every clean plan.",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class PlanReviewPacket",
    "review item dataclass": "class ReviewItem",
    "build packet": "def build_plan_review_packet",
    "checklist": "def build_checklist",
    "ordered plan preserved": "ordered_plan: list[dict[str, str]]",
    "approval": "def requires_separate_approval",
    "previous review approval": "def previous_review_requires_user_approval",
    "revised plan approval": "def revised_plan_needs_user_approval",
    "active route": "ACTIVE_ROUTE",
    "project-local gate": "def selected_gate_is_project_local",
    "hard-stop categories": "REQUIRED_HARD_STOP_CATEGORIES",
    "missing hard-stops": "def missing_hard_stop_categories",
    "status": "def review_status_for",
    "required fields": "REQUIRED_PLANNER_FIELDS",
    "stdin support": "sys.stdin.read()",
}

READY_PLANNER_PACKET = {
    "user_goal": "implement the plan-review role",
    "task_class": "narrow edit",
    "current_route": "post-MVP v0.3 research-to-strategy adoption route",
    "selected_gate": ".agents/skills/agent-plan-review/SKILL.md",
    "plan_status": "ready_for_plan_review",
    "scope_lock": {
        "allowed": [".agents/skills/agent-plan-review/"],
        "forbidden": [
            "live trading, brokerage integration, order generation, or real-money execution",
            "production activation from evidence-only outputs",
            "universe expansion or data-ingestion expansion without explicit approval",
            "valuation/fundamental scoring activation without explicit approval",
        ],
    },
    "ordered_plan": [
        {
            "id": "P1",
            "role": "planner",
            "action": "prepare plan-review role files",
            "output": "bounded plan",
        }
    ],
    "validation_plan": [
        {"command": "git diff --check", "purpose": "check patch formatting"}
    ],
    "context_firewall": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
    "plan_review_handoff": {
        "required_checks": ["scope lock", "hard-stop safety"],
        "approval_question": "none",
    },
    "supervisor_handoff": {
        "ready": False,
        "reason": "waiting for plan-review decision",
    },
    "korean_final_report": True,
}

BAD_READY_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "supervisor_handoff": {
        "ready": True,
        "reason": "incorrectly ready before plan-review",
    },
}

APPROVAL_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "selected_gate": "separate root approval required before gate selection",
    "plan_status": "blocked",
    "plan_review_handoff": {
        "required_checks": ["scope lock", "hard-stop safety"],
        "approval_question": "separate root approval is required before planning this hard-stop scope",
    },
}

INCOMPLETE_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "scope_lock": {"allowed": [".agents/skills/agent-plan-review/"], "forbidden": []},
}

BAD_ROUTE_GATE_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "current_route": "archived v0.1 route",
    "selected_gate": "global/non-project/SKILL.md",
}

PARTIAL_HARD_STOP_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "scope_lock": {"allowed": [".agents/skills/agent-plan-review/"], "forbidden": ["live trading only"]},
}

REVISED_AFTER_FIX_PLANNER_PACKET = {
    **READY_PLANNER_PACKET,
    "user_goal": "revised plan after plan-review fixes",
    "revision_context": {
        "revised_after_review_fix": True,
        "user_approval_ack": False,
    },
}

APPROVED_REVISED_AFTER_FIX_PLANNER_PACKET = {
    **REVISED_AFTER_FIX_PLANNER_PACKET,
    "revision_context": {
        "revised_after_review_fix": True,
        "user_approval_ack": True,
        "user_approval_evidence": "root/user approved revised plan",
    },
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
    if "name: agent-plan-review" not in frontmatter:
        failures.append("frontmatter name is not agent-plan-review")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def load_plan_review_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_plan_review_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load plan-review module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(plan_review_code_path: Path) -> list[str]:
    module = load_plan_review_module(plan_review_code_path)
    failures: list[str] = []

    ready = module.build_plan_review_packet(READY_PLANNER_PACKET)
    if ready.review_status != "approved_for_supervisor":
        failures.append("ready planner packet did not approve supervisor handoff")
    if ready.supervisor_handoff["ready"] is not True:
        failures.append("clean review did not set supervisor handoff ready")
    if ready.user_approval["required"] is not False:
        failures.append("clean review incorrectly required user approval")
    if ready.ordered_plan != READY_PLANNER_PACKET["ordered_plan"]:
        failures.append("plan-review packet did not preserve ordered_plan")

    bad_ready = module.build_plan_review_packet(BAD_READY_PLANNER_PACKET)
    if bad_ready.review_status != "needs_planner_fix":
        failures.append("pre-approved supervisor handoff did not require planner fix")
    if bad_ready.supervisor_handoff["ready"] is not False:
        failures.append("failed review allowed supervisor handoff")
    if bad_ready.user_approval["required"] is not False:
        failures.append("failed review required immediate user approval instead of planner fix")
    if bad_ready.user_approval["required_after_planner_fix"] is not True:
        failures.append("failed review did not mark approval required after planner fix")

    approval = module.build_plan_review_packet(APPROVAL_PLANNER_PACKET)
    if approval.review_status != "separate_approval_required":
        failures.append("separate approval packet did not require approval")
    if approval.user_approval["required"] is not True:
        failures.append("separate approval packet did not mark user approval required")
    if approval.supervisor_handoff["ready"] is not False:
        failures.append("separate approval packet allowed supervisor handoff")

    incomplete = module.build_plan_review_packet(INCOMPLETE_PLANNER_PACKET)
    if incomplete.review_status != "needs_planner_fix":
        failures.append("incomplete scope did not require planner fix")
    if not any(not item.passed for item in incomplete.checklist):
        failures.append("incomplete scope did not produce a failed review item")

    bad_route_gate = module.build_plan_review_packet(BAD_ROUTE_GATE_PLANNER_PACKET)
    if bad_route_gate.review_status != "needs_planner_fix":
        failures.append("bad route/gate packet did not require planner fix")
    if bad_route_gate.supervisor_handoff["ready"] is not False:
        failures.append("bad route/gate packet allowed supervisor handoff")
    failed_checks = [item.id for item in bad_route_gate.checklist if not item.passed]
    if "R1" not in failed_checks or "R2" not in failed_checks:
        failures.append("bad route/gate packet did not fail R1 and R2")

    partial_hard_stop = module.build_plan_review_packet(PARTIAL_HARD_STOP_PLANNER_PACKET)
    if partial_hard_stop.review_status != "needs_planner_fix":
        failures.append("partial hard-stop packet did not require planner fix")
    if partial_hard_stop.supervisor_handoff["ready"] is not False:
        failures.append("partial hard-stop packet allowed supervisor handoff")
    if "R4" not in [item.id for item in partial_hard_stop.checklist if not item.passed]:
        failures.append("partial hard-stop packet did not fail R4")

    revised_without_ack = module.build_plan_review_packet(
        READY_PLANNER_PACKET,
        previous_review=module.asdict(partial_hard_stop),
    )
    if revised_without_ack.review_status != "separate_approval_required":
        failures.append("revised plan after failed review did not require approval")
    if revised_without_ack.user_approval["required"] is not True:
        failures.append("revised plan after failed review did not mark approval required")
    if revised_without_ack.supervisor_handoff["ready"] is not False:
        failures.append("revised plan without approval allowed supervisor handoff")

    revised_still_bad = module.build_plan_review_packet(
        INCOMPLETE_PLANNER_PACKET,
        previous_review=module.asdict(partial_hard_stop),
    )
    if revised_still_bad.review_status != "needs_planner_fix":
        failures.append("bad revised plan asked for approval before planner fixes")

    revised_marker_without_ack = module.build_plan_review_packet(
        REVISED_AFTER_FIX_PLANNER_PACKET
    )
    if revised_marker_without_ack.review_status != "separate_approval_required":
        failures.append("revision marker without approval did not require approval")

    revised_with_ack = module.build_plan_review_packet(
        APPROVED_REVISED_AFTER_FIX_PLANNER_PACKET,
        previous_review=module.asdict(partial_hard_stop),
    )
    if revised_with_ack.review_status != "approved_for_supervisor":
        failures.append("approved revised plan did not reach supervisor approval")
    if revised_with_ack.user_approval["required"] is not False:
        failures.append("approved revised plan still required user approval")

    try:
        module.unwrap_planner_packet({"planner_packet": {"user_goal": "missing"}})
        failures.append("missing planner fields did not raise ValueError")
    except ValueError:
        pass

    return failures


def validate(
    skill_path: Path, architecture_path: Path, plan_review_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    plan_review_code_text = read_text(plan_review_code_path)

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
        f"plan-review code missing required phrase: {label}"
        for label in missing_phrases(plan_review_code_text, REQUIRED_CODE_PHRASES)
    )
    failures.extend(behavior_failures(plan_review_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [
            "clean planner packet approves supervisor without user approval",
            "failed review returns planner fix and delayed approval trigger",
            "separate approval packet blocks supervisor",
            "bad route/gate packet fails closed",
            "partial hard-stop packet fails closed",
            "revised plan after failed review requires user approval",
            "approved revised plan may proceed to supervisor",
            "missing planner fields fail closed",
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
    default_code = Path(__file__).resolve().parent / "plan_review.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-plan-review skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--plan-review-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/plan_review.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(args.skill_path, args.architecture_path, args.plan_review_code_path)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-plan-review validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
