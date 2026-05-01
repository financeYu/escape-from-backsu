#!/usr/bin/env python3
"""Dry-run validator for the agent-worker-pool architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-worker-pool",
    "contract only": "This skill is contract-only",
    "architecture position": "-> worker pool",
    "required input": "The worker pool accepts only a compact `supervisor_packet`",
    "role contracts": "## Worker Role Contracts",
    "context firewall": "## Context Firewall",
    "packet contract": "## Worker Pool Packet Contract",
    "replacement policy": "Existing project-local gates remain the authority",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "worker phase": "Phase 5: Worker Pool",
    "worker code surface": "Worker Pool Code Surface",
    "current migration": "Current state: Phase 5 worker pool introduced.",
    "next component": "Next component: skill replacement.",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class WorkerPoolPacket",
    "role dataclass": "class WorkerRoleSpec",
    "build packet": "def build_worker_pool_packet",
    "role specs": "def build_role_specs",
    "block reason": "def block_reason_for",
    "worker contracts": "def worker_contract_is_safe",
    "expected roles": "EXPECTED_WORKER_ROLES",
    "execution policy": "def execution_policy_is_safe",
    "required fields": "REQUIRED_SUPERVISOR_FIELDS",
    "stdin support": "sys.stdin.read()",
}

BASE_WORKER_PACKET = {
    "ready": True,
    "allowed_scope": [".agents/skills/agent-worker-pool/"],
    "forbidden_scope": [
        "live trading, brokerage integration, order generation, or real-money execution",
        "production activation from evidence-only outputs",
        "universe expansion or data-ingestion expansion without explicit approval",
        "valuation/fundamental scoring activation without explicit approval",
    ],
    "required_output": "compact result",
    "validation_commands": ["git diff --check"],
    "result_contract": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
}

READY_SUPERVISOR_PACKET = {
    "user_goal": "implement worker pool role",
    "task_class": "narrow edit",
    "current_route": "post-MVP v0.3 research-to-strategy adoption route",
    "selected_gate": ".agents/skills/agent-worker-pool/SKILL.md",
    "supervisor_status": "ready_for_workers",
    "block_reason": "none",
    "execution_policy": {
        "fetch": False,
        "pull": False,
        "push": False,
        "commit": False,
        "stage": False,
    },
    "worker_packets": [
        {**BASE_WORKER_PACKET, "worker_role": "coder"},
        {**BASE_WORKER_PACKET, "worker_role": "validator"},
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
        {**BASE_WORKER_PACKET, "worker_role": "tracker"},
    ],
    "context_firewall": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
    "korean_final_report": True,
}

BLOCKED_SUPERVISOR_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "supervisor_status": "blocked",
    "block_reason": "user approval required",
}

UNSAFE_POLICY_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "execution_policy": {
        "fetch": False,
        "pull": False,
        "push": False,
        "commit": True,
        "stage": False,
    },
}

MISSING_WORKER_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {**BASE_WORKER_PACKET, "worker_role": "coder"},
        {**BASE_WORKER_PACKET, "worker_role": "validator"},
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
    ],
}

EXTRA_WORKER_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {**BASE_WORKER_PACKET, "worker_role": "coder"},
        {**BASE_WORKER_PACKET, "worker_role": "validator"},
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
        {**BASE_WORKER_PACKET, "worker_role": "tracker"},
        {
            **BASE_WORKER_PACKET,
            "worker_role": "deployer",
            "allowed_scope": ["production activation"],
            "result_contract": {
                "upward_allowed": ["raw worker logs"],
                "upward_forbidden": [],
            },
        },
    ],
}

DUPLICATE_WORKER_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {**BASE_WORKER_PACKET, "worker_role": "coder"},
        {**BASE_WORKER_PACKET, "worker_role": "coder"},
        {**BASE_WORKER_PACKET, "worker_role": "validator"},
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
        {**BASE_WORKER_PACKET, "worker_role": "tracker"},
    ],
}

UNSAFE_CONTRACT_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {
            **BASE_WORKER_PACKET,
            "worker_role": "coder",
            "result_contract": {
                "upward_allowed": ["status", "raw worker logs"],
                "upward_forbidden": [],
            },
        },
        {**BASE_WORKER_PACKET, "worker_role": "validator"},
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
        {**BASE_WORKER_PACKET, "worker_role": "tracker"},
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
    if "name: agent-worker-pool" not in frontmatter:
        failures.append("frontmatter name is not agent-worker-pool")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def load_worker_pool_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_worker_pool_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load worker-pool module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(worker_pool_code_path: Path) -> list[str]:
    module = load_worker_pool_module(worker_pool_code_path)
    failures: list[str] = []

    ready = module.build_worker_pool_packet(READY_SUPERVISOR_PACKET)
    if ready.worker_pool_status != "ready_for_worker_execution":
        failures.append("ready supervisor packet did not prepare worker execution")
    if ready.block_reason != "none":
        failures.append("ready supervisor packet has unexpected block reason")
    if [spec.worker_role for spec in ready.role_specs] != module.EXPECTED_WORKER_ROLES:
        failures.append("worker role specs are missing or out of order")
    if any(any(spec.execution_limits.values()) for spec in ready.role_specs):
        failures.append("role specs allow forbidden execution flags")

    blocked = module.build_worker_pool_packet(BLOCKED_SUPERVISOR_PACKET)
    if blocked.worker_pool_status != "blocked":
        failures.append("blocked supervisor packet did not block worker pool")
    if any(spec.ready for spec in blocked.role_specs):
        failures.append("blocked worker pool left role spec ready")

    unsafe_policy = module.build_worker_pool_packet(UNSAFE_POLICY_PACKET)
    if unsafe_policy.block_reason != "unsafe execution policy":
        failures.append("unsafe execution policy did not fail closed")

    missing_worker = module.build_worker_pool_packet(MISSING_WORKER_PACKET)
    if "worker packet set incomplete" not in missing_worker.block_reason:
        failures.append("missing worker role did not fail closed")

    extra_worker = module.build_worker_pool_packet(EXTRA_WORKER_PACKET)
    if "worker packet set invalid: unexpected deployer" != extra_worker.block_reason:
        failures.append("unexpected worker role did not fail closed")

    duplicate_worker = module.build_worker_pool_packet(DUPLICATE_WORKER_PACKET)
    if "worker packet set invalid: duplicate coder" != duplicate_worker.block_reason:
        failures.append("duplicate worker role did not fail closed")

    unsafe_contract = module.build_worker_pool_packet(UNSAFE_CONTRACT_PACKET)
    if unsafe_contract.block_reason != "unsafe worker contract":
        failures.append("unsafe worker contract did not fail closed")

    try:
        module.unwrap_supervisor_packet({"supervisor_packet": {"user_goal": "missing"}})
        failures.append("missing supervisor fields did not raise ValueError")
    except ValueError:
        pass

    return failures


def validate(
    skill_path: Path, architecture_path: Path, worker_pool_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    worker_pool_code_text = read_text(worker_pool_code_path)

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
        f"worker-pool code missing required phrase: {label}"
        for label in missing_phrases(worker_pool_code_text, REQUIRED_CODE_PHRASES)
    )
    failures.extend(behavior_failures(worker_pool_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [
            "ready supervisor packet creates role specs",
            "blocked supervisor packet blocks role specs",
            "unsafe execution policy fails closed",
            "missing worker role fails closed",
            "unexpected worker role fails closed",
            "duplicate worker role fails closed",
            "unsafe worker contract fails closed",
            "missing supervisor fields fail closed",
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
    default_code = Path(__file__).resolve().parent / "worker_pool.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-worker-pool skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--worker-pool-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/worker_pool.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(args.skill_path, args.architecture_path, args.worker_pool_code_path)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-worker-pool validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
