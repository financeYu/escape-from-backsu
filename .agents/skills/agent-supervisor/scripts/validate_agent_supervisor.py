#!/usr/bin/env python3
"""Dry-run validator for the agent-supervisor architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-supervisor",
    "orchestration only": "This skill is orchestration-only",
    "architecture position": "user\n  -> coordinator\n  -> planner\n  <-> plan-review\n  -> supervisor/root-agent",
    "required input": "The supervisor accepts only a compact `plan_review_packet`",
    "responsibilities": "The supervisor must:",
    "worker firewall": "## Worker Context Firewall",
    "packet contract": "## Supervisor Packet Contract",
    "replacement policy": "Existing project-local gates remain the authority",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "supervisor phase": "Phase 4: Supervisor",
    "supervisor code surface": "Supervisor Code Surface",
    "current migration": "Current state: Phase 5 worker pool introduced.",
    "next component": "Next component: skill replacement.",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class SupervisorPacket",
    "worker dataclass": "class WorkerPacket",
    "build packet": "def build_supervisor_packet",
    "worker packets": "def build_worker_packets",
    "block reason": "def block_reason_for",
    "approval": "def user_approval_required",
    "handoff": "def supervisor_handoff_ready",
    "execution policy": "\"commit\": False",
    "required fields": "REQUIRED_PLAN_REVIEW_FIELDS",
    "stdin support": "sys.stdin.read()",
}

READY_PLAN_REVIEW_PACKET = {
    "user_goal": "implement supervisor role",
    "task_class": "narrow edit",
    "current_route": "post-MVP v0.3 research-to-strategy adoption route",
    "selected_gate": ".agents/skills/agent-supervisor/SKILL.md",
    "scope_lock": {
        "allowed": [".agents/skills/agent-supervisor/"],
        "forbidden": [
            "live trading, brokerage integration, order generation, or real-money execution",
            "production activation from evidence-only outputs",
            "universe expansion or data-ingestion expansion without explicit approval",
            "valuation/fundamental scoring activation without explicit approval",
        ],
    },
    "validation_plan": [
        {"command": "git diff --check", "purpose": "check patch formatting"}
    ],
    "review_status": "approved_for_supervisor",
    "user_approval": {
        "required": False,
        "reason": "none",
        "required_after_planner_fix": False,
    },
    "supervisor_handoff": {
        "ready": True,
        "reason": "review passed; no user approval trigger",
    },
    "planner_feedback": {"required": False, "fixes": ["none"]},
    "context_firewall": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
    "korean_final_report": True,
}

BLOCKED_REVIEW_PACKET = {
    **READY_PLAN_REVIEW_PACKET,
    "review_status": "needs_planner_fix",
    "supervisor_handoff": {"ready": False, "reason": "blocked by review findings"},
}

APPROVAL_REQUIRED_PACKET = {
    **READY_PLAN_REVIEW_PACKET,
    "review_status": "separate_approval_required",
    "selected_gate": "separate root approval required before gate selection",
    "user_approval": {"required": True, "reason": "separate approval required"},
    "supervisor_handoff": {"ready": False, "reason": "separate approval required"},
}

INCONSISTENT_APPROVAL_GATE_PACKET = {
    **READY_PLAN_REVIEW_PACKET,
    "selected_gate": "separate root approval required before gate selection",
    "user_approval": {"required": False, "reason": "none"},
    "supervisor_handoff": {"ready": True, "reason": "inconsistent upstream packet"},
}

BAD_GATE_PACKET = {
    **READY_PLAN_REVIEW_PACKET,
    "selected_gate": "global/non-project/SKILL.md",
}

READ_ONLY_PACKET = {
    **READY_PLAN_REVIEW_PACKET,
    "task_class": "planning/read-only",
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
    if "name: agent-supervisor" not in frontmatter:
        failures.append("frontmatter name is not agent-supervisor")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def load_supervisor_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_supervisor_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load supervisor module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(supervisor_code_path: Path) -> list[str]:
    module = load_supervisor_module(supervisor_code_path)
    failures: list[str] = []

    ready = module.build_supervisor_packet(READY_PLAN_REVIEW_PACKET)
    if ready.supervisor_status != "ready_for_workers":
        failures.append("approved plan-review packet did not prepare workers")
    if ready.block_reason != "none":
        failures.append("approved plan-review packet has unexpected block reason")
    if len(ready.worker_packets) != 4:
        failures.append("supervisor did not create four worker packets")
    if [worker.worker_role for worker in ready.worker_packets] != [
        "coder",
        "validator",
        "reporter",
        "tracker",
    ]:
        failures.append("worker packet order or roles are wrong")
    if any(ready.execution_policy.values()):
        failures.append("execution policy allowed a forbidden Git operation")
    if not all(worker.result_contract["upward_allowed"] == module.UPWARD_ALLOWED for worker in ready.worker_packets):
        failures.append("worker result contracts do not preserve upward allowed fields")

    blocked = module.build_supervisor_packet(BLOCKED_REVIEW_PACKET)
    if blocked.supervisor_status != "blocked":
        failures.append("failed plan-review packet did not block supervisor")
    if any(worker.ready for worker in blocked.worker_packets):
        failures.append("blocked supervisor packet prepared ready workers")

    approval = module.build_supervisor_packet(APPROVAL_REQUIRED_PACKET)
    if approval.supervisor_status != "blocked":
        failures.append("approval-required packet did not block supervisor")
    if approval.block_reason != "user approval required":
        failures.append("approval-required packet used unexpected block reason")

    inconsistent_approval = module.build_supervisor_packet(INCONSISTENT_APPROVAL_GATE_PACKET)
    if inconsistent_approval.supervisor_status != "blocked":
        failures.append("approval blocker gate did not fail closed")
    if any(worker.ready for worker in inconsistent_approval.worker_packets):
        failures.append("approval blocker gate prepared ready workers")

    bad_gate = module.build_supervisor_packet(BAD_GATE_PACKET)
    if bad_gate.supervisor_status != "blocked":
        failures.append("bad gate packet did not block supervisor")

    read_only = module.build_supervisor_packet(READ_ONLY_PACKET)
    coder = [worker for worker in read_only.worker_packets if worker.worker_role == "coder"][0]
    if coder.ready is not False:
        failures.append("planning/read-only packet incorrectly prepared coder")

    try:
        module.unwrap_plan_review_packet({"plan_review_packet": {"user_goal": "missing"}})
        failures.append("missing plan-review fields did not raise ValueError")
    except ValueError:
        pass

    return failures


def validate(
    skill_path: Path, architecture_path: Path, supervisor_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    supervisor_code_text = read_text(supervisor_code_path)

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
        f"supervisor code missing required phrase: {label}"
        for label in missing_phrases(supervisor_code_text, REQUIRED_CODE_PHRASES)
    )
    failures.extend(behavior_failures(supervisor_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [
            "approved plan-review packet creates bounded workers",
            "failed plan-review packet blocks workers",
            "approval-required packet blocks workers",
            "approval blocker gate fails closed even with inconsistent approval fields",
            "bad gate packet fails closed",
            "planning/read-only packet does not prepare coder",
            "missing plan-review fields fail closed",
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
    default_code = Path(__file__).resolve().parent / "supervisor.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-supervisor skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--supervisor-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/supervisor.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(args.skill_path, args.architecture_path, args.supervisor_code_path)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-supervisor validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
