"""Build v1.0-rc Phase 9 freeze-readiness packet artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.validation.v1_0_rc_freeze_readiness import (
    PROJECT_ROOT,
    build_freeze_readiness_report,
)


OUTPUT_FILES = {
    "phase_status_matrix": "docs/extension/v1_0_rc_phase_status_matrix.md",
    "contract_manifest": "docs/extension/v1_0_rc_contract_manifest.md",
    "artifact_lineage_matrix": "docs/extension/v1_0_rc_artifact_lineage_matrix.md",
    "guardrail_audit": "docs/extension/v1_0_rc_guardrail_audit.md",
    "rebalance_disclosure_audit": "docs/extension/v1_0_rc_rebalance_disclosure_audit.md",
    "validation_test_manifest": "docs/extension/v1_0_rc_validation_test_manifest.md",
    "freeze_readiness_packet": "reports/review/v1_0_rc_freeze_readiness_packet.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument(
        "--validation-result",
        action="append",
        default=[],
        help="Record an actual validation result as 'command || result'.",
    )
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    validation_results = [_parse_validation_result(item) for item in args.validation_result]
    report = build_freeze_readiness_report(root, validation_results=validation_results)
    write_outputs(root, report)
    print(
        "built v1.0-rc freeze readiness packet: "
        f"{root / OUTPUT_FILES['freeze_readiness_packet']} "
        f"verdict={report['freeze_readiness_verdict']}"
    )
    return 0


def _parse_validation_result(raw: str) -> dict[str, Any]:
    if "||" not in raw:
        return {
            "command": raw.strip(),
            "result": "recorded_without_result_detail",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        }
    command, result = raw.split("||", 1)
    return {
        "command": command.strip(),
        "result": result.strip(),
        "run_in_this_session": True,
        "reason_if_not_run": "",
    }


def write_outputs(root: Path, report: Mapping[str, Any]) -> None:
    documents = {
        "phase_status_matrix": _render_phase_status_matrix(report),
        "contract_manifest": _render_contract_manifest(report),
        "artifact_lineage_matrix": _render_lineage_matrix(report),
        "guardrail_audit": _render_guardrail_audit(report),
        "rebalance_disclosure_audit": _render_rebalance_audit(report),
        "validation_test_manifest": _render_test_manifest(report),
        "freeze_readiness_packet": _render_freeze_packet(report),
    }
    for key, content in documents.items():
        path = root / OUTPUT_FILES[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _render_freeze_packet(report: Mapping[str, Any]) -> str:
    lines = [
        "# v1.0-rc Freeze Readiness Packet",
        "",
        f"- packet_version: {report['packet_version']}",
        f"- created_at: {report['created_at']}",
        f"- route_scope: {report['route_scope']}",
        f"- freeze_readiness_verdict: {report['freeze_readiness_verdict']}",
        f"- evidence_only_notice: {report['evidence_only_notice']}",
        f"- prohibited_scope_notice: {report['prohibited_scope_notice']}",
        "",
        "## Verdict",
        "",
    ]
    if report["blockers"]:
        lines.extend(_bullet_lines(report["blockers"]))
    else:
        lines.append("- blockers: none")
    lines.append("")
    lines.append("## Minor Follow-ups")
    lines.extend(_bullet_lines(report["minor_followups"]))
    lines.append("")
    route_state = report["route_state_alignment_audit"]
    lines.append("## Route State Alignment")
    lines.append(f"- expected_route_state: {route_state['expected_route_state']}")
    lines.append(f"- status: {route_state['status']}")
    lines.append(
        f"- missing_required_markers: {route_state['missing_required_markers'] or 'none'}"
    )
    lines.append(f"- stale_markers: {route_state['stale_markers'] or 'none'}")
    lines.append("")
    lines.append("## Phase Status")
    lines.append(_phase_table(report["phase_status_matrix"]))
    lines.append("")
    lines.append("## Boundary Summary")
    boundary = report["boundary_audit"]
    for key in (
        "evidence_only_boundary_preserved",
        "candidate_only_boundary_preserved",
        "manual_review_only_boundary_preserved",
        "selector_output_review_prioritization_only",
        "manual_review_packet_requires_manual_review",
        "production_ranking_changed",
        "backtest_feedback_score_optimization_introduced",
        "valuation_fundamental_active_scoring_enabled",
        "futures_index_macro_regime_active_scoring_enabled",
        "universe_expansion_introduced",
        "new_market_data_ingestion_introduced",
    ):
        lines.append(f"- {key}: {boundary[key]}")
    lines.append("")
    lines.append("## Linked Artifacts")
    for key, rel_path in OUTPUT_FILES.items():
        if key != "freeze_readiness_packet":
            lines.append(f"- {key}: {rel_path}")
    lines.append("")
    return "\n".join(lines)


def _render_phase_status_matrix(report: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# v1.0-rc Phase Status Matrix",
            "",
            _phase_table(report["phase_status_matrix"]),
            "",
        ]
    )


def _render_contract_manifest(report: Mapping[str, Any]) -> str:
    rows = report["contract_manifest"]
    lines = [
        "# v1.0-rc Contract Manifest",
        "",
        "| contract_name | owner_phase | source_file | config_file | validator_file | builder_file | test_file | freeze_readiness_status | prohibited_flags_false | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        flags_false = all(
            row[key] is False
            for key in (
                "live_execution_enabled",
                "brokerage_integration_enabled",
                "order_generation_enabled",
                "user_facing_auto_rebalance_instruction_enabled",
                "production_ranking_update_enabled",
                "valuation_fundamental_active_scoring_enabled",
            )
        )
        lines.append(
            "| {contract_name} | {owner_phase} | {source_file} | {config_file} | {validator_file} | {builder_file} | {test_file} | {freeze_readiness_status} | {flags_false} | {notes} |".format(
                flags_false=flags_false,
                **row,
            )
        )
    lines.append("")
    return "\n".join(lines)


def _render_lineage_matrix(report: Mapping[str, Any]) -> str:
    lines = [
        "# v1.0-rc Artifact Lineage Matrix",
        "",
        "| source_artifact | target_artifact | allowed_dependency | read_only_or_mutating | selector_allowlist_required | rebalancing_disclosure_required | production_ranking_update_allowed | live_execution_allowed | validation_status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["artifact_lineage_matrix"]:
        lines.append(
            "| {source_artifact} | {target_artifact} | {allowed_dependency} | {read_only_or_mutating} | {selector_allowlist_required} | {rebalancing_disclosure_required} | {production_ranking_update_allowed} | {live_execution_allowed} | {validation_status} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def _render_guardrail_audit(report: Mapping[str, Any]) -> str:
    horizon = report["horizon_policy_audit"]
    boundary = report["boundary_audit"]
    route_state = report["route_state_alignment_audit"]
    lines = [
        "# v1.0-rc Guardrail Audit",
        "",
        "## HorizonPolicy",
        f"- supported_horizons: {', '.join(horizon['supported_horizons'])}",
        f"- explicit_default_1d: {horizon['explicit_default_1d']}",
        f"- hidden_1d_hardcoding_found: {horizon['hidden_1d_hardcoding_found']}",
        f"- status: {horizon['status']}",
        "",
        "## Evidence / Selector / Review Boundaries",
    ]
    for key, value in boundary.items():
        if key != "prohibited_language_leaks":
            lines.append(f"- {key}: {value}")
    lines.append(f"- prohibited_language_leaks: {boundary['prohibited_language_leaks'] or 'none'}")
    lines.append("")
    lines.append("## Route State Alignment")
    lines.append(f"- expected_route_state: {route_state['expected_route_state']}")
    lines.append(f"- status: {route_state['status']}")
    lines.append(
        f"- missing_required_markers: {route_state['missing_required_markers'] or 'none'}"
    )
    lines.append(f"- stale_markers: {route_state['stale_markers'] or 'none'}")
    lines.append("")
    return "\n".join(lines)


def _render_rebalance_audit(report: Mapping[str, Any]) -> str:
    rows = report["rebalance_disclosure_audit"]["rows"]
    lines = [
        "# v1.0-rc Rebalance Disclosure Audit",
        "",
        f"- historical_simulated_rebalancing_allowed: {report['rebalance_disclosure_audit']['historical_simulated_rebalancing_allowed']}",
        f"- rebalance_frequency_retained_across_artifacts: {report['rebalance_disclosure_audit']['rebalance_frequency_retained_across_artifacts']}",
        f"- material_rebalancing_disclosure_present: {report['rebalance_disclosure_audit']['material_rebalancing_disclosure_present']}",
        f"- live_user_facing_rebalance_instruction_introduced: {report['rebalance_disclosure_audit']['live_user_facing_rebalance_instruction_introduced']}",
        "",
        "| artifact | rebalance_frequency_present | rebalancing_role_present | materiality_disclosure_present | wording_is_disclosure_not_instruction | status | notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {artifact} | {rebalance_frequency_present} | {rebalancing_role_present} | {materiality_disclosure_present} | {wording_is_disclosure_not_instruction} | {status} | {notes} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def _render_test_manifest(report: Mapping[str, Any]) -> str:
    lines = [
        "# v1.0-rc Validation Test Manifest",
        "",
        "| command | result | run_in_this_session | reason_if_not_run |",
        "|---|---|---|---|",
    ]
    for row in report["test_manifest"]:
        lines.append(
            "| {command} | {result} | {run_in_this_session} | {reason_if_not_run} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def _phase_table(rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "| phase_id | phase_name | status | blocker_summary | follow_up_summary |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {phase_id} | {phase_name} | {status} | {blocker_summary} | {follow_up_summary} |".format(
                **row
            )
        )
    return "\n".join(lines)


def _bullet_lines(items: Sequence[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


if __name__ == "__main__":
    raise SystemExit(main())
