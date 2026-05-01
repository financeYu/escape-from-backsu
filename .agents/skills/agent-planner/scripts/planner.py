#!/usr/bin/env python3
"""Build a planner packet from a coordinator packet.

The planner does not execute work. It turns coordinator output into an ordered,
scope-locked plan that must pass plan-review before supervisor or worker
execution begins.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


REQUIRED_COORDINATOR_FIELDS = [
    "user_goal",
    "task_class",
    "current_route",
    "selected_gate",
    "allowed_scope",
    "forbidden_scope",
    "planner_must_output",
    "validation_expectations",
    "context_firewall",
    "korean_final_report",
    "open_questions",
]

DEFAULT_PLAN_REVIEW_CHECKS = [
    "scope lock",
    "hard-stop safety",
    "selected gate compatibility",
    "validation plan completeness",
    "context firewall compliance",
]


@dataclass(frozen=True)
class PlanStep:
    id: str
    role: str
    action: str
    output: str


@dataclass(frozen=True)
class ValidationItem:
    command: str
    purpose: str


@dataclass(frozen=True)
class PlannerPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    plan_status: str
    scope_lock: dict[str, list[str]]
    ordered_plan: list[PlanStep]
    validation_plan: list[ValidationItem]
    context_firewall: dict[str, list[str]]
    plan_review_handoff: dict[str, Any]
    supervisor_handoff: dict[str, Any]
    korean_final_report: bool


def unwrap_coordinator_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"coordinator_packet": packet}."""
    if "coordinator_packet" in raw_packet:
        raw_packet = raw_packet["coordinator_packet"]
    missing = [field for field in REQUIRED_COORDINATOR_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(f"coordinator packet missing required fields: {', '.join(missing)}")
    return raw_packet


def load_packet(args: argparse.Namespace) -> dict[str, Any]:
    """Load a coordinator packet from CLI JSON or a JSON file."""
    if args.coordinator_packet_json:
        if args.coordinator_packet_json == "-":
            return unwrap_coordinator_packet(json.loads(sys.stdin.read()))
        return unwrap_coordinator_packet(json.loads(args.coordinator_packet_json))
    if args.coordinator_packet_file:
        packet_path = Path(args.coordinator_packet_file)
        return unwrap_coordinator_packet(json.loads(packet_path.read_text(encoding="utf-8")))
    raise ValueError("provide --coordinator-packet-json or --coordinator-packet-file")


def is_blocked(packet: dict[str, Any]) -> bool:
    """Return true when coordinator requires approval before planning."""
    selected_gate = str(packet["selected_gate"])
    open_questions = packet.get("open_questions", [])
    return (
        selected_gate == "separate root approval required before gate selection"
        or open_questions != ["none"]
    )


def build_ordered_plan(packet: dict[str, Any]) -> list[PlanStep]:
    """Create bounded planning steps from the coordinator packet."""
    if is_blocked(packet):
        return [
            PlanStep(
                id="P1",
                role="planner",
                action="Stop planning and surface the coordinator approval request.",
                output="approval request for root/user before gate selection",
            )
        ]

    task_class = str(packet["task_class"])
    selected_gate = str(packet["selected_gate"])
    steps = [
        PlanStep(
            id="P1",
            role="planner",
            action="Confirm coordinator goal, task class, selected gate, and scope lock.",
            output="scope-locked planner summary",
        ),
        PlanStep(
            id="P2",
            role="planner",
            action="Map the task to the selected compatibility gate without replacing it.",
            output=f"compatibility handoff for {selected_gate}",
        ),
        PlanStep(
            id="P3",
            role="planner",
            action="Prepare validation expectations and context firewall rules for plan-review.",
            output="validation and context-firewall handoff",
        ),
    ]
    if task_class == "narrow edit":
        steps.append(
            PlanStep(
                id="P4",
                role="supervisor",
                action="After plan-review approval, assign implementation only inside the locked scope.",
                output="bounded supervisor work packet",
            )
        )
    elif task_class == "Step/gate closure":
        steps.append(
            PlanStep(
                id="P4",
                role="plan-review",
                action="Check closure evidence before any supervisor handoff.",
                output="closure readiness decision",
            )
        )
    else:
        steps.append(
            PlanStep(
                id="P4",
                role="plan-review",
                action="Review the plan for route alignment before any execution.",
                output="planning-only review decision",
            )
        )
    return steps


def build_validation_plan(packet: dict[str, Any]) -> list[ValidationItem]:
    """Convert coordinator validation expectations into planner items."""
    items: list[ValidationItem] = []
    for command in packet.get("validation_expectations", []):
        purpose = "confirm the selected gate and planned scope remain valid"
        if command == "git diff --check":
            purpose = "catch whitespace or patch formatting issues"
        elif "not_applicable" in command:
            purpose = "record why execution validation is not yet applicable"
        items.append(ValidationItem(command=command, purpose=purpose))
    if not items:
        items.append(
            ValidationItem(
                command="not_applicable",
                purpose="coordinator packet did not request validation commands",
            )
        )
    return items


def build_planner_packet(packet: dict[str, Any]) -> PlannerPacket:
    """Build the plan-review-facing planner packet."""
    blocked = is_blocked(packet)
    approval_question = "none"
    if blocked:
        approval_question = "; ".join(str(item) for item in packet.get("open_questions", []))
    return PlannerPacket(
        user_goal=str(packet["user_goal"]),
        task_class=str(packet["task_class"]),
        current_route=str(packet["current_route"]),
        selected_gate=str(packet["selected_gate"]),
        plan_status="blocked" if blocked else "ready_for_plan_review",
        scope_lock={
            "allowed": list(packet["allowed_scope"]),
            "forbidden": list(packet["forbidden_scope"]),
        },
        ordered_plan=build_ordered_plan(packet),
        validation_plan=build_validation_plan(packet),
        context_firewall=dict(packet["context_firewall"]),
        plan_review_handoff={
            "required_checks": DEFAULT_PLAN_REVIEW_CHECKS,
            "approval_question": approval_question,
        },
        supervisor_handoff={
            "ready": False,
            "reason": "blocked by coordinator approval request"
            if blocked
            else "waiting for plan-review decision",
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
        description="Build a planner_packet from a coordinator_packet."
    )
    parser.add_argument(
        "--coordinator-packet-json",
        help="Coordinator packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--coordinator-packet-file", help="Path to coordinator packet JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the planner packet.",
    )
    args = parser.parse_args()

    try:
        coordinator_packet = load_packet(args)
        planner_packet = {
            "planner_packet": asdict(build_planner_packet(coordinator_packet))
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"planner error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(planner_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(planner_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
