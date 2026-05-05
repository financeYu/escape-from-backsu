"""v0.3 EvaluationEvidence execution layer for candidate-only backtests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import json
import re

import pandas as pd

from Quant_mvp.backtest_mvp.candidate_rank_adapter import (
    CandidateRankingSnapshotConfig,
    build_candidate_ranking_snapshot,
)
from Quant_mvp.backtest_mvp.contracts import (
    BacktestConfig,
    ConservativeBacktestResult,
)
from Quant_mvp.backtest_mvp.engine import run_conservative_backtest
from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy


EVALUATION_EVIDENCE_DISCLAIMER = (
    "This EvaluationEvidence record is evidence-only. It is not an adoption "
    "decision and not automatic production activation."
)
DEFAULT_GENERATED_OUTPUT_BOUNDARY = "Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/"
DEFAULT_EVALUATION_METHOD_REF = "Quant_mvp/backtest_mvp/evaluation_evidence.py"
ALLOWED_EVALUATION_OUTPUT_ROOTS = (
    Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence"),
    Path("Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison"),
    Path(DEFAULT_GENERATED_OUTPUT_BOUNDARY),
)
EVALUABLE_STATUSES = frozenset({"evaluable"})
REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "evaluation_id",
        "candidate_id",
        "candidate_version",
        "hypothesis_id",
        "status",
        "owner",
        "created_at",
        "updated_at",
        "source_refs",
        "evaluation_window",
        "universe",
        "assumptions",
        "transaction_cost_assumption",
        "risk_metrics",
        "performance_metrics",
        "comparison_group",
        "evaluation_method_ref",
        "generated_output_boundary",
        "no_lookahead_check",
        "point_in_time_check",
        "generated_output_check",
        "no_feedback_check",
        "v0_2_boundary_check",
        "failure_flags",
        "production_boundary_check",
    }
)


@dataclass(frozen=True)
class EvaluationEvidenceResult:
    """In-memory v0.3 evidence bundle with non-production source objects."""

    evidence: Mapping[str, Any]
    ranking_snapshot: pd.DataFrame
    backtest_result: ConservativeBacktestResult

    def to_dict(self) -> dict[str, Any]:
        return dict(self.evidence)


def run_v0_3_evaluation_evidence(
    candidate_record: Mapping[str, Any],
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    ranking_config: CandidateRankingSnapshotConfig | Mapping[str, Any] | None = None,
    backtest_config: BacktestConfig | Mapping[str, Any] | None = None,
    evaluation_id: str | None = None,
    created_at: str | None = None,
    source_refs: Sequence[str] | None = None,
    generated_output_boundary: str = DEFAULT_GENERATED_OUTPUT_BOUNDARY,
    evaluation_method_ref: str = DEFAULT_EVALUATION_METHOD_REF,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> EvaluationEvidenceResult:
    """Run a candidate-only evaluation and return an EvaluationEvidence record.

    This function is the approved-lane glue between a structured v0.3
    StrategyCandidate, the candidate ranking snapshot adapter, and the
    conservative backtest runner. It does not write production outputs or feed
    metrics upstream.
    """

    candidate = strategy_candidate_payload(candidate_record)
    validate_evaluable_candidate(candidate)
    price_frame = _materialize_price_input(prices)

    ranking_snapshot = build_candidate_ranking_snapshot(
        candidate,
        price_frame,
        config=ranking_config,
        symbol_policy=symbol_policy,
    )
    backtest_result = run_conservative_backtest(
        ranking_snapshot,
        price_frame,
        config=backtest_config,
        symbol_policy=symbol_policy,
    )
    evidence = build_evaluation_evidence_record(
        candidate,
        backtest_result,
        evaluation_id=evaluation_id,
        created_at=created_at,
        source_refs=source_refs,
        generated_output_boundary=generated_output_boundary,
        evaluation_method_ref=evaluation_method_ref,
    )
    validate_evaluation_evidence_record(evidence)
    return EvaluationEvidenceResult(
        evidence=evidence,
        ranking_snapshot=ranking_snapshot,
        backtest_result=backtest_result,
    )


def build_evaluation_evidence_record(
    candidate: Mapping[str, Any],
    backtest_result: ConservativeBacktestResult,
    *,
    evaluation_id: str | None = None,
    created_at: str | None = None,
    source_refs: Sequence[str] | None = None,
    generated_output_boundary: str = DEFAULT_GENERATED_OUTPUT_BOUNDARY,
    evaluation_method_ref: str = DEFAULT_EVALUATION_METHOD_REF,
) -> dict[str, Any]:
    """Build the v0.3 EvaluationEvidence schema payload from a backtest result."""

    candidate_id = str(candidate.get("candidate_id") or "")
    candidate_version = str(candidate.get("candidate_version") or candidate.get("version") or "")
    hypothesis_id = str(
        candidate.get("linked_strategy_hypothesis_id")
        or candidate.get("hypothesis_id")
        or ""
    )
    created = created_at or date.today().isoformat()
    metric_summary = _metric_summary(backtest_result)
    limitation_flags = tuple(str(flag) for flag in backtest_result.limitation_flags)
    default_source_refs = (
        "docs/extension/v0_3_evaluation_evidence_contract.md",
        "docs/extension/v0_3_strategy_candidate_registry_contract.md",
        evaluation_method_ref,
    )
    evidence = {
        "schema_version": "v0_3_evaluation_evidence_0_1",
        "evaluation_boundary": EVALUATION_EVIDENCE_DISCLAIMER,
        "evaluation_id": evaluation_id or _evaluation_id(candidate_id, created),
        "candidate_id": candidate_id,
        "candidate_version": candidate_version,
        "hypothesis_id": hypothesis_id,
        "status": "evidence_recorded",
        "owner": "backtest_evaluation",
        "created_at": created,
        "updated_at": created,
        "source_refs": list(source_refs or default_source_refs),
        "evaluation_window": _evaluation_window(backtest_result),
        "universe": str(
            candidate.get("target_universe")
            or candidate.get("universe")
            or "KOSPI200_candidate_only"
        ),
        "assumptions": _assumptions(candidate, backtest_result),
        "transaction_cost_assumption": _transaction_cost_assumption(backtest_result.config),
        "risk_metrics": [
            "max_drawdown",
            "annualized_volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "turnover_proxy",
            "exposure_stability",
            "coverage_ratio",
            "warmup_period_count",
        ],
        "performance_metrics": [
            "total_return",
            "annualized_return",
            "mean_period_return",
            "hit_rate",
            "benchmark_relative_return",
        ],
        "comparison_group": _comparison_group(candidate),
        "evaluation_method_ref": evaluation_method_ref,
        "generated_output_boundary": generated_output_boundary,
        "no_lookahead_check": (
            "ranking_snapshot_uses_prices_available_through_ranking_date_close; "
            "execution_lag_days >= 1"
        ),
        "point_in_time_check": _point_in_time_check(limitation_flags),
        "generated_output_check": "outputs_are_generated_evidence_only_not_runtime_inputs",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "v0_2_boundary_check": "no_prob_up_1d_training_or_reinterpretation_from_evaluation_metrics",
        "failure_flags": [],
        "production_boundary_check": "no_automatic_production_activation_claim",
        "required_evaluation_checks": _recorded_evaluation_checks(metric_summary),
        "metric_summary": metric_summary,
        "risk_metric_summary": {
            key: metric_summary[key]
            for key in (
                "max_drawdown",
                "annualized_volatility",
                "sharpe_ratio",
                "sortino_ratio",
                "turnover_proxy",
                "exposure_stability",
                "coverage_ratio",
                "warmup_period_count",
            )
        },
        "performance_metric_summary": {
            key: metric_summary[key]
            for key in (
                "total_return",
                "annualized_return",
                "mean_period_return",
                "hit_rate",
                "benchmark_relative_return",
            )
        },
        "known_limitations": list(limitation_flags),
        "review_notes": [
            "benchmark series comparison is not computed unless an approved benchmark input is supplied later",
            "walk_forward_or_out_of_sample_stability remains a downstream evidence requirement",
        ],
    }
    if metric_summary["valid_security_count"] == 0:
        evidence["status"] = "invalidated"
        evidence["failure_flags"] = ["performance_metric_missing"]
    _validate_evaluation_window_within_candidate_contract(candidate, evidence["evaluation_window"])
    return evidence


def build_contract_only_evaluation_evidence_packet(
    candidate_record: Mapping[str, Any],
    *,
    evaluation_id: str | None = None,
    created_at: str | None = None,
    source_refs: Sequence[str] | None = None,
    cohort_id: str = "v0_3_candidate_review_cohort",
    generated_output_boundary: str = DEFAULT_GENERATED_OUTPUT_BOUNDARY,
    evaluation_method_ref: str = DEFAULT_EVALUATION_METHOD_REF,
) -> dict[str, Any]:
    """Build a minimal contract-only EvaluationEvidence packet.

    This is for approved cohort setup before any backtest/simulation metrics are
    recorded. It validates the candidate is evaluable but deliberately leaves
    performance evidence as not-yet-run.
    """

    candidate = strategy_candidate_payload(candidate_record)
    validate_evaluable_candidate(candidate)

    candidate_id = str(candidate.get("candidate_id") or "")
    candidate_version = str(candidate.get("candidate_version") or candidate.get("version") or "")
    hypothesis_id = str(
        candidate.get("linked_strategy_hypothesis_id")
        or candidate.get("hypothesis_id")
        or ""
    )
    created = created_at or date.today().isoformat()
    scope = candidate.get("experiment_scope")
    benchmark = scope.get("benchmark") if isinstance(scope, Mapping) else None
    default_source_refs = (
        "docs/extension/v0_3_evaluation_evidence_contract.md",
        "docs/extension/v0_3_strategy_candidate_registry_contract.md",
        "Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl",
        evaluation_method_ref,
    )
    evidence = {
        "schema_version": "v0_3_evaluation_evidence_0_1",
        "evaluation_boundary": EVALUATION_EVIDENCE_DISCLAIMER,
        "evaluation_id": evaluation_id or _evaluation_id(candidate_id, created),
        "candidate_id": candidate_id,
        "candidate_version": candidate_version,
        "hypothesis_id": hypothesis_id,
        "status": "contract_only",
        "owner": "backtest_evaluation",
        "created_at": created,
        "updated_at": created,
        "source_refs": list(source_refs or default_source_refs),
        "evaluation_window": _contract_only_evaluation_window(candidate),
        "universe": str(
            candidate.get("target_universe")
            or candidate.get("universe")
            or "KOSPI200_candidate_only"
        ),
        "assumptions": _contract_only_assumptions(candidate),
        "transaction_cost_assumption": "not_applicable_for_contract_only",
        "risk_metrics": [
            "max_drawdown",
            "annualized_volatility",
            "turnover_proxy",
            "coverage_ratio",
        ],
        "performance_metrics": [
            "total_return",
            "annualized_return",
            "hit_rate",
            "benchmark_relative_return",
        ],
        "comparison_group": _contract_only_comparison_group(cohort_id, benchmark),
        "evaluation_method_ref": evaluation_method_ref,
        "generated_output_boundary": generated_output_boundary,
        "no_lookahead_check": "required_before_approved_run",
        "point_in_time_check": "required_before_approved_run",
        "generated_output_check": "outputs_are_generated_evidence_only_not_runtime_inputs",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "v0_2_boundary_check": "no_prob_up_1d_training_or_reinterpretation_from_evaluation_metrics",
        "failure_flags": ["not_yet_run"],
        "production_boundary_check": "no_automatic_production_activation_claim",
        "required_evaluation_checks": _contract_only_required_evaluation_checks(),
        "known_limitations": [
            "contract_only_no_backtest_or_simulation_metrics_recorded",
            "approved_evaluation_run_required_before_evidence_recorded_status",
        ],
        "review_notes": [
            "minimal packet reserves the EvaluationEvidence contract for the selected cohort",
            "no adoption decision is implied by contract_only status",
        ],
    }
    validate_evaluation_evidence_record(evidence)
    return evidence


def validate_evaluable_candidate(candidate: Mapping[str, Any]) -> None:
    """Validate that the candidate may request EvaluationEvidence."""

    status = str(candidate.get("status") or "")
    if status not in EVALUABLE_STATUSES:
        raise ValueError("EvaluationEvidence requires an evaluable StrategyCandidate")
    if not candidate.get("candidate_id"):
        raise ValueError("EvaluationEvidence requires candidate_id")
    if not (candidate.get("linked_strategy_hypothesis_id") or candidate.get("hypothesis_id")):
        raise ValueError("EvaluationEvidence requires a linked StrategyHypothesis ID")
    data_requirements = {str(item) for item in _as_list(candidate.get("data_requirements"))}
    if "daily_ohlcv" not in data_requirements and "daily_ohlcv_candidate_review_only" not in data_requirements:
        raise ValueError("EvaluationEvidence requires candidate-only daily_ohlcv data")
    if candidate.get("blocking_issues") or candidate.get("blocked_by"):
        raise ValueError("EvaluationEvidence candidate must not have unresolved blockers")


def validate_evaluation_evidence_record(record: Mapping[str, Any]) -> None:
    """Validate the minimum v0.3 EvaluationEvidence contract shape."""

    missing = sorted(REQUIRED_EVIDENCE_FIELDS - set(record))
    if missing:
        raise ValueError(f"EvaluationEvidence missing required fields: {missing}")
    if record.get("status") not in {
        "contract_only",
        "ready_for_approved_run",
        "evidence_recorded",
        "invalidated",
        "retired",
    }:
        raise ValueError(f"invalid EvaluationEvidence status: {record.get('status')}")
    if not record.get("candidate_id") or not record.get("hypothesis_id"):
        raise ValueError("EvaluationEvidence requires candidate and hypothesis identity")
    if "not automatic production activation" not in str(record.get("evaluation_boundary", "")):
        raise ValueError("EvaluationEvidence boundary disclaimer is missing")
    if "must_not_feed" not in str(record.get("no_feedback_check", "")):
        raise ValueError("EvaluationEvidence no_feedback_check is not explicit")
    if str(record.get("production_boundary_check")) != "no_automatic_production_activation_claim":
        raise ValueError("EvaluationEvidence production boundary check is not explicit")
    if record.get("status") == "evidence_recorded" and record.get("failure_flags"):
        raise ValueError("evidence_recorded EvaluationEvidence must not have active failure_flags")


def write_evaluation_evidence_markdown(
    result: EvaluationEvidenceResult | Mapping[str, Any],
    path: str | Path,
    *,
    project_root: str | Path,
) -> Path:
    """Write a compact evidence-only Markdown packet under an allowed path."""

    evidence = result.evidence if isinstance(result, EvaluationEvidenceResult) else result
    validate_evaluation_evidence_record(evidence)
    output_path = validate_evaluation_evidence_output_path(path, project_root=project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_evidence_markdown(evidence), encoding="utf-8", newline="\n")
    return output_path


def validate_evaluation_evidence_output_path(path: str | Path, *, project_root: str | Path) -> Path:
    """Return an absolute output path if it stays inside evidence-only roots."""

    root = Path(project_root).resolve()
    output_path = Path(path)
    if not output_path.is_absolute():
        output_path = root / output_path
    resolved = output_path.resolve()
    allowed_roots = tuple((root / allowed).resolve() for allowed in ALLOWED_EVALUATION_OUTPUT_ROOTS)
    if not any(resolved == allowed or allowed in resolved.parents for allowed in allowed_roots):
        allowed_text = ", ".join(str(path).replace("\\", "/") for path in ALLOWED_EVALUATION_OUTPUT_ROOTS)
        raise ValueError(f"EvaluationEvidence evidence-only output must stay under one of: {allowed_text}")
    return resolved


def strategy_candidate_payload(candidate_record: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = candidate_record.get("strategy_candidate")
    if isinstance(nested, Mapping):
        return nested
    return candidate_record


def _materialize_price_input(
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(prices, pd.DataFrame):
        return prices.copy(deep=True)
    return pd.DataFrame(list(prices))


def _metric_summary(backtest_result: ConservativeBacktestResult) -> dict[str, Any]:
    summary = backtest_result.summary
    return {
        "period_count": summary.period_count,
        "selected_security_count": summary.selected_security_count,
        "valid_security_count": summary.valid_security_count,
        "skipped_security_count": summary.skipped_security_count,
        "mean_period_return": summary.mean_period_return,
        "total_return": summary.cumulative_return,
        "annualized_return": summary.annualized_return,
        "period_volatility": summary.period_volatility,
        "annualized_volatility": summary.annualized_volatility,
        "sharpe_ratio": summary.sharpe_ratio,
        "sortino_ratio": summary.sortino_ratio,
        "max_drawdown": summary.max_drawdown,
        "turnover_proxy": summary.average_turnover_proxy,
        "hit_rate": summary.hit_rate,
        "coverage_ratio": summary.coverage_ratio,
        "exposure_stability": summary.exposure_stability,
        "benchmark_relative_return": summary.benchmark_relative_return,
        "benchmark_comparison": summary.benchmark_comparison_status,
        "warmup_period_count": summary.warmup_period_count,
        "oos_stability_status": summary.oos_stability_status,
        "cost_slippage_bps_round_trip": 2.0
        * (backtest_result.config.transaction_cost_bps + backtest_result.config.slippage_bps),
    }


def _evaluation_window(backtest_result: ConservativeBacktestResult) -> dict[str, str | None]:
    dates = [period.decision_date for period in backtest_result.period_results]
    return {
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
        "rationale": "predeclared_candidate_backtest_window_from_ranking_snapshot",
    }


def _contract_only_evaluation_window(candidate: Mapping[str, Any]) -> dict[str, str | None]:
    start, end = _candidate_test_period_window(candidate)
    return {
        "start": start,
        "end": end,
        "rationale": "predeclared_candidate_contract_window_pending_approved_run",
    }


def _candidate_test_period_window(candidate: Mapping[str, Any]) -> tuple[str | None, str | None]:
    test_period = str(candidate.get("test_period") or "")
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", test_period)
    if len(dates) < 2:
        return (None, None)
    return (dates[0], dates[1])


def _validate_evaluation_window_within_candidate_contract(
    candidate: Mapping[str, Any],
    evaluation_window: Mapping[str, Any],
) -> None:
    contract_start, contract_end = _candidate_test_period_window(candidate)
    actual_start = evaluation_window.get("start")
    actual_end = evaluation_window.get("end")
    if contract_start and actual_start and str(actual_start) < contract_start:
        raise ValueError(
            f"EvaluationEvidence window starts before predeclared test_period: {actual_start} < {contract_start}"
        )
    if contract_end and actual_end and str(actual_end) > contract_end:
        raise ValueError(
            f"EvaluationEvidence window exceeds predeclared test_period: {actual_end} > {contract_end}"
        )


def _transaction_cost_assumption(config: BacktestConfig) -> dict[str, Any]:
    return {
        "model": "round_trip_cost_and_slippage_subtracted_from_holding_return",
        "transaction_cost_bps": config.transaction_cost_bps,
        "slippage_bps": config.slippage_bps,
    }


def _assumptions(candidate: Mapping[str, Any], backtest_result: ConservativeBacktestResult) -> list[str]:
    assumptions = [
        "candidate_only_interpretation",
        "no_runtime_connection",
        "equal_weight_portfolio",
        f"top_n={backtest_result.config.top_n}",
        f"holding_period_days={backtest_result.config.holding_period_days}",
    ]
    assumptions.extend(str(item) for item in _as_list(candidate.get("known_constraints")) if item)
    return list(dict.fromkeys(assumptions))


def _contract_only_assumptions(candidate: Mapping[str, Any]) -> list[str]:
    assumptions = [
        "candidate_only_interpretation",
        "no_runtime_connection",
        "contract_only_minimal_packet",
        "approved_evaluation_run_required_before_metrics",
    ]
    assumptions.extend(str(item) for item in _as_list(candidate.get("known_constraints")) if item)
    return list(dict.fromkeys(assumptions))


def _contract_only_required_evaluation_checks() -> dict[str, dict[str, Any]]:
    return {
        "cost": {
            "status": "required_before_approved_run",
            "check": "transaction_cost_and_slippage_sensitivity",
            "metric_refs": ["transaction_cost_assumption"],
        },
        "drawdown": {
            "status": "required_before_approved_run",
            "check": "maximum_drawdown_must_be_reported_as_evidence",
            "metric_refs": ["risk_metrics.max_drawdown"],
        },
        "volatility": {
            "status": "required_before_approved_run",
            "check": "annualized_volatility_must_be_reported_as_evidence",
            "metric_refs": ["risk_metrics.annualized_volatility"],
        },
        "turnover": {
            "status": "required_before_approved_run",
            "check": "turnover_proxy_must_be_reported_with_cost_context",
            "metric_refs": ["risk_metrics.turnover_proxy"],
        },
        "oos_walk_forward_stability": {
            "status": "required_before_adoption_review",
            "check": "walk_forward_or_out_of_sample_stability_must_be_recorded_or_explicitly_limited",
            "failure_flag_if_missing": "oos_walk_forward_stability_missing",
        },
        "no_lookahead": {
            "status": "required_before_approved_run",
            "check": "signals_and_inputs_must_use_only_data_available_before_decision_time",
            "metric_refs": ["no_lookahead_check", "point_in_time_check"],
        },
        "no_feedback": {
            "status": "active_boundary_check",
            "check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
            "metric_refs": ["no_feedback_check", "generated_output_check"],
        },
    }


def _recorded_evaluation_checks(metric_summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "cost": {
            "status": "recorded",
            "check": "transaction_cost_and_slippage_sensitivity",
            "metric_refs": ["metric_summary.cost_slippage_bps_round_trip"],
        },
        "drawdown": {
            "status": "recorded",
            "check": "maximum_drawdown_reported_as_evidence",
            "metric_refs": ["risk_metric_summary.max_drawdown"],
        },
        "volatility": {
            "status": "recorded",
            "check": "annualized_volatility_reported_as_evidence",
            "metric_refs": ["risk_metric_summary.annualized_volatility"],
        },
        "turnover": {
            "status": "recorded",
            "check": "turnover_proxy_reported_with_cost_context",
            "metric_refs": ["risk_metric_summary.turnover_proxy"],
        },
        "oos_walk_forward_stability": {
            "status": str(metric_summary.get("oos_stability_status") or "not_available"),
            "check": "walk_forward_or_out_of_sample_stability_must_be_recorded_or_explicitly_limited",
            "required_next_action": "run_walk_forward_or_oos_stability_check_before_adoption_review",
        },
        "no_lookahead": {
            "status": "recorded_boundary_check",
            "check": "ranking_snapshot_uses_prices_available_through_ranking_date_close",
            "metric_refs": ["no_lookahead_check", "point_in_time_check"],
        },
        "no_feedback": {
            "status": "active_boundary_check",
            "check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
            "metric_refs": ["no_feedback_check", "generated_output_check"],
        },
    }


def _comparison_group(candidate: Mapping[str, Any]) -> list[str]:
    scope = candidate.get("experiment_scope")
    benchmark = scope.get("benchmark") if isinstance(scope, Mapping) else None
    values = ["v0_3_candidate_review_cohort"]
    if benchmark:
        values.append(str(benchmark))
    return values


def _contract_only_comparison_group(cohort_id: str, benchmark: Any) -> list[str]:
    values = [cohort_id]
    if benchmark:
        values.append(str(benchmark))
    return values


def _point_in_time_check(limitation_flags: Sequence[str]) -> str:
    if "non_point_in_time_constituent_warning" in limitation_flags:
        return "point_in_time_constituent_membership_unverified_limitation_recorded"
    return "input_rows_validated_before_evaluation_with_no_future_return_columns"


def _evaluation_id(candidate_id: str, created_at: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", candidate_id).strip("_").lower() or "candidate"
    return f"ee_v0_3_{created_at.replace('-', '')}_{slug}"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _evidence_markdown(evidence: Mapping[str, Any]) -> str:
    payload = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        f"# EvaluationEvidence: {evidence.get('evaluation_id')}\n\n"
        f"{EVALUATION_EVIDENCE_DISCLAIMER}\n\n"
        "```json\n"
        f"{payload}\n"
        "```\n"
    )


__all__ = (
    "ALLOWED_EVALUATION_OUTPUT_ROOTS",
    "DEFAULT_EVALUATION_METHOD_REF",
    "DEFAULT_GENERATED_OUTPUT_BOUNDARY",
    "EVALUABLE_STATUSES",
    "EVALUATION_EVIDENCE_DISCLAIMER",
    "EvaluationEvidenceResult",
    "build_contract_only_evaluation_evidence_packet",
    "build_evaluation_evidence_record",
    "run_v0_3_evaluation_evidence",
    "strategy_candidate_payload",
    "validate_evaluable_candidate",
    "validate_evaluation_evidence_output_path",
    "validate_evaluation_evidence_record",
    "write_evaluation_evidence_markdown",
)
