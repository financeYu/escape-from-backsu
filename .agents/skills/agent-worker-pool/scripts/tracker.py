#!/usr/bin/env python3
"""Track worker-pool stage transitions without leaking worker context.

The tracker is a supervisor-owned worker-pool tool. It records compact worker
completion events and advances the workflow order:

coder complete -> validation required -> validator complete -> reporter ready.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_WORKER_POOL_FIELDS = [
    "user_goal",
    "task_class",
    "current_route",
    "selected_gate",
    "worker_pool_status",
    "block_reason",
    "role_specs",
    "context_firewall",
    "korean_final_report",
]

ACTIVE_ROUTE = "post-MVP v0.3 research-to-strategy adoption route"
VALID_RESULT_STATUSES = {"complete", "partial", "failed", "blocked"}
TRACKER_EVENTS = {"coder_completed", "validator_completed"}
UPWARD_ALLOWED = ["status", "changed_scope", "evidence", "next_request"]
UPWARD_FORBIDDEN = [
    "raw worker logs",
    "full exploratory notes",
    "generated output dumps",
    "archive or raw-data context",
    "long private reasoning",
]
FORBIDDEN_RESULT_KEYS = {
    "raw_logs",
    "raw_log",
    "logs",
    "raw_context",
    "full_exploratory_notes",
    "exploratory_notes",
    "private_reasoning",
    "reasoning",
    "generated_output_dump",
    "generated_output_dumps",
    "archive_context",
    "raw_data_context",
}
FORBIDDEN_MARKERS = [
    "live trading",
    "brokerage integration",
    "order generation",
    "real-money execution",
    "production activation",
    "universe expansion",
    "data-ingestion expansion",
    "data ingestion expansion",
    "valuation/fundamental scoring activation",
    "valuation activation",
    "fundamental scoring activation",
    "raw worker logs",
    "generated output dumps",
    "archive or raw-data context",
    "raw_context",
    "raw_logs",
    "private_reasoning",
]


@dataclass(frozen=True)
class TrackerPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    tracker_status: str
    block_reason: str
    workflow_state: dict[str, str]
    worker_result: dict[str, Any]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool


def unwrap_worker_pool_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"worker_pool_packet": packet}."""
    if not isinstance(raw_packet, dict):
        raise ValueError("worker-pool packet must be an object")
    if "worker_pool_packet" in raw_packet:
        raw_packet = raw_packet["worker_pool_packet"]
    missing = [field for field in REQUIRED_WORKER_POOL_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(
            f"worker-pool packet missing required fields: {', '.join(missing)}"
        )
    return raw_packet


def unwrap_worker_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    """Accept a worker result or common packet wrappers around it."""
    if not isinstance(raw_result, dict):
        raise ValueError("worker result must be an object")
    if "worker_result" in raw_result:
        raw_result = raw_result["worker_result"]
    if "coder_result" in raw_result:
        raw_result = raw_result["coder_result"]
    if "coder_packet" in raw_result:
        raw_result = raw_result["coder_packet"].get("worker_result", {})
    if "validator_packet" in raw_result:
        raw_result = raw_result["validator_packet"].get("worker_result", {})
    if not isinstance(raw_result, dict):
        raise ValueError("worker result must be an object")
    return raw_result


def unwrap_tracker_state(raw_state: dict[str, Any] | None) -> dict[str, str]:
    """Accept a workflow_state object or a previous tracker_packet wrapper."""
    if raw_state is None:
        return {}
    if "tracker_packet" in raw_state:
        raw_state = raw_state["tracker_packet"]
    if "workflow_state" in raw_state:
        raw_state = raw_state["workflow_state"]
    if not isinstance(raw_state, dict):
        raise ValueError("tracker state must be an object")
    return {str(key): str(value) for key, value in raw_state.items()}


def load_json_arg(value: str | None, file_value: str | None, stdin_allowed: bool) -> Any:
    """Load JSON from a CLI argument, stdin marker, or file."""
    if value:
        if value == "-":
            if not stdin_allowed:
                raise ValueError("stdin can be used for only one input")
            return json.loads(sys.stdin.read())
        return json.loads(value)
    if file_value:
        return json.loads(Path(file_value).read_text(encoding="utf-8-sig"))
    return None


def load_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Load worker-pool packet, worker result, and optional tracker state."""
    packet_uses_stdin = args.worker_pool_packet_json == "-"
    result_uses_stdin = args.worker_result_json == "-"
    state_uses_stdin = args.tracker_state_json == "-"
    if sum([packet_uses_stdin, result_uses_stdin, state_uses_stdin]) > 1:
        raise ValueError("only one input may read from stdin")
    raw_packet = load_json_arg(
        args.worker_pool_packet_json,
        args.worker_pool_packet_file,
        stdin_allowed=not result_uses_stdin and not state_uses_stdin,
    )
    raw_result = load_json_arg(
        args.worker_result_json,
        args.worker_result_file,
        stdin_allowed=not packet_uses_stdin and not state_uses_stdin,
    )
    if raw_packet is None:
        raise ValueError("provide --worker-pool-packet-json or --worker-pool-packet-file")
    if raw_result is None:
        raise ValueError("provide --worker-result-json or --worker-result-file")
    worker_pool_packet = unwrap_worker_pool_packet(raw_packet)
    worker_result = unwrap_worker_result(raw_result)
    tracker_state = unwrap_tracker_state(
        load_json_arg(
            args.tracker_state_json,
            args.tracker_state_file,
            stdin_allowed=not packet_uses_stdin and not result_uses_stdin,
        )
    )
    return worker_pool_packet, worker_result, tracker_state


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def context_firewall() -> dict[str, list[str]]:
    """Return the tracker's fixed upward context firewall."""
    return {
        "upward_allowed": UPWARD_ALLOWED,
        "upward_forbidden": UPWARD_FORBIDDEN,
    }


def role_spec(packet: dict[str, Any], worker_role: str) -> dict[str, Any]:
    """Return a worker role spec or an empty dict."""
    for item in _as_list(packet.get("role_specs", [])):
        if isinstance(item, dict) and item.get("worker_role") == worker_role:
            return item
    return {}


def role_is_ready(packet: dict[str, Any], worker_role: str) -> bool:
    """Return true when the requested worker role is ready."""
    return role_spec(packet, worker_role).get("ready") is True


def contains_forbidden_context(value: Any) -> bool:
    """Return true when raw or unauthorized worker context is present."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in FORBIDDEN_RESULT_KEYS:
                return True
            if contains_forbidden_context(item):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_context(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in FORBIDDEN_MARKERS)
    return False


def base_workflow_state() -> dict[str, str]:
    """Return the initial compact workflow state."""
    return {
        "coder": "pending",
        "tracker": "pending",
        "validator": "pending",
        "reporter": "pending",
        "next_worker": "coder",
        "next_request": "await coder completion",
    }


def invalid_packet_reason(packet: dict[str, Any], event: str) -> str:
    """Return a packet-level block reason, or none."""
    if event not in TRACKER_EVENTS:
        return "invalid tracker event"
    if str(packet["worker_pool_status"]) != "ready_for_worker_execution":
        return "worker pool blocked: " + str(packet["block_reason"])
    if str(packet["current_route"]) != ACTIVE_ROUTE:
        return "current route is not active v0.3 route"
    if not role_is_ready(packet, "tracker"):
        return "tracker role is not ready"
    if event == "coder_completed" and (
        not role_is_ready(packet, "coder") or not role_is_ready(packet, "validator")
    ):
        return "coder or validator role is not ready"
    if event == "validator_completed" and (
        not role_is_ready(packet, "validator") or not role_is_ready(packet, "reporter")
    ):
        return "validator or reporter role is not ready"
    return "none"


def validate_worker_result(worker_result: dict[str, Any], expected_role: str) -> str:
    """Return a worker-result block reason, or none."""
    if contains_forbidden_context(worker_result):
        return "unauthorized worker context or hard-stop marker"
    if str(worker_result.get("worker_role", "")) != expected_role:
        return f"worker_result worker_role must be {expected_role}"
    if str(worker_result.get("status", "")) not in VALID_RESULT_STATUSES:
        return "worker_result status is invalid"
    if not _string_list(worker_result.get("changed_scope", [])):
        return "worker_result missing changed_scope"
    if not _string_list(worker_result.get("evidence", [])):
        return "worker_result missing evidence"
    return "none"


def state_for_coder_event(
    worker_result: dict[str, Any],
) -> tuple[str, str, dict[str, str]]:
    """Track coder completion and advance to validation when complete."""
    status = str(worker_result.get("status", ""))
    state = base_workflow_state()
    state["tracker"] = "complete"
    if status == "complete":
        state.update(
            {
                "coder": "complete",
                "validator": "pending",
                "reporter": "pending",
                "next_worker": "validator",
                "next_request": "run validator on coder_result before reporting",
            }
        )
        return "validation_required", "none", state
    state.update(
        {
            "coder": status or "blocked",
            "validator": "blocked",
            "reporter": "blocked",
            "next_worker": "coder",
            "next_request": "return to coder before validation",
        }
    )
    return "needs_coder_fix", "coder result is not complete", state


def prior_state_allows_validator(tracker_state: dict[str, str]) -> bool:
    """Return true when validator completion follows tracked coder completion."""
    return (
        tracker_state.get("coder") == "complete"
        and tracker_state.get("next_worker") == "validator"
        and tracker_state.get("validator") == "pending"
    )


def state_for_validator_event(
    worker_result: dict[str, Any], tracker_state: dict[str, str]
) -> tuple[str, str, dict[str, str]]:
    """Track validator completion and advance to reporter when complete."""
    state = {**base_workflow_state(), **tracker_state}
    state["tracker"] = "complete"
    if not prior_state_allows_validator(state):
        state.update(
            {
                "next_worker": "tracker",
                "next_request": "record coder completion before validator completion",
            }
        )
        return "blocked", "out_of_order_workflow", state

    status = str(worker_result.get("status", ""))
    if status == "complete":
        state.update(
            {
                "coder": "complete",
                "validator": "complete",
                "reporter": "pending",
                "next_worker": "reporter",
                "next_request": "collect coder, validator, and tracker worker_results",
            }
        )
        return "ready_for_reporter", "none", state

    state.update(
        {
            "validator": status or "blocked",
            "reporter": "blocked",
            "next_worker": "coder",
            "next_request": "request coder fix from validator evidence",
        }
    )
    return "needs_coder_fix", "validator result is not complete", state


def compact_evidence(event: str, tracker_status: str, block_reason: str) -> list[str]:
    """Return compact tracker evidence for reporter collection."""
    return [
        f"tracker event: {event}",
        f"tracker_status: {tracker_status}; reason: {block_reason}",
    ]


def worker_result_for(
    event: str, tracker_status: str, block_reason: str, workflow_state: dict[str, str]
) -> dict[str, Any]:
    """Build the tracker worker_result consumed by reporter."""
    result_status = "blocked" if tracker_status == "blocked" else "complete"
    return {
        "worker_role": "tracker",
        "status": result_status,
        "changed_scope": ["workflow_state"],
        "evidence": compact_evidence(event, tracker_status, block_reason),
        "next_request": workflow_state.get("next_request", "none"),
    }


def build_tracker_packet(
    worker_pool_packet: dict[str, Any],
    event: str,
    worker_result: dict[str, Any],
    tracker_state: dict[str, str] | None = None,
) -> TrackerPacket:
    """Build tracker packet from worker-pool contract and a worker event."""
    packet_reason = invalid_packet_reason(worker_pool_packet, event)
    expected_role = "coder" if event == "coder_completed" else "validator"
    result_reason = (
        "none"
        if packet_reason != "none"
        else validate_worker_result(worker_result, expected_role)
    )

    if packet_reason != "none" or result_reason != "none":
        block_reason = packet_reason if packet_reason != "none" else result_reason
        workflow_state = {**base_workflow_state(), **(tracker_state or {})}
        workflow_state.update(
            {
                "tracker": "blocked",
                "next_worker": "supervisor",
                "next_request": block_reason,
            }
        )
        tracker_status = "blocked"
    elif event == "coder_completed":
        tracker_status, block_reason, workflow_state = state_for_coder_event(
            worker_result
        )
    else:
        tracker_status, block_reason, workflow_state = state_for_validator_event(
            worker_result, tracker_state or {}
        )

    return TrackerPacket(
        user_goal=str(worker_pool_packet["user_goal"]),
        task_class=str(worker_pool_packet["task_class"]),
        current_route=str(worker_pool_packet["current_route"]),
        selected_gate=str(worker_pool_packet["selected_gate"]),
        tracker_status=tracker_status,
        block_reason=block_reason,
        workflow_state=workflow_state,
        worker_result=worker_result_for(
            event, tracker_status, block_reason, workflow_state
        ),
        context_firewall=context_firewall(),
        korean_final_report=bool(worker_pool_packet["korean_final_report"]),
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
        description="Track worker-pool workflow stage transitions."
    )
    parser.add_argument(
        "--worker-pool-packet-json",
        help="Worker-pool packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--worker-pool-packet-file", help="Path to worker-pool packet JSON."
    )
    parser.add_argument(
        "--event",
        choices=sorted(TRACKER_EVENTS),
        required=True,
        help="Worker completion event to track.",
    )
    parser.add_argument(
        "--worker-result-json",
        help="Worker result JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--worker-result-file", help="Path to worker result JSON.")
    parser.add_argument(
        "--tracker-state-json",
        help="Previous tracker state JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--tracker-state-file", help="Path to previous tracker state JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the tracker packet.",
    )
    args = parser.parse_args()

    try:
        worker_pool_packet, worker_result, tracker_state = load_inputs(args)
        tracker_packet = {
            "tracker_packet": asdict(
                build_tracker_packet(
                    worker_pool_packet,
                    args.event,
                    worker_result,
                    tracker_state,
                )
            )
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"tracker error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(tracker_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(tracker_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
