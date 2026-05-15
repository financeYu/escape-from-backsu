"""v1.1 net profitability evidence runner.

This module summarizes provided historical or simulated candidate results into
candidate-only EvaluationEvidenceV1 and ManualReviewPacket artifacts. It does
not run live systems, issue instructions, or replace production ranking.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from math import ceil
from statistics import fmean
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import build_evaluation_evidence_v1
from Quant_mvp.backtest_mvp.manual_review_packet_v1 import build_manual_review_packet_v1
from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (
    ADOPTION_PRIORITY_VERSION,
    SELECTOR_SCORE_MANIFEST_VERSION,
    validate_selector_score_manifest_v1,
)
from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest
from src.validation.horizon_policy import resolve_horizon_policy


RUNNER_VERSION = "v1_1_net_profitability_evidence_runner_v1_0"
VALIDATION_MANIFEST_VERSION = "v1_1_validation_manifest_v1_0"
DEFAULT_CREATED_AT = "2026-05-13T00:00:00+00:00"
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic live rebalance "
    "instructions, move-to-cash commands, future-return claims, proven-alpha claims, "
    "production ranking replacement, and valuation/fundamental active scoring"
)
EVIDENCE_ONLY_NOTICE = (
    "v1.1 net profitability outputs are historical or simulated evidence-only "
    "manual-review support"
)


@dataclass(frozen=True)
class NetProfitabilityRunnerConfig:
    """Config for deterministic v1.1 net profitability evidence summaries."""

    horizon_policy_id: str = "1d"
    top_k: int = 5
    retained_model_count: int = 5
    initial_capital_amount: float = 10_000_000.0
    simulation_period_days: int = 252
    top_decile_fraction: float = 0.10
    random_seed: int = 0
    cost_rate: float = 0.001
    slippage_rate: float = 0.0005
    created_at: str = DEFAULT_CREATED_AT
    strategy_candidate_ref: str = "Quant_mvp/config/v0_3_strategy_candidate_registry.toml"
    config_ref: str = "Quant_mvp/backtest_mvp/net_profitability_runner_v1.py"

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("v1.1 top_k must be at least 1")
        if self.retained_model_count < 1:
            raise ValueError("v1.1 retained_model_count must be at least 1")
        if self.initial_capital_amount <= 0:
            raise ValueError("v1.1 initial_capital_amount must be positive")
        if self.simulation_period_days < 1:
            raise ValueError("v1.1 simulation_period_days must be at least 1")


def run_net_profitability_evidence_v1_1(
    candidate_records: Sequence[Mapping[str, Any]],
    *,
    config: NetProfitabilityRunnerConfig | None = None,
) -> dict[str, Any]:
    """Build v1.1 net profitability evidence artifacts from candidate records."""

    cfg = config or NetProfitabilityRunnerConfig()
    if not candidate_records:
        raise ValueError("v1.1 net profitability runner requires at least one candidate record")
    normalized = [_normalized_record(record, cfg) for record in candidate_records]
    sorted_records = sorted(normalized, key=lambda item: (-item["selector_score"], item["candidate_id"]))
    top_k_records = sorted_records[: max(1, min(cfg.top_k, len(sorted_records)))]
    top_decile_records = sorted_records[: _top_decile_count(len(sorted_records), cfg.top_decile_fraction)]
    capital_ranked_records = sorted(
        normalized,
        key=lambda item: (-item["capital_simulation"]["final_amount"], item["candidate_id"]),
    )
    retained_records = capital_ranked_records[: max(1, min(cfg.retained_model_count, len(capital_ranked_records)))]
    run_id = make_net_profitability_run_id(sorted_records, cfg)
    evidences = [_build_evidence(record, cfg, run_id) for record in sorted_records]
    selector_manifest = _build_selector_manifest(evidences, sorted_records, cfg, run_id)
    manual_packets = [
        build_manual_review_packet_v1(
            evidence=evidence,
            selector_score_manifest=selector_manifest,
            created_at=cfg.created_at,
            route_scope="v1_1_net_profitability_manual_review_packet",
        )
        for evidence in evidences
        if evidence["candidate_id"] in {record["candidate_id"] for record in top_k_records}
    ]
    artifacts = {
        "v1_1_net_profitability_evidence_runner": _runner_manifest(run_id, cfg, sorted_records, evidences),
        "v1_1_top_k_profitability_report": _profitability_report(
            run_id=run_id,
            report_name="v1_1_top_k_profitability_report",
            records=top_k_records,
            selection_policy=f"top_k={len(top_k_records)} by selector_score descending",
        ),
        "v1_1_cost_turnover_summary": _cost_turnover_summary(run_id, sorted_records),
        "v1_1_capital_simulation_report": _capital_simulation_report(
            run_id=run_id,
            config=cfg,
            records=capital_ranked_records,
            retained_records=retained_records,
        ),
        "v1_1_risk_adjusted_review_report": _risk_adjusted_review_report(
            run_id=run_id,
            records=sorted_records,
        ),
        "v1_1_manual_review_profitability_packet": {
            "packet_set_version": "v1_1_manual_review_profitability_packet_v1_0",
            "run_id": run_id,
            "packet_refs": [packet["packet_id"] for packet in manual_packets],
            "packets": manual_packets,
            "manual_review_required": True,
            "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
            "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        },
        "v1_1_validation_manifest": _validation_manifest(run_id, cfg, sorted_records),
        "v1_1_top_decile_profitability_report": _profitability_report(
            run_id=run_id,
            report_name="v1_1_top_decile_profitability_report",
            records=top_decile_records,
            selection_policy=f"top_decile_count={len(top_decile_records)} by selector_score descending",
        ),
        "evaluation_evidence_v1": evidences,
        "selector_score_manifest": selector_manifest,
    }
    validate_net_profitability_artifacts_v1_1(artifacts)
    return artifacts


def validate_net_profitability_artifacts_v1_1(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_1_net_profitability_evidence_runner",
        "v1_1_top_k_profitability_report",
        "v1_1_cost_turnover_summary",
        "v1_1_manual_review_profitability_packet",
        "v1_1_validation_manifest",
        "evaluation_evidence_v1",
        "selector_score_manifest",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.1 net profitability artifacts missing: {', '.join(missing)}")
    manifest = artifacts["v1_1_validation_manifest"]
    if manifest.get("validation_manifest_version") != VALIDATION_MANIFEST_VERSION:
        raise ValueError("unsupported v1.1 validation manifest version")
    for flag in PROHIBITED_FLAGS:
        if bool(manifest.get(flag)):
            raise ValueError(f"v1.1 validation manifest blocked flag must remain false: {flag}")
    validate_selector_score_manifest_v1(artifacts["selector_score_manifest"])
    _reject_prohibited_language(artifacts)


def make_net_profitability_run_id(
    records: Sequence[Mapping[str, Any]],
    config: NetProfitabilityRunnerConfig,
) -> str:
    payload = {
        "version": RUNNER_VERSION,
        "records": [
            {
                "candidate_id": record["candidate_id"],
                "strategy_candidate_id": record["strategy_candidate_id"],
                "strategy_candidate_ref": record["strategy_candidate_ref"],
                "selector_score": record["selector_score"],
                "gross_return": record["gross_return"],
                "benchmark_return": record["benchmark_return"],
                "net_return": record["net_return"],
                "benchmark_relative_net_return": record["benchmark_relative_net_return"],
                "cost_drag": record["cost_drag"],
                "turnover": record["turnover"],
                "cost_rate": record["cost_rate"],
                "slippage_rate": record["slippage_rate"],
                "volatility": record["volatility"],
                "max_drawdown": record["max_drawdown"],
                "sharpe_like_historical_summary": record["sharpe_like_historical_summary"],
                "coverage_ratio": record["coverage_ratio"],
                "invalid_period_count": record["invalid_period_count"],
                "missing_data_count": record["missing_data_count"],
                "date_range": record["date_range"],
                "evidence_period_days": record["evidence_period_days"],
                "simulation_period_days": config.simulation_period_days,
                "initial_capital_amount": config.initial_capital_amount,
                "simulation_period_net_return": record["simulation_period_net_return"],
                "final_amount": record["capital_simulation"]["final_amount"],
                "leakage_check_status": record["leakage_check_status"],
                "no_lookahead_check_status": record["no_lookahead_check_status"],
            }
            for record in records
        ],
        "config": config.__dict__,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_1_net_profitability_{digest}"


def _normalized_record(record: Mapping[str, Any], config: NetProfitabilityRunnerConfig) -> dict[str, Any]:
    candidate_id = _required_str(record, "candidate_id")
    strategy_candidate_id = str(record.get("strategy_candidate_id") or candidate_id)
    gross_return = _as_float(record.get("gross_return"), "gross_return")
    benchmark_return = _as_float(record.get("benchmark_return", 0.0), "benchmark_return")
    selector_score = _as_float(record.get("selector_score", 0.0), "selector_score")
    turnover = max(0.0, _as_float(record.get("turnover", 0.0), "turnover"))
    cost_rate = max(0.0, _as_float(record.get("cost_rate", config.cost_rate), "cost_rate"))
    slippage_rate = max(0.0, _as_float(record.get("slippage_rate", config.slippage_rate), "slippage_rate"))
    cost_drag = turnover * (cost_rate + slippage_rate)
    net_return = gross_return - cost_drag
    if net_return <= -1.0:
        raise ValueError("v1.1 net_return must be greater than -1 for capital simulation")
    volatility = max(0.0, _as_float(record.get("volatility", 0.0), "volatility"))
    max_drawdown = _as_float(record.get("max_drawdown", 0.0), "max_drawdown")
    coverage_ratio = _bounded_ratio(record.get("coverage_ratio", 1.0), "coverage_ratio")
    leakage_check_status = _required_pass_status(record, "leakage_check_status")
    no_lookahead_check_status = _required_pass_status(record, "no_lookahead_check_status")
    date_range = _required_date_range(record)
    evidence_period_days = _date_range_day_count(date_range)
    simulation_period_net_return = _compound_return_for_days(
        net_return=net_return,
        evidence_period_days=evidence_period_days,
        simulation_period_days=config.simulation_period_days,
    )
    final_amount = config.initial_capital_amount * (1.0 + simulation_period_net_return)
    return {
        "candidate_id": candidate_id,
        "strategy_candidate_id": strategy_candidate_id,
        "strategy_candidate_ref": str(record.get("strategy_candidate_ref") or config.strategy_candidate_ref),
        "selector_score": selector_score,
        "gross_return": gross_return,
        "benchmark_return": benchmark_return,
        "net_return": net_return,
        "benchmark_relative_net_return": net_return - benchmark_return,
        "cost_drag": cost_drag,
        "turnover": turnover,
        "cost_rate": cost_rate,
        "slippage_rate": slippage_rate,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "sharpe_like_historical_summary": (net_return / volatility) if volatility > 0 else None,
        "coverage_ratio": coverage_ratio,
        "invalid_period_count": int(record.get("invalid_period_count", 0)),
        "missing_data_count": int(record.get("missing_data_count", 0)),
        "date_range": date_range,
        "evidence_period_days": evidence_period_days,
        "simulation_period_net_return": simulation_period_net_return,
        "capital_simulation": {
            "initial_capital_amount": round(config.initial_capital_amount, 2),
            "simulation_period_days": config.simulation_period_days,
            "final_amount": round(final_amount, 2),
            "profit_amount": round(final_amount - config.initial_capital_amount, 2),
            "period_scaling_policy": "compound_existing_candidate_net_evidence_over_configured_days",
        },
        "leakage_check_status": leakage_check_status,
        "no_lookahead_check_status": no_lookahead_check_status,
        "universe_scope": str(record.get("universe_scope") or "KOSPI200_candidate_only"),
        "input_artifact_refs": list(record.get("input_artifact_refs") or []),
        "output_artifact_refs": list(record.get("output_artifact_refs") or []),
        "rebalance_frequency": str(record.get("rebalance_frequency") or "none"),
        "rebalancing_role": str(record.get("rebalancing_role") or "evaluation_mechanics"),
        "rebalance_disclosure": str(
            record.get("rebalance_disclosure")
            or "historical simulated net profitability context only not user instruction"
        ),
    }


def _build_evidence(
    record: Mapping[str, Any],
    config: NetProfitabilityRunnerConfig,
    run_id: str,
) -> dict[str, Any]:
    policy = resolve_horizon_policy(config.horizon_policy_id)
    output_refs = [*record["output_artifact_refs"], f"{run_id}:v1_1_net_profitability_evidence_runner"]
    manifest = build_simulation_run_manifest(
        strategy_candidate_id=record["strategy_candidate_id"],
        strategy_candidate_ref=record["strategy_candidate_ref"],
        date_range=record["date_range"],
        horizon_policy=policy,
        route_scope="v1_1_net_profitability_evidence_runner",
        run_mode="candidate_only_simulation",
        evidence_mode="evidence_only",
        input_artifact_refs=record["input_artifact_refs"],
        output_artifact_refs=output_refs,
        data_context="v1_1_historical_or_simulated_candidate_only_context",
        universe_scope=record["universe_scope"],
        rebalance_disclosure=record["rebalance_disclosure"],
        cost_model=f"turnover_times_cost_rate_{record['cost_rate']}",
        slippage_model=f"turnover_times_slippage_rate_{record['slippage_rate']}",
        random_seed=config.random_seed,
        code_version=RUNNER_VERSION,
        config_refs=[config.config_ref],
    )
    return build_evaluation_evidence_v1(
        candidate_result={
            "candidate_id": record["candidate_id"],
            "strategy_candidate_id": record["strategy_candidate_id"],
            "strategy_candidate_ref": record["strategy_candidate_ref"],
            "metric_values": {
                "realized_return_summary": {
                    "gross_return": record["gross_return"],
                    "net_return": record["net_return"],
                    "benchmark_return": record["benchmark_return"],
                    "benchmark_relative_net_return": record["benchmark_relative_net_return"],
                },
                "realized_drawdown_summary": record["max_drawdown"],
                "realized_volatility_summary": record["volatility"],
                "realized_turnover_summary": record["turnover"],
                "realized_cost_summary": {
                    "cost_drag": record["cost_drag"],
                    "cost_rate": record["cost_rate"],
                    "slippage_rate": record["slippage_rate"],
                },
                "sharpe_like_historical_summary": record["sharpe_like_historical_summary"],
                "coverage_ratio": record["coverage_ratio"],
                "invalid_period_count": record["invalid_period_count"],
                "missing_data_count": record["missing_data_count"],
            },
            "coverage_summary": {
                "coverage_ratio": record["coverage_ratio"],
                "invalid_period_count": record["invalid_period_count"],
            },
            "data_quality_summary": {
                "missing_data_count": record["missing_data_count"],
                "flags": [] if record["missing_data_count"] == 0 else ["missing_data_present"],
            },
            "turnover_summary": {
                "realized_turnover_summary": record["turnover"],
                "cost_drag": record["cost_drag"],
            },
            "leakage_check_status": record["leakage_check_status"],
            "no_lookahead_check_status": record["no_lookahead_check_status"],
            "rebalancing_role": record["rebalancing_role"],
            "rebalance_disclosure": record["rebalance_disclosure"],
            "input_artifact_refs": record["input_artifact_refs"],
            "output_artifact_refs": output_refs,
            "universe_scope": record["universe_scope"],
            "date_range": record["date_range"],
        },
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at=config.created_at,
        route_scope="v1_1_net_profitability_evaluation_evidence",
        evidence_mode="candidate_only_simulation_evidence",
    )


def _build_selector_manifest(
    evidences: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    config: NetProfitabilityRunnerConfig,
    run_id: str,
) -> dict[str, Any]:
    record_by_candidate = {record["candidate_id"]: record for record in records}
    priorities = []
    for rank, evidence in enumerate(evidences, start=1):
        record = record_by_candidate[evidence["candidate_id"]]
        reasons = ["net_metric_available", "cost_drag_available", "benchmark_context_available"]
        if rank <= max(1, min(config.top_k, len(evidences))):
            reasons.append("top_k_profitability_review")
        priorities.append(
            {
                "priority_version": ADOPTION_PRIORITY_VERSION,
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "review_priority_score": round(max(0.0, min(100.0, record["selector_score"])), 6),
                "review_priority_bucket": _priority_bucket(rank),
                "review_priority_rank": rank,
                "reason_codes": reasons,
                "evidence_refs": [evidence["evidence_id"]],
                "manual_review_required": True,
                "limitation_summary": ["selector_score_used_for_review_grouping_only"],
                "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
            }
        )
    manifest = {
        "manifest_version": SELECTOR_SCORE_MANIFEST_VERSION,
        "selector_run_id": f"selector_{run_id}",
        "created_at": config.created_at,
        "selector_mode": "rule_based_review_prioritization",
        "selector_type": "v1_1_provided_selector_score_grouping",
        "input_manifest_ref": run_id,
        "model_manifest_ref": None,
        "rule_manifest_ref": "Quant_mvp.backtest_mvp.net_profitability_runner_v1",
        "candidate_review_priorities": priorities,
        "priority_score_name": "review_priority_score",
        "priority_score_definition": "provided selector score used only to group candidates for manual review of net profitability evidence",
        "priority_bucket": [priority["review_priority_bucket"] for priority in priorities],
        "reason_codes": sorted({code for priority in priorities for code in priority["reason_codes"]}),
        "evidence_refs": [evidence["evidence_id"] for evidence in evidences],
        "limitation_summary": ["v1_1_does_not_train_or_activate_ml_model"],
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "not_investment_advice_notice": "manual review support only; not investment advice",
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }
    validate_selector_score_manifest_v1(manifest)
    return manifest


def _runner_manifest(
    run_id: str,
    config: NetProfitabilityRunnerConfig,
    records: Sequence[Mapping[str, Any]],
    evidences: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "runner_version": RUNNER_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "horizon_policy_id": config.horizon_policy_id,
        "random_seed": config.random_seed,
        "candidate_count": len(records),
        "input_candidate_ids": [record["candidate_id"] for record in records],
        "evaluation_evidence_refs": [evidence["evidence_id"] for evidence in evidences],
        "reproducibility_policy": "same config, seed, and candidate manifest inputs produce the same run_id and metrics",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }


def _profitability_report(
    *,
    run_id: str,
    report_name: str,
    records: Sequence[Mapping[str, Any]],
    selection_policy: str,
) -> dict[str, Any]:
    return {
        "report_name": report_name,
        "run_id": run_id,
        "selection_policy": selection_policy,
        "candidate_count": len(records),
        "candidate_summaries": [
            {
                "candidate_id": record["candidate_id"],
                "selector_score": record["selector_score"],
                "gross_return": record["gross_return"],
                "net_return": record["net_return"],
                "benchmark_return": record["benchmark_return"],
                "benchmark_relative_net_return": record["benchmark_relative_net_return"],
                "max_drawdown": record["max_drawdown"],
                "sharpe_like_historical_summary": record["sharpe_like_historical_summary"],
                "turnover": record["turnover"],
                "cost_drag": record["cost_drag"],
                "capital_simulation": record["capital_simulation"],
            }
            for record in records
        ],
        "aggregate_summary": _aggregate_summary(records),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _cost_turnover_summary(run_id: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "summary_name": "v1_1_cost_turnover_summary",
        "run_id": run_id,
        "candidate_count": len(records),
        "average_turnover": _mean(record["turnover"] for record in records),
        "average_cost_drag": _mean(record["cost_drag"] for record in records),
        "max_cost_drag": max(record["cost_drag"] for record in records),
        "cost_model": "net_return = gross_return - turnover * (cost_rate + slippage_rate)",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _capital_simulation_report(
    *,
    run_id: str,
    config: NetProfitabilityRunnerConfig,
    records: Sequence[Mapping[str, Any]],
    retained_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "report_name": "v1_1_capital_simulation_report",
        "run_id": run_id,
        "selection_policy": (
            f"retain_top_n={len(retained_records)} by final_amount descending "
            f"from configured retained_model_count={config.retained_model_count}"
        ),
        "initial_capital_amount": round(config.initial_capital_amount, 2),
        "simulation_period_days": config.simulation_period_days,
        "candidate_count": len(records),
        "retained_model_count": len(retained_records),
        "retained_candidate_ids": [record["candidate_id"] for record in retained_records],
        "retained_model_summaries": [
            _capital_model_summary(record, rank=index)
            for index, record in enumerate(retained_records, start=1)
        ],
        "all_model_summaries": [
            _capital_model_summary(record, rank=index)
            for index, record in enumerate(records, start=1)
        ],
        "ranking_metric": "final_amount",
        "risk_metrics_available_separately": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _risk_adjusted_review_report(
    *,
    run_id: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ranked = sorted(
        records,
        key=lambda item: (
            item["sharpe_like_historical_summary"] is None,
            -(item["sharpe_like_historical_summary"] or 0.0),
            item["candidate_id"],
        ),
    )
    return {
        "report_name": "v1_1_risk_adjusted_review_report",
        "run_id": run_id,
        "selection_policy": "rank candidates by sharpe_like_historical_summary for separate user review",
        "candidate_count": len(ranked),
        "risk_adjusted_summaries": [
            {
                "risk_adjusted_rank": index,
                "candidate_id": record["candidate_id"],
                "net_return": record["net_return"],
                "simulation_period_net_return": record["simulation_period_net_return"],
                "volatility": record["volatility"],
                "max_drawdown": record["max_drawdown"],
                "sharpe_like_historical_summary": record["sharpe_like_historical_summary"],
                "turnover": record["turnover"],
                "coverage_ratio": record["coverage_ratio"],
            }
            for index, record in enumerate(ranked, start=1)
        ],
        "capital_ranking_not_overwritten": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _capital_model_summary(record: Mapping[str, Any], *, rank: int) -> dict[str, Any]:
    simulation = record["capital_simulation"]
    return {
        "capital_rank": rank,
        "candidate_id": record["candidate_id"],
        "initial_capital_amount": simulation["initial_capital_amount"],
        "simulation_period_days": simulation["simulation_period_days"],
        "simulation_period_net_return": record["simulation_period_net_return"],
        "final_amount": simulation["final_amount"],
        "profit_amount": simulation["profit_amount"],
        "net_return": record["net_return"],
        "evidence_period_days": record["evidence_period_days"],
        "max_drawdown": record["max_drawdown"],
        "volatility": record["volatility"],
        "sharpe_like_historical_summary": record["sharpe_like_historical_summary"],
    }


def _validation_manifest(
    run_id: str,
    config: NetProfitabilityRunnerConfig,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "validation_manifest_version": VALIDATION_MANIFEST_VERSION,
        "run_id": run_id,
        "candidate_count": len(records),
        "reproducible_run": True,
        "net_metric_output": True,
        "capital_simulation_output": True,
        "retained_model_count": config.retained_model_count,
        "initial_capital_amount": round(config.initial_capital_amount, 2),
        "simulation_period_days": config.simulation_period_days,
        "retention_policy": "top_n_by_final_amount_with_risk_adjusted_metrics_separate",
        "top_k_evidence": True,
        "manifest_lineage": "HorizonPolicy -> SimulationRunManifest -> EvaluationEvidenceV1",
        "guardrail_status": "pass",
        "tests_required": [
            "runner unit test",
            "fixture test",
            "guardrail/language test",
        ],
        "config_snapshot": config.__dict__,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }


def _aggregate_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    return {
        "average_gross_return": _mean(record["gross_return"] for record in records),
        "average_net_return": _mean(record["net_return"] for record in records),
        "average_benchmark_relative_net_return": _mean(
            record["benchmark_relative_net_return"] for record in records
        ),
        "average_turnover": _mean(record["turnover"] for record in records),
        "average_cost_drag": _mean(record["cost_drag"] for record in records),
        "worst_max_drawdown": min(record["max_drawdown"] for record in records),
    }


def _top_decile_count(candidate_count: int, fraction: float) -> int:
    if candidate_count <= 0:
        return 0
    bounded = max(0.01, min(1.0, fraction))
    return max(1, ceil(candidate_count * bounded))


def _priority_bucket(rank: int) -> str:
    if rank <= 3:
        return "high_review_priority"
    if rank <= 10:
        return "standard_review_priority"
    return "low_review_priority"


def _mean(values: Sequence[float] | Any) -> float:
    items = [float(value) for value in values]
    return round(fmean(items), 8) if items else 0.0


def _as_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"v1.1 net profitability record requires numeric {field_name}") from exc


def _bounded_ratio(value: Any, field_name: str) -> float:
    ratio = _as_float(value, field_name)
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return ratio


def _required_str(record: Mapping[str, Any], field_name: str) -> str:
    value = str(record.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"v1.1 net profitability record requires {field_name}")
    return value


def _required_pass_status(record: Mapping[str, Any], field_name: str) -> str:
    value = _required_str(record, field_name)
    if value != "pass":
        raise ValueError(f"v1.1 net profitability record requires {field_name}=pass")
    return value


def _required_date_range(record: Mapping[str, Any]) -> dict[str, str]:
    value = record.get("date_range")
    if not isinstance(value, Mapping):
        raise ValueError("v1.1 net profitability record requires date_range with start and end")
    start = str(value.get("start") or "").strip()
    end = str(value.get("end") or "").strip()
    if not start or not end or start == "unknown" or end == "unknown":
        raise ValueError("v1.1 net profitability record requires explicit date_range start and end")
    _date_range_day_count({"start": start, "end": end})
    return {"start": start, "end": end}


def _date_range_day_count(date_range: Mapping[str, str]) -> int:
    start = date.fromisoformat(str(date_range["start"]))
    end = date.fromisoformat(str(date_range["end"]))
    if end < start:
        raise ValueError("v1.1 date_range end must be on or after start")
    return (end - start).days + 1


def _compound_return_for_days(
    *,
    net_return: float,
    evidence_period_days: int,
    simulation_period_days: int,
) -> float:
    if evidence_period_days < 1:
        raise ValueError("v1.1 evidence_period_days must be at least 1")
    scaled = (1.0 + net_return) ** (simulation_period_days / evidence_period_days) - 1.0
    return round(scaled, 8)


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice"}
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
        r"\bfuture[- ]return\b",
        r"\bexpected[- ]return\b",
        r"\bproven[- ]alpha\b",
        r"\bproduction ranking replacement\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.1 net profitability artifacts contain prohibited language: {pattern}")


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


__all__ = (
    "NetProfitabilityRunnerConfig",
    "RUNNER_VERSION",
    "make_net_profitability_run_id",
    "run_net_profitability_evidence_v1_1",
    "validate_net_profitability_artifacts_v1_1",
)
