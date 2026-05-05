#!/usr/bin/env python3
"""Validate coder output against supervisor-approved worker-pool contracts.

This validator is a supervisor-owned worker-pool tool. It does not execute
project tests or approve final completion. It checks that the coder_result
stays aligned with the active route, hard stops, locked scope, and approved
assigned_plan_steps before reporter collection.
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
ARCHIVE_ROUTE_MARKERS = [
    "archived v0.1",
    "archived v0.2",
    "v0.1 route",
    "v0.2 route",
]


@dataclass(frozen=True)
class ValidatorPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    validator_status: str
    block_reason: str
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


def unwrap_coder_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    """Accept a coder result or common packet wrappers around it."""
    if "worker_result" in raw_result:
        raw_result = raw_result["worker_result"]
    if "coder_result" in raw_result:
        raw_result = raw_result["coder_result"]
    if "coder_packet" in raw_result:
        raw_result = raw_result["coder_packet"].get("worker_result", {})
    if not isinstance(raw_result, dict):
        raise ValueError("coder result must be an object")
    return raw_result


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


def load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load worker-pool packet and coder result."""
    packet_uses_stdin = args.worker_pool_packet_json == "-"
    result_uses_stdin = args.coder_result_json == "-"
    if packet_uses_stdin and result_uses_stdin:
        raise ValueError("only one input may read from stdin")
    worker_pool_packet = unwrap_worker_pool_packet(
        load_json_arg(
            args.worker_pool_packet_json,
            args.worker_pool_packet_file,
            stdin_allowed=not result_uses_stdin,
        )
    )
    coder_result = unwrap_coder_result(
        load_json_arg(
            args.coder_result_json,
            args.coder_result_file,
            stdin_allowed=not packet_uses_stdin,
        )
    )
    return worker_pool_packet, coder_result


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _lower_text(values: list[str]) -> str:
    return " ".join(values).lower()


def context_firewall() -> dict[str, list[str]]:
    """Return the validator's fixed upward context firewall."""
    return {
        "upward_allowed": UPWARD_ALLOWED,
        "upward_forbidden": UPWARD_FORBIDDEN,
    }


def role_spec(packet: dict[str, Any], worker_role: str) -> dict[str, Any]:
    """Return the worker role spec or an empty dict."""
    for item in _as_list(packet.get("role_specs", [])):
        if isinstance(item, dict) and item.get("worker_role") == worker_role:
            return item
    return {}


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


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolved_workspace_path(raw_path: str, workspace_root: Path) -> Path | None:
    path_text = raw_path.strip().split(" ")[0].strip()
    if not path_text:
        return None
    candidate = Path(path_text.replace("\\", "/"))
    try:
        resolved = candidate.resolve() if candidate.is_absolute() else (workspace_root / candidate).resolve()
    except OSError:
        return None
    if not _is_relative_to(resolved, workspace_root):
        return None
    return resolved


def allowed_prefixes(role: dict[str, Any], workspace_root: Path | None = None) -> list[Path]:
    """Extract path-like prefixes from allowed scope entries."""
    root = (workspace_root or Path.cwd()).resolve()
    prefixes: list[Path] = []
    for item in _string_list(role.get("allowed_scope", [])):
        prefix = _resolved_workspace_path(item, root)
        if prefix:
            prefixes.append(prefix)
    return prefixes


def scope_is_allowed(
    changed_scope: list[str], coder_role: dict[str, Any], workspace_root: Path | None = None
) -> bool:
    """Return true when every changed scope entry stays inside allowed scope."""
    root = (workspace_root or Path.cwd()).resolve()
    prefixes = allowed_prefixes(coder_role, root)
    if not prefixes:
        return False
    for changed in changed_scope:
        resolved = _resolved_workspace_path(changed, root)
        if resolved is None:
            return False
        if not any(resolved == prefix or _is_relative_to(resolved, prefix) for prefix in prefixes):
            return False
    return True


def assigned_step_ids(coder_role: dict[str, Any]) -> list[str]:
    """Return approved assigned plan step ids for coder."""
    ids: list[str] = []
    for step in _as_list(coder_role.get("assigned_plan_steps", [])):
        if isinstance(step, dict) and str(step.get("id", "")).strip():
            ids.append(str(step["id"]).strip())
    return ids


def evidence_covers_assigned_steps(evidence: list[str], coder_role: dict[str, Any]) -> bool:
    """Return true when coder evidence names every assigned plan step id."""
    evidence_text = _lower_text(evidence)
    return all(step_id.lower() in evidence_text for step_id in assigned_step_ids(coder_role))


def validate_coder_result(
    worker_pool_packet: dict[str, Any], coder_result: dict[str, Any]
) -> tuple[str, str, list[str], list[str]]:
    """Validate coder result and return status, reason, changed scope, evidence."""
    changed_scope = _string_list(coder_result.get("changed_scope", []))
    evidence = _string_list(coder_result.get("evidence", []))
    text = _lower_text(changed_scope + evidence + [str(coder_result.get("next_request", ""))])
    coder_role = role_spec(worker_pool_packet, "coder")
    validator_role = role_spec(worker_pool_packet, "validator")

    if str(worker_pool_packet["worker_pool_status"]) != "ready_for_worker_execution":
        return "blocked", "worker pool blocked: " + str(worker_pool_packet["block_reason"]), [], []
    if str(worker_pool_packet["current_route"]) != ACTIVE_ROUTE:
        return "blocked", "current route is not active v0.3 route", [], []
    if not coder_role or coder_role.get("ready") is not True:
        return "blocked", "coder role is not ready", [], []
    if not validator_role or validator_role.get("ready") is not True:
        return "blocked", "validator role is not ready", [], []
    if contains_forbidden_context(coder_result):
        return "blocked", "unauthorized worker context or hard-stop marker", changed_scope, evidence
    if str(coder_result.get("worker_role", "")) != "coder":
        return "needs_coder_fix", "coder result worker_role must be coder", changed_scope, evidence
    if str(coder_result.get("status", "")) not in VALID_RESULT_STATUSES:
        return "needs_coder_fix", "coder result status is invalid", changed_scope, evidence
    if not changed_scope:
        return "needs_coder_fix", "coder result missing changed_scope", changed_scope, evidence
    if not evidence:
        return "needs_coder_fix", "coder result missing evidence", changed_scope, evidence
    if not scope_is_allowed(changed_scope, coder_role):
        return "blocked", "coder changed_scope is outside assigned scope", changed_scope, evidence
    if any(marker in text for marker in ARCHIVE_ROUTE_MARKERS):
        return "blocked", "coder result drifted into archived route", changed_scope, evidence
    if not evidence_covers_assigned_steps(evidence, coder_role):
        return "needs_coder_fix", "coder result does not cover assigned_plan_steps", changed_scope, evidence
    if str(coder_result.get("status")) in {"failed", "blocked"}:
        return "needs_coder_fix", "coder reported incomplete or blocked work", changed_scope, evidence
    return "passed", "none", changed_scope, evidence


def worker_result_for(
    validator_status: str, block_reason: str, changed_scope: list[str], evidence: list[str]
) -> dict[str, Any]:
    """Build the validator worker_result consumed by reporter."""
    result_status = "complete" if validator_status == "passed" else "blocked"
    next_request = "none" if validator_status == "passed" else "request coder fix"
    return {
        "worker_role": "validator",
        "status": result_status,
        "changed_scope": changed_scope or ["validator_packet"],
        "evidence": evidence + [f"validator: {validator_status}; reason: {block_reason}"],
        "next_request": next_request,
    }


def build_validator_packet(
    worker_pool_packet: dict[str, Any], coder_result: dict[str, Any]
) -> ValidatorPacket:
    """Build validator packet from worker-pool contract and coder result."""
    validator_status, block_reason, changed_scope, evidence = validate_coder_result(
        worker_pool_packet, coder_result
    )
    return ValidatorPacket(
        user_goal=str(worker_pool_packet["user_goal"]),
        task_class=str(worker_pool_packet["task_class"]),
        current_route=str(worker_pool_packet["current_route"]),
        selected_gate=str(worker_pool_packet["selected_gate"]),
        validator_status=validator_status,
        block_reason=block_reason,
        worker_result=worker_result_for(
            validator_status, block_reason, changed_scope, evidence
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
        description="Validate coder_result against worker-pool direction contract."
    )
    parser.add_argument(
        "--worker-pool-packet-json",
        help="Worker-pool packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--worker-pool-packet-file", help="Path to worker-pool packet JSON."
    )
    parser.add_argument(
        "--coder-result-json",
        help="Coder worker_result JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--coder-result-file", help="Path to coder result JSON.")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the validator packet.",
    )
    args = parser.parse_args()

    try:
        worker_pool_packet, coder_result = load_inputs(args)
        validator_packet = {
            "validator_packet": asdict(
                build_validator_packet(worker_pool_packet, coder_result)
            )
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"validator error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(validator_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(validator_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
