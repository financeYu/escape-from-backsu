#!/usr/bin/env python3
"""Build supervisor worker packets from an approved plan-review packet.

The supervisor does not execute workers. It prepares bounded worker packets only
after plan-review approval opens the supervisor handoff. Worker execution order
is coder -> tracker -> validator -> tracker -> reporter. Reporter owns
worker-result collection for supervisor/user reporting.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_PLAN_REVIEW_FIELDS = [
    "user_goal",
    "task_class",
    "current_route",
    "selected_gate",
    "scope_lock",
    "ordered_plan",
    "validation_plan",
    "review_status",
    "user_approval",
    "supervisor_handoff",
    "planner_feedback",
    "context_firewall",
    "korean_final_report",
]

ACTIVE_ROUTE = "post-MVP v0.3 research-to-strategy adoption route"
PROJECT_LOCAL_GATE_PREFIX = ".agents/skills/"
APPROVAL_GATE = "separate root approval required before gate selection"
WORKER_ROLES = ["coder", "tracker", "validator", "reporter"]
UPWARD_ALLOWED = ["status", "changed_scope", "evidence", "next_request"]


@dataclass(frozen=True)
class WorkerPacket:
    worker_role: str
    ready: bool
    allowed_scope: list[str]
    forbidden_scope: list[str]
    assigned_plan_steps: list[dict[str, str]]
    required_output: str
    validation_commands: list[str]
    result_contract: dict[str, list[str]]


@dataclass(frozen=True)
class SupervisorPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    supervisor_status: str
    block_reason: str
    execution_policy: dict[str, bool]
    worker_packets: list[WorkerPacket]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool


def unwrap_plan_review_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"plan_review_packet": packet}."""
    if "plan_review_packet" in raw_packet:
        raw_packet = raw_packet["plan_review_packet"]
    missing = [field for field in REQUIRED_PLAN_REVIEW_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(
            f"plan-review packet missing required fields: {', '.join(missing)}"
        )
    return raw_packet


def load_packet(args: argparse.Namespace) -> dict[str, Any]:
    """Load a plan-review packet from CLI JSON or a JSON file."""
    if args.plan_review_packet_json:
        if args.plan_review_packet_json == "-":
            return unwrap_plan_review_packet(json.loads(sys.stdin.read()))
        return unwrap_plan_review_packet(json.loads(args.plan_review_packet_json))
    if args.plan_review_packet_file:
        packet_path = Path(args.plan_review_packet_file)
        return unwrap_plan_review_packet(json.loads(packet_path.read_text(encoding="utf-8")))
    raise ValueError("provide --plan-review-packet-json or --plan-review-packet-file")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value)]


def _scope_values(packet: dict[str, Any], key: str) -> list[str]:
    return _string_list(_as_dict(packet.get("scope_lock", {})).get(key, []))


def _validation_commands(packet: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for item in _as_list(packet.get("validation_plan", [])):
        if isinstance(item, dict) and item.get("command"):
            commands.append(str(item["command"]))
    return commands or ["not_applicable until worker validation is assigned"]


def _ordered_plan(packet: dict[str, Any]) -> list[dict[str, str]]:
    """Return approved planner steps preserved by plan-review."""
    steps: list[dict[str, str]] = []
    for item in _as_list(packet.get("ordered_plan", [])):
        if isinstance(item, dict):
            steps.append(
                {
                    "id": str(item.get("id", "")),
                    "role": str(item.get("role", "")),
                    "action": str(item.get("action", "")),
                    "output": str(item.get("output", "")),
                }
            )
    return steps


def selected_gate_is_project_local(selected_gate: str) -> bool:
    """Return true for project-local skill gates only."""
    return selected_gate.startswith(PROJECT_LOCAL_GATE_PREFIX) and selected_gate.endswith(
        "/SKILL.md"
    )


def user_approval_required(packet: dict[str, Any]) -> bool:
    """Return true when plan-review says user/root approval is required."""
    return bool(_as_dict(packet.get("user_approval", {})).get("required", False))


def supervisor_handoff_ready(packet: dict[str, Any]) -> bool:
    """Return true when plan-review opened the supervisor handoff."""
    return bool(_as_dict(packet.get("supervisor_handoff", {})).get("ready", False))


def block_reason_for(packet: dict[str, Any]) -> str:
    """Return the reason supervisor must block, or none."""
    current_route = str(packet["current_route"])
    selected_gate = str(packet["selected_gate"])
    if current_route != ACTIVE_ROUTE:
        return "current route is not active v0.3 route"
    if selected_gate == APPROVAL_GATE:
        return "user approval required"
    if not selected_gate_is_project_local(selected_gate):
        return "selected gate is outside project-local authority"
    if user_approval_required(packet):
        return "user approval required"
    if str(packet["review_status"]) != "approved_for_supervisor":
        return "plan-review not approved"
    if not supervisor_handoff_ready(packet):
        return "supervisor handoff not ready"
    if str(packet["task_class"]) == "planning/read-only":
        return "planning/read-only does not open worker execution"
    if not _scope_values(packet, "allowed") or not _scope_values(packet, "forbidden"):
        return "scope lock missing"
    return "none"


def result_contract(context_firewall: dict[str, Any]) -> dict[str, list[str]]:
    """Build the compact worker result contract."""
    upward_forbidden = _string_list(context_firewall.get("upward_forbidden", []))
    return {
        "upward_allowed": UPWARD_ALLOWED,
        "upward_forbidden": upward_forbidden,
    }


def build_worker_packets(packet: dict[str, Any], ready: bool) -> list[WorkerPacket]:
    """Create bounded worker packets without executing them."""
    allowed = _scope_values(packet, "allowed")
    forbidden = _scope_values(packet, "forbidden")
    commands = _validation_commands(packet)
    assigned_plan_steps = _ordered_plan(packet)
    contract = result_contract(_as_dict(packet.get("context_firewall", {})))

    return [
        WorkerPacket(
            worker_role="coder",
            ready=ready,
            allowed_scope=allowed,
            forbidden_scope=forbidden,
            assigned_plan_steps=assigned_plan_steps if ready else [],
            required_output="implementation summary, changed_scope, and completed assigned_plan_steps only"
            if ready
            else "not_applicable for blocked supervisor packet",
            validation_commands=["not_applicable for coder"],
            result_contract=contract,
        ),
        WorkerPacket(
            worker_role="tracker",
            ready=ready,
            allowed_scope=allowed,
            forbidden_scope=forbidden,
            assigned_plan_steps=assigned_plan_steps if ready else [],
            required_output=(
                "coder completion tracking, validation-stage handoff, "
                "validator completion tracking, and next_request"
            ),
            validation_commands=["not_applicable for tracker"],
            result_contract=contract,
        ),
        WorkerPacket(
            worker_role="validator",
            ready=ready,
            allowed_scope=allowed,
            forbidden_scope=forbidden,
            assigned_plan_steps=assigned_plan_steps if ready else [],
            required_output=(
                "validation evidence for coder output, project direction, "
                "hard-stop safety, scope lock, and assigned_plan_steps only; "
                "no final acceptance"
            ),
            validation_commands=commands,
            result_contract=contract,
        ),
        WorkerPacket(
            worker_role="reporter",
            ready=ready,
            allowed_scope=allowed,
            forbidden_scope=forbidden,
            assigned_plan_steps=[],
            required_output=(
                "collect approved worker_result summaries and draft compact "
                "Korean supervisor/user report only"
            ),
            validation_commands=["not_applicable for reporter"],
            result_contract=contract,
        ),
    ]


def build_supervisor_packet(packet: dict[str, Any]) -> SupervisorPacket:
    """Build worker-facing supervisor packet from plan-review output."""
    block_reason = block_reason_for(packet)
    ready = block_reason == "none"
    context_firewall = _as_dict(packet["context_firewall"])
    return SupervisorPacket(
        user_goal=str(packet["user_goal"]),
        task_class=str(packet["task_class"]),
        current_route=str(packet["current_route"]),
        selected_gate=str(packet["selected_gate"]),
        supervisor_status="ready_for_workers" if ready else "blocked",
        block_reason=block_reason,
        execution_policy={
            "fetch": False,
            "pull": False,
            "push": False,
            "commit": False,
            "stage": False,
        },
        worker_packets=build_worker_packets(packet, ready),
        context_firewall={
            "upward_allowed": _string_list(context_firewall.get("upward_allowed", [])),
            "upward_forbidden": _string_list(context_firewall.get("upward_forbidden", [])),
        },
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
        description="Build supervisor worker packets from a plan_review_packet."
    )
    parser.add_argument(
        "--plan-review-packet-json",
        help="Plan-review packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--plan-review-packet-file", help="Path to plan-review packet JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the supervisor packet.",
    )
    args = parser.parse_args()

    try:
        plan_review_packet = load_packet(args)
        supervisor_packet = {
            "supervisor_packet": asdict(build_supervisor_packet(plan_review_packet))
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"supervisor error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(supervisor_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(supervisor_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
