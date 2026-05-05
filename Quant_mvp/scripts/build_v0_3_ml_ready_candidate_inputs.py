"""Build v0.3 candidate-level ML-ready input rows.

The generated rows are candidate/evidence metadata for ML/evaluator review.
Actual outcome labels are populated only from approved EvaluationEvidence
records with metric summaries. Surrogate prediction columns stay separate and
must not be used as supervised labels or adoption evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
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


DEFAULT_SELECTOR_INPUT = Path("Quant_mvp/data/v0_3/selector_inputs/v0_3_selector_input.jsonl")
DEFAULT_REGISTRY = Path("Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl")
DEFAULT_EVIDENCE_DIR = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/ml_ready_candidate_inputs")
DEFAULT_JSONL_NAME = "v0_3_ml_ready_candidate_input.jsonl"
DEFAULT_CSV_NAME = "v0_3_ml_ready_candidate_input.csv"
DEFAULT_MANIFEST_NAME = "v0_3_ml_ready_candidate_input_manifest.json"

SCHEMA_VERSION = "v0_3_candidate_ml_input_0_1"
ROW_BOUNDARY = (
    "This candidate ML input row is evidence-only metadata for evaluator "
    "review. It is not a production ranking input, not a trading signal, not "
    "an adoption decision, and not automatic production activation."
)
SPLIT_POLICY = "time_aware_required_before_training"
UNLABELED_SOURCE = "unlabeled"
APPROVED_LABEL_SOURCE = "approved_evaluation_evidence"
PSEUDO_LABEL_SOURCE = "pseudo_model"

ACTUAL_LABEL_COLUMNS = [
    "actual_total_return",
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


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


def _parse_json_from_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"{path} does not contain a json fenced block")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} json fenced block is not an object")
    payload["_source_path"] = str(path)
    return payload


def read_evaluation_evidence_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for evidence_path in sorted(path.rglob("ee_v0_3_*.md")):
        records.append(_parse_json_from_markdown(evidence_path))
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


def _approved_actual_labels(evidence: dict[str, Any] | None) -> dict[str, Any]:
    labels = {column: None for column in ACTUAL_LABEL_COLUMNS}
    if not evidence:
        return labels
    if evidence.get("status") != "evidence_recorded":
        return labels
    if not isinstance(evidence.get("metric_summary"), dict):
        return labels
    if _as_list(evidence.get("failure_flags")):
        return labels
    if _generic_proxy_evidence(evidence):
        return labels

    labels["actual_total_return"] = _path_value(
        evidence,
        ["performance_metric_summary.total_return", "metric_summary.total_return"],
    )
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
    return GENERIC_PROXY_LIMITATION in _as_list(evidence.get("known_limitations"))


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


def build_ml_ready_row(
    registry_record: dict[str, Any],
    selector_record: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
    *,
    registry_ref: Path,
    selector_ref: Path,
    row_generated_at: str,
) -> dict[str, Any]:
    candidate = registry_record.get("strategy_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("registry record missing strategy_candidate")
    candidate_id = str(candidate.get("candidate_id") or "")
    if not candidate_id:
        raise ValueError("strategy_candidate.candidate_id is required")

    evidence_card_id = evidence_card_id_from_candidate(candidate_id, registry_record)
    evaluation_window_start, evaluation_window_end = _evaluation_window(evidence, candidate)
    evidence_status = evidence.get("status") if evidence else "missing_evaluation_evidence"
    metric_summary_available = isinstance(_get(evidence, "metric_summary"), dict) if evidence else False
    adoption_checks_ready = _adoption_checks_ready(evidence)
    actual_labels = _approved_actual_labels(evidence)
    actual_present = any(value is not None for value in actual_labels.values())
    generic_proxy_label = bool(evidence and _generic_proxy_evidence(evidence))
    actual_label_source = APPROVED_LABEL_SOURCE if actual_present else None
    label_source = actual_label_source or UNLABELED_SOURCE
    failure_flags = _compact_list(evidence.get("failure_flags") if evidence else [])
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
        **actual_labels,
        "label_source": label_source,
        "actual_label_source": actual_label_source,
        "actual_label_evidence_id": evidence.get("evaluation_id") if actual_label_source else None,
        "actual_label_generated_at": evidence.get("updated_at") if actual_label_source else None,
        "actual_label_blocked_reason": GENERIC_PROXY_BLOCKED_REASON if generic_proxy_label else None,
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
        "supervised_label_eligible": bool(actual_label_source) and not generic_proxy_label,
        "adoption_review_eligible": bool(
            actual_label_source
            and evidence_status == "evidence_recorded"
            and metric_summary_available
            and not failure_flags
            and adoption_checks_ready
        ),
        "ml_training_status": (
            "blocked_generic_proxy_metric_summary"
            if generic_proxy_label
            else "eligible_actual_label" if actual_label_source else "blocked_no_actual_metric_summary"
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
        "actual_label_source",
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
    if actual_present and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("actual_* labels require approved EvaluationEvidence source")
    if row.get("actual_label_source") == APPROVED_LABEL_SOURCE:
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
    elif actual_present:
        raise ValueError("actual_* labels must stay null without approved evidence")

    if row.get("label_source") == PSEUDO_LABEL_SOURCE and row.get("supervised_label_eligible") is True:
        raise ValueError("pseudo_model rows are not supervised training labels")
    if row.get("supervised_label_eligible") is True and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("supervised labels require approved actual evidence")
    if row.get("adoption_review_eligible") is True and row.get("actual_label_source") != APPROVED_LABEL_SOURCE:
        raise ValueError("adoption review requires actual evidence, not pseudo evidence")
    if row.get("adoption_review_eligible") is True and row.get("adoption_required_checks_ready") is not True:
        raise ValueError("adoption review requires completed required evidence checks")

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
    actual_label_count = sum(record.get("actual_label_source") == APPROVED_LABEL_SOURCE for record in records)
    prediction_count = sum(any(record.get(column) is not None for column in PREDICTION_VALUE_COLUMNS) for record in records)
    training_status_counts = Counter(str(record.get("ml_training_status")) for record in records)
    evaluation_status_counts = Counter(str(record.get("evaluation_status")) for record in records)
    approval_required_next_steps = []
    if training_status_counts.get("blocked_generic_proxy_metric_summary", 0):
        approval_required_next_steps.append("replace_generic_momentum_proxy_with_candidate_specific_evaluation_before_training")
    if actual_label_count == 0 and evaluation_status_counts.get("invalidated", 0):
        approval_required_next_steps.append("repair_invalidated_evaluation_evidence_before_actual_labels")
    elif actual_label_count == 0:
        approval_required_next_steps.append("convert_contract_only_momentum_evaluation_evidence_to_actual_runs")
    if any(
        record.get("actual_label_source") == APPROVED_LABEL_SOURCE
        and record.get("adoption_required_checks_ready") is not True
        for record in records
    ):
        approval_required_next_steps.append("run_walk_forward_or_oos_stability_check_before_adoption_review")
    if actual_label_count > 0:
        approval_required_next_steps.append("train_momentum_only_surrogate_after_metric_summary_exists")
    return {
        "schema_version": "v0_3_candidate_ml_input_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "record_count": len(records),
        "actual_label_count": actual_label_count,
        "prediction_value_row_count": prediction_count,
        "supervised_label_eligible_count": sum(record.get("supervised_label_eligible") is True for record in records),
        "adoption_review_eligible_count": sum(record.get("adoption_review_eligible") is True for record in records),
        "time_aware_split_ready_count": sum(record.get("time_aware_split_ready") is True for record in records),
        "candidate_status_counts": dict(sorted(Counter(str(record.get("candidate_status")) for record in records).items())),
        "evaluation_status_counts": dict(sorted(evaluation_status_counts.items())),
        "strategy_type_counts": dict(sorted(Counter(str(record.get("strategy_type")) for record in records).items())),
        "ml_training_status_counts": dict(sorted(training_status_counts.items())),
        "model_training_status": (
            "blocked_no_metric_summary_labels" if actual_label_count == 0 else "labels_available_for_later_approval"
        ),
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
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    selector_records = read_jsonl(selector_input)
    registry_records = read_jsonl(registry)
    evidence_records = read_evaluation_evidence_dir(evidence_dir)

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
                row_generated_at=row_generated_at,
            )
        )

    validate_ml_ready_rows(records)
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-input", type=Path, default=DEFAULT_SELECTOR_INPUT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("ml_ready_candidate_input_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = build_ml_ready_candidate_inputs(
        args.selector_input,
        args.registry,
        args.evidence_dir,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
