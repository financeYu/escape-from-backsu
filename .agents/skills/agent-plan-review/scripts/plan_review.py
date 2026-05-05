#!/usr/bin/env python3
"""Review a planner packet before supervisor execution.

Plan Review does not execute work. It checks the planner output and either
approves a supervisor handoff, asks the planner for fixes, or requires separate
user/root approval for guarded boundaries.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_PLANNER_FIELDS = [
    "user_goal",
    "task_class",
    "current_route",
    "selected_gate",
    "plan_status",
    "scope_lock",
    "ordered_plan",
    "validation_plan",
    "context_firewall",
    "plan_review_handoff",
    "supervisor_handoff",
    "korean_final_report",
]

RESOURCE_USAGE_PROFILE = {
    "coordinator": "medium",
    "planner": "xhigh",
    "plan_review": "high",
    "supervisor": "xhigh",
    "coder": "medium",
    "validator": "medium",
    "reporter": "low",
    "tracker": "low",
}

ACTIVE_ROUTE = "post-MVP v0.3 research-to-strategy adoption route"
PROJECT_LOCAL_GATE_PREFIX = ".agents/skills/"
APPROVAL_GATE = "separate root approval required before gate selection"

REQUIRED_HARD_STOP_CATEGORIES = {
    "live trading/order execution": [
        "live trading",
        "brokerage integration",
        "order generation",
        "real-money execution",
    ],
    "production activation": ["production activation"],
    "universe/data-ingestion expansion": [
        "universe expansion",
        "data-ingestion expansion",
        "data ingestion expansion",
    ],
    "valuation/fundamental activation": [
        "valuation/fundamental scoring activation",
        "valuation activation",
        "fundamental scoring activation",
    ],
}

REQUIRED_UPWARD_ALLOWED = {"status", "changed_scope", "evidence", "next_request"}


@dataclass(frozen=True)
class ReviewItem:
    id: str
    check: str
    passed: bool
    message: str
    required_fix: str


@dataclass(frozen=True)
class PlanReviewPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    resource_usage_profile: dict[str, str]
    scope_lock: dict[str, list[str]]
    ordered_plan: list[dict[str, str]]
    validation_plan: list[dict[str, str]]
    revision_context: dict[str, Any]
    review_status: str
    checklist: list[ReviewItem]
    user_approval: dict[str, Any]
    supervisor_handoff: dict[str, Any]
    planner_feedback: dict[str, Any]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool


def unwrap_planner_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"planner_packet": packet}."""
    if "planner_packet" in raw_packet:
        raw_packet = raw_packet["planner_packet"]
    missing = [field for field in REQUIRED_PLANNER_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(f"planner packet missing required fields: {', '.join(missing)}")
    return raw_packet


def load_packet(args: argparse.Namespace) -> dict[str, Any]:
    """Load a planner packet from CLI JSON or a JSON file."""
    if args.planner_packet_json:
        if args.planner_packet_json == "-":
            return unwrap_planner_packet(json.loads(sys.stdin.read()))
        return unwrap_planner_packet(json.loads(args.planner_packet_json))
    if args.planner_packet_file:
        packet_path = Path(args.planner_packet_file)
        return unwrap_planner_packet(json.loads(packet_path.read_text(encoding="utf-8")))
    raise ValueError("provide --planner-packet-json or --planner-packet-file")


def unwrap_previous_plan_review_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the previous packet itself or {"plan_review_packet": packet}."""
    if "plan_review_packet" in raw_packet:
        raw_packet = raw_packet["plan_review_packet"]
    return raw_packet


def load_previous_review(args: argparse.Namespace) -> dict[str, Any] | None:
    """Load an optional previous plan-review packet for revised-plan approval checks."""
    if args.previous_plan_review_packet_json:
        if args.previous_plan_review_packet_json == "-":
            raise ValueError("previous plan-review packet cannot also read stdin")
        return unwrap_previous_plan_review_packet(
            json.loads(args.previous_plan_review_packet_json)
        )
    if args.previous_plan_review_packet_file:
        packet_path = Path(args.previous_plan_review_packet_file)
        return unwrap_previous_plan_review_packet(
            json.loads(packet_path.read_text(encoding="utf-8"))
        )
    return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value)]


def _scope_values(packet: dict[str, Any], key: str) -> list[str]:
    scope_lock = packet.get("scope_lock", {})
    if not isinstance(scope_lock, dict):
        return []
    return _string_list(scope_lock.get(key, []))


def _context_values(packet: dict[str, Any], key: str) -> list[str]:
    context_firewall = packet.get("context_firewall", {})
    if not isinstance(context_firewall, dict):
        return []
    return _string_list(context_firewall.get(key, []))


def _approval_question(packet: dict[str, Any]) -> str:
    handoff = packet.get("plan_review_handoff", {})
    if not isinstance(handoff, dict):
        return ""
    return str(handoff.get("approval_question", ""))


def _planner_supervisor_ready(packet: dict[str, Any]) -> bool:
    handoff = packet.get("supervisor_handoff", {})
    if not isinstance(handoff, dict):
        return False
    return bool(handoff.get("ready", False))


def _revision_context(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("revision_context", {})
    return context if isinstance(context, dict) else {}


def _revision_user_approval_ack(packet: dict[str, Any]) -> bool:
    """Return true when the revised plan carries explicit user/root approval."""
    revision_context = _revision_context(packet)
    if bool(revision_context.get("user_approval_ack", False)):
        return True
    handoff = packet.get("plan_review_handoff", {})
    if isinstance(handoff, dict) and bool(handoff.get("user_approval_ack", False)):
        return True
    return False


def _planner_marks_revised_after_fix(packet: dict[str, Any]) -> bool:
    """Return true when the planner says this packet revises a failed review."""
    revision_context = _revision_context(packet)
    if bool(revision_context.get("revised_after_review_fix", False)):
        return True
    handoff = packet.get("plan_review_handoff", {})
    if isinstance(handoff, dict) and bool(handoff.get("revised_after_review_fix", False)):
        return True
    return False


def previous_review_requires_user_approval(
    previous_review: dict[str, Any] | None,
) -> bool:
    """Return true when the previous review said fixes require user approval."""
    if not previous_review:
        return False
    user_approval = previous_review.get("user_approval", {})
    if not isinstance(user_approval, dict):
        return False
    return bool(user_approval.get("required_after_planner_fix", False))


def revised_plan_needs_user_approval(
    packet: dict[str, Any],
    previous_review: dict[str, Any] | None,
) -> bool:
    """Return true when a fixed/revised plan cannot proceed without user approval."""
    if _revision_user_approval_ack(packet):
        return False
    return previous_review_requires_user_approval(
        previous_review
    ) or _planner_marks_revised_after_fix(packet)


def selected_gate_is_project_local(selected_gate: str) -> bool:
    """Return true for project-local skill gates only."""
    return selected_gate.startswith(PROJECT_LOCAL_GATE_PREFIX) and selected_gate.endswith(
        "/SKILL.md"
    )


def missing_hard_stop_categories(forbidden_text: str) -> list[str]:
    """Return required hard-stop categories absent from forbidden scope."""
    missing: list[str] = []
    for category, markers in REQUIRED_HARD_STOP_CATEGORIES.items():
        if not any(marker in forbidden_text for marker in markers):
            missing.append(category)
    return missing


def requires_separate_approval(
    packet: dict[str, Any], previous_review: dict[str, Any] | None = None
) -> bool:
    """Return true when the plan already names a separate approval boundary."""
    if requires_guarded_boundary_approval(packet):
        return True
    if revised_plan_needs_user_approval(packet, previous_review):
        return not _revision_user_approval_ack(packet)
    return False


def requires_guarded_boundary_approval(packet: dict[str, Any]) -> bool:
    """Return true when the plan names a hard-stop or out-of-scope approval."""
    selected_gate = str(packet["selected_gate"])
    approval_question = _approval_question(packet).lower()
    if selected_gate == "separate root approval required before gate selection":
        return True
    if approval_question and approval_question != "none":
        return True
    if str(packet["plan_status"]) == "blocked" and "approval" in approval_question:
        return True
    return False


def build_checklist(packet: dict[str, Any]) -> list[ReviewItem]:
    """Review the planner packet and return pass/fail checklist items."""
    allowed = _scope_values(packet, "allowed")
    forbidden = _scope_values(packet, "forbidden")
    validation_plan = _as_list(packet.get("validation_plan", []))
    ordered_plan = _as_list(packet.get("ordered_plan", []))
    upward_allowed = set(_context_values(packet, "upward_allowed"))
    upward_forbidden = _context_values(packet, "upward_forbidden")
    forbidden_text = " ".join(forbidden).lower()
    current_route = str(packet["current_route"]).strip()
    selected_gate = str(packet["selected_gate"]).strip()
    plan_status = str(packet["plan_status"]).strip()
    route_aligned = current_route == ACTIVE_ROUTE
    gate_aligned = selected_gate == APPROVAL_GATE or selected_gate_is_project_local(
        selected_gate
    )
    missing_hard_stops = missing_hard_stop_categories(forbidden_text)

    checklist = [
        ReviewItem(
            id="R1",
            check="current route is active v0.3 route",
            passed=route_aligned,
            message="current_route matches active route"
            if route_aligned
            else f"current_route is not active route: {current_route or '<missing>'}",
            required_fix="none"
            if route_aligned
            else f"Set current_route to {ACTIVE_ROUTE!r}.",
        ),
        ReviewItem(
            id="R2",
            check="selected gate is project-local or approval blocker",
            passed=gate_aligned,
            message="selected_gate is project-local or approval blocker"
            if gate_aligned
            else f"selected_gate is outside project-local authority: {selected_gate or '<missing>'}",
            required_fix="none"
            if gate_aligned
            else "Use a project-local .agents/skills/*/SKILL.md gate or the separate approval blocker.",
        ),
        ReviewItem(
            id="R3",
            check="scope lock has allowed and forbidden boundaries",
            passed=bool(allowed) and bool(forbidden),
            message="scope lock contains allowed and forbidden boundaries"
            if allowed and forbidden
            else "scope lock is incomplete",
            required_fix="none"
            if allowed and forbidden
            else "Add explicit scope_lock.allowed and scope_lock.forbidden entries.",
        ),
        ReviewItem(
            id="R4",
            check="all required hard-stop categories remain forbidden",
            passed=not missing_hard_stops,
            message="all required hard-stop categories are represented in forbidden scope"
            if not missing_hard_stops
            else "missing hard-stop categories: " + ", ".join(missing_hard_stops),
            required_fix="none"
            if not missing_hard_stops
            else "Carry every required hard-stop category into scope_lock.forbidden.",
        ),
        ReviewItem(
            id="R5",
            check="ordered plan exists",
            passed=bool(ordered_plan),
            message="ordered plan is present" if ordered_plan else "ordered plan is missing",
            required_fix="none" if ordered_plan else "Add ordered_plan steps before review.",
        ),
        ReviewItem(
            id="R6",
            check="validation plan exists",
            passed=bool(validation_plan),
            message="validation plan is present"
            if validation_plan
            else "validation plan is missing",
            required_fix="none" if validation_plan else "Add validation_plan entries.",
        ),
        ReviewItem(
            id="R7",
            check="context firewall preserves compact upward fields",
            passed=REQUIRED_UPWARD_ALLOWED.issubset(upward_allowed)
            and bool(upward_forbidden),
            message="context firewall allows only compact upward summaries"
            if REQUIRED_UPWARD_ALLOWED.issubset(upward_allowed) and upward_forbidden
            else "context firewall is incomplete",
            required_fix="none"
            if REQUIRED_UPWARD_ALLOWED.issubset(upward_allowed) and upward_forbidden
            else "Preserve upward_allowed status/changed_scope/evidence/next_request and upward_forbidden entries.",
        ),
        ReviewItem(
            id="R8",
            check="planner did not pre-approve supervisor execution",
            passed=_planner_supervisor_ready(packet) is False,
            message="planner left supervisor handoff blocked for plan-review"
            if _planner_supervisor_ready(packet) is False
            else "planner marked supervisor handoff ready before review",
            required_fix="none"
            if _planner_supervisor_ready(packet) is False
            else "Planner supervisor_handoff.ready must remain false before plan-review.",
        ),
        ReviewItem(
            id="R9",
            check="plan status is reviewable",
            passed=plan_status in {"ready_for_plan_review", "blocked"},
            message=f"plan_status is {plan_status}"
            if plan_status in {"ready_for_plan_review", "blocked"}
            else f"unsupported plan_status {plan_status}",
            required_fix="none"
            if plan_status in {"ready_for_plan_review", "blocked"}
            else "Use plan_status ready_for_plan_review or blocked.",
        ),
    ]
    return checklist


def review_status_for(
    packet: dict[str, Any],
    checklist: list[ReviewItem],
    previous_review: dict[str, Any] | None = None,
) -> str:
    """Derive the review status from checklist and approval triggers."""
    if requires_guarded_boundary_approval(packet):
        return "separate_approval_required"
    if str(packet["plan_status"]) == "blocked":
        return "blocked"
    if any(not item.passed for item in checklist):
        return "needs_planner_fix"
    if revised_plan_needs_user_approval(packet, previous_review):
        return "separate_approval_required"
    return "approved_for_supervisor"


def build_plan_review_packet(
    packet: dict[str, Any], previous_review: dict[str, Any] | None = None
) -> PlanReviewPacket:
    """Build the supervisor-facing or planner-feedback plan-review packet."""
    checklist = build_checklist(packet)
    resource_usage_profile = packet.get("resource_usage_profile", RESOURCE_USAGE_PROFILE)
    review_status = review_status_for(packet, checklist, previous_review)
    failed_items = [item for item in checklist if not item.passed]
    planner_fixes = [item.required_fix for item in failed_items if item.required_fix != "none"]

    separate_approval = review_status == "separate_approval_required"
    review_fix = review_status == "needs_planner_fix"
    user_approval_required = separate_approval
    user_approval_reason = "none"
    if separate_approval:
        if revised_plan_needs_user_approval(packet, previous_review):
            user_approval_reason = "review_fix_required_after_plan_change"
        else:
            user_approval_reason = "separate approval required"
    elif review_fix:
        user_approval_reason = "review_fix_required_after_plan_change"

    supervisor_ready = review_status == "approved_for_supervisor"
    supervisor_reason = "review passed; no user approval trigger"
    if separate_approval:
        supervisor_reason = "separate approval required"
    elif review_fix:
        supervisor_reason = "blocked by review findings"
    elif review_status == "blocked":
        supervisor_reason = "blocked by planner packet"

    return PlanReviewPacket(
        user_goal=str(packet["user_goal"]),
        task_class=str(packet["task_class"]),
        current_route=str(packet["current_route"]),
        selected_gate=str(packet["selected_gate"]),
        resource_usage_profile=dict(resource_usage_profile),
        scope_lock={
            "allowed": _scope_values(packet, "allowed"),
            "forbidden": _scope_values(packet, "forbidden"),
        },
        ordered_plan=[
            dict(item) for item in packet["ordered_plan"] if isinstance(item, dict)
        ],
        validation_plan=[
            dict(item) for item in packet["validation_plan"] if isinstance(item, dict)
        ],
        revision_context={
            "revised_after_review_fix": bool(
                previous_review_requires_user_approval(previous_review)
                or _planner_marks_revised_after_fix(packet)
            ),
            "user_approval_ack": _revision_user_approval_ack(packet),
            "previous_review_required_user_approval": previous_review_requires_user_approval(
                previous_review
            ),
        },
        review_status=review_status,
        checklist=checklist,
        user_approval={
            "required": user_approval_required,
            "reason": user_approval_reason,
            "required_after_planner_fix": review_fix,
        },
        supervisor_handoff={
            "ready": supervisor_ready,
            "reason": supervisor_reason,
        },
        planner_feedback={
            "required": bool(planner_fixes) or review_status == "blocked",
            "fixes": planner_fixes if planner_fixes else ["none"],
        },
        context_firewall=dict(packet["context_firewall"]),
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
        description="Review a planner_packet before supervisor execution."
    )
    parser.add_argument(
        "--planner-packet-json",
        help="Planner packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--planner-packet-file", help="Path to planner packet JSON.")
    parser.add_argument(
        "--previous-plan-review-packet-json",
        help=(
            "Previous plan-review packet JSON. When it required approval after "
            "planner fixes, the revised planner packet must carry user_approval_ack."
        ),
    )
    parser.add_argument(
        "--previous-plan-review-packet-file",
        help="Path to the previous plan-review packet JSON.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the plan-review packet.",
    )
    args = parser.parse_args()

    try:
        planner_packet = load_packet(args)
        previous_review = load_previous_review(args)
        plan_review_packet = {
            "plan_review_packet": asdict(
                build_plan_review_packet(planner_packet, previous_review)
            )
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"plan-review error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(plan_review_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(plan_review_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
