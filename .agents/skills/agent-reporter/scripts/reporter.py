#!/usr/bin/env python3
"""Collect worker results and prepare compact supervisor/user summaries.

The reporter does not execute work. It validates worker_result summaries from
approved worker roles, blocks raw context, and emits an upward-safe packet.
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

REQUIRED_INPUT_WORKER_ROLES = ["coder", "validator", "tracker"]
VALID_RESULT_STATUSES = ["complete", "partial", "failed", "blocked"]
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
FORBIDDEN_CONTEXT_MARKERS = [
    "raw worker logs",
    "full exploratory notes",
    "generated output dumps",
    "archive or raw-data context",
    "private_reasoning",
    "raw_context",
    "raw_logs",
]
MAX_CHANGED_SCOPE_ITEMS = 20
MAX_EVIDENCE_ITEMS = 20
MAX_FIELD_CHARS = 500
MAX_NEXT_REQUEST_CHARS = 500
TRACKER_READY_MARKER = "tracker_status: ready_for_reporter"


@dataclass(frozen=True)
class WorkerSummary:
    worker_role: str
    status: str
    changed_scope: list[str]
    evidence: list[str]
    next_request: str


@dataclass(frozen=True)
class ReporterPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    reporter_status: str
    block_reason: str
    worker_summaries: list[WorkerSummary]
    supervisor_summary: dict[str, Any]
    worker_result: dict[str, Any]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool


def unwrap_worker_pool_packet(raw_packet: dict[str, Any]) -> dict[str, Any]:
    """Accept either the packet itself or {"worker_pool_packet": packet}."""
    if "worker_pool_packet" in raw_packet:
        raw_packet = raw_packet["worker_pool_packet"]
    missing = [field for field in REQUIRED_WORKER_POOL_FIELDS if field not in raw_packet]
    if missing:
        raise ValueError(
            f"worker-pool packet missing required fields: {', '.join(missing)}"
        )
    return raw_packet


def unwrap_worker_results(raw_results: Any) -> list[dict[str, Any]]:
    """Accept a list, {"worker_results": list}, or {"worker_result": item}."""
    if isinstance(raw_results, dict) and "worker_results" in raw_results:
        raw_results = raw_results["worker_results"]
    elif isinstance(raw_results, dict) and "worker_result" in raw_results:
        raw_results = [raw_results["worker_result"]]
    if not isinstance(raw_results, list):
        raise ValueError("worker results must be a list or worker_results object")
    if not all(isinstance(item, dict) for item in raw_results):
        raise ValueError("every worker result must be an object")
    return raw_results


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
    raise ValueError("missing JSON input")


def load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load worker-pool packet and worker results."""
    packet_uses_stdin = args.worker_pool_packet_json == "-"
    results_uses_stdin = args.worker_results_json == "-"
    if packet_uses_stdin and results_uses_stdin:
        raise ValueError("only one input may read from stdin")
    worker_pool_raw = load_json_arg(
        args.worker_pool_packet_json,
        args.worker_pool_packet_file,
        stdin_allowed=not results_uses_stdin,
    )
    worker_results_raw = load_json_arg(
        args.worker_results_json,
        args.worker_results_file,
        stdin_allowed=not packet_uses_stdin,
    )
    return unwrap_worker_pool_packet(worker_pool_raw), unwrap_worker_results(worker_results_raw)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            values.append(item)
    return values


def duplicate_values(items: list[str]) -> list[str]:
    """Return duplicate values in stable sorted order."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return sorted(duplicates)


def approved_worker_roles(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ready role specs indexed by worker role."""
    indexed: dict[str, dict[str, Any]] = {}
    for spec in _as_list(packet.get("role_specs", [])):
        if isinstance(spec, dict) and spec.get("worker_role") and spec.get("ready") is True:
            indexed[str(spec["worker_role"])] = spec
    return indexed


def required_input_worker_roles(packet: dict[str, Any]) -> list[str]:
    """Return input worker roles that are ready for this worker-pool packet."""
    approved_roles = approved_worker_roles(packet)
    return [role for role in REQUIRED_INPUT_WORKER_ROLES if role in approved_roles]


def context_firewall_is_safe(packet: dict[str, Any]) -> bool:
    """Return true when the worker-pool packet keeps upward context compact."""
    firewall = _as_dict(packet.get("context_firewall", {}))
    upward_allowed = _string_list(firewall.get("upward_allowed", []))
    upward_forbidden = _string_list(firewall.get("upward_forbidden", []))
    return (
        upward_allowed == UPWARD_ALLOWED
        and "raw worker logs" in upward_forbidden
        and "generated output dumps" in upward_forbidden
        and "raw worker logs" not in upward_allowed
    )


def context_firewall() -> dict[str, list[str]]:
    """Return the reporter's fixed upward context firewall."""
    return {
        "upward_allowed": UPWARD_ALLOWED,
        "upward_forbidden": UPWARD_FORBIDDEN,
    }


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
        return any(marker in lowered for marker in FORBIDDEN_CONTEXT_MARKERS)
    return False


def compact_list_failures(label: str, values: list[str], max_items: int) -> list[str]:
    """Return compactness failures for an upward list field."""
    failures: list[str] = []
    if len(values) > max_items:
        failures.append(f"{label} has too many items")
    if any(len(item) > MAX_FIELD_CHARS for item in values):
        failures.append(f"{label} item exceeds compact limit")
    return failures


def compact_text_failure(label: str, value: str) -> list[str]:
    """Return compactness failures for an upward text field."""
    if len(value) > MAX_NEXT_REQUEST_CHARS:
        return [f"{label} exceeds compact limit"]
    return []


def worker_summary_from_result(
    result: dict[str, Any], approved_roles: dict[str, dict[str, Any]]
) -> tuple[WorkerSummary | None, list[str]]:
    """Validate and compact one worker_result."""
    failures: list[str] = []
    worker_role = str(result.get("worker_role", "")).strip()
    status = str(result.get("status", "")).strip()
    changed_scope = _string_list(result.get("changed_scope", []))
    evidence = _string_list(result.get("evidence", []))
    next_request = str(result.get("next_request", "")).strip() or "none"

    if contains_forbidden_context(result):
        failures.append("unauthorized worker context")
    if worker_role == "reporter":
        failures.append("reporter worker_result is output-only, not input")
    elif worker_role not in REQUIRED_INPUT_WORKER_ROLES:
        failures.append("unknown worker role")
    elif worker_role not in approved_roles:
        failures.append("worker role is not ready in worker_pool_packet")
    if status not in VALID_RESULT_STATUSES:
        failures.append("invalid or missing status")
    if not changed_scope:
        failures.append("missing changed_scope")
    if not evidence:
        failures.append("missing evidence")
    failures.extend(
        compact_list_failures(
            "changed_scope", changed_scope, MAX_CHANGED_SCOPE_ITEMS
        )
    )
    failures.extend(compact_list_failures("evidence", evidence, MAX_EVIDENCE_ITEMS))
    failures.extend(compact_text_failure("next_request", next_request))
    allowed_keys = {"worker_role", "status", "changed_scope", "evidence", "next_request"}
    extra_keys = sorted(set(result) - allowed_keys)
    if extra_keys:
        failures.append("unapproved worker result fields: " + ", ".join(extra_keys))

    if failures:
        return None, failures
    return (
        WorkerSummary(
            worker_role=worker_role,
            status=status,
            changed_scope=changed_scope,
            evidence=evidence,
            next_request=next_request,
        ),
        [],
    )


def aggregate_status(summaries: list[WorkerSummary]) -> str:
    """Aggregate worker statuses into one supervisor-facing status."""
    statuses = [summary.status for summary in summaries]
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "partial" for status in statuses):
        return "partial"
    return "complete"


def aggregate_next_request(summaries: list[WorkerSummary]) -> str:
    """Preserve one compact next request for the supervisor."""
    requests = [
        f"{summary.worker_role}: {summary.next_request}"
        for summary in summaries
        if summary.next_request and summary.next_request != "none"
    ]
    next_request = "; ".join(requests) if requests else "none"
    if len(next_request) > MAX_NEXT_REQUEST_CHARS:
        return "multiple worker requests; supervisor review required"
    return next_request


def tracker_allows_reporting(summaries: list[WorkerSummary]) -> bool:
    """Return true when tracker advanced the workflow to reporter collection."""
    for summary in summaries:
        if summary.worker_role != "tracker" or summary.status != "complete":
            continue
        evidence_text = " ".join(summary.evidence).lower()
        if TRACKER_READY_MARKER in evidence_text:
            return True
    return False


def supervisor_summary_from_worker_summaries(
    summaries: list[WorkerSummary],
) -> dict[str, Any]:
    """Build the reporter-owned supervisor/user summary."""
    return {
        "status": aggregate_status(summaries),
        "changed_scope": _unique(
            [scope for summary in summaries for scope in summary.changed_scope]
        ),
        "evidence": [
            f"{summary.worker_role}: {item}"
            for summary in summaries
            for item in summary.evidence
        ],
        "next_request": aggregate_next_request(summaries),
    }


def reporter_worker_result_for(
    reporter_status: str, block_reason: str, supervisor_summary: dict[str, Any]
) -> dict[str, Any]:
    """Build the reporter worker_result emitted upward after gate checks."""
    result_status = "complete" if reporter_status == "ready_for_supervisor_summary" else "blocked"
    next_request = str(supervisor_summary.get("next_request", "none"))
    return {
        "worker_role": "reporter",
        "status": result_status,
        "changed_scope": ["reporter_packet"],
        "evidence": [f"reporter_status: {reporter_status}; reason: {block_reason}"],
        "next_request": next_request,
    }


def build_reporter_packet(
    worker_pool_packet: dict[str, Any], worker_results: list[dict[str, Any]]
) -> ReporterPacket:
    """Build a reporter packet from worker-pool output and worker results."""
    if str(worker_pool_packet["worker_pool_status"]) != "ready_for_worker_execution":
        supervisor_summary = {
            "status": "blocked",
            "changed_scope": [],
            "evidence": [],
            "next_request": "worker pool must be ready before reporting",
        }
        return ReporterPacket(
            user_goal=str(worker_pool_packet["user_goal"]),
            task_class=str(worker_pool_packet["task_class"]),
            current_route=str(worker_pool_packet["current_route"]),
            selected_gate=str(worker_pool_packet["selected_gate"]),
            reporter_status="blocked",
            block_reason="worker pool blocked: "
            + str(worker_pool_packet.get("block_reason", "unknown")),
            worker_summaries=[],
            supervisor_summary=supervisor_summary,
            worker_result=reporter_worker_result_for(
                "blocked",
                "worker pool blocked: "
                + str(worker_pool_packet.get("block_reason", "unknown")),
                supervisor_summary,
            ),
            context_firewall=context_firewall(),
            korean_final_report=bool(worker_pool_packet["korean_final_report"]),
        )

    if not context_firewall_is_safe(worker_pool_packet):
        supervisor_summary = {
            "status": "blocked",
            "changed_scope": [],
            "evidence": ["unsafe worker_pool context_firewall"],
            "next_request": "request corrected worker_pool_packet context_firewall",
        }
        return ReporterPacket(
            user_goal=str(worker_pool_packet["user_goal"]),
            task_class=str(worker_pool_packet["task_class"]),
            current_route=str(worker_pool_packet["current_route"]),
            selected_gate=str(worker_pool_packet["selected_gate"]),
            reporter_status="blocked",
            block_reason="unsafe context firewall",
            worker_summaries=[],
            supervisor_summary=supervisor_summary,
            worker_result=reporter_worker_result_for(
                "blocked", "unsafe context firewall", supervisor_summary
            ),
            context_firewall=context_firewall(),
            korean_final_report=bool(worker_pool_packet["korean_final_report"]),
        )

    approved_roles = approved_worker_roles(worker_pool_packet)
    summaries: list[WorkerSummary] = []
    failures: list[str] = []
    for result in worker_results:
        summary, result_failures = worker_summary_from_result(result, approved_roles)
        if summary:
            summaries.append(summary)
        failures.extend(result_failures)

    summary_roles = [summary.worker_role for summary in summaries]
    duplicate_roles = duplicate_values(summary_roles)
    if duplicate_roles:
        failures.append("duplicate worker result roles: " + ", ".join(duplicate_roles))
    required_roles = required_input_worker_roles(worker_pool_packet)
    missing_roles = [role for role in required_roles if role not in summary_roles]
    if missing_roles:
        failures.append("missing worker result roles: " + ", ".join(missing_roles))
    if not failures and not tracker_allows_reporting(summaries):
        failures.append("tracker has not advanced workflow to reporter")

    if failures:
        supervisor_summary = {
            "status": "blocked",
            "changed_scope": _unique(
                [scope for summary in summaries for scope in summary.changed_scope]
            ),
            "evidence": ["; ".join(_unique(failures))],
            "next_request": "request corrected worker_result summaries",
        }
        block_reason = (
            "unauthorized worker context"
            if any("unauthorized worker context" in failure for failure in failures)
            else "worker result contract violation"
        )
        return ReporterPacket(
            user_goal=str(worker_pool_packet["user_goal"]),
            task_class=str(worker_pool_packet["task_class"]),
            current_route=str(worker_pool_packet["current_route"]),
            selected_gate=str(worker_pool_packet["selected_gate"]),
            reporter_status="blocked",
            block_reason=block_reason,
            worker_summaries=summaries,
            supervisor_summary=supervisor_summary,
            worker_result=reporter_worker_result_for(
                "blocked", block_reason, supervisor_summary
            ),
            context_firewall=context_firewall(),
            korean_final_report=bool(worker_pool_packet["korean_final_report"]),
        )

    supervisor_summary = supervisor_summary_from_worker_summaries(summaries)
    return ReporterPacket(
        user_goal=str(worker_pool_packet["user_goal"]),
        task_class=str(worker_pool_packet["task_class"]),
        current_route=str(worker_pool_packet["current_route"]),
        selected_gate=str(worker_pool_packet["selected_gate"]),
        reporter_status="ready_for_supervisor_summary",
        block_reason="none",
        worker_summaries=summaries,
        supervisor_summary=supervisor_summary,
        worker_result=reporter_worker_result_for(
            "ready_for_supervisor_summary", "none", supervisor_summary
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
        description="Collect worker_result summaries into a reporter packet."
    )
    parser.add_argument(
        "--worker-pool-packet-json",
        help="Worker-pool packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--worker-pool-packet-file", help="Path to worker-pool packet JSON."
    )
    parser.add_argument(
        "--worker-results-json",
        help="Worker results JSON list, worker_results object, or '-' for stdin.",
    )
    parser.add_argument("--worker-results-file", help="Path to worker results JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the reporter packet.",
    )
    args = parser.parse_args()

    try:
        worker_pool_packet, worker_results = load_inputs(args)
        reporter_packet = {
            "reporter_packet": asdict(
                build_reporter_packet(worker_pool_packet, worker_results)
            )
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"reporter error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(reporter_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(reporter_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
