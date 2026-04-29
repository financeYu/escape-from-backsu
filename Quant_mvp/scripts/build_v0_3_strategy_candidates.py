"""Build v0.3 StrategyCandidate registry entries from StrategyHypothesis outputs.

The generated registry is a candidate-only experiment management artifact. It
does not run simulations, does not produce evidence, does not activate
production ranking or scoring, and does not make trading recommendations.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("Quant_mvp/data/v0_3/strategy_hypotheses/v0_3_strategy_hypotheses.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/strategy_candidates")
DEFAULT_JSONL_NAME = "v0_3_strategy_candidate_registry.jsonl"
DEFAULT_CSV_NAME = "v0_3_strategy_candidate_registry.csv"
DEFAULT_MANIFEST_NAME = "v0_3_strategy_candidate_manifest.json"
DEFAULT_GROUPS_NAME = "v0_3_strategy_candidate_groups.json"

CURRENT_STAGE = "StrategyCandidate"
CANDIDATE_VERSION = "v0.3.0"
CANDIDATE_BOUNDARY = (
    "This StrategyCandidate registry is candidate-only experiment management. "
    "It is not EvaluationEvidence, not a production ranking input, not a score "
    "input, not a runtime model feature source, not a trading recommendation, "
    "and not an adoption decision."
)

CANDIDATE_STATUSES = {
    "draft",
    "registered",
    "evaluable",
    "blocked",
    "retired",
}
NEXT_ACTIONS = {"create_evaluation_evidence", "refine_strategy_hypothesis", "resolve_blocker", "reject"}


def _get(payload: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compact_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(payload)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _candidate_id(strategy_hypothesis_id: str) -> str:
    return f"sc:{strategy_hypothesis_id.removeprefix('sh:')}"


def _status(strategy_record: dict[str, Any]) -> str:
    conversion_status = _get(strategy_record, "strategy_hypothesis.conversion_status")
    if conversion_status == "ready_for_candidate_registry":
        return "evaluable"
    if conversion_status == "blocked":
        return "blocked"
    return "draft"


def _next_action(status: str) -> str:
    if status == "evaluable":
        return "create_evaluation_evidence"
    if status == "retired":
        return "reject"
    if status == "blocked":
        return "resolve_blocker"
    return "refine_strategy_hypothesis"


def _reason_for_next_action(status: str) -> str:
    if status == "evaluable":
        return (
            "Candidate has linked StrategyHypothesis rules, data requirements, "
            "experiment scope, and acceptance criteria sufficient for an "
            "EvaluationEvidence request."
        )
    if status == "retired":
        return "Candidate has been retired from the current v0.3 candidate scope."
    if status == "blocked":
        return "Blocking issues must be resolved before evaluation can be requested."
    return "Linked StrategyHypothesis requires clearer signal, data route, or test rules before evaluation."


def _experiment_scope(strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "candidate_only_backtest_or_simulation_design",
        "strategy_type": strategy.get("strategy_type"),
        "entry_rule": strategy.get("entry_rule"),
        "exit_rule": strategy.get("exit_rule"),
        "holding_period": strategy.get("holding_period"),
        "rebalance_rule": strategy.get("rebalance_rule"),
        "benchmark": strategy.get("benchmark"),
        "primary_metric": strategy.get("primary_metric"),
        "no_feedback_boundary": "evaluation_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
    }


def _feature_requirements(strategy: dict[str, Any]) -> list[str]:
    strategy_type = strategy.get("strategy_type")
    requirements = [
        "point_in_time_daily_ohlcv_features",
        "signal_percentile_or_bucket",
        "warmup_coverage_flag",
        "benchmark_return_series",
        "transaction_cost_model",
        "no_lookahead_validation_flag",
    ]
    if strategy_type == "volatility":
        requirements.append("rolling_volatility_state")
    if strategy_type == "reversal":
        requirements.append("short_horizon_return_bucket")
    if strategy_type == "momentum":
        requirements.append("medium_horizon_return_bucket")
    if strategy_type == "statistical_arbitrage":
        requirements.append("rolling_dependence_feature")
    return sorted(set(requirements))


def _signal_inputs(strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        "signal_definition": strategy.get("signal_definition"),
        "signal_calculation_window": strategy.get("signal_calculation_window"),
        "entry_rule": strategy.get("entry_rule"),
        "exit_rule": strategy.get("exit_rule"),
        "rebalance_rule": strategy.get("rebalance_rule"),
    }


def _known_constraints(status: str, strategy_record: dict[str, Any]) -> list[str]:
    constraints = [
        "candidate_only_not_production",
        "approved_daily_ohlcv_scope_only",
        "no_universe_expansion_without_later_approval",
        "evaluation_evidence_required_before_adoption_review",
    ]
    constraints.extend(str(item) for item in _as_list(strategy_record.get("blocker")) if item)
    if status != "evaluable":
        constraints.append("not_ready_for_evaluation")
    return sorted(set(constraints))


def _risk_notes(strategy_record: dict[str, Any]) -> list[str]:
    risks = [
        "paper_claims_not_reproduced",
        "transaction_cost_sensitivity_required",
        "walk_forward_or_out_of_sample_check_required",
        "no_feedback_into_scores_rankings_reports_models_or_auto_adoption",
    ]
    strategy = strategy_record.get("strategy_hypothesis", {})
    if isinstance(strategy, dict) and strategy.get("strategy_type") in {"other", "volatility"}:
        risks.append("signal_specificity_review_required")
    return risks


def _acceptance_criteria(strategy: dict[str, Any]) -> list[str]:
    return [
        "EvaluationEvidence record is produced by an approved candidate-only evaluation lane.",
        "No-lookahead and no-survivorship checks are documented as pass or explicit limitation.",
        "Coverage after warmup is at least 80 percent or the limitation is documented.",
        "Primary metric is computed versus the declared benchmark after transaction costs.",
        "Secondary risk metrics include drawdown, volatility, turnover, and coverage.",
        "Results remain evidence-only and do not modify production scores, rankings, reports, or runtime model features.",
        f"Null hypothesis is evaluated: {strategy.get('null_hypothesis')}",
    ]


def _rejection_criteria(strategy: dict[str, Any]) -> list[str]:
    return [
        "Required data is unavailable inside the approved scope.",
        "Signal cannot be computed from predeclared inputs.",
        "Lookahead or survivorship risk cannot be bounded.",
        "Transaction cost sensitivity removes the evidence-only separation.",
        "Walk-forward or out-of-sample split is unstable.",
        f"Expected failure case occurs: {strategy.get('expected_failure_case')}",
    ]


def _required_evidence(strategy: dict[str, Any]) -> list[str]:
    return [
        "EvaluationEvidence schema record",
        "candidate configuration snapshot",
        "data coverage and warmup report",
        "benchmark comparison table",
        "transaction cost sensitivity table",
        "drawdown volatility turnover summary",
        "no-lookahead and no-feedback validation notes",
        f"primary metric: {strategy.get('primary_metric')}",
    ]


def _blocking_issues(status: str, strategy_record: dict[str, Any]) -> list[str]:
    if status == "evaluable":
        return []
    issues = [str(item) for item in _as_list(strategy_record.get("blocker")) if item]
    if issues:
        return sorted(set(issues))
    if status == "blocked":
        return ["linked_strategy_hypothesis_blocked_or_out_of_scope"]
    return ["strategy_hypothesis_requires_refinement_before_evaluation"]


def _next_stage_input(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if candidate["status"] != "evaluable":
        return None
    return {
        "next_stage": "EvaluationEvidence",
        "candidate_id": candidate["candidate_id"],
        "linked_strategy_hypothesis_id": candidate["linked_strategy_hypothesis_id"],
        "candidate_version": candidate["candidate_version"],
        "experiment_scope": candidate["experiment_scope"],
        "data_requirements": candidate["data_requirements"],
        "feature_requirements": candidate["feature_requirements"],
        "acceptance_criteria": candidate["acceptance_criteria"],
        "required_evidence": candidate["required_evidence"],
        "no_feedback_check": "evaluation_evidence_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
    }


def strategy_record_to_candidate_record(strategy_record: dict[str, Any]) -> dict[str, Any]:
    strategy = strategy_record.get("strategy_hypothesis")
    if not isinstance(strategy, dict):
        raise ValueError("record missing strategy_hypothesis")

    linked_strategy_id = str(strategy.get("strategy_hypothesis_id"))
    status = _status(strategy_record)
    candidate = {
        "candidate_id": _candidate_id(linked_strategy_id),
        "linked_strategy_hypothesis_id": linked_strategy_id,
        "candidate_name": _compact_text(strategy.get("title"), limit=300),
        "candidate_version": CANDIDATE_VERSION,
        "status": status,
        "experiment_scope": _experiment_scope(strategy),
        "target_universe": strategy.get("universe_filter"),
        "test_period": (
            "2015-01-01 through 2025-12-31 or the latest approved local daily "
            "OHLCV snapshot before evaluation, whichever is earlier; no future data."
        ),
        "data_requirements": _as_list(strategy.get("data_requirements")),
        "feature_requirements": _feature_requirements(strategy),
        "signal_inputs": _signal_inputs(strategy),
        "implementation_notes": _as_list(strategy.get("implementation_notes")),
        "known_constraints": _known_constraints(status, strategy_record),
        "expected_edge": strategy.get("expected_positive_pattern"),
        "risk_notes": _risk_notes(strategy_record),
        "acceptance_criteria": _acceptance_criteria(strategy),
        "rejection_criteria": _rejection_criteria(strategy),
        "required_evidence": _required_evidence(strategy),
        "blocking_issues": _blocking_issues(status, strategy_record),
        "next_action": _next_action(status),
        "reason_for_next_action": _reason_for_next_action(status),
    }
    output = {
        "schema_version": "v0_3_strategy_candidate_registry_0_1",
        "current_stage": CURRENT_STAGE,
        "candidate_boundary": CANDIDATE_BOUNDARY,
        "linked_strategy_hypothesis": {
            "strategy_hypothesis_id": linked_strategy_id,
            "strategy_type": strategy.get("strategy_type"),
            "conversion_status": strategy.get("conversion_status"),
            "primary_metric": strategy.get("primary_metric"),
        },
        "strategy_candidate": candidate,
        "evaluation_readiness": {
            "status": status,
            "ready_for_evaluation": status == "evaluable",
            "required_data_present_in_contract": bool(candidate["data_requirements"]),
            "rules_present_in_contract": bool(candidate["signal_inputs"].get("entry_rule"))
            and bool(candidate["signal_inputs"].get("exit_rule")),
        },
        "required_evidence": candidate["required_evidence"],
        "next_stage_input": _next_stage_input(candidate),
        "blocker": candidate["blocking_issues"],
        "minimal_fix": [] if status == "evaluable" else _minimal_fix(status),
        "no_feedback_check": "strategy_candidates_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    validate_candidate_record(output)
    return output


def _minimal_fix(status: str) -> list[str]:
    if status == "blocked":
        return ["Resolve blocking issues or retire the candidate before requesting EvaluationEvidence."]
    if status == "retired":
        return ["Do not create EvaluationEvidence for this candidate unless a later route reopens it."]
    return [
        "Refine StrategyHypothesis signal, rules, data requirements, and test scope.",
        "Regenerate StrategyCandidate after the StrategyHypothesis becomes ready_for_candidate_registry.",
    ]


def validate_candidate_record(record: dict[str, Any]) -> None:
    if record.get("current_stage") != CURRENT_STAGE:
        raise ValueError("current_stage must be StrategyCandidate")
    candidate = record.get("strategy_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("strategy_candidate must be an object")
    required_keys = {
        "candidate_id",
        "linked_strategy_hypothesis_id",
        "candidate_name",
        "candidate_version",
        "status",
        "experiment_scope",
        "target_universe",
        "test_period",
        "data_requirements",
        "feature_requirements",
        "signal_inputs",
        "implementation_notes",
        "known_constraints",
        "expected_edge",
        "risk_notes",
        "acceptance_criteria",
        "rejection_criteria",
        "required_evidence",
        "blocking_issues",
        "next_action",
        "reason_for_next_action",
    }
    missing = sorted(required_keys - set(candidate))
    if missing:
        raise ValueError(f"strategy_candidate missing keys: {missing}")
    if candidate["status"] not in CANDIDATE_STATUSES:
        raise ValueError(f"invalid candidate status: {candidate['status']}")
    if candidate["next_action"] not in NEXT_ACTIONS:
        raise ValueError(f"invalid next_action: {candidate['next_action']}")
    if not candidate.get("candidate_version"):
        raise ValueError("candidate_version is required")
    if candidate["status"] == "evaluable":
        if not record.get("next_stage_input"):
            raise ValueError("evaluable candidate requires next_stage_input")
        if candidate.get("blocking_issues"):
            raise ValueError("evaluable candidate must not have blocking_issues")
    if candidate["status"] not in {"registered", "evaluable"} and not candidate.get("blocking_issues"):
        raise ValueError("non-evaluable candidate requires blocking_issues")
    if "trading recommendation" not in str(record.get("candidate_boundary", "")):
        raise ValueError("candidate boundary disclaimer is missing")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    candidate = record["strategy_candidate"]
    return {
        "schema_version": record["schema_version"],
        "current_stage": record["current_stage"],
        "candidate_boundary": record["candidate_boundary"],
        **candidate,
        "linked_strategy_hypothesis": record["linked_strategy_hypothesis"],
        "evaluation_readiness": record["evaluation_readiness"],
        "next_stage_input": record["next_stage_input"],
        "blocker": record["blocker"],
        "minimal_fix": record["minimal_fix"],
        "no_feedback_check": record["no_feedback_check"],
        "activation_boundary": record["activation_boundary"],
    }


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    flattened = [_flatten_record(record) for record in records]
    fieldnames = list(flattened[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in flattened:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


def build_candidate_groups(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(_get(record, "linked_strategy_hypothesis.strategy_type", "unknown"))].append(record)

    groups: dict[str, Any] = {}
    for strategy_type, group_records in sorted(grouped.items()):
        statuses = Counter(_get(record, "strategy_candidate.status") for record in group_records)
        evaluable_ids = [
            _get(record, "strategy_candidate.candidate_id")
            for record in group_records
            if _get(record, "strategy_candidate.status") == "evaluable"
        ]
        groups[strategy_type] = {
            "strategy_type": strategy_type,
            "record_count": len(group_records),
            "status_counts": dict(sorted(statuses.items())),
            "evaluable_candidate_ids": evaluable_ids,
            "next_action_counts": dict(
                sorted(Counter(_get(record, "strategy_candidate.next_action") for record in group_records).items())
            ),
            "group_management_rule": (
                "Only evaluable candidates may request EvaluationEvidence; draft, blocked, "
                "registered, or retired candidates remain in their contract queues."
            ),
            "boundary": "candidate_registry_management_not_evaluation_evidence_not_adoption",
        }

    return {
        "schema_version": "v0_3_strategy_candidate_groups_0_1",
        "current_stage": CURRENT_STAGE,
        "record_count": len(records),
        "groups": groups,
        "no_feedback_check": "candidate_groups_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_manifest(
    records: list[dict[str, Any]],
    groups: dict[str, Any],
    *,
    source_path: Path,
    run_id: str,
) -> dict[str, Any]:
    candidates = [record["strategy_candidate"] for record in records]
    return {
        "schema_version": "v0_3_strategy_candidate_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "candidate_status_counts": dict(sorted(Counter(item["status"] for item in candidates).items())),
        "next_action_counts": dict(sorted(Counter(item["next_action"] for item in candidates).items())),
        "evaluable_count": sum(item["status"] == "evaluable" for item in candidates),
        "group_count": len(groups["groups"]),
        "candidate_boundary": CANDIDATE_BOUNDARY,
        "no_feedback_check": "strategy_candidates_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_strategy_candidates(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    strategy_records = _read_jsonl(input_path)
    records = [strategy_record_to_candidate_record(record) for record in strategy_records]
    groups = build_candidate_groups(records)
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    groups_path = output_dir / DEFAULT_GROUPS_NAME
    _write_jsonl(jsonl_path, records)
    groups_path.write_text(
        json.dumps(groups, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = build_manifest(records, groups, source_path=input_path, run_id=run_id)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    paths = {"jsonl": jsonl_path, "manifest": manifest_path, "groups": groups_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        _write_csv(csv_path, records)
        paths["csv"] = csv_path
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("strategy_candidates_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_strategy_candidates(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
