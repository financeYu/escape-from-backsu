#!/usr/bin/env python3
"""Apply supervisor-approved coder file operations inside a worker-pool scope.

The coder is a supervisor-owned worker-pool tool. It executes only explicit
file operations from a compact coder_task, and only when the worker_pool_packet
marks the coder role ready inside approved assigned_plan_steps.
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
VALID_ACTIONS = {"write_file"}
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
MAX_OPERATIONS = 20
MAX_EVIDENCE_ITEMS = 20
MAX_EVIDENCE_CHARS = 500
MAX_CONTENT_CHARS = 400_000


@dataclass(frozen=True)
class FileOperation:
    action: str
    path: str
    bytes_written: int
    existed_before: bool
    dry_run: bool


@dataclass(frozen=True)
class CoderPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    coder_status: str
    block_reason: str
    applied_operations: list[FileOperation]
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


def unwrap_coder_task(raw_task: dict[str, Any]) -> dict[str, Any]:
    """Accept either the task itself or {"coder_task": task}."""
    if not isinstance(raw_task, dict):
        raise ValueError("coder task must be an object")
    if "coder_task" in raw_task:
        raw_task = raw_task["coder_task"]
    if not isinstance(raw_task, dict):
        raise ValueError("coder task must be an object")
    return raw_task


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
    """Load worker-pool packet and coder task."""
    packet_uses_stdin = args.worker_pool_packet_json == "-"
    task_uses_stdin = args.coder_task_json == "-"
    if packet_uses_stdin and task_uses_stdin:
        raise ValueError("only one input may read from stdin")
    worker_pool_packet = unwrap_worker_pool_packet(
        load_json_arg(
            args.worker_pool_packet_json,
            args.worker_pool_packet_file,
            stdin_allowed=not task_uses_stdin,
        )
    )
    coder_task = unwrap_coder_task(
        load_json_arg(
            args.coder_task_json,
            args.coder_task_file,
            stdin_allowed=not packet_uses_stdin,
        )
    )
    return worker_pool_packet, coder_task


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
    """Return the coder's fixed upward context firewall."""
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
    """Return true when raw context or hard-stop markers are present."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in FORBIDDEN_RESULT_KEYS:
                return True
            if str(key) == "content":
                continue
            if contains_forbidden_context(item):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_context(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in FORBIDDEN_MARKERS)
    return False


def assigned_step_ids(coder_role: dict[str, Any]) -> list[str]:
    """Return approved assigned plan step ids for coder."""
    ids: list[str] = []
    for step in _as_list(coder_role.get("assigned_plan_steps", [])):
        if isinstance(step, dict) and str(step.get("id", "")).strip():
            ids.append(str(step["id"]).strip())
    return ids


def completed_steps_cover_assigned_steps(
    completed_plan_steps: list[str], coder_role: dict[str, Any]
) -> bool:
    """Return true when completed_plan_steps covers every assigned step id."""
    completed = {step.lower() for step in completed_plan_steps}
    return all(step_id.lower() in completed for step_id in assigned_step_ids(coder_role))


def allowed_prefixes(role: dict[str, Any]) -> list[str]:
    """Extract path-like prefixes from allowed scope entries."""
    prefixes: list[str] = []
    for item in _string_list(role.get("allowed_scope", [])):
        prefix = item.strip().split(" ")[0]
        if prefix:
            prefixes.append(prefix.rstrip("/\\"))
    return prefixes


def forbidden_prefixes(role: dict[str, Any]) -> list[str]:
    """Extract path-like prefixes from forbidden scope entries."""
    prefixes: list[str] = []
    for item in _string_list(role.get("forbidden_scope", [])):
        prefix = item.strip().split(" ")[0]
        if "/" in prefix or "\\" in prefix:
            prefixes.append(prefix.rstrip("/\\"))
    return prefixes


def relative_to_root(path: Path, workspace_root: Path) -> str:
    """Return a POSIX-like path relative to workspace root."""
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def resolve_workspace_path(path_value: str, workspace_root: Path) -> Path:
    """Resolve a requested path and ensure it stays inside workspace root."""
    requested = Path(path_value)
    resolved = requested if requested.is_absolute() else workspace_root / requested
    resolved = resolved.resolve()
    try:
        resolved.relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise ValueError("operation path escapes workspace root") from exc
    return resolved


def path_matches_prefix(path_value: str, prefix: str) -> bool:
    """Return true when a relative path equals or is contained by a prefix."""
    path_norm = path_value.replace("\\", "/").rstrip("/")
    prefix_norm = prefix.replace("\\", "/").rstrip("/")
    return path_norm == prefix_norm or path_norm.startswith(prefix_norm + "/")


def scope_is_allowed(
    changed_scope: list[str], coder_role: dict[str, Any], workspace_root: Path
) -> bool:
    """Return true when every changed scope entry stays inside allowed scope."""
    prefixes = allowed_prefixes(coder_role)
    if not prefixes:
        return False
    forbidden = forbidden_prefixes(coder_role)
    for changed in changed_scope:
        try:
            resolved = resolve_workspace_path(changed, workspace_root)
            relative = relative_to_root(resolved, workspace_root)
        except ValueError:
            return False
        if not any(path_matches_prefix(relative, prefix) for prefix in prefixes):
            return False
        if any(path_matches_prefix(relative, prefix) for prefix in forbidden):
            return False
    return True


def validate_file_operations(
    coder_task: dict[str, Any], coder_role: dict[str, Any], workspace_root: Path
) -> tuple[str, str, list[dict[str, Any]], list[str]]:
    """Validate operation shape and scope before any file is written."""
    operations = _as_list(coder_task.get("operations", []))
    if not operations:
        return "blocked", "coder task missing operations", [], []
    if len(operations) > MAX_OPERATIONS:
        return "blocked", "coder task has too many operations", [], []

    normalized_operations: list[dict[str, Any]] = []
    changed_scope: list[str] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            return "blocked", f"operation {index} must be an object", [], []
        action = str(operation.get("action", "")).strip()
        if action not in VALID_ACTIONS:
            return "blocked", f"operation {index} action is not allowed", [], []
        path_value = str(operation.get("path", "")).strip()
        if not path_value:
            return "blocked", f"operation {index} missing path", [], []
        content = operation.get("content", "")
        if not isinstance(content, str):
            return "blocked", f"operation {index} content must be text", [], []
        if len(content) > MAX_CONTENT_CHARS:
            return "blocked", f"operation {index} content exceeds compact limit", [], []
        try:
            resolved = resolve_workspace_path(path_value, workspace_root)
            relative = relative_to_root(resolved, workspace_root)
        except ValueError as exc:
            return "blocked", str(exc), [], []
        normalized_operations.append(
            {
                "action": action,
                "path": relative,
                "content": content,
                "encoding": str(operation.get("encoding", "utf-8")),
                "create_parents": bool(operation.get("create_parents", True)),
            }
        )
        changed_scope.append(relative)

    if not scope_is_allowed(changed_scope, coder_role, workspace_root):
        return "blocked", "operation path is outside coder allowed scope", [], []
    return "ready", "none", normalized_operations, changed_scope


def validate_coder_task(
    worker_pool_packet: dict[str, Any],
    coder_task: dict[str, Any],
    workspace_root: Path,
) -> tuple[str, str, list[dict[str, Any]], list[str], list[str]]:
    """Validate the packet and coder_task before executing file operations."""
    coder_role = role_spec(worker_pool_packet, "coder")
    evidence = _string_list(coder_task.get("evidence", []))
    completed_plan_steps = _string_list(coder_task.get("completed_plan_steps", []))
    task_text = _lower_text(
        evidence
        + completed_plan_steps
        + [str(coder_task.get("next_request", ""))]
        + [
            str(operation.get("path", ""))
            for operation in _as_list(coder_task.get("operations", []))
            if isinstance(operation, dict)
        ]
    )

    if str(worker_pool_packet["worker_pool_status"]) != "ready_for_worker_execution":
        return (
            "blocked",
            "worker pool blocked: " + str(worker_pool_packet["block_reason"]),
            [],
            [],
            [],
        )
    if str(worker_pool_packet["current_route"]) != ACTIVE_ROUTE:
        return "blocked", "current route is not active v0.3 route", [], [], []
    if not coder_role or coder_role.get("ready") is not True:
        return "blocked", "coder role is not ready", [], [], []
    if contains_forbidden_context(coder_task):
        return "blocked", "unauthorized worker context or hard-stop marker", [], [], []
    if any(marker in task_text for marker in ARCHIVE_ROUTE_MARKERS):
        return "blocked", "coder task drifted into archived route", [], [], []
    if not evidence:
        return "blocked", "coder task missing compact evidence", [], [], []
    if len(evidence) > MAX_EVIDENCE_ITEMS or any(
        len(item) > MAX_EVIDENCE_CHARS for item in evidence
    ):
        return "blocked", "coder task evidence exceeds compact limit", [], [], []
    if not completed_steps_cover_assigned_steps(completed_plan_steps, coder_role):
        return "blocked", "coder task does not cover assigned_plan_steps", [], [], []

    op_status, op_reason, operations, changed_scope = validate_file_operations(
        coder_task, coder_role, workspace_root
    )
    if op_status != "ready":
        return "blocked", op_reason, [], [], []
    return "ready", "none", operations, changed_scope, evidence


def apply_operations(
    operations: list[dict[str, Any]], workspace_root: Path, dry_run: bool
) -> list[FileOperation]:
    """Apply validated file operations and return compact operation evidence."""
    applied: list[FileOperation] = []
    for operation in operations:
        target = resolve_workspace_path(str(operation["path"]), workspace_root)
        existed_before = target.exists()
        content = str(operation["content"])
        if not dry_run:
            if bool(operation.get("create_parents", True)):
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding=str(operation.get("encoding", "utf-8")))
        applied.append(
            FileOperation(
                action=str(operation["action"]),
                path=relative_to_root(target, workspace_root),
                bytes_written=len(content.encode(str(operation.get("encoding", "utf-8")))),
                existed_before=existed_before,
                dry_run=dry_run,
            )
        )
    return applied


def operation_evidence(applied_operations: list[FileOperation]) -> list[str]:
    """Return compact evidence lines for applied file operations."""
    evidence: list[str] = []
    for operation in applied_operations:
        mode = "dry-run" if operation.dry_run else "applied"
        prior = "updated" if operation.existed_before else "created"
        evidence.append(
            f"coder {mode}: {prior} {operation.path} ({operation.bytes_written} bytes)"
        )
    return evidence


def worker_result_for(
    coder_status: str,
    block_reason: str,
    changed_scope: list[str],
    evidence: list[str],
    completed_plan_steps: list[str],
    next_request: str,
) -> dict[str, Any]:
    """Build the coder worker_result consumed by tracker, validator, reporter."""
    result_status = "complete" if coder_status == "complete" else "blocked"
    step_evidence = "completed assigned_plan_steps: " + ", ".join(completed_plan_steps)
    return {
        "worker_role": "coder",
        "status": result_status,
        "changed_scope": changed_scope or ["coder_packet"],
        "evidence": evidence
        + [step_evidence, f"coder_status: {coder_status}; reason: {block_reason}"],
        "next_request": next_request if result_status == "complete" else block_reason,
    }


def build_coder_packet(
    worker_pool_packet: dict[str, Any],
    coder_task: dict[str, Any],
    workspace_root: Path | None = None,
    dry_run: bool = False,
) -> CoderPacket:
    """Validate and apply coder file operations under worker-pool supervision."""
    if workspace_root is None:
        workspace_root = Path(__file__).resolve().parents[4]
    workspace_root = workspace_root.resolve()
    status, reason, operations, changed_scope, evidence = validate_coder_task(
        worker_pool_packet, coder_task, workspace_root
    )
    completed_plan_steps = _string_list(coder_task.get("completed_plan_steps", []))
    next_request = str(coder_task.get("next_request", "none")).strip() or "none"

    applied_operations: list[FileOperation] = []
    if status == "ready":
        applied_operations = apply_operations(operations, workspace_root, dry_run)
        evidence = evidence + operation_evidence(applied_operations)
        status = "complete"

    return CoderPacket(
        user_goal=str(worker_pool_packet["user_goal"]),
        task_class=str(worker_pool_packet["task_class"]),
        current_route=str(worker_pool_packet["current_route"]),
        selected_gate=str(worker_pool_packet["selected_gate"]),
        coder_status=status,
        block_reason=reason,
        applied_operations=applied_operations,
        worker_result=worker_result_for(
            status,
            reason,
            changed_scope,
            evidence,
            completed_plan_steps,
            next_request,
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
        description="Apply supervisor-approved coder file operations."
    )
    parser.add_argument(
        "--worker-pool-packet-json",
        help="Worker-pool packet JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--worker-pool-packet-file", help="Path to worker-pool packet JSON."
    )
    parser.add_argument(
        "--coder-task-json",
        help="Coder task JSON, or '-' to read JSON from stdin.",
    )
    parser.add_argument("--coder-task-file", help="Path to coder task JSON.")
    parser.add_argument(
        "--workspace-root",
        default=str(Path(__file__).resolve().parents[4]),
        help="Workspace root for safe relative file writes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report operations without writing files.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the coder packet.",
    )
    args = parser.parse_args()

    try:
        worker_pool_packet, coder_task = load_inputs(args)
        coder_packet = {
            "coder_packet": asdict(
                build_coder_packet(
                    worker_pool_packet,
                    coder_task,
                    workspace_root=Path(args.workspace_root),
                    dry_run=bool(args.dry_run),
                )
            )
        }
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"coder error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(coder_packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(coder_packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
