#!/usr/bin/env python3
"""Dry-run validator for the agent-reporter architecture skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_SKILL_PHRASES = {
    "frontmatter name": "name: agent-reporter",
    "collection only": "This skill is collection-and-reporting-only",
    "required input": "The reporter accepts only:",
    "result contract": "## Worker Result Collection Contract",
    "responsibilities": "The reporter must:",
    "tracker ready": "ready_for_reporter",
    "raw context": "raw worker logs",
    "packet contract": "## Reporter Packet Contract",
    "replacement policy": "domain authorities as compatibility targets",
    "korean output": "Answer in Korean",
}

REQUIRED_ARCHITECTURE_PHRASES = {
    "reporter phase": "Phase 6: Reporter Result Collection",
    "reporter code surface": "Reporter Result Collection Code Surface",
    "current migration": (
        "Current state: Phase 7 skill replacement completed in active compatibility mode."
    ),
    "next component": "Next component: none",
    "reporter owns collection": "reporter owns worker_result collection",
}

REQUIRED_CODE_PHRASES = {
    "packet dataclass": "class ReporterPacket",
    "summary dataclass": "class WorkerSummary",
    "build packet": "def build_reporter_packet",
    "context check": "def contains_forbidden_context",
    "firewall check": "def context_firewall_is_safe",
    "compact limits": "MAX_FIELD_CHARS",
    "tracker gate": "def tracker_allows_reporting",
    "reporter worker result": "def reporter_worker_result_for",
    "worker summary": "def worker_summary_from_result",
    "supervisor summary": "def supervisor_summary_from_worker_summaries",
    "required fields": "REQUIRED_WORKER_POOL_FIELDS",
    "stdin support": "sys.stdin.read()",
}

READY_WORKER_POOL_PACKET = {
    "user_goal": "collect worker results through reporter",
    "task_class": "narrow edit",
    "current_route": "post-MVP v0.3 research-to-strategy adoption route",
    "selected_gate": ".agents/skills/agent-reporter/SKILL.md",
    "worker_pool_status": "ready_for_worker_execution",
    "block_reason": "none",
    "role_specs": [
        {"worker_role": "coder", "ready": True},
        {"worker_role": "validator", "ready": True},
        {"worker_role": "reporter", "ready": True},
        {"worker_role": "tracker", "ready": True},
    ],
    "context_firewall": {
        "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
        "upward_forbidden": ["raw worker logs", "generated output dumps"],
    },
    "korean_final_report": True,
}

READY_WORKER_RESULTS = [
    {
        "worker_role": "coder",
        "status": "complete",
        "changed_scope": [".agents/skills/agent-reporter/"],
        "evidence": ["implementation summary compact"],
        "next_request": "none",
    },
    {
        "worker_role": "validator",
        "status": "complete",
        "changed_scope": [".agents/skills/agent-reporter/scripts/reporter.py"],
        "evidence": ["validator dry-run passed"],
        "next_request": "none",
    },
    {
        "worker_role": "tracker",
        "status": "complete",
        "changed_scope": ["workflow state"],
        "evidence": ["tracker_status: ready_for_reporter; reason: none"],
        "next_request": "collect coder, validator, and tracker worker_results",
    },
]

PLANNING_READ_ONLY_WORKER_POOL_PACKET = {
    **READY_WORKER_POOL_PACKET,
    "task_class": "planning/read-only",
    "role_specs": [
        {"worker_role": "coder", "ready": False},
        {"worker_role": "validator", "ready": True},
        {"worker_role": "reporter", "ready": True},
        {"worker_role": "tracker", "ready": True},
    ],
}

PLANNING_READ_ONLY_WORKER_RESULTS = [
    READY_WORKER_RESULTS[1],
    READY_WORKER_RESULTS[2],
]

RAW_CONTEXT_WORKER_RESULTS = [
    *READY_WORKER_RESULTS[:1],
    {
        "worker_role": "validator",
        "status": "complete",
        "changed_scope": [".agents/skills/agent-reporter/scripts/reporter.py"],
        "evidence": ["raw worker logs attached"],
        "next_request": "none",
        "raw_logs": "full validator output",
    },
    *READY_WORKER_RESULTS[2:],
]

MISSING_FIELD_WORKER_RESULTS = [
    *READY_WORKER_RESULTS[:2],
    {
        "worker_role": "tracker",
        "status": "complete",
        "changed_scope": ["workflow state"],
        "next_request": "none",
    },
]

REPORTER_INPUT_WORKER_RESULTS = [
    *READY_WORKER_RESULTS,
    {
        "worker_role": "reporter",
        "status": "complete",
        "changed_scope": ["reporter_packet"],
        "evidence": ["prebuilt reporter worker_result"],
        "next_request": "none",
    },
]

TRACKER_NOT_READY_WORKER_RESULTS = [
    *READY_WORKER_RESULTS[:2],
    {
        "worker_role": "tracker",
        "status": "complete",
        "changed_scope": ["workflow state"],
        "evidence": ["current task tracked only"],
        "next_request": "none",
    },
]

LARGE_EVIDENCE_WORKER_RESULTS = [
    *READY_WORKER_RESULTS[:2],
    {
        "worker_role": "tracker",
        "status": "complete",
        "changed_scope": ["workflow state"],
        "evidence": ["x" * 20000],
        "next_request": "none",
    },
]

BLOCKED_WORKER_POOL_PACKET = {
    **READY_WORKER_POOL_PACKET,
    "worker_pool_status": "blocked",
    "block_reason": "unsafe context firewall",
}

UNSAFE_CONTEXT_FIREWALL_PACKET = {
    **READY_WORKER_POOL_PACKET,
    "context_firewall": {
        "upward_allowed": ["status", "raw worker logs"],
        "upward_forbidden": [],
    },
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
    if "name: agent-reporter" not in frontmatter:
        failures.append("frontmatter name is not agent-reporter")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    return failures


def load_reporter_module(path: Path) -> object:
    spec = importlib.util.spec_from_file_location("agent_reporter_code", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load reporter module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavior_failures(reporter_code_path: Path) -> list[str]:
    module = load_reporter_module(reporter_code_path)
    failures: list[str] = []

    ready = module.build_reporter_packet(READY_WORKER_POOL_PACKET, READY_WORKER_RESULTS)
    if ready.reporter_status != "ready_for_supervisor_summary":
        failures.append("ready worker results did not produce supervisor summary")
    if ready.block_reason != "none":
        failures.append("ready worker results have unexpected block reason")
    if len(ready.worker_summaries) != 3:
        failures.append("ready worker results did not preserve three input summaries")
    if set(ready.supervisor_summary) != set(module.UPWARD_ALLOWED):
        failures.append("supervisor summary contains fields outside upward contract")
    if ready.worker_result["worker_role"] != "reporter":
        failures.append("reporter did not emit its own reporter worker_result")
    if "raw worker logs" not in ready.context_firewall["upward_forbidden"]:
        failures.append("reporter context firewall does not forbid raw logs")

    planning_read_only = module.build_reporter_packet(
        PLANNING_READ_ONLY_WORKER_POOL_PACKET, PLANNING_READ_ONLY_WORKER_RESULTS
    )
    if planning_read_only.reporter_status != "ready_for_supervisor_summary":
        failures.append("planning/read-only reporter required inactive coder result")
    if len(planning_read_only.worker_summaries) != 2:
        failures.append("planning/read-only reporter did not preserve ready input summaries")

    raw_context = module.build_reporter_packet(
        READY_WORKER_POOL_PACKET, RAW_CONTEXT_WORKER_RESULTS
    )
    if raw_context.reporter_status != "blocked":
        failures.append("raw worker context did not block reporter")
    if raw_context.block_reason != "unauthorized worker context":
        failures.append("raw worker context used unexpected block reason")

    missing = module.build_reporter_packet(
        READY_WORKER_POOL_PACKET, MISSING_FIELD_WORKER_RESULTS
    )
    if missing.reporter_status != "blocked":
        failures.append("missing worker result field did not block reporter")
    if missing.block_reason != "worker result contract violation":
        failures.append("missing worker result field used unexpected block reason")

    blocked_pool = module.build_reporter_packet(
        BLOCKED_WORKER_POOL_PACKET, READY_WORKER_RESULTS
    )
    if blocked_pool.reporter_status != "blocked":
        failures.append("blocked worker pool did not block reporter")
    if "worker pool blocked" not in blocked_pool.block_reason:
        failures.append("blocked worker pool reason was not preserved")

    reporter_input = module.build_reporter_packet(
        READY_WORKER_POOL_PACKET, REPORTER_INPUT_WORKER_RESULTS
    )
    if reporter_input.reporter_status != "blocked":
        failures.append("reporter input worker_result did not block reporter")

    tracker_not_ready = module.build_reporter_packet(
        READY_WORKER_POOL_PACKET, TRACKER_NOT_READY_WORKER_RESULTS
    )
    if tracker_not_ready.reporter_status != "blocked":
        failures.append("tracker not ready_for_reporter did not block reporter")

    large_evidence = module.build_reporter_packet(
        READY_WORKER_POOL_PACKET, LARGE_EVIDENCE_WORKER_RESULTS
    )
    if large_evidence.reporter_status != "blocked":
        failures.append("oversized evidence did not block reporter")

    unsafe_firewall = module.build_reporter_packet(
        UNSAFE_CONTEXT_FIREWALL_PACKET, READY_WORKER_RESULTS
    )
    if unsafe_firewall.reporter_status != "blocked":
        failures.append("unsafe worker-pool context_firewall did not block reporter")

    try:
        module.unwrap_worker_pool_packet({"worker_pool_packet": {"user_goal": "missing"}})
        failures.append("missing worker-pool fields did not raise ValueError")
    except ValueError:
        pass

    try:
        module.unwrap_worker_results({"worker_result": "bad"})
        failures.append("malformed worker result did not raise ValueError")
    except ValueError:
        pass

    return failures


def validate(
    skill_path: Path, architecture_path: Path, reporter_code_path: Path
) -> dict[str, object]:
    skill_text = read_text(skill_path)
    architecture_text = read_text(architecture_path)
    reporter_code_text = read_text(reporter_code_path)

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
        f"reporter code missing required phrase: {label}"
        for label in missing_phrases(reporter_code_text, REQUIRED_CODE_PHRASES)
    )
    failures.extend(behavior_failures(reporter_code_path))

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "failures": failures,
        "checked_skill_phrases": sorted(REQUIRED_SKILL_PHRASES),
        "checked_architecture_phrases": sorted(REQUIRED_ARCHITECTURE_PHRASES),
        "checked_code_phrases": sorted(REQUIRED_CODE_PHRASES),
        "checked_behavior_cases": [
            "ready worker results produce supervisor summary",
            "planning/read-only worker results omit inactive coder",
            "raw worker context fails closed",
            "missing worker result fields fail closed",
            "blocked worker pool fails closed",
            "reporter worker_result input fails closed",
            "tracker must be ready_for_reporter",
            "oversized compact fields fail closed",
            "unsafe worker-pool context firewall fails closed",
            "missing worker-pool fields fail closed",
            "malformed worker results fail closed",
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
    default_code = Path(__file__).resolve().parent / "reporter.py"

    parser = argparse.ArgumentParser(
        description="Validate the agent-reporter skill and architecture doc."
    )
    parser.add_argument("skill_path", nargs="?", default=default_skill, type=Path)
    parser.add_argument(
        "--architecture-path",
        default=default_architecture,
        type=Path,
        help="Path to docs/architecture/agent_orchestration_architecture.md.",
    )
    parser.add_argument(
        "--reporter-code-path",
        default=default_code,
        type=Path,
        help="Path to scripts/reporter.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document and behavior checks only; no writes or Git commands.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = validate(args.skill_path, args.architecture_path, args.reporter_code_path)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"agent-reporter validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
