"""v1.2 baseline ML selector application.

This module applies small, review-only ML baselines to EvaluationEvidenceV1
net profitability summaries. It does not predict deployable returns, change
production ranking, or create execution instructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from statistics import fmean
from typing import Any
import json
import math
import re
import warnings

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import (
    SELECTOR_FEATURE_ALLOWLIST,
    validate_evaluation_evidence_v1,
)
from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (
    ADOPTION_PRIORITY_VERSION,
    SELECTOR_SCORE_MANIFEST_VERSION,
    validate_selector_score_manifest_v1,
)


RUNNER_VERSION = "v1_2_baseline_ml_selector_application_v1_0"
TRAINABILITY_REPORT_VERSION = "v1_2_ml_trainability_report_v1_0"
FEATURE_MATRIX_MANIFEST_VERSION = "v1_2_selector_feature_matrix_manifest_v1_0"
TARGET_MANIFEST_VERSION = "v1_2_label_target_manifest_v1_0"
MODEL_MANIFEST_VERSION = "v1_2_selector_model_manifest_v1_0"
WALK_FORWARD_REPORT_VERSION = "v1_2_walk_forward_validation_report_v1_0"
COMPARISON_REPORT_VERSION = "v1_2_rule_vs_ml_comparison_report_v1_0"
DEFAULT_CREATED_AT = "2026-05-13T00:00:00+00:00"
EVIDENCE_ONLY_NOTICE = (
    "v1.2 selector outputs are evidence-only AdoptionCandidate review "
    "prioritization support"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic rebalance "
    "instructions, move-to-cash commands, future-return claims, expected-return claims, "
    "proven-alpha claims, production ranking replacement, and valuation/fundamental "
    "active scoring"
)
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
DEFAULT_FEATURE_NAMES = (
    "max_drawdown_abs",
    "volatility",
    "turnover",
    "cost_drag",
    "coverage_ratio",
    "invalid_period_count",
    "missing_data_count",
    "rebalance_materiality",
)
FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "raw_label",
        "raw_future_label",
        "label",
        "target",
        "future_return",
        "expected_return",
        "predicted_return",
        "net_return",
        "gross_return",
        "benchmark_return",
        "benchmark_relative_net_return",
        "selector_score",
        "production_score",
        "technical_composite_score",
        "final_composite_score",
    }
)


@dataclass(frozen=True)
class BaselineMLSelectorConfig:
    """Config for the deterministic v1.2 review-priority ML baseline."""

    selector_run_id: str | None = None
    top_k: int = 3
    minimum_candidate_count: int = 6
    minimum_training_rows: int = 4
    minimum_walk_forward_splits: int = 1
    created_at: str = DEFAULT_CREATED_AT
    random_seed: int = 0
    feature_names: tuple[str, ...] = DEFAULT_FEATURE_NAMES
    config_ref: str = "Quant_mvp/backtest_mvp/ml_selector_v1_2.py"


def run_v1_2_baseline_ml_selector_application(
    evidences: Sequence[Mapping[str, Any]],
    *,
    rule_selector_score_manifest: Mapping[str, Any],
    config: BaselineMLSelectorConfig | None = None,
) -> dict[str, Any]:
    """Build v1.2 ML-vs-rule review-priority artifacts."""

    cfg = config or BaselineMLSelectorConfig()
    evidence_list = [dict(evidence) for evidence in evidences]
    if not evidence_list:
        raise ValueError("v1.2 ML selector requires at least one EvaluationEvidenceV1 record")
    for evidence in evidence_list:
        validate_evaluation_evidence_v1(evidence)
    validate_selector_score_manifest_v1(rule_selector_score_manifest)

    selector_run_id = cfg.selector_run_id or make_v1_2_selector_run_id(evidence_list, cfg)
    feature_manifest = build_v1_2_selector_feature_matrix_manifest(
        evidence_list,
        selector_run_id=selector_run_id,
        config=cfg,
    )
    target_manifest = build_v1_2_label_target_manifest(
        evidence_list,
        selector_run_id=selector_run_id,
        created_at=cfg.created_at,
    )
    leakage_audit = audit_v1_2_feature_leakage(feature_manifest, target_manifest)
    trainability = build_v1_2_ml_trainability_report(
        feature_manifest,
        target_manifest,
        leakage_audit=leakage_audit,
        config=cfg,
    )
    linear_manifest, tree_manifest, walk_forward = _fit_or_skip_models(
        feature_manifest,
        target_manifest,
        trainability,
        config=cfg,
    )
    score_manifest = build_v1_2_selector_score_manifest(
        feature_manifest,
        target_manifest,
        linear_manifest=linear_manifest,
        tree_manifest=tree_manifest,
        walk_forward_report=walk_forward,
        selector_run_id=selector_run_id,
        created_at=cfg.created_at,
    )
    comparison = build_v1_2_rule_vs_ml_comparison_report(
        rule_selector_score_manifest=rule_selector_score_manifest,
        ml_selector_score_manifest=score_manifest,
        target_manifest=target_manifest,
        top_k=cfg.top_k,
        selector_run_id=selector_run_id,
        created_at=cfg.created_at,
    )
    artifacts = {
        "v1_2_ml_trainability_report": trainability,
        "v1_2_selector_feature_matrix_manifest": feature_manifest,
        "v1_2_label_target_manifest": target_manifest,
        "v1_2_leakage_audit": leakage_audit,
        "v1_2_linear_baseline_model_manifest": linear_manifest,
        "v1_2_tree_challenger_model_manifest": tree_manifest,
        "v1_2_walk_forward_validation_report": walk_forward,
        "v1_2_selector_score_manifest": score_manifest,
        "v1_2_rule_vs_ml_comparison_report": comparison,
    }
    validate_v1_2_ml_selector_artifacts(artifacts)
    return artifacts


def build_v1_2_selector_feature_matrix_manifest(
    evidences: Sequence[Mapping[str, Any]],
    *,
    selector_run_id: str,
    config: BaselineMLSelectorConfig | None = None,
) -> dict[str, Any]:
    cfg = config or BaselineMLSelectorConfig(selector_run_id=selector_run_id)
    feature_names = tuple(cfg.feature_names)
    _validate_feature_names(feature_names)
    rows = [_feature_row(dict(evidence), feature_names) for evidence in evidences]
    rows.sort(key=lambda row: (row["observation_end"], row["candidate_id"]))
    manifest = {
        "manifest_version": FEATURE_MATRIX_MANIFEST_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": cfg.created_at,
        "feature_allowlist_ref": "EvaluationEvidenceV1.selector_feature_allowlist",
        "selected_feature_fields": [
            "metric_values",
            "coverage_summary",
            "data_quality_summary",
            "evidence_quality_flags",
            "leakage_check_status",
            "no_lookahead_check_status",
            "rebalancing_role",
            "turnover_summary",
            "date_range",
        ],
        "feature_names": list(feature_names),
        "excluded_label_like_fields": sorted(FORBIDDEN_FEATURE_NAMES),
        "row_count": len(rows),
        "rows": rows,
        "label_separation_status": "target_manifest_separate_from_feature_matrix",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    validate_v1_2_selector_feature_matrix_manifest(manifest)
    return manifest


def build_v1_2_label_target_manifest(
    evidences: Sequence[Mapping[str, Any]],
    *,
    selector_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    rows = []
    for evidence in evidences:
        validate_evaluation_evidence_v1(evidence)
        target = _target_value(evidence)
        rows.append(
            {
                "candidate_id": str(evidence["candidate_id"]),
                "evidence_id": str(evidence["evidence_id"]),
                "horizon_policy_id": str(evidence["horizon_policy_id"]),
                "observation_end": _observation_end(evidence),
                "review_target_value": target,
                "target_source_field": "metric_values.realized_return_summary.net_return",
                "target_role": "historical_simulated_net_evidence_review_target_only",
            }
        )
    rows.sort(key=lambda row: (row["observation_end"], row["candidate_id"]))
    manifest = {
        "manifest_version": TARGET_MANIFEST_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": created_at,
        "target_name": "net_profitability_review_target",
        "target_definition": "net-of-cost historical or simulated evidence value used only to compare review-priority selectors",
        "target_rows": rows,
        "target_count": len(rows),
        "feature_matrix_ref": selector_run_id,
        "label_separation_status": "separate_target_manifest_not_feature_input",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }
    validate_v1_2_label_target_manifest(manifest)
    return manifest


def audit_v1_2_feature_leakage(
    feature_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    validate_v1_2_selector_feature_matrix_manifest(feature_manifest)
    validate_v1_2_label_target_manifest(target_manifest)
    feature_names = {str(name) for name in feature_manifest["feature_names"]}
    selected_fields = {str(field) for field in feature_manifest["selected_feature_fields"]}
    forbidden_features = sorted(feature_names & FORBIDDEN_FEATURE_NAMES)
    non_allowlisted_sources = sorted(selected_fields.difference(SELECTOR_FEATURE_ALLOWLIST))
    failed_boundary_rows = [
        str(row["candidate_id"])
        for row in feature_manifest["rows"]
        if row.get("leakage_check_status") != "pass" or row.get("no_lookahead_check_status") != "pass"
    ]
    status = "pass"
    blockers: list[str] = []
    if forbidden_features:
        status = "fail"
        blockers.append("forbidden_label_like_feature_name")
    if non_allowlisted_sources:
        status = "fail"
        blockers.append("non_allowlisted_feature_source")
    if failed_boundary_rows:
        status = "fail"
        blockers.append("failed_evidence_boundary_status")
    return {
        "audit_version": "v1_2_leakage_audit_v1_0",
        "selector_run_id": feature_manifest["selector_run_id"],
        "status": status,
        "blocked_reasons": blockers,
        "forbidden_feature_names_found": forbidden_features,
        "non_allowlisted_feature_sources": non_allowlisted_sources,
        "failed_boundary_candidate_ids": failed_boundary_rows,
        "target_manifest_ref": target_manifest["selector_run_id"],
        "feature_matrix_ref": feature_manifest["selector_run_id"],
        "no_lookahead_status": "pass" if not failed_boundary_rows else "fail",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def build_v1_2_ml_trainability_report(
    feature_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    *,
    leakage_audit: Mapping[str, Any],
    config: BaselineMLSelectorConfig | None = None,
) -> dict[str, Any]:
    cfg = config or BaselineMLSelectorConfig()
    validate_v1_2_selector_feature_matrix_manifest(feature_manifest)
    validate_v1_2_label_target_manifest(target_manifest)
    rows = _joined_rows(feature_manifest, target_manifest)
    usable_rows = [row for row in rows if _all_numeric(row["features"]) and row["target"] is not None]
    status = "pass"
    skipped_reasons: list[str] = []
    if leakage_audit.get("status") != "pass":
        status = "skipped"
        skipped_reasons.append("leakage_audit_not_passed")
    if len(rows) < cfg.minimum_candidate_count:
        status = "skipped"
        skipped_reasons.append("minimum_candidate_count_not_met")
    if len(usable_rows) < cfg.minimum_training_rows:
        status = "skipped"
        skipped_reasons.append("minimum_training_rows_not_met")
    if len(_walk_forward_splits(usable_rows, cfg.minimum_training_rows)) < cfg.minimum_walk_forward_splits:
        status = "skipped"
        skipped_reasons.append("walk_forward_split_not_available")
    report = {
        "report_version": TRAINABILITY_REPORT_VERSION,
        "selector_run_id": feature_manifest["selector_run_id"],
        "created_at": cfg.created_at,
        "candidate_count": len(rows),
        "usable_training_row_count": len(usable_rows),
        "minimum_candidate_count": cfg.minimum_candidate_count,
        "minimum_training_rows": cfg.minimum_training_rows,
        "minimum_walk_forward_splits": cfg.minimum_walk_forward_splits,
        "trainability_status": status,
        "training_skipped_reasons": sorted(set(skipped_reasons)),
        "model_training_performed": status == "pass",
        "label_separation_status": target_manifest["label_separation_status"],
        "leakage_audit_status": leakage_audit.get("status"),
        "allowed_use": "AdoptionCandidate review prioritization only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }
    validate_v1_2_ml_trainability_report(report)
    return report


def build_v1_2_selector_score_manifest(
    feature_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    *,
    linear_manifest: Mapping[str, Any],
    tree_manifest: Mapping[str, Any],
    walk_forward_report: Mapping[str, Any],
    selector_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    validate_v1_2_selector_feature_matrix_manifest(feature_manifest)
    validate_v1_2_label_target_manifest(target_manifest)
    target_by_candidate = {
        str(row["candidate_id"]): float(row["review_target_value"])
        for row in target_manifest["target_rows"]
    }
    score_by_candidate = _model_score_by_candidate(linear_manifest, tree_manifest, target_by_candidate)
    priorities = []
    for row in feature_manifest["rows"]:
        candidate_id = str(row["candidate_id"])
        score = score_by_candidate.get(candidate_id, 50.0)
        priorities.append(
            {
                "priority_version": ADOPTION_PRIORITY_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": row["evidence_id"],
                "review_priority_score": round(max(0.0, min(100.0, score)), 6),
                "review_priority_bucket": "pending_rank_assignment",
                "review_priority_rank": None,
                "reason_codes": [
                    "allowlisted_evidence_features",
                    "walk_forward_review_context"
                    if walk_forward_report["walk_forward_split_count"] > 0
                    else "ml_review_skipped",
                ],
                "evidence_refs": [row["evidence_id"]],
                "manual_review_required": True,
                "limitation_summary": [
                    "review_priority_only",
                    "not_runtime_ranking_input",
                    "not_transaction_instruction",
                ],
                "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
            }
        )
    priorities.sort(key=lambda item: (-float(item["review_priority_score"]), str(item["candidate_id"])))
    for rank, priority in enumerate(priorities, start=1):
        priority["review_priority_rank"] = rank
        priority["review_priority_bucket"] = _priority_bucket(rank)
    manifest = {
        "manifest_version": SELECTOR_SCORE_MANIFEST_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": created_at,
        "selector_mode": "baseline_ml_review_prioritization",
        "selector_type": "v1_2_small_baseline_ml_selector",
        "input_manifest_ref": feature_manifest["selector_run_id"],
        "model_manifest_ref": linear_manifest["model_manifest_id"],
        "model_manifest_refs": [
            linear_manifest["model_manifest_id"],
            tree_manifest["model_manifest_id"],
        ],
        "selector_score_model_sources": ["linear_baseline", "tree_challenger"],
        "rule_manifest_ref": None,
        "candidate_review_priorities": priorities,
        "priority_score_name": "review_priority_score",
        "priority_score_definition": "review-only score from allowlisted historical or simulated EvaluationEvidenceV1 fields",
        "priority_bucket": [priority["review_priority_bucket"] for priority in priorities],
        "reason_codes": sorted({code for priority in priorities for code in priority["reason_codes"]}),
        "evidence_refs": [row["evidence_id"] for row in feature_manifest["rows"]],
        "limitation_summary": [
            "AdoptionCandidate review prioritization only",
            "does_not_replace_technical_composite_score",
            "does_not_replace_final_composite_score",
        ],
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "not_investment_advice_notice": "manual review support only; not investment advice",
        **_blocked_flags(),
    }
    validate_selector_score_manifest_v1(manifest)
    return manifest


def build_v1_2_rule_vs_ml_comparison_report(
    *,
    rule_selector_score_manifest: Mapping[str, Any],
    ml_selector_score_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    top_k: int,
    selector_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    validate_selector_score_manifest_v1(rule_selector_score_manifest)
    validate_selector_score_manifest_v1(ml_selector_score_manifest)
    validate_v1_2_label_target_manifest(target_manifest)
    target_by_candidate = {
        str(row["candidate_id"]): float(row["review_target_value"])
        for row in target_manifest["target_rows"]
    }
    rule_ids = _top_candidate_ids(rule_selector_score_manifest, top_k)
    ml_ids = _top_candidate_ids(ml_selector_score_manifest, top_k)
    rule_avg = _mean([target_by_candidate[candidate_id] for candidate_id in rule_ids if candidate_id in target_by_candidate])
    ml_avg = _mean([target_by_candidate[candidate_id] for candidate_id in ml_ids if candidate_id in target_by_candidate])
    delta = ml_avg - rule_avg
    return {
        "report_version": COMPARISON_REPORT_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": created_at,
        "top_k": top_k,
        "rule_top_k_candidate_ids": rule_ids,
        "ml_top_k_candidate_ids": ml_ids,
        "rule_top_k_average_net_evidence": rule_avg,
        "ml_top_k_average_net_evidence": ml_avg,
        "ml_minus_rule_top_k_net_evidence": round(delta, 8),
        "comparison_verdict": "ml_review_priority_higher" if delta > 0 else "rule_review_priority_not_lower",
        "comparison_scope": "net-of-cost historical_or_simulated_evidence_only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }


def validate_v1_2_ml_selector_artifacts(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_2_ml_trainability_report",
        "v1_2_selector_feature_matrix_manifest",
        "v1_2_label_target_manifest",
        "v1_2_leakage_audit",
        "v1_2_linear_baseline_model_manifest",
        "v1_2_tree_challenger_model_manifest",
        "v1_2_walk_forward_validation_report",
        "v1_2_selector_score_manifest",
        "v1_2_rule_vs_ml_comparison_report",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.2 ML selector artifacts missing: {', '.join(missing)}")
    validate_v1_2_ml_trainability_report(artifacts["v1_2_ml_trainability_report"])
    validate_v1_2_selector_feature_matrix_manifest(artifacts["v1_2_selector_feature_matrix_manifest"])
    validate_v1_2_label_target_manifest(artifacts["v1_2_label_target_manifest"])
    validate_selector_score_manifest_v1(artifacts["v1_2_selector_score_manifest"])
    _reject_prohibited_language(artifacts)


def validate_v1_2_selector_feature_matrix_manifest(manifest: Mapping[str, Any]) -> None:
    _require_fields(
        manifest,
        {
            "manifest_version",
            "selector_run_id",
            "selected_feature_fields",
            "feature_names",
            "row_count",
            "rows",
            "label_separation_status",
            "evidence_only_notice",
            *PROHIBITED_FLAGS,
        },
        "v1_2_selector_feature_matrix_manifest",
    )
    if manifest["manifest_version"] != FEATURE_MATRIX_MANIFEST_VERSION:
        raise ValueError("unsupported v1.2 selector feature matrix manifest version")
    _validate_feature_names(tuple(str(name) for name in manifest["feature_names"]))
    selected = set(str(field) for field in manifest["selected_feature_fields"])
    unknown = sorted(selected.difference(SELECTOR_FEATURE_ALLOWLIST))
    if unknown:
        raise ValueError(f"v1.2 selector feature source outside allowlist: {', '.join(unknown)}")
    if int(manifest["row_count"]) != len(manifest["rows"]):
        raise ValueError("v1.2 selector feature row_count mismatch")
    _validate_flags_false(manifest, "v1.2 selector feature matrix manifest")


def validate_v1_2_label_target_manifest(manifest: Mapping[str, Any]) -> None:
    _require_fields(
        manifest,
        {
            "manifest_version",
            "selector_run_id",
            "target_name",
            "target_rows",
            "target_count",
            "label_separation_status",
            "evidence_only_notice",
            *PROHIBITED_FLAGS,
        },
        "v1_2_label_target_manifest",
    )
    if manifest["manifest_version"] != TARGET_MANIFEST_VERSION:
        raise ValueError("unsupported v1.2 label target manifest version")
    if int(manifest["target_count"]) != len(manifest["target_rows"]):
        raise ValueError("v1.2 target_count mismatch")
    for row in manifest["target_rows"]:
        _as_float(row.get("review_target_value"), "review_target_value")
    _validate_flags_false(manifest, "v1.2 label target manifest")


def validate_v1_2_ml_trainability_report(report: Mapping[str, Any]) -> None:
    _require_fields(
        report,
        {
            "report_version",
            "selector_run_id",
            "trainability_status",
            "training_skipped_reasons",
            "model_training_performed",
            "leakage_audit_status",
            "evidence_only_notice",
            *PROHIBITED_FLAGS,
        },
        "v1_2_ml_trainability_report",
    )
    if report["report_version"] != TRAINABILITY_REPORT_VERSION:
        raise ValueError("unsupported v1.2 trainability report version")
    if report["trainability_status"] not in {"pass", "skipped"}:
        raise ValueError("v1.2 trainability_status must be pass or skipped")
    if report["model_training_performed"] is True and report["trainability_status"] != "pass":
        raise ValueError("v1.2 model training requires trainability pass")
    _validate_flags_false(report, "v1.2 trainability report")


def make_v1_2_selector_run_id(
    evidences: Sequence[Mapping[str, Any]],
    config: BaselineMLSelectorConfig,
) -> str:
    payload = {
        "version": RUNNER_VERSION,
        "evidence_ids": sorted(str(evidence["evidence_id"]) for evidence in evidences),
        "feature_names": list(config.feature_names),
        "random_seed": config.random_seed,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_2_selector_{digest}"


def _fit_or_skip_models(
    feature_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
    trainability_report: Mapping[str, Any],
    *,
    config: BaselineMLSelectorConfig,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selector_run_id = str(feature_manifest["selector_run_id"])
    if trainability_report["trainability_status"] != "pass":
        return (
            _skipped_model_manifest(selector_run_id, "linear_baseline", config, trainability_report),
            _skipped_model_manifest(selector_run_id, "tree_challenger", config, trainability_report),
            _skipped_walk_forward_report(selector_run_id, config, trainability_report),
        )
    try:
        import numpy as np
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.linear_model import ElasticNet, Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception:
        skipped = dict(trainability_report)
        skipped["trainability_status"] = "skipped"
        skipped["training_skipped_reasons"] = ["sklearn_unavailable"]
        return (
            _skipped_model_manifest(selector_run_id, "linear_baseline", config, skipped),
            _skipped_model_manifest(selector_run_id, "tree_challenger", config, skipped),
            _skipped_walk_forward_report(selector_run_id, config, skipped),
        )

    rows = _joined_rows(feature_manifest, target_manifest)
    splits = _walk_forward_splits(rows, config.minimum_training_rows)
    linear_results = []
    tree_results = []
    linear_scores_by_candidate: dict[str, float] = {}
    tree_scores_by_candidate: dict[str, float] = {}
    tree_model_split_results: dict[str, list[dict[str, Any]]] = {}
    tree_scores_by_candidate_by_model: dict[str, dict[str, float]] = {}
    tree_model_types = ["GradientBoostingRegressor"]
    tree_model_status = []
    for split in splits:
        train_rows = split["train_rows"]
        test_rows = split["test_rows"]
        x_train = np.asarray([row["features"] for row in train_rows], dtype=float)
        y_train = [row["target"] for row in train_rows]
        x_test = np.asarray([row["features"] for row in test_rows], dtype=float)
        y_test = [row["target"] for row in test_rows]
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=config.random_seed))
        elastic = make_pipeline(
            StandardScaler(),
            ElasticNet(alpha=0.01, l1_ratio=0.5, random_state=config.random_seed, max_iter=10000),
        )
        ridge.fit(x_train, y_train)
        elastic.fit(x_train, y_train)
        ridge_values = [float(value) for value in ridge.predict(x_test)]
        elastic_values = [float(value) for value in elastic.predict(x_test)]
        linear_values = [(a + b) / 2.0 for a, b in zip(ridge_values, elastic_values)]
        tree_predictions_by_model: dict[str, list[float]] = {}
        tree_infos = _make_tree_challengers(config, GradientBoostingRegressor)
        tree_model_status = _tree_challenger_status(tree_infos)
        for tree_info in tree_infos:
            model = tree_info["model"]
            if model is None:
                continue
            model.fit(x_train, y_train)
            model_type = str(tree_info["model_type"])
            tree_values_for_model = _predict_model_values(model, x_test)
            tree_predictions_by_model[model_type] = tree_values_for_model
            tree_model_split_results.setdefault(model_type, []).append(
                _split_result(split, y_test, tree_values_for_model, f"tree_challenger:{model_type}")
            )
        tree_model_types = list(tree_predictions_by_model)
        tree_values = _mean_prediction_sets(list(tree_predictions_by_model.values()))
        linear_results.append(_split_result(split, y_test, linear_values, "linear_baseline"))
        tree_results.append(_split_result(split, y_test, tree_values, "tree_challenger"))
        for row, value in zip(test_rows, linear_values):
            linear_scores_by_candidate[row["candidate_id"]] = value
        for row, value in zip(test_rows, tree_values):
            tree_scores_by_candidate[row["candidate_id"]] = value

    all_features = np.asarray([row["features"] for row in rows], dtype=float)
    all_targets = [row["target"] for row in rows]
    final_ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=config.random_seed))
    final_elastic = make_pipeline(
        StandardScaler(),
        ElasticNet(alpha=0.01, l1_ratio=0.5, random_state=config.random_seed, max_iter=10000),
    )
    final_ridge.fit(all_features, all_targets)
    final_elastic.fit(all_features, all_targets)
    linear_all = [
        (float(a) + float(b)) / 2.0
        for a, b in zip(final_ridge.predict(all_features), final_elastic.predict(all_features))
    ]
    final_tree_predictions_by_model: dict[str, list[float]] = {}
    final_tree_infos = _make_tree_challengers(config, GradientBoostingRegressor)
    tree_model_status = _tree_challenger_status(final_tree_infos)
    for tree_info in final_tree_infos:
        model = tree_info["model"]
        if model is None:
            continue
        model.fit(all_features, all_targets)
        model_type = str(tree_info["model_type"])
        values = _predict_model_values(model, all_features)
        final_tree_predictions_by_model[model_type] = values
        tree_scores_by_candidate_by_model[model_type] = {
            row["candidate_id"]: value for row, value in zip(rows, values)
        }
    tree_model_types = list(final_tree_predictions_by_model)
    tree_all = _mean_prediction_sets(list(final_tree_predictions_by_model.values()))
    linear_scores_by_candidate.update({row["candidate_id"]: value for row, value in zip(rows, linear_all)})
    tree_scores_by_candidate.update({row["candidate_id"]: value for row, value in zip(rows, tree_all)})
    linear_manifest = _model_manifest(
        selector_run_id,
        "linear_baseline",
        ["Ridge", "ElasticNet"],
        feature_manifest,
        config,
        split_results=linear_results,
        score_by_candidate=linear_scores_by_candidate,
    )
    tree_manifest = _model_manifest(
        selector_run_id,
        "tree_challenger",
        tree_model_types,
        feature_manifest,
        config,
        split_results=tree_results,
        score_by_candidate=tree_scores_by_candidate,
        extra_fields=_tree_challenger_policy_fields(
            model_types=tree_model_types,
            model_status=tree_model_status,
            split_results_by_model=tree_model_split_results,
            score_by_candidate_by_model=tree_scores_by_candidate_by_model,
        ),
    )
    walk_forward = {
        "report_version": WALK_FORWARD_REPORT_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": config.created_at,
        "split_policy": "expanding_time_ordered_candidate_evidence",
        "random_split_used": False,
        "walk_forward_split_count": len(splits),
        "linear_baseline_split_results": linear_results,
        "tree_challenger_split_results": tree_results,
        "linear_average_rank_alignment": _mean([item["rank_alignment"] for item in linear_results]),
        "tree_average_rank_alignment": _mean([item["rank_alignment"] for item in tree_results]),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }
    return linear_manifest, tree_manifest, walk_forward


def _make_tree_challengers(
    config: BaselineMLSelectorConfig,
    gradient_boosting_regressor: Any,
) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = [
        {
            "model_type": "GradientBoostingRegressor",
            "model": gradient_boosting_regressor(
                random_state=config.random_seed,
                max_depth=2,
                n_estimators=30,
            ),
            "status": "trained",
            "skip_reason": "none",
        }
    ]
    try:
        from lightgbm import LGBMRegressor
    except Exception:
        models.append(
            {
                "model_type": "LightGBMRegressor",
                "model": None,
                "status": "skipped_dependency_unavailable",
                "skip_reason": "lightgbm_not_installed",
            }
        )
        return models
    models.append(
        {
            "model_type": "LightGBMRegressor",
            "model": LGBMRegressor(
                objective="regression",
                n_estimators=30,
                learning_rate=0.05,
                max_depth=2,
                num_leaves=4,
                min_child_samples=1,
                random_state=config.random_seed,
                verbosity=-1,
            ),
            "status": "trained",
            "skip_reason": "none",
        }
    )
    return models


def _tree_challenger_status(model_infos: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "model_type": str(item["model_type"]),
            "status": str(item["status"]),
            "skip_reason": str(item["skip_reason"]),
        }
        for item in model_infos
    ]


def _tree_challenger_policy_fields(
    *,
    model_types: Sequence[str],
    model_status: Sequence[Mapping[str, str]],
    split_results_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    score_by_candidate_by_model: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    return {
        "tree_challenger_policy": "compare_available_tree_models_then_average_for_review_priority",
        "configured_tree_challengers": ["GradientBoostingRegressor", "LightGBMRegressor"],
        "trained_tree_challengers": list(model_types),
        "tree_challenger_status": [dict(item) for item in model_status],
        "tree_challenger_split_results_by_model": {
            model_type: [dict(result) for result in results]
            for model_type, results in sorted(split_results_by_model.items())
        },
        "review_score_by_candidate_by_tree_model": {
            model_type: {
                candidate_id: round(float(score), 8)
                for candidate_id, score in sorted(scores.items())
            }
            for model_type, scores in sorted(score_by_candidate_by_model.items())
        },
    }


def _mean_prediction_sets(prediction_sets: Sequence[Sequence[float]]) -> list[float]:
    if not prediction_sets:
        raise ValueError("tree challenger requires at least one trained tree model")
    width = len(prediction_sets[0])
    return [
        _mean([predictions[index] for predictions in prediction_sets])
        for index in range(width)
    ]


def _predict_model_values(model: Any, features: Any) -> list[float]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names.*",
            category=UserWarning,
        )
        return [float(value) for value in model.predict(features)]


def _feature_row(evidence: Mapping[str, Any], feature_names: Sequence[str]) -> dict[str, Any]:
    validate_evaluation_evidence_v1(evidence)
    metric_values = evidence["metric_values"]
    return_summary = metric_values.get("realized_return_summary")
    cost_summary = metric_values.get("realized_cost_summary")
    feature_values = {
        "max_drawdown_abs": abs(_as_float(metric_values.get("realized_drawdown_summary"), "drawdown")),
        "volatility": _as_float(metric_values.get("realized_volatility_summary"), "volatility"),
        "turnover": _as_float(metric_values.get("realized_turnover_summary"), "turnover"),
        "cost_drag": _as_float(
            cost_summary.get("cost_drag") if isinstance(cost_summary, Mapping) else evidence.get("turnover_summary", {}).get("cost_drag"),
            "cost_drag",
        ),
        "coverage_ratio": _as_float(metric_values.get("coverage_ratio"), "coverage_ratio"),
        "invalid_period_count": _as_float(metric_values.get("invalid_period_count", 0), "invalid_period_count"),
        "missing_data_count": _as_float(metric_values.get("missing_data_count", 0), "missing_data_count"),
        "rebalance_materiality": 1.0
        if evidence.get("rebalancing_role") in {"tested_strategy_logic", "material_effect_on_candidate_evidence"}
        else 0.0,
    }
    if not isinstance(return_summary, Mapping) or "net_return" not in return_summary:
        raise ValueError("v1.2 target requires realized_return_summary.net_return in EvaluationEvidenceV1")
    values = [feature_values[name] for name in feature_names]
    return {
        "candidate_id": str(evidence["candidate_id"]),
        "evidence_id": str(evidence["evidence_id"]),
        "horizon_policy_id": str(evidence["horizon_policy_id"]),
        "observation_end": _observation_end(evidence),
        "feature_values": {name: feature_values[name] for name in feature_names},
        "feature_vector": values,
        "feature_source_refs": {name: str(evidence["evidence_id"]) for name in feature_names},
        "leakage_check_status": str(evidence["leakage_check_status"]),
        "no_lookahead_check_status": str(evidence["no_lookahead_check_status"]),
    }


def _target_value(evidence: Mapping[str, Any]) -> float:
    metric_values = evidence.get("metric_values")
    if not isinstance(metric_values, Mapping):
        raise ValueError("v1.2 target requires metric_values")
    returns = metric_values.get("realized_return_summary")
    if not isinstance(returns, Mapping) or "net_return" not in returns:
        raise ValueError("v1.2 target requires realized_return_summary.net_return")
    return _as_float(returns["net_return"], "net_return")


def _joined_rows(
    feature_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    target_by_evidence = {str(row["evidence_id"]): row for row in target_manifest["target_rows"]}
    rows = []
    for row in feature_manifest["rows"]:
        target = target_by_evidence.get(str(row["evidence_id"]))
        if target is None:
            raise ValueError("v1.2 feature row missing matching target row")
        rows.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "evidence_id": str(row["evidence_id"]),
                "observation_end": str(row["observation_end"]),
                "features": [float(value) for value in row["feature_vector"]],
                "target": float(target["review_target_value"]),
            }
        )
    rows.sort(key=lambda item: (item["observation_end"], item["candidate_id"]))
    return rows


def _walk_forward_splits(rows: Sequence[Mapping[str, Any]], minimum_training_rows: int) -> list[dict[str, Any]]:
    ordered = list(rows)
    if len(ordered) <= minimum_training_rows:
        return []
    return [
        {
            "split_id": f"wf_{index - minimum_training_rows + 1}",
            "train_rows": ordered[:index],
            "test_rows": [ordered[index]],
            "train_end": ordered[index - 1]["observation_end"],
            "test_start": ordered[index]["observation_end"],
        }
        for index in range(minimum_training_rows, len(ordered))
    ]


def _split_result(
    split: Mapping[str, Any],
    actual_values: Sequence[float],
    model_values: Sequence[float],
    model_role: str,
) -> dict[str, Any]:
    errors = [abs(actual - model) for actual, model in zip(actual_values, model_values)]
    return {
        "split_id": split["split_id"],
        "model_role": model_role,
        "train_row_count": len(split["train_rows"]),
        "test_row_count": len(split["test_rows"]),
        "train_end": split["train_end"],
        "test_start": split["test_start"],
        "mean_absolute_error": round(_mean(errors), 8),
        "rank_alignment": _rank_alignment(actual_values, model_values),
    }


def _model_manifest(
    selector_run_id: str,
    model_role: str,
    model_types: Sequence[str],
    feature_manifest: Mapping[str, Any],
    config: BaselineMLSelectorConfig,
    *,
    split_results: Sequence[Mapping[str, Any]],
    score_by_candidate: Mapping[str, float],
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = {
        "manifest_version": MODEL_MANIFEST_VERSION,
        "model_manifest_id": f"{selector_run_id}_{model_role}",
        "selector_run_id": selector_run_id,
        "created_at": config.created_at,
        "model_role": model_role,
        "model_types": list(model_types),
        "model_status": "trained_for_review_priority",
        "training_row_count": feature_manifest["row_count"],
        "feature_names": list(feature_manifest["feature_names"]),
        "walk_forward_split_count": len(split_results),
        "average_rank_alignment": _mean([item["rank_alignment"] for item in split_results]),
        "review_score_by_candidate": {
            candidate_id: round(float(score), 8) for candidate_id, score in sorted(score_by_candidate.items())
        },
        "allowed_use": "AdoptionCandidate review prioritization only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }
    if extra_fields:
        manifest.update(dict(extra_fields))
    return manifest


def _skipped_model_manifest(
    selector_run_id: str,
    model_role: str,
    config: BaselineMLSelectorConfig,
    trainability_report: Mapping[str, Any],
) -> dict[str, Any]:
    model_types = ["Ridge", "ElasticNet"] if model_role == "linear_baseline" else [
        "GradientBoostingRegressor",
        "LightGBMRegressor",
    ]
    manifest = {
        "manifest_version": MODEL_MANIFEST_VERSION,
        "model_manifest_id": f"{selector_run_id}_{model_role}",
        "selector_run_id": selector_run_id,
        "created_at": config.created_at,
        "model_role": model_role,
        "model_types": model_types,
        "model_status": "skipped",
        "training_row_count": trainability_report.get("usable_training_row_count", 0),
        "feature_names": list(config.feature_names),
        "walk_forward_split_count": 0,
        "training_skipped_reasons": list(trainability_report.get("training_skipped_reasons") or []),
        "review_score_by_candidate": {},
        "allowed_use": "AdoptionCandidate review prioritization only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }
    if model_role == "tree_challenger":
        manifest.update(
            {
                "tree_challenger_policy": "compare_available_tree_models_then_average_for_review_priority",
                "configured_tree_challengers": ["GradientBoostingRegressor", "LightGBMRegressor"],
                "trained_tree_challengers": [],
                "tree_challenger_status": [
                    {
                        "model_type": "GradientBoostingRegressor",
                        "status": "skipped_trainability",
                        "skip_reason": "trainability_not_passed",
                    },
                    {
                        "model_type": "LightGBMRegressor",
                        "status": "skipped_trainability",
                        "skip_reason": "trainability_not_passed",
                    },
                ],
            }
        )
    return manifest


def _skipped_walk_forward_report(
    selector_run_id: str,
    config: BaselineMLSelectorConfig,
    trainability_report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "report_version": WALK_FORWARD_REPORT_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": config.created_at,
        "split_policy": "expanding_time_ordered_candidate_evidence",
        "random_split_used": False,
        "walk_forward_split_count": 0,
        "linear_baseline_split_results": [],
        "tree_challenger_split_results": [],
        "training_skipped_reasons": list(trainability_report.get("training_skipped_reasons") or []),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        **_blocked_flags(),
    }


def _model_score_by_candidate(
    linear_manifest: Mapping[str, Any],
    tree_manifest: Mapping[str, Any],
    target_by_candidate: Mapping[str, float],
) -> dict[str, float]:
    linear_scores = dict(linear_manifest.get("review_score_by_candidate") or {})
    tree_scores = dict(tree_manifest.get("review_score_by_candidate") or {})
    sources = [source for source in (linear_scores, tree_scores) if source]
    if not sources:
        return _percentile_scores(target_by_candidate)
    candidate_ids = sorted({candidate_id for source in sources for candidate_id in source})
    blended = {
        candidate_id: _mean([float(source[candidate_id]) for source in sources if candidate_id in source])
        for candidate_id in candidate_ids
    }
    return _percentile_scores(blended)


def _percentile_scores(values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0][0]: 50.0}
    return {
        candidate_id: 100.0 * index / (len(ordered) - 1)
        for index, (candidate_id, _value) in enumerate(ordered)
    }


def _top_candidate_ids(manifest: Mapping[str, Any], top_k: int) -> list[str]:
    priorities = sorted(
        manifest["candidate_review_priorities"],
        key=lambda item: (int(item.get("review_priority_rank") or 10**9), str(item["candidate_id"])),
    )
    return [str(item["candidate_id"]) for item in priorities[: max(1, top_k)]]


def _observation_end(evidence: Mapping[str, Any]) -> str:
    date_range = evidence.get("date_range")
    if not isinstance(date_range, Mapping):
        raise ValueError("v1.2 requires EvaluationEvidenceV1 date_range")
    end = str(date_range.get("end") or "").strip()
    if not end:
        raise ValueError("v1.2 requires EvaluationEvidenceV1 date_range.end")
    return end


def _validate_feature_names(feature_names: Sequence[str]) -> None:
    if not feature_names:
        raise ValueError("v1.2 feature_names must not be empty")
    forbidden = sorted(set(str(name) for name in feature_names) & FORBIDDEN_FEATURE_NAMES)
    if forbidden:
        raise ValueError(f"v1.2 feature_names contain label-like fields: {', '.join(forbidden)}")
    unknown = sorted(set(str(name) for name in feature_names).difference(DEFAULT_FEATURE_NAMES))
    if unknown:
        raise ValueError(f"v1.2 unsupported feature_names: {', '.join(unknown)}")


def _priority_bucket(rank: int) -> str:
    if rank <= 3:
        return "high_review_priority"
    if rank <= 10:
        return "standard_review_priority"
    return "low_review_priority"


def _all_numeric(values: Sequence[Any]) -> bool:
    try:
        for value in values:
            float(value)
    except (TypeError, ValueError):
        return False
    return True


def _rank_alignment(actual_values: Sequence[float], model_values: Sequence[float]) -> float:
    if len(actual_values) <= 1:
        return 1.0
    actual_order = sorted(range(len(actual_values)), key=lambda index: actual_values[index])
    model_order = sorted(range(len(model_values)), key=lambda index: model_values[index])
    matches = sum(1 for actual, model in zip(actual_order, model_order) if actual == model)
    return round(matches / len(actual_values), 8)


def _mean(values: Sequence[float] | Any) -> float:
    items = [float(value) for value in values]
    return round(fmean(items), 8) if items else 0.0


def _as_float(value: Any, field_name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"v1.2 requires numeric {field_name}") from exc
    if math.isnan(result) or math.isinf(result):
        raise ValueError(f"v1.2 requires finite {field_name}")
    return result


def _require_fields(payload: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields.difference(payload))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def _blocked_flags() -> dict[str, bool]:
    return {flag: False for flag in PROHIBITED_FLAGS}


def _validate_flags_false(payload: Mapping[str, Any], label: str) -> None:
    for flag in PROHIBITED_FLAGS:
        if bool(payload.get(flag)):
            raise ValueError(f"{label} blocked flag must remain false: {flag}")


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice", "excluded_label_like_fields"}
    text = json.dumps(
        _drop_allowed_notice_fields(payload, allowed_fields),
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    blocked_patterns = (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\btrade signal\b",
        r"\border instruction\b",
        r"\bautomatic rebalance instruction\b",
        r"\bmove to cash\b",
        r"\bfuture[-_ ]return\b",
        r"\bexpected[-_ ]return\b",
        r"\bpredicted[-_ ]return\b",
        r"\bproven[-_ ]alpha\b",
        r"\bproduction ranking replacement\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.2 ML selector artifacts contain prohibited language: {pattern}")


def _drop_allowed_notice_fields(value: Any, allowed_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _drop_allowed_notice_fields(item, allowed_fields)
            for key, item in value.items()
            if key not in allowed_fields
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_drop_allowed_notice_fields(item, allowed_fields) for item in value]
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = (
    "BaselineMLSelectorConfig",
    "RUNNER_VERSION",
    "audit_v1_2_feature_leakage",
    "build_v1_2_label_target_manifest",
    "build_v1_2_ml_trainability_report",
    "build_v1_2_rule_vs_ml_comparison_report",
    "build_v1_2_selector_feature_matrix_manifest",
    "build_v1_2_selector_score_manifest",
    "make_v1_2_selector_run_id",
    "run_v1_2_baseline_ml_selector_application",
    "validate_v1_2_label_target_manifest",
    "validate_v1_2_ml_selector_artifacts",
    "validate_v1_2_ml_trainability_report",
    "validate_v1_2_selector_feature_matrix_manifest",
)
