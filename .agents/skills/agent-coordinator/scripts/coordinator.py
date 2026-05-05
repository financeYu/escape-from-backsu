#!/usr/bin/env python3
"""Build a coordinator packet from a user's natural-language request.

The coordinator does not execute work. It normalizes user intent into the
smallest planner-facing packet that preserves the current project route,
existing gate authority, and the context firewall.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Any


ACTIVE_ROUTE = "post-MVP v0.3 research-to-strategy adoption route"

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

CONTEXT_FIREWALL = {
    "upward_allowed": ["status", "changed_scope", "evidence", "next_request"],
    "upward_forbidden": [
        "raw worker logs",
        "full exploratory notes",
        "failed implementation attempts unless they change the next decision",
        "long private reasoning",
        "generated output dumps",
        "archive or raw-data context",
    ],
}

BASE_FORBIDDEN_SCOPE = [
    "archive reads unless named provenance/regression/compatibility check",
    "generated outputs, raw data, caches, charts, logs, or release evidence by default",
    "universe or data-ingestion expansion without explicit approval",
    "live trading, brokerage integration, order generation, or real-money execution",
    "valuation/fundamental scoring activation without explicit approval",
    "production activation from evidence-only outputs",
    "existing project-local gate deletion or bypass before replacement approval",
]

HARD_STOP_TERMS = [
    "live trading",
    "brokerage",
    "order generation",
    "real-money",
    "production activation",
    "data ingestion expansion",
    "valuation activation",
    "실거래",
    "주문",
    "프로덕션 활성화",
    "데이터 수집 확장",
    "밸류에이션 활성화",
]

REVIEW_TERMS = [
    "review",
    "code review",
    "점검",
    "검토",
    "코드리뷰",
    "리뷰",
    "검토",
]

SAFE_HARD_STOP_CONTEXT_TERMS = [
    "ban",
    "block",
    "blocked",
    "forbid",
    "forbidden",
    "guardrail",
    "document",
    "documentation",
    "review",
    "검토",
    "금지",
    "차단",
    "문서",
    "문서화",
    "가드레일",
]

PLANNER_TERMS = [
    "planner",
    "planning",
    "plan this",
    "make a plan",
    "계획",
    "계획 세워",
    "플래너",
]
PLAN_REVIEW_TERMS = ["plan-review", "plan review", "플랜리뷰", "플랜 리뷰"]
SUPERVISOR_TERMS = [
    "supervisor",
    "root-agent",
    "root agent",
    "orchestrate",
    "orchestration",
    "root orchestration",
    "수퍼바이저",
    "슈퍼바이저",
    "오케스트레이션",
    "루트 오케스트레이션",
    "작업 지휘",
    "실행 지휘",
]
REPORTER_TERMS = [
    "reporter",
    "reporter role",
    "agent-reporter",
    "worker result",
    "worker_result",
    "result collection",
    "reporter contract",
    "supervisor/user report",
    "final reporting",
    "final report",
    "리포터",
    "보고서",
    "최종 보고",
    "최종 리포트",
    "결과 보고",
]
WORKER_POOL_TERMS = [
    "worker pool",
    "worker-pool",
    "coder role",
    "validator role",
    "reporter role",
    "tracker role",
    "direct implementation",
    "direct validation",
    "workflow status",
    "작업자",
    "코더",
    "밸리데이터",
    "리포터",
    "트래커",
    "직접 구현",
    "직접 검증",
    "워크플로우 상태",
]
REPLACEMENT_TERMS = [
    "replacement",
    "replace",
    "migration",
    "migrate",
    "skill replacement",
    "process replacement",
    "agent-replacement",
    "resource usage",
    "resource profile",
    "대체",
    "교체",
    "마이그레이션",
    "대체",
    "마이그레이션",
    "프로세스 전환",
    "프로세스 교체",
]


@dataclass(frozen=True)
class CoordinatorPacket:
    user_goal: str
    task_class: str
    current_route: str
    selected_gate: str
    resource_usage_profile: dict[str, str]
    allowed_scope: list[str]
    forbidden_scope: list[str]
    planner_must_output: list[str]
    validation_expectations: list[str]
    context_firewall: dict[str, list[str]]
    korean_final_report: bool
    open_questions: list[str]


def normalize_goal(user_goal: str) -> str:
    """Collapse whitespace while preserving the user's wording."""
    return " ".join(user_goal.strip().split())


def classify_task(goal: str) -> str:
    """Classify the request into the root task classes used by AGENTS.md."""
    text = goal.lower()
    if is_review_request(text):
        return "planning/read-only"
    step_gate_terms = [
        "step closure",
        "gate closure",
        "final validation",
        "최종 검증",
        "게이트 종료",
        "단계 종료",
    ]
    edit_terms = [
        "implement",
        "add",
        "modify",
        "update",
        "change",
        "configure",
        "resource usage",
        "resource profile",
        "fix",
        "refactor",
        "write code",
        "skillize",
        "codex skill",
        "수정",
        "구현",
        "정리",
        "적용",
        "스킬화",
        "제작",
        "적용",
        "대체",
        "전환",
        "교체",
        "코드",
        "구현",
        "수정",
        "추가",
        "리팩터",
        "작성",
    ]
    if any(term in text for term in step_gate_terms):
        return "Step/gate closure"
    if any(term in text for term in edit_terms):
        return "narrow edit"
    return "planning/read-only"


def select_gate(goal: str, task_class: str) -> str:
    """Select the current compatibility gate; do not replace gate authority."""
    text = goal.lower()
    if crosses_hard_stop(text):
        return "separate root approval required before gate selection"
    if is_replacement_request(text):
        return ".agents/skills/agent-replacement/SKILL.md"
    if is_plan_review_request(text):
        return ".agents/skills/agent-plan-review/SKILL.md"
    if is_planner_request(text):
        return ".agents/skills/agent-planner/SKILL.md"
    if is_supervisor_request(text):
        return ".agents/skills/agent-supervisor/SKILL.md"
    if is_reporter_request(text):
        return ".agents/skills/agent-reporter/SKILL.md"
    if is_worker_pool_request(text):
        return ".agents/skills/agent-worker-pool/SKILL.md"
    if "아키텍처" in text:
        return ".agents/skills/agent-coordinator/SKILL.md"
    if any(term in text for term in ["coordinator", "planner", "architecture", "아키텍쳐", "아키텍처"]):
        return ".agents/skills/agent-coordinator/SKILL.md"
    if is_review_request(text):
        return ".agents/skills/review_gate/SKILL.md"
    if any(term in text for term in ["prob_up_1d", "probability", "확률", "candidate ml"]):
        return ".agents/skills/quant-candidate-ml-gate/SKILL.md"
    if any(term in text for term in ["strategy", "adoption", "v0.3", "전략", "채택"]):
        return ".agents/skills/quant-strategy-adoption-gate/SKILL.md"
    if any(term in text for term in ["audit", "scope-watchdog", "감사", "스코프"]):
        return ".agents/skills/quant-subproject-audit-gate/SKILL.md"
    if task_class == "narrow edit":
        return ".agents/skills/quant-work-cycle/SKILL.md"
    return "none yet"


def allowed_scope_for(selected_gate: str) -> list[str]:
    """Return the narrow planning scope implied by the selected gate."""
    if selected_gate == "separate root approval required before gate selection":
        return ["approval question only; no planning or file edits before root approval"]
    if selected_gate.endswith("agent-coordinator/SKILL.md"):
        return [
            ".agents/skills/agent-coordinator/",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md router line for architecture redesign only",
        ]
    if selected_gate.endswith("agent-planner/SKILL.md"):
        return [
            ".agents/skills/agent-planner/",
            ".agents/skills/agent-coordinator/ planner routing only",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md architecture routing lines only",
        ]
    if selected_gate.endswith("agent-plan-review/SKILL.md"):
        return [
            ".agents/skills/agent-plan-review/",
            ".agents/skills/agent-planner/ plan-review handoff wording only",
            ".agents/skills/agent-coordinator/ plan-review routing only",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md router line for architecture redesign only",
        ]
    if selected_gate.endswith("agent-supervisor/SKILL.md"):
        return [
            ".agents/skills/agent-supervisor/",
            ".agents/skills/agent-plan-review/ supervisor handoff fields only",
            ".agents/skills/agent-coordinator/ supervisor routing only",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md router line for architecture redesign only",
        ]
    if selected_gate.endswith("agent-worker-pool/SKILL.md"):
        return [
            ".agents/skills/agent-worker-pool/",
            ".agents/skills/agent-supervisor/ worker packet contract only",
            ".agents/skills/agent-coordinator/ worker-pool routing only",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md router line for architecture redesign only",
        ]
    if selected_gate.endswith("agent-reporter/SKILL.md"):
        return [
            ".agents/skills/agent-reporter/",
            ".agents/skills/agent-supervisor/ reporter worker contract only",
            ".agents/skills/agent-worker-pool/ reporter role contract only",
            ".agents/skills/agent-coordinator/ reporter routing only",
            "docs/architecture/agent_orchestration_architecture.md",
            "AGENTS.md router line for architecture redesign only",
        ]
    if selected_gate.endswith("agent-replacement/SKILL.md"):
        return [
            ".agents/skills/agent-replacement/",
            ".agents/skills/agent-coordinator/ replacement routing only",
            ".agents/skills/agent-planner/ replacement handoff wording only",
            ".agents/skills/agent-plan-review/ replacement review checks only",
            ".agents/skills/agent-supervisor/ replacement packet contract only",
            ".agents/skills/agent-worker-pool/ replacement worker contract only",
            ".agents/skills/agent-reporter/ replacement report contract only",
            "docs/architecture/agent_orchestration_architecture.md",
            "docs/root_hard_stops.md architecture process wording only",
            "docs/roadmap_status.md architecture process wording only",
            "AGENTS.md architecture routing lines only",
        ]
    if selected_gate.endswith("quant-candidate-ml-gate/SKILL.md"):
        return [
            "archived/supporting prob_up_1d_candidate compatibility inputs only",
            "candidate probability sidecars, feature tables, and leakage checks when explicitly requested",
        ]
    if selected_gate.endswith("quant-strategy-adoption-gate/SKILL.md"):
        return [
            "v0.3 candidate/evidence route docs, schemas, validators, fixtures, and review packets",
            "ResearchHypothesis, StrategyHypothesis, StrategyCandidate, EvaluationEvidence, AdoptionCandidate artifacts",
        ]
    if selected_gate.endswith("quant-subproject-audit-gate/SKILL.md"):
        return [
            "Quant subproject-wide audit or scope-watchdog evidence",
            "audit verdict and validation evidence as separate outputs",
        ]
    if selected_gate.endswith("quant-work-cycle/SKILL.md"):
        return [
            "explicitly assigned implementation files only",
            "diff review, fix pass, focused verification, and commit-ready report without staging or committing",
        ]
    if selected_gate.endswith("review_gate/SKILL.md"):
        return [
            "changed paths, validation summaries, and targeted review routing only",
            "no code implementation, final acceptance, GitHub PR automation, or remote Git work",
        ]
    return ["planning packet only; no file edits yet"]


def validation_for(selected_gate: str, task_class: str) -> list[str]:
    """Return planner-facing validation expectations."""
    if selected_gate == "separate root approval required before gate selection":
        return ["not_applicable until separate root approval is granted"]
    checks = ["git diff --check"]
    if selected_gate.endswith("agent-coordinator/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-coordinator/scripts/validate_agent_coordinator.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal \"<goal>\" --format json",
        )
    elif selected_gate.endswith("agent-planner/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-planner/scripts/validate_agent_planner.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json \"<json>\" --format json",
        )
    elif selected_gate.endswith("agent-plan-review/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-plan-review/scripts/validate_agent_plan_review.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json \"<json>\" --format json",
        )
    elif selected_gate.endswith("agent-supervisor/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-supervisor/scripts/validate_agent_supervisor.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json \"<json>\" --format json",
        )
    elif selected_gate.endswith("agent-worker-pool/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-worker-pool/scripts/validate_agent_worker_pool.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json \"<json>\" --format json",
        )
    elif selected_gate.endswith("agent-reporter/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-reporter/scripts/validate_agent_reporter.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-reporter/scripts/reporter.py --worker-pool-packet-json \"<json>\" --worker-results-json \"<json>\" --format json",
        )
    elif selected_gate.endswith("agent-replacement/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/agent-replacement/scripts/validate_agent_replacement.py --dry-run",
        )
        checks.insert(
            1,
            ".venv\\Scripts\\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal \"<replacement goal>\" --format json",
        )
    elif selected_gate.endswith("quant-candidate-ml-gate/SKILL.md"):
        checks.insert(
            0,
            "powershell -ExecutionPolicy Bypass -File scripts\\run_bash_validator.ps1 .agents\\skills\\quant-candidate-ml-gate\\scripts\\validate_gate_contract.sh",
        )
    elif selected_gate.endswith("quant-strategy-adoption-gate/SKILL.md"):
        checks.insert(
            0,
            "powershell -ExecutionPolicy Bypass -File scripts\\run_bash_validator.ps1 .agents\\skills\\quant-strategy-adoption-gate\\scripts\\validate_strategy_adoption_gate.sh",
        )
    elif selected_gate.endswith("quant-work-cycle/SKILL.md"):
        checks.insert(
            0,
            ".venv\\Scripts\\python.exe .agents/skills/quant-work-cycle/scripts/validate_work_cycle.py --dry-run",
        )
    elif selected_gate.endswith("review_gate/SKILL.md"):
        checks.append("targeted review routing check; no implementation validators")
    if task_class == "planning/read-only":
        checks.append("task-specific validators not_applicable until edits are planned")
    return checks


def open_questions_for(goal: str) -> list[str]:
    """Ask only when the request appears to cross a hard stop."""
    if crosses_hard_stop(goal.lower()):
        return ["separate root approval is required before planning this hard-stop scope"]
    return ["none"]


def crosses_hard_stop(text: str) -> bool:
    """Return true when the request appears to require separate approval."""
    if any(term in text for term in SAFE_HARD_STOP_CONTEXT_TERMS):
        return False
    return any(term in text for term in HARD_STOP_TERMS)


def is_review_request(text: str) -> bool:
    """Return true when the request should be routed as review/read-only."""
    return not is_plan_review_request(text) and any(term in text for term in REVIEW_TERMS)


def is_plan_review_request(text: str) -> bool:
    """Return true for the architecture role, not a generic code review."""
    return any(term in text for term in PLAN_REVIEW_TERMS)


def is_planner_request(text: str) -> bool:
    """Return true for manual planning requests."""
    return any(term in text for term in PLANNER_TERMS)


def is_supervisor_request(text: str) -> bool:
    """Return true for the supervisor architecture role."""
    return any(term in text for term in SUPERVISOR_TERMS)


def is_worker_pool_request(text: str) -> bool:
    """Return true for the worker-pool architecture role."""
    return any(term in text for term in WORKER_POOL_TERMS)


def is_reporter_request(text: str) -> bool:
    """Return true for the reporter worker-result collection role."""
    return any(term in text for term in REPORTER_TERMS)


def is_replacement_request(text: str) -> bool:
    """Return true for active architecture replacement work."""
    return any(term in text for term in REPLACEMENT_TERMS)


def build_packet(user_goal: str) -> CoordinatorPacket:
    """Build the planner-facing packet from natural language."""
    normalized_goal = normalize_goal(user_goal)
    task_class = classify_task(normalized_goal)
    selected_gate = select_gate(normalized_goal, task_class)
    return CoordinatorPacket(
        user_goal=normalized_goal,
        task_class=task_class,
        current_route=ACTIVE_ROUTE,
        selected_gate=selected_gate,
        resource_usage_profile=dict(RESOURCE_USAGE_PROFILE),
        allowed_scope=allowed_scope_for(selected_gate),
        forbidden_scope=BASE_FORBIDDEN_SCOPE,
        planner_must_output=[
            "ordered plan",
            "scope lock",
            "validation plan",
            "handoff packet for plan-review",
        ],
        validation_expectations=validation_for(selected_gate, task_class),
        context_firewall=CONTEXT_FIREWALL,
        korean_final_report=True,
        open_questions=open_questions_for(normalized_goal),
    )


def render_yaml(value: Any, indent: int = 0) -> str:
    """Render the packet as simple YAML without external dependencies."""
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
        description="Build a coordinator_packet from a user request."
    )
    parser.add_argument(
        "--user-goal",
        required=True,
        help="The user's natural-language request.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="yaml",
        help="Output format for the coordinator packet.",
    )
    args = parser.parse_args()

    packet = {"coordinator_packet": asdict(build_packet(args.user_goal))}
    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=True, indent=2))
    else:
        print(render_yaml(packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
