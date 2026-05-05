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
    "normalizer contract": "The worker-pool normalizer is contract-only",
    "architecture position": "-> worker pool",
    "required input": "The worker pool accepts only a compact `supervisor_packet`",
    "role contracts": "## Worker Role Contracts",
    "coder tool": "## Coder Tool Contract",
    "tracker tool": "## Tracker Tool Contract",
    "context firewall": "## Context Firewall",
    "packet contract": "## Worker Pool Packet Contract",
    "replacement policy": "domain authorities as compatibility targets",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "worker phase": "Phase 5: Worker Pool",
    "worker code surface": "Worker Pool Code Surface",
    "current migration": (
        "Current state: Phase 7 skill replacement completed in active compatibility mode."
    ),
    "next component": "Next component: none",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class WorkerPoolPacket",
    "role dataclass": "class WorkerRoleSpec",
    "build packet": "def build_worker_pool_packet",
    "role specs": "def build_role_specs",
    "block reason": "def block_reason_for",
    "worker contracts": "def worker_contract_is_safe",
    "assigned plan steps": "assigned_plan_steps",
    "context firewall safety": "def context_firewall_is_safe",
    "context firewall normalization": "def normalized_context_firewall",
    "expected roles": "EXPECTED_WORKER_ROLES",
    "execution policy": "def execution_policy_is_safe",
    "required fields": "REQUIRED_SUPERVISOR_FIELDS",
    "stdin support": "sys.stdin.read()",
}

REQUIRED_CODER_TOOL_PHRASES = {
    "coder packet": "class CoderPacket",
    "build coder packet": "def build_coder_packet",
    "file operation": "class FileOperation",
    "file operation validation": "def validate_file_operations",
    "coder task validation": "def validate_coder_task",
    "assigned plan steps": "def completed_steps_cover_assigned_steps",
    "scope check": "def scope_is_allowed",
    "hard stop markers": "FORBIDDEN_MARKERS",
    "reporter worker result": "def worker_result_for",
    "actual file write": "target.write_text",
    "dry run": "--dry-run",
    "stdin support": "sys.stdin.read()",
}

REQUIRED_VALIDATOR_TOOL_PHRASES = {
    "validator packet": "class ValidatorPacket",
    "build validator packet": "def build_validator_packet",
    "coder result validation": "def validate_coder_result",
    "direction route": "ACTIVE_ROUTE",
    "assigned plan steps": "def evidence_covers_assigned_steps",
    "scope check": "def scope_is_allowed",
    "hard stop markers": "FORBIDDEN_MARKERS",
    "reporter worker result": "def worker_result_for",
    "stdin support": "sys.stdin.read()",
}

REQUIRED_TRACKER_TOOL_PHRASES = {
    "tracker packet": "class TrackerPacket",
    "build tracker packet": "def build_tracker_packet",
    "coder transition": "def state_for_coder_event",
    "validator transition": "def state_for_validator_event",
    "out of order": "def prior_state_allows_validator",
    "workflow state": "workflow_state",
    "tracker events": "TRACKER_EVENTS",
    "reporter handoff": "ready_for_reporter",
    "raw context guard": "def contains_forbidden_context",
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
    "assigned_plan_steps": [
        {
            "id": "P4",
            "role": "supervisor",
            "action": "assign implementation only inside locked scope",
            "output": "bounded coder packet",
        }
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

PLANNING_READ_ONLY_SUPERVISOR_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "task_class": "planning/read-only",
    "supervisor_status": "blocked",
    "block_reason": "planning/read-only does not open worker execution",
    "worker_packets": [
        {
            **BASE_WORKER_PACKET,
            "worker_role": "coder",
            "ready": False,
            "assigned_plan_steps": [],
            "required_output": (
                "not_applicable for blocked supervisor packet"
            ),
            "validation_commands": ["not_applicable for coder"],
        },
        {**BASE_WORKER_PACKET, "worker_role": "validator", "ready": False},
        {
            **BASE_WORKER_PACKET,
            "worker_role": "reporter",
            "ready": False,
            "assigned_plan_steps": [],
            "validation_commands": ["not_applicable for reporter"],
        },
        {**BASE_WORKER_PACKET, "worker_role": "tracker", "ready": False},
    ],
}

APPROVAL_GATE_READY_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "selected_gate": "separate root approval required before gate selection",
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

EMPTY_WORKER_INSTRUCTION_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {
            **BASE_WORKER_PACKET,
            "worker_role": "coder",
            "required_output": "",
        },
        {
            **BASE_WORKER_PACKET,
            "worker_role": "validator",
            "validation_commands": [],
        },
        {**BASE_WORKER_PACKET, "worker_role": "reporter"},
        {**BASE_WORKER_PACKET, "worker_role": "tracker"},
    ],
}

MISSING_CODER_STEPS_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "worker_packets": [
        {
            **BASE_WORKER_PACKET,
            "worker_role": "coder",
            "assigned_plan_steps": [],
        },
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

UNSAFE_CONTEXT_FIREWALL_PACKET = {
    **READY_SUPERVISOR_PACKET,
    "context_firewall": {
        "upward_allowed": ["status", "raw worker logs"],
        "upward_forbidden": [],
    },
}

GOOD_CODER_RESULT = {
    "worker_role": "coder",
    "status": "complete",
    "changed_scope": [".agents/skills/agent-worker-pool/scripts/worker_pool.py"],
    "evidence": ["completed assigned_plan_steps: P4"],
    "next_request": "none",
}

ESCAPED_SCOPE_CODER_RESULT = {
    "worker_role": "coder",
    "status": "complete",
    "changed_scope": [
        ".agents/skills/agent-worker-pool/../../docs/root_hard_stops.md"
    ],
    "evidence": ["completed assigned_plan_steps: P4"],
    "next_request": "none",
}

DIRECTION_MISMATCH_CODER_RESULT = {
    "worker_role": "coder",
    "status": "complete",
    "changed_scope": ["production activation"],
    "evidence": ["implemented outside active v0.3 evidence-only direction"],
    "next_request": "none",
}

MISSING_STEP_CODER_RESULT = {
    "worker_role": "coder",
    "status": "complete",
    "changed_scope": [".agents/skills/agent-worker-pool/scripts/worker_pool.py"],
    "evidence": ["implementation complete without step evidence"],
    "next_request": "none",
}

RAW_CONTEXT_CODER_RESULT = {
    "worker_role": "coder",
    "status": "complete",
    "changed_scope": [".agents/skills/agent-worker-pool/scripts/worker_pool.py"],
    "evidence": ["completed assigned_plan_steps: P4"],
    "next_request": "none",
    "raw_logs": "full implementation output",
}

GOOD_CODER_TASK = {
    "operations": [
        {
            "action": "write_file",
            "path": ".agents/skills/agent-worker-pool/generated_coder_fixture.txt",
            "content": "generated by coder tool\n",
        }
    ],
    "completed_plan_steps": ["P4"],
    "evidence": ["supervisor-approved file operation for assigned_plan_steps: P4"],
    "next_request": "none",
}

OUT_OF_SCOPE_CODER_TASK = {
    **GOOD_CODER_TASK,
    "operations": [
        {
            "action": "write_file",
            "path": "docs/outside_worker_pool.txt",
            "content": "outside scope\n",
        }
    ],
}

MISSING_STEP_CODER_TASK = {
    **GOOD_CODER_TASK,
    "completed_plan_steps": [],
}

RAW_CONTEXT_CODER_TASK = {
    **GOOD_CODER_TASK,
    "raw_logs": "full implementation transcript",
}

GOOD_VALIDATOR_RESULT = {
    "worker_role": "validator",
    "status": "complete",
    "changed_scope": [".agents/skills/agent-worker-pool/scripts/worker_pool.py"],
    "evidence": ["validator passed coder output against assigned_plan_steps: P4"],
    "next_request": "none",
}

FAILED_VALIDATOR_RESULT = {
    "worker_role": "validator",
    "status": "failed",
    "changed_scope": [".agents/skills/agent-worker-pool/scripts/worker_pool.py"],
    "evidence": ["validator found coder output needs fix for assigned_plan_steps: P4"],
    "next_request": "request coder fix",
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


def load_coder_tool_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_worker_pool_coder_tool", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load worker-pool coder tool: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_validator_tool_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_worker_pool_validator_tool", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load worker-pool validator tool: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_tracker_tool_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_worker_pool_tracker_tool", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load worker-pool tracker tool: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(
    worker_pool_code_path: Path,
    coder_tool_path: Path,
    validator_tool_path: Path,
    tracker_tool_path: Path,
) -> list[str]:
    module = load_worker_pool_module(worker_pool_code_path)
    coder_tool = load_coder_tool_module(coder_tool_path)
    validator_tool = load_validator_tool_module(validator_tool_path)
    tracker_tool = load_tracker_tool_module(tracker_tool_path)
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
    coder = [spec for spec in ready.role_specs if spec.worker_role == "coder"][0]
    if not coder.assigned_plan_steps:
        failures.append("worker-pool role spec did not preserve coder assigned_plan_steps")
    if coder.required_input != "supervisor worker packet with approved assigned_plan_steps only":
        failures.append("coder required_input does not require approved assigned_plan_steps")

    blocked = module.build_worker_pool_packet(BLOCKED_SUPERVISOR_PACKET)
    if blocked.worker_pool_status != "blocked":
        failures.append("blocked supervisor packet did not block worker pool")
    if any(spec.ready for spec in blocked.role_specs):
        failures.append("blocked worker pool left role spec ready")

    planning_read_only = module.build_worker_pool_packet(
        PLANNING_READ_ONLY_SUPERVISOR_PACKET
    )
    if planning_read_only.worker_pool_status != "blocked":
        failures.append("planning/read-only worker pool opened worker execution")
    if any(spec.ready for spec in planning_read_only.role_specs):
        failures.append("planning/read-only worker pool left a worker ready")

    approval_gate_ready = module.build_worker_pool_packet(APPROVAL_GATE_READY_PACKET)
    if approval_gate_ready.block_reason != "supervisor blocked: user approval required":
        failures.append("approval blocker gate did not fail closed")

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

    empty_instruction = module.build_worker_pool_packet(EMPTY_WORKER_INSTRUCTION_PACKET)
    if empty_instruction.block_reason != "unsafe worker contract":
        failures.append("empty worker instruction did not fail closed")

    missing_coder_steps = module.build_worker_pool_packet(MISSING_CODER_STEPS_PACKET)
    if missing_coder_steps.block_reason != "unsafe worker contract":
        failures.append("missing coder assigned_plan_steps did not fail closed")

    unsafe_firewall = module.build_worker_pool_packet(UNSAFE_CONTEXT_FIREWALL_PACKET)
    if unsafe_firewall.block_reason != "unsafe context firewall":
        failures.append("unsafe top-level context firewall did not fail closed")
    if unsafe_firewall.context_firewall["upward_allowed"] != module.UPWARD_ALLOWED:
        failures.append("unsafe top-level context firewall was not normalized")

    try:
        module.unwrap_supervisor_packet({"supervisor_packet": {"user_goal": "missing"}})
        failures.append("missing supervisor fields did not raise ValueError")
    except ValueError:
        pass

    ready_packet = module.asdict(ready)
    coder_ready = coder_tool.build_coder_packet(
        ready_packet, GOOD_CODER_TASK, workspace_root=Path.cwd(), dry_run=True
    )
    if coder_ready.coder_status != "complete":
        failures.append("coder tool did not complete an aligned file operation")
    if coder_ready.worker_result["worker_role"] != "coder":
        failures.append("coder tool did not emit coder worker_result")
    if not coder_ready.applied_operations or not coder_ready.applied_operations[0].dry_run:
        failures.append("coder tool did not expose dry-run file operation evidence")

    coder_scope_block = coder_tool.build_coder_packet(
        ready_packet, OUT_OF_SCOPE_CODER_TASK, workspace_root=Path.cwd(), dry_run=True
    )
    if coder_scope_block.coder_status != "blocked":
        failures.append("coder tool did not block out-of-scope file operation")

    coder_missing_step = coder_tool.build_coder_packet(
        ready_packet, MISSING_STEP_CODER_TASK, workspace_root=Path.cwd(), dry_run=True
    )
    if coder_missing_step.coder_status != "blocked":
        failures.append("coder tool did not block missing assigned step evidence")

    coder_raw_context = coder_tool.build_coder_packet(
        ready_packet, RAW_CONTEXT_CODER_TASK, workspace_root=Path.cwd(), dry_run=True
    )
    if coder_raw_context.coder_status != "blocked":
        failures.append("coder tool did not block raw coder task context")

    validator_generated = validator_tool.build_validator_packet(
        ready_packet, coder_ready.worker_result
    )
    if validator_generated.validator_status != "passed":
        failures.append("validator tool did not pass coder tool worker_result")

    validator_ready = validator_tool.build_validator_packet(
        ready_packet, GOOD_CODER_RESULT
    )
    if validator_ready.validator_status != "passed":
        failures.append("validator tool did not pass aligned coder result")
    if validator_ready.worker_result["worker_role"] != "validator":
        failures.append("validator tool did not emit validator worker_result")

    validator_scope_escape = validator_tool.build_validator_packet(
        ready_packet, ESCAPED_SCOPE_CODER_RESULT
    )
    if validator_scope_escape.validator_status != "blocked":
        failures.append("validator tool did not block escaped changed_scope path")

    validator_direction = validator_tool.build_validator_packet(
        ready_packet, DIRECTION_MISMATCH_CODER_RESULT
    )
    if validator_direction.validator_status != "blocked":
        failures.append("validator tool did not block direction mismatch")

    validator_missing_step = validator_tool.build_validator_packet(
        ready_packet, MISSING_STEP_CODER_RESULT
    )
    if validator_missing_step.validator_status != "needs_coder_fix":
        failures.append("validator tool did not require fix for missing assigned step evidence")

    validator_raw_context = validator_tool.build_validator_packet(
        ready_packet, RAW_CONTEXT_CODER_RESULT
    )
    if validator_raw_context.validator_status != "blocked":
        failures.append("validator tool did not block raw coder context")

    tracker_coder = tracker_tool.build_tracker_packet(
        ready_packet, "coder_completed", GOOD_CODER_RESULT
    )
    if tracker_coder.tracker_status != "validation_required":
        failures.append("tracker tool did not advance completed coder to validation")
    if tracker_coder.workflow_state["next_worker"] != "validator":
        failures.append("tracker tool did not request validator after coder completion")

    tracker_validator = tracker_tool.build_tracker_packet(
        ready_packet,
        "validator_completed",
        GOOD_VALIDATOR_RESULT,
        tracker_coder.workflow_state,
    )
    if tracker_validator.tracker_status != "ready_for_reporter":
        failures.append("tracker tool did not advance completed validator to reporter")
    if tracker_validator.workflow_state["next_worker"] != "reporter":
        failures.append("tracker tool did not request reporter after validator completion")

    tracker_out_of_order = tracker_tool.build_tracker_packet(
        ready_packet, "validator_completed", GOOD_VALIDATOR_RESULT
    )
    if tracker_out_of_order.block_reason != "out_of_order_workflow":
        failures.append("tracker tool did not block validator completion before coder tracking")

    tracker_raw_context = tracker_tool.build_tracker_packet(
        ready_packet, "coder_completed", RAW_CONTEXT_CODER_RESULT
    )
    if tracker_raw_context.tracker_status != "blocked":
        failures.append("tracker tool did not block raw worker context")

    tracker_failed_validation = tracker_tool.build_tracker_packet(
        ready_packet,
        "validator_completed",
        FAILED_VALIDATOR_RESULT,
        tracker_coder.workflow_state,
    )
    if tracker_failed_validation.tracker_status != "needs_coder_fix":
        failures.append("tracker tool did not route failed validation back to coder")

    return failures


def validate(
    skill_path: Path,
    architecture_path: Path,
    worker_pool_code_path: Path,
    coder_tool_path: Path,
    validator_tool_path: Path,
    tracker_tool_path: Path,
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    worker_pool_code_text = read_text(worker_pool_code_path)
    coder_tool_text = read_text(coder_tool_path)
    validator_tool_text = read_text(validator_tool_path)
    tracker_tool_text = read_text(tracker_tool_path)

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
    failures.extend(
        f"coder tool missing required phrase: {label}"
        for label in missing_phrases(coder_tool_text, REQUIRED_CODER_TOOL_PHRASES)
    )
    failures.extend(
        f"validator tool missing required phrase: {label}"
        for label in missing_phrases(validator_tool_text, REQUIRED_VALIDATOR_TOOL_PHRASES)
    )
    failures.extend(
        f"tracker tool missing required phrase: {label}"
        for label in missing_phrases(tracker_tool_text, REQUIRED_TRACKER_TOOL_PHRASES)
    )
    failures.extend(
        behavior_failures(
            worker_pool_code_path,
            coder_tool_path,
            validator_tool_path,
            tracker_tool_path,
        )
    )

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_coder_tool_phrases": sorted(REQUIRED_CODER_TOOL_PHRASES),
        "checked_validator_tool_phrases": sorted(REQUIRED_VALIDATOR_TOOL_PHRASES),
        "checked_tracker_tool_phrases": sorted(REQUIRED_TRACKER_TOOL_PHRASES),
        "checked_behavior_cases": [
            "ready supervisor packet creates role specs",
            "blocked supervisor packet blocks role specs",
            "planning/read-only packet blocks worker execution",
            "approval blocker gate fails closed",
            "unsafe execution policy fails closed",
            "missing worker role fails closed",
            "unexpected worker role fails closed",
            "duplicate worker role fails closed",
            "unsafe worker contract fails closed",
            "empty worker instruction fails closed",
            "missing coder assigned_plan_steps fails closed",
            "unsafe top-level context firewall fails closed",
            "missing supervisor fields fail closed",
            "coder tool completes aligned dry-run file operation",
            "coder tool blocks out-of-scope operation",
            "coder tool blocks missing assigned step evidence",
            "coder tool blocks raw coder context",
            "validator tool passes coder tool worker_result",
            "validator tool passes aligned coder result",
            "validator tool blocks direction mismatch",
            "validator tool requires assigned step evidence",
            "validator tool blocks raw coder context",
            "tracker tool advances coder completion to validation",
            "tracker tool advances validator completion to reporter",
            "tracker tool blocks validator completion before coder tracking",
            "tracker tool blocks raw worker context",
            "tracker tool routes failed validation back to coder",
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
    default_coder_tool = Path(__file__).resolve().parent / "coder.py"
    default_validator_tool = Path(__file__).resolve().parent / "validator.py"
    default_tracker_tool = Path(__file__).resolve().parent / "tracker.py"

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
        "--coder-tool-path",
        default=default_coder_tool,
        type=Path,
        help="Path to scripts/coder.py.",
    )
    parser.add_argument(
        "--validator-tool-path",
        default=default_validator_tool,
        type=Path,
        help="Path to scripts/validator.py.",
    )
    parser.add_argument(
        "--tracker-tool-path",
        default=default_tracker_tool,
        type=Path,
        help="Path to scripts/tracker.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(
        args.skill_path,
        args.architecture_path,
        args.worker_pool_code_path,
        args.coder_tool_path,
        args.validator_tool_path,
        args.tracker_tool_path,
    )
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
