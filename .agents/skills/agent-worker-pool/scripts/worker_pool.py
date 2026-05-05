#!/usr/bin/env python3
"""Normalize worker role specs from a supervisor packet.

The worker pool does not execute worker tasks. It checks that the supervisor
provided bounded worker packets and returns role specs for coder, validator,
reporter, and tracker.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_SUPERVISOR_FIELDS = [
    "user_goal",
    "task_class",
    "current_route",
    "selected_gate",
    "supervisor_status",
    "block_reason",
    "execution_policy",
    "worker_packets",
    "context_firewall",
    "korean_final_report",
]

ACTIVE_ROUTE = "post-MVP v0.3 research-to-strategy adoption route"
PROJECT_LOCAL_GATE_PREFIX = ".agents/skills/"
APPROVAL_GATE = "separate root approval required before gate selection"
EXPECTED_WORKER_ROLES = ["coder", "tracker", "validator", "reporter"]
UPWARD_ALLOWED = ["status", "changed_scope", "evidence", "next_request"]
DEFAULT_UPWARD_FORBIDDEN = ["raw worker logs"]
FORBIDDEN_EXECUTION_FLAGS = ["fetch", "pull", "push", "commit", "stage"]

ROLE_PURPOSES = {
    "coder": "implement only inside the assigned scope",
    "validator": (
        "check coder output against project direction, hard stops, scope lock, "
        "assigned_plan_steps, and assigned validation commands"
    ),
    "reporter": (
        "collect approved worker_result summaries and produce compact "
        "Korean supervisor/user reports only"
    ),
    "tracker": (
        "record coder completion, advance validation, record validator "
        "completion, and advance the next worker request"
    ),
}


@dataclass(frozen=True)
class WorkerRoleSpec:
    worker_role: str
    ready: bool
    purpose: str
    allowed_scope: list[str]
    forbidden_scope: list[str]
    assigned_plan_steps: list[dict[str, str]]
    required_input: str
    required_output: str
    validation_commands: list[str]
    result_contract: dict[str, list[str]]
    execution_limits: dict[str, bool]


@dataclass(frozen=True)
class WorkerPoolPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    worker_pool_status: str
    block_reason: str
    role_specs: list[WorkerRoleSpec]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool


def unwrap_supervisor_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"supervisor_packet": packet}."""
    if "supervisor_packet" in raw_packet:
        raw_packet = raw_packet["supervisor_packet"]
    missing = [field for field in REQUIRED_SUPERVISOR_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(
            f"supervisor packet missing required fields: {', '.join(missing)}"
        )
    return raw_packet


def load_packet(args: argparse.Namespace) -> dict[str, Any]:
    """Load a supervisor packet from CLI JSON or a JSON file."""
    if args.supervisor_packet_json:
        if args.supervisor_packet_json == "-":
            return unwrap_supervisor_packet(json.loads(sys.stdin.read()))
        return unwrap_supervisor_packet(json.loads(args.supervisor_packet_json))
    if args.supervisor_packet_file:
        packet_path = Path(args.supervisor_packet_file)
        return unwrap_supervisor_packet(json.loads(packet_path.read_text(encoding="utf-8")))
    raise ValueError("provide --supervisor-packet-json or --supervisor-packet-file")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value)]


def selected_gate_is_project_local(selected_gate: str) -> bool:
    """Return true for project-local skill gates only."""
    return selected_gate.startswith(PROJECT_LOCAL_GATE_PREFIX) and selected_gate.endswith(
        "/SKILL.md"
    )


def execution_policy_is_safe(packet: dict[str, Any]) -> bool:
    """Return true when every Git/network execution flag is disabled."""
    policy = _as_dict(packet.get("execution_policy", {}))
    return all(policy.get(flag) is False for flag in FORBIDDEN_EXECUTION_FLAGS)


def context_firewall_is_safe(context_firewall: dict[str, Any]) -> bool:
    """Return true when the top-level context firewall blocks raw context."""
    upward_allowed = _string_list(context_firewall.get("upward_allowed", []))
    upward_forbidden = _string_list(context_firewall.get("upward_forbidden", []))
    return (
        upward_allowed == UPWARD_ALLOWED
        and bool(upward_forbidden)
        and "raw worker logs" not in upward_allowed
    )


def normalized_context_firewall(context_firewall: dict[str, Any]) -> dict[str, list[str]]:
    """Return a safe top-level context firewall for worker-pool output."""
    if context_firewall_is_safe(context_firewall):
        return {
            "upward_allowed": _string_list(context_firewall.get("upward_allowed", [])),
            "upward_forbidden": _string_list(context_firewall.get("upward_forbidden", [])),
        }
    return {
        "upward_allowed": UPWARD_ALLOWED,
        "upward_forbidden": DEFAULT_UPWARD_FORBIDDEN,
    }


def worker_packets_by_role(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index worker packets by role, ignoring malformed items."""
    indexed: dict[str, dict[str, Any]] = {}
    for item in _as_list(packet.get("worker_packets", [])):
        if isinstance(item, dict) and item.get("worker_role"):
            indexed[str(item["worker_role"])] = item
    return indexed


def worker_role_values(packet: dict[str, Any]) -> list[str]:
    """Return every worker_role value from well-formed worker packets."""
    roles: list[str] = []
    for item in _as_list(packet.get("worker_packets", [])):
        if isinstance(item, dict) and item.get("worker_role"):
            roles.append(str(item["worker_role"]))
    return roles


def unexpected_worker_roles(packet: dict[str, Any]) -> list[str]:
    """Return worker roles outside the exact worker-pool contract."""
    return sorted(
        {role for role in worker_role_values(packet) if role not in EXPECTED_WORKER_ROLES}
    )


def duplicate_worker_roles(packet: dict[str, Any]) -> list[str]:
    """Return duplicate worker roles in the supervisor packet."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for role in worker_role_values(packet):
        if role in seen:
            duplicates.add(role)
        seen.add(role)
    return sorted(duplicates)


def missing_worker_roles(packet: dict[str, Any]) -> list[str]:
    """Return expected worker roles absent from the supervisor packet."""
    indexed = worker_packets_by_role(packet)
    return [role for role in EXPECTED_WORKER_ROLES if role not in indexed]


def worker_contract_is_safe(worker_packet: dict[str, Any]) -> bool:
    """Return true when a worker packet has bounded scope and compact output."""
    contract = _as_dict(worker_packet.get("result_contract", {}))
    upward_allowed = _string_list(contract.get("upward_allowed", []))
    upward_forbidden = _string_list(contract.get("upward_forbidden", []))
    worker_role = str(worker_packet.get("worker_role", ""))
    assigned_plan_steps = _as_list(worker_packet.get("assigned_plan_steps", []))
    worker_ready = bool(worker_packet.get("ready", False))
    coder_has_steps = worker_role != "coder" or not worker_ready or (
        bool(assigned_plan_steps)
        and all(
            isinstance(step, dict)
            and str(step.get("id", "")).strip()
            and str(step.get("action", "")).strip()
            for step in assigned_plan_steps
        )
    )
    return (
        bool(_string_list(worker_packet.get("allowed_scope", [])))
        and bool(_string_list(worker_packet.get("forbidden_scope", [])))
        and coder_has_steps
        and bool(str(worker_packet.get("required_output", "")).strip())
        and bool(_string_list(worker_packet.get("validation_commands", [])))
        and upward_allowed == UPWARD_ALLOWED
        and bool(upward_forbidden)
        and "raw worker logs" not in upward_allowed
    )


def all_worker_contracts_safe(packet: dict[str, Any]) -> bool:
    """Return true when all expected worker packets have safe contracts."""
    indexed = worker_packets_by_role(packet)
    return all(worker_contract_is_safe(indexed[role]) for role in EXPECTED_WORKER_ROLES if role in indexed)


def block_reason_for(packet: dict[str, Any]) -> str:
    """Return the worker-pool block reason, or none."""
    current_route = str(packet["current_route"])
    selected_gate = str(packet["selected_gate"])
    if current_route != ACTIVE_ROUTE:
        return "current route is not active v0.3 route"
    if selected_gate == APPROVAL_GATE:
        return "supervisor blocked: user approval required"
    if not selected_gate_is_project_local(selected_gate):
        return "selected gate is outside project-local authority"
    if not execution_policy_is_safe(packet):
        return "unsafe execution policy"
    if not context_firewall_is_safe(_as_dict(packet.get("context_firewall", {}))):
        return "unsafe context firewall"
    unexpected_roles = unexpected_worker_roles(packet)
    if unexpected_roles:
        return "worker packet set invalid: unexpected " + ", ".join(unexpected_roles)
    duplicate_roles = duplicate_worker_roles(packet)
    if duplicate_roles:
        return "worker packet set invalid: duplicate " + ", ".join(duplicate_roles)
    if str(packet["supervisor_status"]) != "ready_for_workers":
        return "supervisor blocked: " + str(packet.get("block_reason", "unknown"))
    if str(packet.get("block_reason", "none")) != "none":
        return "supervisor blocked: " + str(packet["block_reason"])
    missing_roles = missing_worker_roles(packet)
    if missing_roles:
        return "worker packet set incomplete: " + ", ".join(missing_roles)
    if not all_worker_contracts_safe(packet):
        return "unsafe worker contract"
    return "none"


def role_spec_from_worker(worker_packet: dict[str, Any], blocked: bool) -> WorkerRoleSpec:
    """Convert a supervisor worker packet into a normalized role spec."""
    worker_role = str(worker_packet.get("worker_role", "unknown"))
    contract = _as_dict(worker_packet.get("result_contract", {}))
    required_input = "supervisor worker packet only"
    if worker_role in {"coder", "validator"}:
        required_input = "supervisor worker packet with approved assigned_plan_steps only"
    return WorkerRoleSpec(
        worker_role=worker_role,
        ready=bool(worker_packet.get("ready", False)) and not blocked,
        purpose=ROLE_PURPOSES.get(worker_role, "unknown worker role"),
        allowed_scope=_string_list(worker_packet.get("allowed_scope", [])),
        forbidden_scope=_string_list(worker_packet.get("forbidden_scope", [])),
        assigned_plan_steps=[
            dict(step)
            for step in _as_list(worker_packet.get("assigned_plan_steps", []))
            if isinstance(step, dict)
        ],
        required_input=required_input,
        required_output=str(worker_packet.get("required_output", "")),
        validation_commands=_string_list(worker_packet.get("validation_commands", [])),
        result_contract={
            "upward_allowed": _string_list(contract.get("upward_allowed", [])),
            "upward_forbidden": _string_list(contract.get("upward_forbidden", [])),
        },
        execution_limits={flag: False for flag in FORBIDDEN_EXECUTION_FLAGS},
    )


def build_role_specs(packet: dict[str, Any], blocked: bool) -> list[WorkerRoleSpec]:
    """Build role specs in stable worker order."""
    indexed = worker_packets_by_role(packet)
    specs: list[WorkerRoleSpec] = []
    for role in EXPECTED_WORKER_ROLES:
        if role in indexed:
            specs.append(role_spec_from_worker(indexed[role], blocked))
    return specs


def build_worker_pool_packet(packet: dict[str, Any]) -> WorkerPoolPacket:
    """Build worker-pool packet from supervisor output."""
    block_reason = block_reason_for(packet)
    blocked = block_reason != "none"
    context_firewall = _as_dict(packet["context_firewall"])
    return WorkerPoolPacket(
        user_goal=str(packet["user_goal"]),
        task_class=str(packet["task_class"]),
        current_route=str(packet["current_route"]),
        selected_gate=str(packet["selected_gate"]),
        worker_pool_status="blocked" if blocked else "ready_for_worker_execution",
        block_reason=block_reason,
        role_specs=build_role_specs(packet, blocked),
        context_firewall=normalized_context_firewall(context_firewall),
        korean_final_report=bool(packet["korean_final_report"]),
    )


def render_yaml(value: Any, indent: int = 0) -> str:
    """Render a simple YAML form without external dependencies."""
    spaces = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}{key}:")
                lines.append(render_yaml(item, indent + 2))
            else:
                lines.append(f"{spaces}{key}: {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}-")
                lines.append(render_yaml(item, indent + 2))
            else:
                lines.append(f"{spaces}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    return f"{spaces}{json.dumps(value, ensure_ascii=False)}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize worker role specs from a supervisor_packet."
    )
    parser.add_argument(
        "--supervisor-packet-json",
        help="Supervisor packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--supervisor-packet-file", help="Path to supervisor packet JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the worker-pool packet.",
    )
    args = parser.parse_args()

    try:
        supervisor_packet = load_packet(args)
        worker_pool_packet = {
            "worker_pool_packet": asdict(build_worker_pool_packet(supervisor_packet))
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"worker-pool error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(worker_pool_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(worker_pool_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
