from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_FIELDS_BY_SECTION = {
    "Subproject": ("name", "responsible scope", "operating level"),
    "Change summary": ("changed files", "purpose", "local owner"),
    "Git isolation": (
        "owned change files",
        "unrelated dirty files",
        "generated outputs excluded",
        "mixed-change files requiring hunk-level staging",
    ),
    "Branch integration queue": (
        "queue state",
        "branch under review",
        "previous branch gate",
        "next branch blocked",
    ),
    "Validation layering": (
        "branch integration validation",
        "step-end validation",
        "full validation repeated per branch",
        "escalation condition",
    ),
    "Required fix routing": (
        "required findings owner",
        "fix target worktree/branch",
        "master direct fixes",
        "rerun scope",
    ),
    "Root-Agent Conflict Stop": (
        "triggered / not triggered",
        "stop trigger",
        "conflicting root area or protected work",
        "resume decision",
        "unresolved risk",
    ),
    "Local review completed": (
        "worker scope declaration",
        "watchdog audit required",
        "watchdog verdict",
        "scope compliance",
        "local tests/checks",
        "generated-output/cache boundary",
        "hard stop check",
    ),
    "Evidence": ("commands run", "outputs checked"),
    "Remaining risks": ("unresolved", "unknown", "inference"),
    "Scope watchdog audit": (
        "required / optional / not needed",
        "verdict",
        "reason",
        "blocking findings",
    ),
    "Cross-Step Conflict Checkpoint": (
        "required / optional / not needed",
        "trigger",
        "review packet",
        "verdict",
        "roadmap/order",
        "hard stops",
        "score/composite boundary",
        "valuation boundary",
        "diagnostics boundary",
        "handoff consistency",
        "generated-output boundary",
        "dirty worktree isolation",
        "blocking findings",
    ),
    "review_mvp request": ("required / optional / not needed", "reason"),
    "Step-end gate readiness": (
        "integration validation evidence ready",
        "cross-step conflict checkpoint ready",
        "code review owner",
        "expected fix owner",
        "validation rerun plan",
        "commit scope",
    ),
}

DECISION_SECTION = "Master decision requested"
BAD_REQUIRED_VERDICT_VALUES = ("not run", "pending", "needs_clarification", "blocking_issue")
PLACEHOLDER_VALUES = {"", "...", "tbd", "todo", "pending", "n/a?"}
VALID_OPERATING_LEVELS = ("level 1", "level 2", "level 3")
VALID_QUEUE_STATES = (
    "handoff-ready",
    "preflight passed",
    "merged",
    "focused validation passed",
    "checkpoint passed",
    "queued for step-end",
)
ALLOWED_VALIDATION_ESCALATION_REASONS = (
    "shared contract",
    "merge conflict",
    "gate-critical",
    "gate critical",
    "blocking finding",
    "blocking review",
    "blocking audit",
)
MASTER_DIRECT_FIX_APPROVAL_MARKERS = (
    "explicitly approved",
    "user approved",
    "approved by user",
    "root approved",
    "approved by root",
    "master approved",
    "approved by master",
)


@dataclass(frozen=True)
class MasterUpPreflightResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def check_master_up_preflight(text: str) -> MasterUpPreflightResult:
    sections = _parse_sections(text)
    errors: list[str] = []
    warnings: list[str] = []

    for section, required_fields in REQUIRED_FIELDS_BY_SECTION.items():
        body = sections.get(section)
        if body is None:
            errors.append(f"Missing section: [{section}]")
            continue
        fields = _parse_fields(body)
        for field in required_fields:
            value = fields.get(field)
            if _is_placeholder(value):
                errors.append(f"Missing value: [{section}] {field}")

    _check_required_gate(
        sections,
        "Scope watchdog audit",
        "required / optional / not needed",
        "verdict",
        errors,
    )
    _check_required_gate(
        sections,
        "Cross-Step Conflict Checkpoint",
        "required / optional / not needed",
        "verdict",
        errors,
    )
    _check_branch_queue(sections, errors)
    _check_validation_layering(sections, errors, warnings)
    _check_fix_routing(sections, errors, warnings)
    _check_operating_level(sections, errors, warnings)
    _check_local_watchdog(sections, errors)
    _check_master_decision(sections, errors)
    _collect_gate_warnings(sections, warnings)

    return MasterUpPreflightResult(errors=tuple(errors), warnings=tuple(warnings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether a master-up summary is complete enough for master review."
    )
    parser.add_argument("--summary", required=True, help="Path to the filled master-up summary Markdown file.")
    args = parser.parse_args(argv)

    summary_path = Path(args.summary)
    text = summary_path.read_text(encoding="utf-8")
    result = check_master_up_preflight(text)
    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "ok": result.ok,
                "errors": list(result.errors),
                "warnings": list(result.warnings),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.ok else 1


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^\[(.+)]\s*$", line.strip())
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {section: "\n".join(lines).strip() for section, lines in sections.items()}


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        top_level_field = re.match(r"^-\s+([^:]+):\s*(.*)$", line)
        if top_level_field:
            current = _normalize_field(top_level_field.group(1))
            fields[current] = [top_level_field.group(2).strip()]
            continue
        if current is not None and line.strip():
            fields[current].append(line.strip())
    return {field: " ".join(value).strip() for field, value in fields.items()}


def _check_required_gate(
    sections: dict[str, str],
    section: str,
    requirement_field: str,
    verdict_field: str,
    errors: list[str],
) -> None:
    fields = _parse_fields(sections.get(section, ""))
    requirement = _normalized_value(fields.get(_normalize_field(requirement_field)))
    verdict = _normalized_value(fields.get(_normalize_field(verdict_field)))
    if requirement.startswith("required") and _contains_any(verdict, BAD_REQUIRED_VERDICT_VALUES):
        errors.append(f"Blocking gate not complete: [{section}] verdict is {fields.get(verdict_field, 'missing')!r}")
    if "blocking_issue" in verdict:
        errors.append(f"Blocking gate unresolved: [{section}] verdict is BLOCKING_ISSUE")


def _check_local_watchdog(sections: dict[str, str], errors: list[str]) -> None:
    fields = _parse_fields(sections.get("Local review completed", ""))
    required = _normalized_value(fields.get("watchdog audit required"))
    verdict = _normalized_value(fields.get("watchdog verdict"))
    if required.startswith("yes") and _contains_any(verdict, BAD_REQUIRED_VERDICT_VALUES):
        errors.append("[Local review completed] watchdog audit is required but not complete")
    if "blocking_issue" in verdict:
        errors.append("[Local review completed] watchdog verdict is BLOCKING_ISSUE")


def _check_branch_queue(sections: dict[str, str], errors: list[str]) -> None:
    fields = _parse_fields(sections.get("Branch integration queue", ""))
    queue_state = _normalized_value(fields.get("queue state"))
    if not any(queue_state == state or queue_state.startswith(f"{state} ") for state in VALID_QUEUE_STATES):
        errors.append("[Branch integration queue] queue state must use a known branch integration state")


def _check_validation_layering(sections: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    fields = _parse_fields(sections.get("Validation layering", ""))
    branch_validation = _normalized_value(fields.get("branch integration validation"))
    step_end_validation = _normalized_value(fields.get("step-end validation"))
    repeated = _normalized_value(fields.get("full validation repeated per branch"))
    escalation_condition = _normalized_value(fields.get("escalation condition"))
    if "focused" not in branch_validation:
        errors.append("[Validation layering] branch integration validation must identify focused branch checks")
    if "after all" not in step_end_validation and "step-end" not in step_end_validation:
        errors.append("[Validation layering] step-end validation must be separated from branch validation")
    if repeated.startswith("yes"):
        if _contains_any(escalation_condition, ALLOWED_VALIDATION_ESCALATION_REASONS):
            warnings.append("[Validation layering] full validation repeated for an allowed escalation condition")
        else:
            errors.append("[Validation layering] full validation must not be repeated for every branch by default")


def _check_fix_routing(sections: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    fields = _parse_fields(sections.get("Required fix routing", ""))
    master_direct_fixes = _normalized_value(fields.get("master direct fixes"))
    if master_direct_fixes.startswith("yes"):
        if _contains_any(master_direct_fixes, MASTER_DIRECT_FIX_APPROVAL_MARKERS):
            warnings.append("[Required fix routing] master direct fixes are explicitly approved; verify isolation")
        else:
            errors.append("[Required fix routing] master direct fixes must be no or explicitly approved")


def _check_operating_level(sections: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    subproject_fields = _parse_fields(sections.get("Subproject", ""))
    level = _extract_operating_level(subproject_fields.get("operating level"))
    if not level:
        errors.append("[Subproject] operating level must be Level 1, Level 2, or Level 3")
        return

    watchdog_fields = _parse_fields(sections.get("Scope watchdog audit", ""))
    checkpoint_fields = _parse_fields(sections.get("Cross-Step Conflict Checkpoint", ""))
    review_fields = _parse_fields(sections.get("review_mvp request", ""))

    watchdog_requirement = _normalized_value(watchdog_fields.get("required / optional / not needed"))
    checkpoint_requirement = _normalized_value(checkpoint_fields.get("required / optional / not needed"))
    review_requirement = _normalized_value(review_fields.get("required / optional / not needed"))

    if level == "level 3":
        if not watchdog_requirement.startswith("required"):
            errors.append("Level 3 master-up requires [Scope watchdog audit] to be required")
        if not checkpoint_requirement.startswith("required"):
            errors.append("Level 3 master-up requires [Cross-Step Conflict Checkpoint] to be required")
        if review_requirement.startswith("not needed"):
            errors.append("Level 3 master-up cannot mark [review_mvp request] as not needed")
    elif level == "level 2":
        if checkpoint_requirement.startswith("not needed"):
            warnings.append("Level 2 master-up skipped Cross-Step Conflict Checkpoint; verify this is not a gated handoff")


def _check_master_decision(sections: dict[str, str], errors: list[str]) -> None:
    body = sections.get(DECISION_SECTION)
    if body is None:
        errors.append(f"Missing section: [{DECISION_SECTION}]")
        return
    compact = " ".join(line.strip() for line in body.splitlines() if line.strip())
    if "ACCEPT / HOLD / REJECT" in compact:
        errors.append(f"Missing value: [{DECISION_SECTION}] choose ACCEPT, HOLD, or REJECT")
        return
    if not re.search(r"\b(ACCEPT|HOLD|REJECT)\b", compact):
        errors.append(f"Missing value: [{DECISION_SECTION}] choose ACCEPT, HOLD, or REJECT")


def _collect_gate_warnings(sections: dict[str, str], warnings: list[str]) -> None:
    for section in ("Scope watchdog audit", "Cross-Step Conflict Checkpoint"):
        fields = _parse_fields(sections.get(section, ""))
        verdict = _normalized_value(fields.get("verdict"))
        if "warning" in verdict:
            warnings.append(f"[{section}] carries WARNING; copy the risk into master-up notes")


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = _normalized_value(value)
    return normalized in PLACEHOLDER_VALUES


def _normalized_value(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def _normalize_field(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _extract_operating_level(value: str | None) -> str:
    normalized = _normalized_value(value)
    for level in VALID_OPERATING_LEVELS:
        if level in normalized:
            return level
    return ""


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)


if __name__ == "__main__":
    sys.exit(main())
