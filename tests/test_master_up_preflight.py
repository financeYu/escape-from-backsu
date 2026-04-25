from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_master_up_preflight.py"
SPEC = importlib.util.spec_from_file_location("check_master_up_preflight", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_master_up_preflight_accepts_complete_summary() -> None:
    result = module.check_master_up_preflight(_complete_summary())

    assert result.ok
    assert result.errors == ()


def test_master_up_preflight_rejects_blank_required_field() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace("- changed files: docs/review_flow.md", "- changed files:")
    )

    assert not result.ok
    assert "Missing value: [Change summary] changed files" in result.errors


def test_master_up_preflight_rejects_required_checkpoint_not_run() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace("- verdict: PASS", "- verdict: not run", 1)
    )

    assert not result.ok
    assert "Blocking gate not complete: [Scope watchdog audit]" in " ".join(result.errors)


def test_master_up_preflight_allows_optional_watchdog_not_run_with_reason() -> None:
    summary = (
        _complete_summary()
        .replace("- operating level: Level 3", "- operating level: Level 1")
        .replace("- review_mvp request: required", "- review_mvp request: not needed")
        .replace("- required / optional / not needed: required", "- required / optional / not needed: not needed", 1)
        .replace("- verdict: PASS", "- verdict: not run", 1)
        .replace("- reason: ranking guardrail change", "- reason: docs-only typo, no gated behavior", 1)
    )

    result = module.check_master_up_preflight(summary)

    assert result.ok


def test_master_up_preflight_rejects_unselected_master_decision() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace("- ACCEPT", "- ACCEPT / HOLD / REJECT")
    )

    assert not result.ok
    assert "Missing value: [Master decision requested] choose ACCEPT, HOLD, or REJECT" in result.errors


def test_master_up_preflight_rejects_level_3_without_required_checkpoint() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace(
            "- required / optional / not needed: required",
            "- required / optional / not needed: not needed",
            2,
        )
    )

    assert not result.ok
    assert "Level 3 master-up requires [Cross-Step Conflict Checkpoint] to be required" in result.errors


def test_master_up_preflight_rejects_unknown_queue_state() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace("- queue state: handoff-ready", "- queue state: almost merged")
    )

    assert not result.ok
    assert "[Branch integration queue] queue state must use a known branch integration state" in result.errors


def test_master_up_preflight_rejects_full_validation_per_branch() -> None:
    result = module.check_master_up_preflight(
        _complete_summary()
        .replace("- full validation repeated per branch: no", "- full validation repeated per branch: yes")
        .replace(
            "- escalation condition: blocker, merge conflict, or shared contract change",
            "- escalation condition: routine branch",
        )
    )

    assert not result.ok
    assert "[Validation layering] full validation must not be repeated for every branch by default" in result.errors


def test_master_up_preflight_allows_full_validation_for_allowed_escalation() -> None:
    result = module.check_master_up_preflight(
        _complete_summary()
        .replace("- full validation repeated per branch: no", "- full validation repeated per branch: yes")
        .replace(
            "- escalation condition: blocker, merge conflict, or shared contract change",
            "- escalation condition: shared contract change",
        )
    )

    assert result.ok
    assert "[Validation layering] full validation repeated for an allowed escalation condition" in result.warnings


def test_master_up_preflight_rejects_master_direct_fixes() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace("- master direct fixes: no", "- master direct fixes: yes")
    )

    assert not result.ok
    assert "[Required fix routing] master direct fixes must be no or explicitly approved" in result.errors


def test_master_up_preflight_allows_explicitly_approved_master_direct_fix() -> None:
    result = module.check_master_up_preflight(
        _complete_summary().replace(
            "- master direct fixes: no",
            "- master direct fixes: yes, explicitly approved by root for this isolated docs repair",
        )
    )

    assert result.ok
    assert "[Required fix routing] master direct fixes are explicitly approved; verify isolation" in result.warnings


def _complete_summary() -> str:
    return """[Subproject]
- name: root
- responsible scope: master governance
- operating level: Level 3

[Change summary]
- changed files: docs/review_flow.md
- purpose: reduce master-up bottleneck
- local owner: root master

[Git isolation]
- owned change files: docs/review_flow.md
- unrelated dirty files: none
- generated outputs excluded: yes
- mixed-change files requiring hunk-level staging: none

[Branch integration queue]
- queue state: handoff-ready
- branch under review: docs/step16-master-up-preflight
- previous branch gate: passed
- next branch blocked: no

[Validation layering]
- branch integration validation: focused checks for this branch only
- step-end validation: full validation after all queued branches are integrated
- full validation repeated per branch: no
- escalation condition: blocker, merge conflict, or shared contract change

[Required fix routing]
- required findings owner: responsible worker
- fix target worktree/branch: narrowest responsible worktree
- master direct fixes: no
- rerun scope: affected focused checks, then Step-end validation

[Root-Agent Conflict Stop]
- triggered / not triggered: not triggered
- stop trigger: none
- conflicting root area or protected work: none
- report location or summary: not needed
- resume decision: not needed
- unresolved risk: none

[Local review completed]
- worker scope declaration: master governance only
- watchdog audit required: yes
- watchdog verdict: PASS
- watchdog unresolved warnings: none
- scope compliance: PASS
- local tests/checks: pytest focused
- generated-output/cache boundary: PASS
- config-first compliance: not applicable
- hard stop check: PASS

[Evidence]
- commands run: python -m pytest tests/test_master_up_preflight.py
- outputs checked: pass
- docs updated: docs/review_flow.md

[What did not change]
- No score implementation unless current roadmap step allows it
- No backtest unless current roadmap step allows it
- No valuation/fundamental scoring unless current roadmap step allows it
- No financial data merge into technical_composite_score
- No financial data merge into final_composite_score

[Remaining risks]
- unresolved: none
- unknown: none
- inference: none

[Scope watchdog audit]
- required / optional / not needed: required
- verdict: PASS
- reason: ranking guardrail change
- blocking findings: none
- warnings carried to master: none

[Cross-Step Conflict Checkpoint]
- required / optional / not needed: required
- trigger: implementation ready for master-up
- review packet: docs/current_review_packet.md
- verdict: PASS
- roadmap/order: PASS
- hard stops: PASS
- score/composite boundary: PASS
- valuation boundary: PASS
- diagnostics boundary: PASS
- handoff consistency: PASS
- generated-output boundary: PASS
- dirty worktree isolation: PASS
- warnings carried to master: none
- blocking findings: none

[review_mvp request]
- required / optional / not needed: required
- reason: code and tests touched

[Step-end gate readiness]
- master-up preflight result: PASS
- integration validation evidence ready: yes
- cross-step conflict checkpoint ready: yes
- code review owner: review_mvp
- expected fix owner: responsible worker
- validation rerun plan: rerun focused pytest
- commit scope: owned files only

[Master decision requested]
- ACCEPT
"""
