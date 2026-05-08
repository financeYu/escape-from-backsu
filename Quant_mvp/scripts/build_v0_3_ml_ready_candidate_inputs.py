"""Build v0.3 candidate-level ML-ready input rows.

The generated rows are candidate/evidence metadata for ML/evaluator review.
Actual outcome labels are populated only from approved EvaluationEvidence
records with metric summaries. Surrogate prediction columns stay separate and
must not be used as supervised labels or adoption evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.v0_3_ml_label_policy import (
    GENERIC_PROXY_BLOCKED_REASON,
    GENERIC_PROXY_LABEL_ROLE,
    GENERIC_PROXY_LABEL_STATUS,
    GENERIC_PROXY_LIMITATION,
)
from Quant_mvp.scripts.artifact_io import (
    parse_json_fenced_markdown,
    read_jsonl,
    write_csv,
    write_jsonl,
)


DEFAULT_SELECTOR_INPUT = Path("Quant_mvp/data/v0_3/selector_inputs/v0_3_selector_input.jsonl")
DEFAULT_REGISTRY = Path("Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl")
DEFAULT_EVIDENCE_DIR = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/ml_ready_candidate_inputs")
DEFAULT_LABEL_RULES = Path("Quant_mvp/config/v0_3_selector_label_rules.toml")
DEFAULT_JSONL_NAME = "v0_3_ml_ready_candidate_input.jsonl"
DEFAULT_CSV_NAME = "v0_3_ml_ready_candidate_input.csv"
DEFAULT_MANIFEST_NAME = "v0_3_ml_ready_candidate_input_manifest.json"

SCHEMA_VERSION = "v0_3_candidate_ml_input_0_2"
ROW_BOUNDARY = (
    "This candidate ML input row is evidence-only metadata for evaluator "
    "review. It is not a production ranking input, not a trading signal, not "
    "an adoption decision, and not automatic production activation."
)
SPLIT_POLICY = "time_aware_required_before_training"
UNLABELED_SOURCE = "unlabeled"
APPROVED_METRIC_SOURCE = "approved_evaluation_evidence"
APPROVED_LABEL_SOURCE = "candidate_level_evaluation_evidence"
PSEUDO_LABEL_SOURCE = "pseudo_model"
REFERENCE_FEATURE_USE_STATUS = "benchmark_reference_feature_candidate"
CANDIDATE_LABEL_USE_STATUS = "candidate_level_supervised_label_candidate"
REFERENCE_FEATURE_BLOCKED_REASON = "metric_use_status_not_supervised_label"

LABEL_POSITIVE = "positive"
LABEL_NEGATIVE = "negative"
NULL_MISSING_EVIDENCE = "null_missing_evidence"
NULL_MISSING_CANDIDATE_LEVEL_METRIC = "null_missing_candidate_level_metric"
EXCLUDED_UNTRADABLE = "excluded_untradable"
EXCLUDED_FAILURE = "excluded_failure"
BLOCKED_GENERIC_PROXY = "blocked_generic_proxy_not_candidate_level"
BLOCKED_NOT_CANDIDATE_LEVEL = "blocked_not_candidate_level"
RULE_INCONCLUSIVE = "rule_inconclusive"

ACTUAL_LABEL_COLUMNS = [
    "actual_total_return",
    "actual_benchmark_return",
    "actual_proxy_return",
    "actual_excess_return_vs_proxy",
    "actual_max_drawdown",
    "actual_volatility",
    "actual_turnover",
    "actual_sharpe",
    "actual_oos_stability",
]
PREDICTION_VALUE_COLUMNS = [
    "pred_total_return",
    "pred_max_drawdown",
    "pred_volatility",
    "pred_turnover",
    "pred_sharpe",
    "pred_oos_stability",
    "prediction_uncertainty",
]
PREDICTION_COLUMNS = [
    *PREDICTION_VALUE_COLUMNS,
    "prediction_model_version",
    "prediction_generated_at",
]
ALLOWED_PREDICTION_USES = [
    "evaluation_prioritization",
    "active_learning",
    "uncertainty_ranking",
    "review_triage",
]
TRAIN_SPLIT_NAMES = {"train", "validation", "test"}


def _get(payload: dict[str, Any] | None, path: str, default: Any = None) -> Any:
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


def _compact_list(value: Any) -> list[str]:
    return sorted(str(item) for item in _as_list(value) if item is not None and str(item) != "")


def read_label_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a TOML object")
    return payload


def evidence_card_id_from_candidate(candidate_id: str, registry_record: dict[str, Any]) -> str | None:
    if candidate_id.startswith("sc:ecard:"):
        return f"ecard:{candidate_id.removeprefix('sc:ecard:')}"
    linked_id = (
        _get(registry_record, "strategy_candidate.linked_strategy_hypothesis_id")
        or _get(registry_record, "linked_strategy_hypothesis.strategy_hypothesis_id")
    )
    if isinstance(linked_id, str) and linked_id.startswith("sh:ecard:"):
        return f"ecard:{linked_id.removeprefix('sh:ecard:')}"
    return None


def read_evaluation_evidence_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for evidence_path in sorted(path.rglob("ee_v0_3_*.md")):
        payload = parse_json_fenced_markdown(evidence_path)
        if payload is not None:
            records.append(payload)
    return records


def _evidence_sort_key(evidence: dict[str, Any]) -> tuple[int, str, str]:
    status_priority = 1 if evidence.get("status") == "evidence_recorded" else 0
    timestamp = str(evidence.get("updated_at") or evidence.get("created_at") or "")
    evaluation_id = str(evidence.get("evaluation_id") or "")
    return (status_priority, timestamp, evaluation_id)


def evidence_index_by_candidate(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for evidence in records:
        candidate_id = evidence.get("candidate_id")
        if not candidate_id:
            continue
        grouped.setdefault(str(candidate_id), []).append(evidence)
    return {
        candidate_id: sorted(items, key=_evidence_sort_key, reverse=True)[0]
        for candidate_id, items in grouped.items()
    }


def _path_value(payload: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        value = _get(payload, path)
        if value is not None:
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _benchmark_rule(label_rules: dict[str, Any]) -> dict[str, Any]:
    rule = _get(label_rules, "metric_rules.total_return_vs_benchmark", {})
    return rule if isinstance(rule, dict) else {}


def _benchmark_cost_profile(label_rules: dict[str, Any]) -> dict[str, Any]:
    profile = _get(label_rules, "metric_rules.total_return_vs_benchmark.benchmark_cost_profile", {})
    return profile if isinstance(profile, dict) else {}


def _benchmark_cost_items(label_rules: dict[str, Any]) -> list[dict[str, Any]]:
    profile = _benchmark_cost_profile(label_rules)
    if profile.get("enabled") is not True:
        return []
    items: list[dict[str, Any]] = []
    for item in _as_list(profile.get("cost_items")):
        if not isinstance(item, dict):
            continue
        if item.get("included_in_benchmark_scoring") is False:
            continue
        rate = _as_float(item.get("rate"))
        if rate is None:
            continue
        if rate < 0:
            raise ValueError("benchmark cost item rate may not be negative")
        normalized = dict(item)
        normalized["rate"] = rate
        items.append(normalized)
    return items


def _benchmark_cost_total_adjustment(label_rules: dict[str, Any]) -> float:
    return sum(float(item["rate"]) for item in _benchmark_cost_items(label_rules))


def _benchmark_cost_metadata(
    *,
    benchmark_return: float | None,
    label_rules: dict[str, Any],
) -> dict[str, Any]:
    profile = _benchmark_cost_profile(label_rules)
    cost_items = _benchmark_cost_items(label_rules)
    total_adjustment = _benchmark_cost_total_adjustment(label_rules)
    application = str(profile.get("cost_application") or "none")
    adjusted_benchmark_return = benchmark_return
    if benchmark_return is not None and application == "subtract_from_benchmark_return":
        adjusted_benchmark_return = benchmark_return - total_adjustment
    return {
        "benchmark_cost_profile_id": profile.get("profile_id"),
        "benchmark_cost_market": profile.get("market"),
        "benchmark_cost_instrument_type": profile.get("instrument_type"),
        "benchmark_cost_application": application,
        "benchmark_cost_items": cost_items,
        "benchmark_cost_total_adjustment": total_adjustment,
        "benchmark_return_before_cost": benchmark_return,
        "benchmark_return_after_cost": adjusted_benchmark_return,
    }


def _approved_actual_labels(evidence: dict[str, Any] | None, label_rules: dict[str, Any]) -> dict[str, Any]:
    labels = {column: None for column in ACTUAL_LABEL_COLUMNS}
    if not evidence:
        return labels
    if evidence.get("status") != "evidence_recorded":
        return labels
    if not isinstance(evidence.get("metric_summary"), dict):
        return labels
    if _as_list(evidence.get("failure_flags")):
        return labels

    labels["actual_total_return"] = _path_value(
        evidence,
        ["performance_metric_summary.total_return", "metric_summary.total_return"],
    )
    labels["actual_benchmark_return"] = _path_value(
        evidence,
        [
            "performance_metric_summary.benchmark_return",
            "performance_metric_summary.benchmark_total_return",
            "metric_summary.benchmark_return",
            "metric_summary.benchmark_total_return",
        ],
    )
    labels["actual_proxy_return"] = _path_value(
        evidence,
        ["performance_metric_summary.proxy_return", "metric_summary.proxy_return"],
    )
    labels["actual_excess_return_vs_proxy"] = _path_value(
        evidence,
        [
            "performance_metric_summary.benchmark_relative_return",
            "metric_summary.benchmark_relative_return",
            "performance_metric_summary.excess_return_vs_proxy",
            "metric_summary.excess_return_vs_proxy",
        ],
    )
    adjusted_relative_return = _benchmark_relative_return(evidence, label_rules)
    if adjusted_relative_return is not None:
        labels["actual_excess_return_vs_proxy"] = adjusted_relative_return
    labels["actual_max_drawdown"] = _path_value(
        evidence,
        ["risk_metric_summary.max_drawdown", "metric_summary.max_drawdown"],
    )
    labels["actual_volatility"] = _path_value(
        evidence,
        [
            "risk_metric_summary.annualized_volatility",
            "risk_metric_summary.volatility",
            "metric_summary.annualized_volatility",
            "metric_summary.volatility",
        ],
    )
    labels["actual_turnover"] = _path_value(
        evidence,
        ["risk_metric_summary.turnover_proxy", "metric_summary.turnover_proxy"],
    )
    labels["actual_sharpe"] = _path_value(
        evidence,
        ["risk_metric_summary.sharpe_ratio", "metric_summary.sharpe_ratio"],
    )
    labels["actual_oos_stability"] = _path_value(
        evidence,
        ["metric_summary.oos_stability_status", "performance_metric_summary.oos_stability_status"],
    )
    return labels


def _generic_proxy_evidence(evidence: dict[str, Any]) -> bool:
    if evidence.get("label_use_status") == GENERIC_PROXY_LABEL_STATUS:
        return True
    if _get(evidence, "metric_summary.label_role") == GENERIC_PROXY_LABEL_ROLE:
        return True
    return False


def _actual_label_role(evidence: dict[str, Any] | None, label_rules: dict[str, Any]) -> str | None:
    if not evidence:
        return None
    role = _get(evidence, "metric_summary.label_role")
    if role is not None:
        return str(role)
    if any(_approved_actual_labels(evidence, label_rules).values()):
        return "candidate_specific"
    return None


def _metric_subject(
    *,
    evidence: dict[str, Any] | None,
    candidate_id: str,
    actual_present: bool,
    generic_proxy_label: bool,
) -> tuple[str | None, str | None, bool, str]:
    if not actual_present:
        return (None, None, False, "metric_summary_missing_or_unavailable")
    if generic_proxy_label:
        return ("generic_proxy", GENERIC_PROXY_LABEL_ROLE, False, GENERIC_PROXY_BLOCKED_REASON)
    explicit_subject_type = evidence.get("metric_subject_type") if evidence else None
    explicit_subject_id = evidence.get("metric_subject_id") if evidence else None
    explicit_match = evidence.get("candidate_metric_match") if evidence else None
    if explicit_subject_type is not None or explicit_subject_id is not None or explicit_match is not None:
        subject_type = str(explicit_subject_type) if explicit_subject_type is not None else None
        subject_id = str(explicit_subject_id) if explicit_subject_id is not None else None
        match = (
            subject_type == "strategy_candidate"
            and subject_id == candidate_id
            and explicit_match is True
        )
        reason = (
            "candidate_id_matches_candidate_level_evaluation_evidence"
            if match
            else str(evidence.get("candidate_metric_match_reason") or "blocked_not_candidate_level")
        )
        return (subject_type, subject_id, match, reason)
    evidence_candidate_id = str(evidence.get("candidate_id") or "") if evidence else ""
    return ("strategy_candidate", evidence_candidate_id or None, False, "metric_subject_contract_fields_missing")


def _parse_test_period_window(test_period: Any) -> tuple[str | None, str | None]:
    if not isinstance(test_period, str):
        return (None, None)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", test_period)
    if len(dates) >= 2:
        return (dates[0], dates[1])
    return (None, None)


def _evaluation_window(
    evidence: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> tuple[str | None, str | None]:
    start = _get(evidence, "evaluation_window.start") if evidence else None
    end = _get(evidence, "evaluation_window.end") if evidence else None
    if start or end:
        return (start, end)
    return _parse_test_period_window(candidate.get("test_period"))


def _time_aware_split_ready(row: dict[str, Any]) -> bool:
    return all(
        row.get(key)
        for key in [
            "publication_date",
            "created_at",
            "evaluation_window_start",
            "evaluation_window_end",
        ]
    )


def _adoption_checks_ready(evidence: dict[str, Any] | None) -> bool:
    if not evidence:
        return False
    checks = evidence.get("required_evaluation_checks")
    if not isinstance(checks, dict):
        return False
    oos_status = str(_get(checks, "oos_walk_forward_stability.status") or "")
    if oos_status in {
        "",
        "not_available",
        "not_available_single_pass_snapshot",
        "required_before_adoption_review",
        "required_before_approved_run",
    }:
        return False
    return True


def _excluded_untradable_flag(failure_flags: list[str]) -> bool:
    return any("untradable" in flag.lower() for flag in failure_flags)


def _critical_failure_flag(failure_flags: list[str], label_rules: dict[str, Any]) -> bool:
    configured = set(
        _compact_list(_get(label_rules, "safety_rules.blocking_failure_flags"))
    )
    if not configured:
        configured = {
            "lookahead_risk_detected",
            "point_in_time_unverified",
            "generated_output_boundary_violation",
            "no_feedback_boundary_violation",
            "universe_boundary_violation",
            "candidate_contract_mismatch",
            "unsupported_production_activation_claim",
            "production_connection_detected",
        }
    return any(flag in configured for flag in failure_flags)


def _metric_rule_value(evidence: dict[str, Any] | None, paths: list[str]) -> float | None:
    if evidence is None:
        return None
    return _as_float(_path_value(evidence, paths))


def _benchmark_relative_return(evidence: dict[str, Any] | None, label_rules: dict[str, Any]) -> float | None:
    if evidence is None:
        return None
    rule = _benchmark_rule(label_rules)
    relative_paths = _as_list(_get(rule, "benchmark_relative_return_paths"))
    relative_value = _metric_rule_value(evidence, [str(path) for path in relative_paths])

    total_paths = [str(path) for path in _as_list(_get(rule, "total_return_paths"))]
    if not total_paths:
        total_paths = [str(_get(rule, "total_return_path") or "metric_summary.total_return")]
    benchmark_paths = [str(path) for path in _as_list(_get(rule, "benchmark_return_paths"))]
    total_return = _metric_rule_value(evidence, total_paths)
    benchmark_return = _metric_rule_value(evidence, benchmark_paths)
    cost_metadata = _benchmark_cost_metadata(benchmark_return=benchmark_return, label_rules=label_rules)
    adjusted_benchmark_return = cost_metadata["benchmark_return_after_cost"]
    if total_return is not None and adjusted_benchmark_return is not None:
        return total_return - float(adjusted_benchmark_return)
    if relative_value is not None:
        return relative_value
    if total_return is None or benchmark_return is None:
        return None
    return total_return - benchmark_return


def _oos_rule_status(evidence: dict[str, Any] | None, label_rules: dict[str, Any]) -> str | None:
    if evidence is None:
        return None
    paths = [str(path) for path in _as_list(_get(label_rules, "oos_rule.paths"))]
    value = _path_value(evidence, paths)
    return str(value).strip().lower() if value is not None else None


def _selector_label_result(
    *,
    evidence: dict[str, Any] | None,
    label_rules: dict[str, Any],
    actual_present: bool,
    candidate_level_metric: bool,
    generic_proxy_label: bool,
    candidate_metric_match: bool,
    excluded_untradable: bool,
    failure_flags: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label_pass_minimum_gate": None,
        "label_review_preferred": None,
        "label_decision": None,
        "label_null_reason": None,
        "supervised_label_eligible": False,
        "excluded_failure": False,
    }

    if evidence is None or evidence.get("status") == "missing_evaluation_evidence":
        result["label_decision"] = NULL_MISSING_EVIDENCE
        result["label_null_reason"] = NULL_MISSING_EVIDENCE
        return result
    if excluded_untradable:
        result["label_decision"] = EXCLUDED_UNTRADABLE
        result["label_null_reason"] = EXCLUDED_UNTRADABLE
        return result
    if _critical_failure_flag(failure_flags, label_rules):
        result["label_decision"] = EXCLUDED_FAILURE
        result["label_null_reason"] = EXCLUDED_FAILURE
        result["excluded_failure"] = True
        return result
    if generic_proxy_label:
        result["label_decision"] = BLOCKED_GENERIC_PROXY
        result["label_null_reason"] = BLOCKED_GENERIC_PROXY
        return result
    if actual_present and not candidate_metric_match:
        result["label_decision"] = BLOCKED_NOT_CANDIDATE_LEVEL
        result["label_null_reason"] = BLOCKED_NOT_CANDIDATE_LEVEL
        return result
    if not candidate_level_metric:
        result["label_decision"] = NULL_MISSING_CANDIDATE_LEVEL_METRIC
        result["label_null_reason"] = NULL_MISSING_CANDIDATE_LEVEL_METRIC
        return result

    relative_return = _benchmark_relative_return(evidence, label_rules)
    sharpe_rule = _get(label_rules, "metric_rules.sharpe", {})
    drawdown_rule = _get(label_rules, "metric_rules.max_drawdown", {})
    sharpe = _metric_rule_value(evidence, [str(path) for path in _as_list(_get(sharpe_rule, "paths"))])
    max_drawdown = _metric_rule_value(evidence, [str(path) for path in _as_list(_get(drawdown_rule, "paths"))])
    minimum_relative = _as_float(_get(label_rules, "metric_rules.total_return_vs_benchmark.minimum_relative_return"))
    minimum_sharpe = _as_float(_get(sharpe_rule, "minimum"))
    minimum_drawdown = _as_float(_get(drawdown_rule, "minimum"))

    if (
        relative_return is None
        or sharpe is None
        or max_drawdown is None
        or minimum_relative is None
        or minimum_sharpe is None
        or minimum_drawdown is None
    ):
        result["label_decision"] = RULE_INCONCLUSIVE
        result["label_null_reason"] = RULE_INCONCLUSIVE
        return result

    strict_metric_gate_pass = (
        relative_return > minimum_relative
        and sharpe >= minimum_sharpe
        and max_drawdown >= minimum_drawdown
    )
    oos_status = _oos_rule_status(evidence, label_rules)
    passing_statuses = {item.lower() for item in _compact_list(_get(label_rules, "oos_rule.passing_statuses"))}
    failing_statuses = {item.lower() for item in _compact_list(_get(label_rules, "oos_rule.failing_statuses"))}
    supervised_rules = _get(label_rules, "supervised_label_rules", {})
    positive_minimum_relative = _as_float(
        _get(supervised_rules, "positive_minimum_benchmark_relative_return")
    )
    if positive_minimum_relative is None:
        positive_minimum_relative = minimum_relative
    supervised_positive = (
        relative_return > positive_minimum_relative
        and oos_status in passing_statuses
    )
    supervised_negative = (
        oos_status in failing_statuses
        or relative_return <= positive_minimum_relative
        or not strict_metric_gate_pass
    )

    result["label_pass_minimum_gate"] = 1 if strict_metric_gate_pass else 0
    if supervised_positive:
        result["label_review_preferred"] = 1
        result["label_decision"] = LABEL_POSITIVE
        result["supervised_label_eligible"] = True
        return result
    if supervised_negative:
        result["label_review_preferred"] = 0
        result["label_decision"] = LABEL_NEGATIVE
        result["supervised_label_eligible"] = True
        return result

    if oos_status in passing_statuses:
        result["label_review_preferred"] = 1
        result["label_decision"] = LABEL_POSITIVE
        result["supervised_label_eligible"] = True
    elif oos_status in failing_statuses:
        result["label_review_preferred"] = 0
        result["label_decision"] = LABEL_NEGATIVE
        result["supervised_label_eligible"] = True
    else:
        result["label_decision"] = RULE_INCONCLUSIVE
        result["label_null_reason"] = RULE_INCONCLUSIVE
    return result


def build_ml_ready_row(
    registry_record: dict[str, Any],
    selector_record: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
    *,
    registry_ref: Path,
    selector_ref: Path,
    label_rules: dict[str, Any] | None = None,
    label_rule_ref: Path = DEFAULT_LABEL_RULES,
    row_generated_at: str,
) -> dict[str, Any]:
    label_rules = label_rules if label_rules is not None else read_label_rules(label_rule_ref)
    candidate = registry_record.get("strategy_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("registry record missing strategy_candidate")
    candidate_id = str(candidate.get("candidate_id") or "")
    if not candidate_id:
        raise ValueError("strategy_candidate.candidate_id is required")

    evidence_card_id = evidence_card_id_from_candidate(candidate_id, registry_record)
    evaluation_window_start, evaluation_window_end = _evaluation_window(evidence, candidate)
    evidence_status = evidence.get("status") if evidence else "missing_evaluation_evidence"
    metric_summary_available = (
        evidence_status == "evidence_recorded"
        and isinstance(_get(evidence, "metric_summary"), dict)
        if evidence
        else False
    )
    adoption_checks_ready = _adoption_checks_ready(evidence)
    actual_labels = _approved_actual_labels(evidence, label_rules)
    benchmark_cost_metadata = _benchmark_cost_metadata(
        benchmark_return=_as_float(actual_labels.get("actual_benchmark_return")),
        label_rules=label_rules,
    )
    actual_present = any(value is not None for value in actual_labels.values())
    generic_proxy_label = bool(evidence and _generic_proxy_evidence(evidence))
    metric_source = APPROVED_METRIC_SOURCE if actual_present else None
    metric_role = _actual_label_role(evidence, label_rules) if actual_present else None
    explicit_metric_use_status = (
        str(evidence.get("label_use_status"))
        if actual_present and evidence and evidence.get("label_use_status") is not None
        else None
    )
    metric_use_status = (
        REFERENCE_FEATURE_USE_STATUS
        if generic_proxy_label
        else explicit_metric_use_status if explicit_metric_use_status is not None
        else CANDIDATE_LABEL_USE_STATUS if actual_present else None
    )
    (
        metric_subject_type,
        metric_subject_id,
        candidate_metric_match,
        candidate_metric_match_reason,
    ) = _metric_subject(
        evidence=evidence,
        candidate_id=candidate_id,
        actual_present=actual_present,
        generic_proxy_label=generic_proxy_label,
    )
    candidate_level_metric = bool(
        actual_present
        and metric_subject_type == "strategy_candidate"
        and candidate_metric_match
        and metric_use_status == CANDIDATE_LABEL_USE_STATUS
    )
    reference_feature_candidate = bool(actual_present and metric_use_status == REFERENCE_FEATURE_USE_STATUS)
    actual_label_source = APPROVED_LABEL_SOURCE if candidate_level_metric else None
    actual_label_role = "candidate_specific" if candidate_level_metric else None
    actual_label_use_status = CANDIDATE_LABEL_USE_STATUS if candidate_level_metric else None
    label_source = actual_label_source or UNLABELED_SOURCE
    failure_flags = _compact_list(evidence.get("failure_flags") if evidence else [])
    excluded_untradable = _excluded_untradable_flag(failure_flags)
    label_result = _selector_label_result(
        evidence=evidence,
        label_rules=label_rules,
        actual_present=actual_present,
        candidate_level_metric=candidate_level_metric,
        generic_proxy_label=generic_proxy_label,
        candidate_metric_match=candidate_metric_match,
        excluded_untradable=excluded_untradable,
        failure_flags=failure_flags,
    )
    required_checks = sorted(str(item) for item in (_get(evidence, "required_evaluation_checks") or {}))
    created_at = (
        candidate.get("created_at")
        or _get(registry_record, "created_at")
        or (evidence.get("created_at") if evidence else None)
    )

    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "row_boundary": ROW_BOUNDARY,
        "candidate_id": candidate_id,
        "candidate_version": candidate.get("candidate_version"),
        "hypothesis_id": candidate.get("linked_strategy_hypothesis_id")
        or _get(registry_record, "linked_strategy_hypothesis.strategy_hypothesis_id"),
        "evidence_card_id": evidence_card_id,
        "selector_input_ref": str(selector_ref),
        "registry_ref": str(registry_ref),
        "evaluation_evidence_ref": evidence.get("_source_path") if evidence else None,
        "row_generated_at": row_generated_at,
        "candidate_status": candidate.get("status"),
        "strategy_type": _get(candidate, "experiment_scope.strategy_type")
        or _get(registry_record, "linked_strategy_hypothesis.strategy_type"),
        "candidate_next_action": candidate.get("next_action"),
        "candidate_ready_for_evaluation": _get(registry_record, "evaluation_readiness.ready_for_evaluation"),
        "candidate_blocker_count": len(_compact_list(candidate.get("blocking_issues"))),
        "candidate_data_requirement_count": len(_compact_list(candidate.get("data_requirements"))),
        "candidate_feature_requirement_count": len(_compact_list(candidate.get("feature_requirements"))),
        "candidate_required_evidence_count": len(_compact_list(candidate.get("required_evidence"))),
        "ml_use_status": _get(selector_record, "ml_use_status"),
        "importance_score": _get(selector_record, "importance_score"),
        "importance_bucket": _get(selector_record, "importance_bucket"),
        "research_branch": _get(selector_record, "research_branch"),
        "downstream_route": _get(selector_record, "downstream_route"),
        "signal_family_candidate": _get(selector_record, "signal_family_candidate"),
        "formula_clarity": _get(selector_record, "formula_clarity"),
        "implementation_readiness": _get(selector_record, "implementation_readiness"),
        "classification_confidence": _get(selector_record, "classification_confidence"),
        "selector_evidence_status": _get(selector_record, "evidence_status"),
        "reproducibility_level": _get(selector_record, "reproducibility_level"),
        "transaction_costs_discussed": _get(selector_record, "transaction_costs_discussed"),
        "lookahead_bias_discussed": _get(selector_record, "lookahead_bias_discussed"),
        "survivorship_bias_discussed": _get(selector_record, "survivorship_bias_discussed"),
        "risk_flag_count": len(_compact_list(_get(selector_record, "risk_flags"))),
        "blocked_reason_count": len(_compact_list(_get(selector_record, "blocked_reasons"))),
        "publication_date": _get(selector_record, "publication_date"),
        "publication_year": _get(selector_record, "publication_year"),
        "created_at": created_at,
        "candidate_created_at": candidate.get("created_at"),
        "evaluation_id": evidence.get("evaluation_id") if evidence else None,
        "evaluation_status": evidence_status,
        "evaluation_created_at": evidence.get("created_at") if evidence else None,
        "evaluation_updated_at": evidence.get("updated_at") if evidence else None,
        "evaluation_window_start": evaluation_window_start,
        "evaluation_window_end": evaluation_window_end,
        "evaluation_failure_flags": failure_flags,
        "required_evaluation_check_ids": required_checks,
        "required_evaluation_check_count": len(required_checks),
        "adoption_required_checks_ready": adoption_checks_ready,
        "actual_metric_summary_available": metric_summary_available,
        **benchmark_cost_metadata,
        "metric_source": metric_source,
        "metric_role": metric_role,
        "metric_use_status": metric_use_status,
        "metric_subject_type": metric_subject_type,
        "metric_subject_id": metric_subject_id,
        "candidate_metric_match": candidate_metric_match,
        "candidate_metric_match_reason": candidate_metric_match_reason,
        "reference_feature_candidate": reference_feature_candidate,
        "excluded_untradable": excluded_untradable,
        "excluded_failure": label_result["excluded_failure"],
        **actual_labels,
        "label_pass_minimum_gate": label_result["label_pass_minimum_gate"],
        "label_review_preferred": label_result["label_review_preferred"],
        "label_source": label_source,
        "label_null_reason": label_result["label_null_reason"],
        "label_decision": label_result["label_decision"],
        "label_rule_config_ref": str(label_rule_ref),
        "actual_label_source": actual_label_source,
        "actual_label_role": actual_label_role,
        "actual_label_use_status": actual_label_use_status,
        "actual_label_evidence_id": evidence.get("evaluation_id") if actual_label_source else None,
        "actual_label_generated_at": evidence.get("updated_at") if actual_label_source else None,
        "actual_label_blocked_reason": (
            GENERIC_PROXY_BLOCKED_REASON
            if generic_proxy_label
            else REFERENCE_FEATURE_BLOCKED_REASON if reference_feature_candidate else None
        ),
        "pred_total_return": None,
        "pred_max_drawdown": None,
        "pred_volatility": None,
        "pred_turnover": None,
        "pred_sharpe": None,
        "pred_oos_stability": None,
        "prediction_uncertainty": None,
        "prediction_model_version": None,
        "prediction_generated_at": None,
        "prediction_allowed_uses": list(ALLOWED_PREDICTION_USES),
        "split_policy": SPLIT_POLICY,
        "split_name": None,
        "time_aware_split_ready": False,
        "random_split_allowed": False,
        "candidate_research_group_id": _get(selector_record, "parent_evidence_card_id")
        or _get(selector_record, "canonical_paper_id")
        or evidence_card_id,
        "duplication_group_id": _get(selector_record, "parent_evidence_card_id")
        or _get(selector_record, "canonical_paper_id")
        or evidence_card_id,
        "supervised_label_eligible": label_result["supervised_label_eligible"],
        "adoption_review_eligible": bool(
            label_result["supervised_label_eligible"]
            and label_result["label_review_preferred"] == 1
            and label_result["label_pass_minimum_gate"] == 1
            and evidence_status == "evidence_recorded"
            and metric_summary_available
            and not failure_flags
            and adoption_checks_ready
            and not generic_proxy_label
        ),
        "ml_training_status": (
            "blocked_generic_proxy_metric_summary"
            if generic_proxy_label
            else "eligible_candidate_level_label"
            if label_result["supervised_label_eligible"]
            else "excluded_untradable"
            if label_result["label_decision"] == EXCLUDED_UNTRADABLE
            else "excluded_failure"
            if label_result["label_decision"] == EXCLUDED_FAILURE
            else "blocked_not_candidate_level"
            if label_result["label_decision"] == BLOCKED_NOT_CANDIDATE_LEVEL
            else "blocked_missing_evaluation_evidence"
            if label_result["label_decision"] == NULL_MISSING_EVIDENCE
            else "blocked_no_candidate_level_metric"
            if label_result["label_decision"] == NULL_MISSING_CANDIDATE_LEVEL_METRIC
            else "blocked_rule_inconclusive"
            if label_result["label_decision"] == RULE_INCONCLUSIVE
            else "blocked_metric_not_supervised_label"
            if actual_present and candidate_metric_match
            else "blocked_no_actual_metric_summary"
        ),
        "no_feedback_check": "ml_rows_must_not_feed_scores_rankings_reports_backtests_trading_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    row["time_aware_split_ready"] = _time_aware_split_ready(row)
    validate_ml_ready_row(row, source_evidence=evidence)
    return row


def validate_ml_ready_row(row: dict[str, Any], *, source_evidence: dict[str, Any] | None = None) -> None:
    required = {
        "candidate_id",
        "schema_version",
        "label_source",
        "metric_source",
        "metric_role",
        "metric_use_status",
        "metric_subject_type",
        "metric_subject_id",
        "candidate_metric_match",
        "candidate_metric_match_reason",
        "reference_feature_candidate",
        "actual_label_source",
        "actual_label_role",
        "actual_label_use_status",
        "label_pass_minimum_gate",
        "label_review_preferred",
        "label_null_reason",
        "label_decision",
        "label_rule_config_ref",
        "supervised_label_eligible",
        "adoption_review_eligible",
        "split_policy",
        "random_split_allowed",
        "prediction_allowed_uses",
        "publication_date",
        "created_at",
        "candidate_created_at",
        "evaluation_window_start",
        "evaluation_window_end",
    }
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"ML-ready row missing required keys: {missing}")
    if row.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"invalid schema_version: {row.get('schema_version')}")
    if "production ranking input" not in str(row.get("row_boundary", "")):
        raise ValueError("row boundary disclaimer is missing")

    actual_values = {column: row.get(column) for column in ACTUAL_LABEL_COLUMNS}
    actual_present = any(value is not None for value in actual_values.values())
    if row.get("actual_label_source") == PSEUDO_LABEL_SOURCE:
        raise ValueError("actual_label_source may not be pseudo_model")
    if actual_present and row.get("metric_source") != APPROVED_METRIC_SOURCE:
        raise ValueError("actual_* metrics require approved EvaluationEvidence metric_source")
    if row.get("actual_label_source") and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("actual_label_source must be candidate-level EvaluationEvidence")
    if row.get("actual_label_source") == APPROVED_LABEL_SOURCE:
        if not row.get("actual_label_role"):
            raise ValueError("approved actual labels require actual_label_role")
        if not row.get("actual_label_use_status"):
            raise ValueError("approved actual labels require actual_label_use_status")
        if row.get("candidate_metric_match") is not True:
            raise ValueError("approved actual labels require candidate_metric_match")
        if row.get("evaluation_status") != "evidence_recorded":
            raise ValueError("approved actual labels require evidence_recorded status")
        if row.get("actual_metric_summary_available") is not True:
            raise ValueError("approved actual labels require metric_summary")
        if row.get("evaluation_failure_flags"):
            raise ValueError("approved actual labels require no active failure_flags")
        if not row.get("actual_label_evidence_id"):
            raise ValueError("approved actual labels require actual_label_evidence_id")
        if source_evidence is not None and not isinstance(source_evidence.get("metric_summary"), dict):
            raise ValueError("approved actual labels require source metric_summary")
    elif row.get("candidate_metric_match") is True and row.get("metric_use_status") == CANDIDATE_LABEL_USE_STATUS:
        raise ValueError("candidate metric matches must become approved actual labels")

    if row.get("label_source") == PSEUDO_LABEL_SOURCE and row.get("supervised_label_eligible") is True:
        raise ValueError("pseudo_model rows are not supervised training labels")
    if row.get("supervised_label_eligible") is True and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("supervised labels require approved actual evidence")
    if row.get("supervised_label_eligible") is True and row.get("label_review_preferred") not in {0, 1}:
        raise ValueError("supervised labels require binary label_review_preferred")
    if row.get("label_review_preferred") in {0, 1} and row.get("supervised_label_eligible") is not True:
        raise ValueError("binary label_review_preferred requires supervised_label_eligible")
    if row.get("excluded_untradable") is True and row.get("label_review_preferred") == 0:
        raise ValueError("excluded_untradable rows may not become negative labels")
    if row.get("excluded_failure") is True and row.get("label_review_preferred") in {0, 1}:
        raise ValueError("excluded_failure rows may not become binary labels")
    if row.get("adoption_review_eligible") is True and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("adoption review requires actual evidence, not pseudo evidence")
    if row.get("adoption_review_eligible") is True and row.get("adoption_required_checks_ready") is not True:
        raise ValueError("adoption review requires completed required evidence checks")
    if row.get("reference_feature_candidate") is True:
        if row.get("supervised_label_eligible") is True or row.get("adoption_review_eligible") is True:
            raise ValueError("reference feature candidates may not become supervised/adoption labels")
        if row.get("label_source") != UNLABELED_SOURCE:
            raise ValueError("reference feature candidates must keep label_source unlabeled")
        if row.get("metric_use_status") != REFERENCE_FEATURE_USE_STATUS:
            raise ValueError("reference feature candidates require benchmark/reference metric_use_status")

    pred_values_present = any(row.get(column) is not None for column in PREDICTION_VALUE_COLUMNS)
    if pred_values_present:
        allowed_uses = set(_compact_list(row.get("prediction_allowed_uses")))
        if not allowed_uses:
            raise ValueError("pred_* values require prediction_allowed_uses")
        disallowed = sorted(allowed_uses - set(ALLOWED_PREDICTION_USES))
        if disallowed:
            raise ValueError(f"pred_* values have disallowed uses: {disallowed}")
        if not row.get("prediction_model_version") or not row.get("prediction_generated_at"):
            raise ValueError("pred_* values require model version and generated timestamp")
        if row.get("adoption_review_eligible") is True and not actual_present:
            raise ValueError("pred_* values may not make adoption review eligible")

    split_policy = row.get("split_policy")
    split_name = row.get("split_name")
    if split_policy == "random" and row.get("random_split_allowed") is not True:
        raise ValueError("random split is disallowed without isolated duplication groups")
    if split_policy == "random":
        if not row.get("candidate_research_group_id") or not row.get("duplication_group_id"):
            raise ValueError("random split requires explicit duplication group isolation")
    if split_name in TRAIN_SPLIT_NAMES and row.get("time_aware_split_ready") is not True:
        raise ValueError("train/validation/test split assignment requires time-aware fields")
    if split_name in TRAIN_SPLIT_NAMES and not str(split_policy).startswith("time_aware"):
        raise ValueError("train/validation/test split assignment must be time-aware")


def validate_ml_ready_rows(records: list[dict[str, Any]]) -> None:
    candidate_ids = [str(record.get("candidate_id")) for record in records]
    duplicates = [candidate_id for candidate_id, count in Counter(candidate_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate candidate_id rows: {sorted(duplicates)}")
    for record in records:
        validate_ml_ready_row(record)


def build_manifest(records: list[dict[str, Any]], *, run_id: str) -> dict[str, Any]:
    metric_available_count = sum(record.get("metric_source") == APPROVED_METRIC_SOURCE for record in records)
    candidate_level_metric_count = sum(
        record.get("metric_source") == APPROVED_METRIC_SOURCE
        and record.get("metric_subject_type") == "strategy_candidate"
        and record.get("candidate_metric_match") is True
    for record in records)
    generic_proxy_metric_count = sum(
        record.get("metric_role") == GENERIC_PROXY_LABEL_ROLE
        or record.get("metric_subject_type") == "generic_proxy"
        for record in records
    )
    blocked_generic_proxy_count = sum(
        record.get("label_decision") == BLOCKED_GENERIC_PROXY for record in records
    )
    null_missing_evidence_count = sum(record.get("label_decision") == NULL_MISSING_EVIDENCE for record in records)
    null_missing_candidate_level_metric_count = sum(
        record.get("label_decision") == NULL_MISSING_CANDIDATE_LEVEL_METRIC for record in records
    )
    excluded_untradable_count = sum(record.get("label_decision") == EXCLUDED_UNTRADABLE for record in records)
    excluded_failure_count = sum(record.get("label_decision") == EXCLUDED_FAILURE for record in records)
    blocked_not_candidate_level_count = sum(record.get("label_decision") == BLOCKED_NOT_CANDIDATE_LEVEL for record in records)
    rule_inconclusive_count = sum(record.get("label_decision") == RULE_INCONCLUSIVE for record in records)
    label_positive_count = sum(record.get("label_decision") == LABEL_POSITIVE for record in records)
    label_negative_count = sum(record.get("label_decision") == LABEL_NEGATIVE for record in records)
    actual_label_count = sum(record.get("actual_label_source") == APPROVED_LABEL_SOURCE for record in records)
    supervised_label_count = sum(record.get("supervised_label_eligible") is True for record in records)
    has_positive_negative_classes = label_positive_count > 0 and label_negative_count > 0
    adoption_review_eligible_count = sum(record.get("adoption_review_eligible") is True for record in records)
    prediction_count = sum(any(record.get(column) is not None for column in PREDICTION_VALUE_COLUMNS) for record in records)
    benchmark_cost_adjusted_count = sum(
        record.get("benchmark_return_before_cost") is not None
        and record.get("benchmark_return_after_cost") is not None
        and record.get("benchmark_return_before_cost") != record.get("benchmark_return_after_cost")
        for record in records
    )
    benchmark_cost_profile_ids = sorted(
        str(record.get("benchmark_cost_profile_id"))
        for record in records
        if record.get("benchmark_cost_profile_id")
    )
    benchmark_cost_markets = sorted(
        str(record.get("benchmark_cost_market"))
        for record in records
        if record.get("benchmark_cost_market")
    )
    training_status_counts = Counter(str(record.get("ml_training_status")) for record in records)
    evaluation_status_counts = Counter(str(record.get("evaluation_status")) for record in records)
    approval_required_next_steps = []
    if training_status_counts.get("blocked_generic_proxy_metric_summary", 0):
        approval_required_next_steps.append("replace_generic_momentum_proxy_with_candidate_specific_evaluation_before_training")
    if candidate_level_metric_count == 0 and evaluation_status_counts.get("invalidated", 0):
        approval_required_next_steps.append("repair_invalidated_evaluation_evidence_before_actual_labels")
    elif candidate_level_metric_count == 0:
        approval_required_next_steps.append("convert_contract_only_momentum_evaluation_evidence_to_actual_runs")
    if any(
            record.get("metric_source") == APPROVED_METRIC_SOURCE
            and record.get("adoption_required_checks_ready") is not True
            for record in records
    ):
        approval_required_next_steps.append("run_walk_forward_or_oos_stability_check_before_adoption_review")
    if has_positive_negative_classes:
        approval_required_next_steps.append("train_momentum_only_surrogate_after_metric_summary_exists")
    if candidate_level_metric_count == 0:
        model_training_status = "blocked_binary_supervised_ml_no_candidate_level_labels"
    elif supervised_label_count == 0:
        model_training_status = "blocked_no_supervised_label_eligible_rows"
    elif not has_positive_negative_classes:
        model_training_status = "blocked_no_positive_negative_classes"
    else:
        model_training_status = "labels_available_for_later_approval"
    if model_training_status == "blocked_binary_supervised_ml_no_candidate_level_labels":
        binary_supervised_ml_status = "blocked_no_candidate_level_supervised_labels"
    elif model_training_status == "blocked_no_supervised_label_eligible_rows":
        binary_supervised_ml_status = "blocked_no_candidate_level_supervised_labels"
    elif model_training_status == "blocked_no_positive_negative_classes":
        binary_supervised_ml_status = "blocked_no_positive_negative_classes"
    else:
        binary_supervised_ml_status = "candidate_level_supervised_labels_available_for_later_approval"
    return {
        "schema_version": "v0_3_candidate_ml_input_manifest_0_2",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "record_count": len(records),
        "total_rows": len(records),
        "metric_available_count": metric_available_count,
        "candidate_level_metric_count": candidate_level_metric_count,
        "generic_proxy_metric_count": generic_proxy_metric_count,
        "blocked_generic_proxy_not_candidate_level": blocked_generic_proxy_count,
        "null_missing_evidence": null_missing_evidence_count,
        "null_missing_candidate_level_metric": null_missing_candidate_level_metric_count,
        "excluded_untradable": excluded_untradable_count,
        "excluded_failure": excluded_failure_count,
        "blocked_not_candidate_level": blocked_not_candidate_level_count,
        "rule_inconclusive": rule_inconclusive_count,
        "label_positive": label_positive_count,
        "label_negative": label_negative_count,
        "actual_label_count": actual_label_count,
        "prediction_value_row_count": prediction_count,
        "benchmark_cost_adjusted_row_count": benchmark_cost_adjusted_count,
        "benchmark_cost_profile_ids": sorted(set(benchmark_cost_profile_ids)),
        "benchmark_cost_markets": sorted(set(benchmark_cost_markets)),
        "benchmark_cost_policy": "config_driven_benchmark_cost_items_adjust_benchmark_return_when_benchmark_return_available",
        "supervised_label_eligible_count": supervised_label_count,
        "adoption_review_eligible_count": adoption_review_eligible_count,
        "time_aware_split_ready_count": sum(record.get("time_aware_split_ready") is True for record in records),
        "candidate_status_counts": dict(sorted(Counter(str(record.get("candidate_status")) for record in records).items())),
        "evaluation_status_counts": dict(sorted(evaluation_status_counts.items())),
        "strategy_type_counts": dict(sorted(Counter(str(record.get("strategy_type")) for record in records).items())),
        "ml_training_status_counts": dict(sorted(training_status_counts.items())),
        "model_training_status": model_training_status,
        "binary_supervised_ml_status": binary_supervised_ml_status,
        "generic_proxy_policy": "generic_proxy_metrics_are_benchmark_reference_feature_candidates_not_labels",
        "prediction_policy": "predictions_are_for_prioritization_active_learning_uncertainty_ranking_review_triage_only",
        "approval_required_next_steps": approval_required_next_steps,
        "no_feedback_check": "ml_ready_inputs_must_not_feed_scores_rankings_reports_backtests_trading_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_ml_ready_candidate_inputs(
    selector_input: Path,
    registry: Path,
    evidence_dir: Path,
    output_dir: Path,
    *,
    label_rule_config: Path = DEFAULT_LABEL_RULES,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    records = build_ml_ready_candidate_input_records(
        selector_input,
        registry,
        evidence_dir,
        label_rule_config=label_rule_config,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    write_jsonl(jsonl_path, records)
    manifest = build_manifest(records, run_id=run_id)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths = {"jsonl": jsonl_path, "manifest": manifest_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        write_csv(csv_path, records)
        paths["csv"] = csv_path
    return paths


def build_ml_ready_candidate_input_records(
    selector_input: Path,
    registry: Path,
    evidence_dir: Path,
    *,
    label_rule_config: Path = DEFAULT_LABEL_RULES,
) -> list[dict[str, Any]]:
    selector_records = read_jsonl(selector_input)
    registry_records = read_jsonl(registry)
    evidence_records = read_evaluation_evidence_dir(evidence_dir)
    label_rules = read_label_rules(label_rule_config)

    selector_by_card = {
        str(record.get("evidence_card_id")): record
        for record in selector_records
        if record.get("evidence_card_id")
    }
    evidence_by_candidate = evidence_index_by_candidate(evidence_records)
    row_generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    records: list[dict[str, Any]] = []
    for registry_record in sorted(
        registry_records,
        key=lambda record: str(_get(record, "strategy_candidate.candidate_id") or ""),
    ):
        candidate_id = str(_get(registry_record, "strategy_candidate.candidate_id") or "")
        evidence_card_id = evidence_card_id_from_candidate(candidate_id, registry_record)
        records.append(
            build_ml_ready_row(
                registry_record,
                selector_by_card.get(str(evidence_card_id)),
                evidence_by_candidate.get(candidate_id),
                registry_ref=registry,
                selector_ref=selector_input,
                label_rules=label_rules,
                label_rule_ref=label_rule_config,
                row_generated_at=row_generated_at,
            )
        )

    validate_ml_ready_rows(records)
    return records


def dry_run_ml_ready_candidate_inputs(
    selector_input: Path,
    registry: Path,
    evidence_dir: Path,
    *,
    label_rule_config: Path = DEFAULT_LABEL_RULES,
    run_id: str,
) -> dict[str, Any]:
    records = build_ml_ready_candidate_input_records(
        selector_input,
        registry,
        evidence_dir,
        label_rule_config=label_rule_config,
    )
    manifest = build_manifest(records, run_id=run_id)
    return {
        "mode": "dry_run",
        "output_written": False,
        "record_count": len(records),
        "manifest": manifest,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-input", type=Path, default=DEFAULT_SELECTOR_INPUT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--label-rule-config", type=Path, default=DEFAULT_LABEL_RULES)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("ml_ready_candidate_input_%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate rows, then print a manifest summary without writing outputs.",
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        result = dry_run_ml_ready_candidate_inputs(
            args.selector_input,
            args.registry,
            args.evidence_dir,
            label_rule_config=args.label_rule_config,
            run_id=args.run_id,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    paths = build_ml_ready_candidate_inputs(
        args.selector_input,
        args.registry,
        args.evidence_dir,
        args.output_dir,
        label_rule_config=args.label_rule_config,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
