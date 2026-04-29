"""Build v0.3 StrategyHypothesis records from ResearchHypothesis outputs.

The generated strategy hypotheses are candidate-only test specifications. They
are not production ranking inputs, live trading rules, score replacements, or
adoption decisions.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("Quant_mvp/data/v0_3/research_hypotheses/v0_3_research_hypotheses.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/strategy_hypotheses")
DEFAULT_JSONL_NAME = "v0_3_strategy_hypotheses.jsonl"
DEFAULT_CSV_NAME = "v0_3_strategy_hypotheses.csv"
DEFAULT_MANIFEST_NAME = "v0_3_strategy_hypotheses_manifest.json"
DEFAULT_RULE_GROUPS_NAME = "v0_3_strategy_ml_rule_groups.json"

CURRENT_STAGE = "StrategyHypothesis"
STRATEGY_BOUNDARY = (
    "This StrategyHypothesis output is candidate-only research structure for "
    "backtest or simulation design. It is not a production ranking input, not "
    "a score input, not a runtime model feature source, not a trading "
    "recommendation, and not an adoption decision."
)

STRATEGY_TYPES = {
    "momentum",
    "reversal",
    "quality",
    "value",
    "volatility",
    "seasonality",
    "event_driven",
    "statistical_arbitrage",
    "machine_learning",
    "hybrid",
    "other",
}
CONVERSION_STATUSES = {"ready_for_candidate_registry", "needs_refinement", "blocked"}


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


def _strategy_type_from_research(record: dict[str, Any]) -> str:
    text = " ".join(
        str(item or "").lower()
        for item in (
            _get(record, "research_hypothesis.title"),
            _get(record, "research_hypothesis.expected_signal"),
            _get(record, "next_stage_input.signal_family_candidate"),
        )
    )
    if "machine" in text or "gradient" in text or "classifier" in text:
        return "machine_learning"
    if "hybrid" in text:
        return "hybrid"
    if "event" in text or "insider" in text or "filing" in text:
        return "event_driven"
    if "value" in text or "valuation" in text or "fundamental" in text:
        return "value"
    if "quality" in text:
        return "quality"
    if "season" in text or "calendar" in text:
        return "seasonality"
    if "correlation" in text or "serial" in text or "arbitrage" in text:
        return "statistical_arbitrage"
    if "mean" in text or "reversion" in text or "reversal" in text:
        return "reversal"
    if "vol" in text or "squeeze" in text or "range" in text:
        return "volatility"
    if "momentum" in text or "trend" in text or "breakout" in text:
        return "momentum"
    return "other"


def _rule_template(strategy_type: str) -> dict[str, Any]:
    templates: dict[str, dict[str, Any]] = {
        "momentum": {
            "signal_definition": "Cross-sectional percentile rank of 20-trading-day close-to-close return, with valid daily OHLCV warmup.",
            "signal_calculation_window": "20 trading days primary; 60 trading days optional stability context.",
            "entry_rule": "On each rebalance date, include securities with signal_percentile >= 0.80 and complete warmup coverage.",
            "exit_rule": "Remove after 20 trading days or when signal_percentile < 0.50 at a scheduled rebalance.",
            "holding_period": "20 trading days.",
            "rebalance_rule": "Every 20 trading days using only data available through the prior close.",
            "primary_metric": "Information ratio versus the benchmark after the stated transaction-cost assumption.",
            "expected_positive_pattern": "Higher signal quantiles show stronger evidence-only forward return or risk-adjusted metric than lower quantiles after costs.",
        },
        "reversal": {
            "signal_definition": "Cross-sectional percentile rank of negative 5-trading-day return, with optional 20-day volatility filter.",
            "signal_calculation_window": "5 trading days primary; 20 trading days volatility context.",
            "entry_rule": "On each rebalance date, include securities with reversal_signal_percentile >= 0.80 and valid warmup coverage.",
            "exit_rule": "Remove after 5 trading days or when reversal_signal_percentile < 0.50 at a scheduled rebalance.",
            "holding_period": "5 trading days.",
            "rebalance_rule": "Weekly using only data available through the prior close.",
            "primary_metric": "Mean forward return spread between top and bottom signal quantiles after costs.",
            "expected_positive_pattern": "Extreme short-horizon losers show evidence-only recovery relative to the benchmark bucket after costs.",
        },
        "volatility": {
            "signal_definition": "Rolling 20-trading-day volatility percentile and volatility expansion or compression state from daily returns.",
            "signal_calculation_window": "20 trading days primary; 60 trading days regime context.",
            "entry_rule": "On each rebalance date, include securities in the predeclared volatility state bucket and complete warmup coverage.",
            "exit_rule": "Remove after 20 trading days or when the volatility state changes at a scheduled rebalance.",
            "holding_period": "20 trading days.",
            "rebalance_rule": "Every 20 trading days using only data available through the prior close.",
            "primary_metric": "Downside-risk-adjusted return spread versus benchmark state bucket after costs.",
            "expected_positive_pattern": "The predeclared volatility state shows a stable evidence-only metric advantage over the benchmark state bucket.",
        },
        "statistical_arbitrage": {
            "signal_definition": "Rolling correlation or serial-dependence feature computed from daily returns.",
            "signal_calculation_window": "60 trading days primary; 120 trading days stability context.",
            "entry_rule": "On each rebalance date, include securities with predeclared dependence_feature_percentile in the target bucket.",
            "exit_rule": "Remove after 20 trading days or when the dependence feature leaves the target bucket.",
            "holding_period": "20 trading days.",
            "rebalance_rule": "Every 20 trading days using only data available through the prior close.",
            "primary_metric": "Out-of-sample quantile monotonicity and risk-adjusted spread after costs.",
            "expected_positive_pattern": "Predeclared dependence buckets show stable separation without lookahead or survivorship bias.",
        },
    }
    default = {
        "signal_definition": "Predeclared daily OHLCV-derived feature percentile defined before simulation.",
        "signal_calculation_window": "20 trading days primary unless the strategy group requires a longer warmup.",
        "entry_rule": "On each rebalance date, include securities in the predeclared top signal bucket with complete warmup coverage.",
        "exit_rule": "Remove after the predeclared holding period or when the signal leaves the target bucket.",
        "holding_period": "20 trading days.",
        "rebalance_rule": "Every 20 trading days using only data available through the prior close.",
        "primary_metric": "Risk-adjusted spread versus benchmark after costs.",
        "expected_positive_pattern": "The predeclared signal bucket shows evidence-only separation from the benchmark after costs.",
    }
    return templates.get(strategy_type, default)


def _conversion_status(record: dict[str, Any], strategy_type: str) -> str:
    action = _get(record, "research_hypothesis.next_action")
    if action == "reject":
        return "blocked"
    if action != "convert_to_strategy_hypothesis":
        return "needs_refinement"
    if strategy_type in {"value", "hybrid", "event_driven", "machine_learning"}:
        return "needs_refinement"
    return "ready_for_candidate_registry"


def _reason_for_status(record: dict[str, Any], status: str, strategy_type: str) -> str:
    if status == "ready_for_candidate_registry":
        return "ResearchHypothesis has a technical daily-OHLCV route and enough rule structure for candidate registry drafting."
    if status == "blocked":
        return "ResearchHypothesis was rejected or out of current v0.3 candidate scope."
    if strategy_type in {"value", "hybrid"}:
        return "Non-technical or mixed inputs require split review before testable candidate registration."
    if strategy_type in {"event_driven", "machine_learning"}:
        return "Event or ML-specific features require a separate approved feature and label contract before candidate registration."
    return "ResearchHypothesis needs more specific signal, data, or falsification details before candidate registration."


def _universe_filter(record: dict[str, Any]) -> str:
    target = _get(record, "research_hypothesis.target_universe") or "daily equity universe"
    return (
        f"Candidate-only test universe: approved KOSPI200 daily OHLCV universe by default; "
        f"source target noted as {target}. Any wider universe requires explicit later approval."
    )


def _data_requirements(record: dict[str, Any]) -> list[str]:
    data = [str(item) for item in _as_list(_get(record, "research_hypothesis.required_data"))]
    if "daily_ohlcv" not in data:
        data.append("daily_ohlcv")
    return sorted(set(data))


def _next_stage_input(strategy: dict[str, Any]) -> dict[str, Any] | None:
    if strategy["conversion_status"] != "ready_for_candidate_registry":
        return None
    return {
        "next_stage": "StrategyCandidate",
        "strategy_hypothesis_id": strategy["strategy_hypothesis_id"],
        "linked_research_id": strategy["linked_research_id"],
        "strategy_type": strategy["strategy_type"],
        "candidate_registry_status": "draft_ready",
        "required_data": strategy["data_requirements"],
        "entry_rule": strategy["entry_rule"],
        "exit_rule": strategy["exit_rule"],
        "holding_period": strategy["holding_period"],
        "rebalance_rule": strategy["rebalance_rule"],
        "benchmark": strategy["benchmark"],
        "primary_metric": strategy["primary_metric"],
        "no_feedback_check": "strategy_hypothesis_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
    }


def _non_ready_blocker(record: dict[str, Any], status: str, strategy_type: str) -> list[str]:
    blockers = [str(item) for item in _as_list(record.get("blocker")) if item]
    if blockers:
        return blockers
    if status == "blocked":
        return ["research_hypothesis_rejected_or_out_of_scope"]
    return [f"{strategy_type}_strategy_requires_refinement_before_candidate_registry"]


def research_record_to_strategy_record(record: dict[str, Any]) -> dict[str, Any]:
    hypothesis = record.get("research_hypothesis")
    if not isinstance(hypothesis, dict):
        raise ValueError("record missing research_hypothesis")

    strategy_type = _strategy_type_from_research(record)
    template = _rule_template(strategy_type)
    status = _conversion_status(record, strategy_type)
    linked_research_id = str(hypothesis.get("research_id"))
    strategy = {
        "strategy_hypothesis_id": f"sh:{linked_research_id.removeprefix('rh:')}",
        "linked_research_id": linked_research_id,
        "title": _compact_text(hypothesis.get("title"), limit=300),
        "strategy_type": strategy_type,
        "signal_definition": template["signal_definition"],
        "signal_calculation_window": template["signal_calculation_window"],
        "entry_rule": template["entry_rule"] if status == "ready_for_candidate_registry" else "Blocked until signal definition and data route are refined.",
        "exit_rule": template["exit_rule"] if status == "ready_for_candidate_registry" else "Blocked until exit condition is measurable.",
        "holding_period": template["holding_period"] if status == "ready_for_candidate_registry" else "Blocked until holding period is defined.",
        "rebalance_rule": template["rebalance_rule"] if status == "ready_for_candidate_registry" else "Blocked until rebalance cadence is defined.",
        "universe_filter": _universe_filter(record),
        "position_sizing": "Equal-weight evidence-only basket; max 5 percent per security; no leverage.",
        "risk_control": "Skip records with missing warmup data; apply no-lookahead, no-survivorship-bias, and transaction-cost checks before evidence use.",
        "transaction_cost_assumption": "Initial candidate-only assumption: 10 bps per side; must be sensitivity-tested before EvaluationEvidence.",
        "benchmark": "Equal-weight approved KOSPI200 daily OHLCV universe and a passive KOSPI200 proxy where available.",
        "primary_metric": template["primary_metric"],
        "secondary_metrics": [
            "annualized_volatility",
            "max_drawdown",
            "turnover",
            "hit_rate",
            "quantile_monotonicity",
            "coverage_ratio",
        ],
        "null_hypothesis": "The predeclared signal has no evidence-only advantage over the benchmark after costs and bias checks.",
        "expected_positive_pattern": template["expected_positive_pattern"],
        "expected_failure_case": "No stable quantile separation, poor coverage, high turnover cost, or instability across walk-forward splits.",
        "data_requirements": _data_requirements(record),
        "implementation_notes": [
            "Candidate-only ML/evaluator rule; not a production feature source.",
            "Use labels only after candidate simulation is run in an approved EvaluationEvidence lane.",
            f"Source ResearchHypothesis action: {hypothesis.get('next_action')}",
        ],
        "conversion_status": status,
        "reason_for_status": _reason_for_status(record, status, strategy_type),
    }
    output = {
        "schema_version": "v0_3_strategy_hypothesis_output_0_1",
        "current_stage": CURRENT_STAGE,
        "strategy_boundary": STRATEGY_BOUNDARY,
        "linked_research_hypothesis": {
            "research_id": linked_research_id,
            "title": hypothesis.get("title"),
            "next_action": hypothesis.get("next_action"),
            "evidence_quality": hypothesis.get("evidence_quality"),
            "confidence_level": hypothesis.get("confidence_level"),
        },
        "strategy_hypothesis": strategy,
        "testable_rules": {
            "signal_definition": strategy["signal_definition"],
            "entry_rule": strategy["entry_rule"],
            "exit_rule": strategy["exit_rule"],
            "holding_period": strategy["holding_period"],
            "rebalance_rule": strategy["rebalance_rule"],
            "universe_filter": strategy["universe_filter"],
            "position_sizing": strategy["position_sizing"],
            "risk_control": strategy["risk_control"],
        },
        "evaluation_plan": {
            "benchmark": strategy["benchmark"],
            "primary_metric": strategy["primary_metric"],
            "secondary_metrics": strategy["secondary_metrics"],
            "transaction_cost_assumption": strategy["transaction_cost_assumption"],
        },
        "failure_definition": strategy["expected_failure_case"],
        "next_stage_input": _next_stage_input(strategy),
        "blocker": [] if status == "ready_for_candidate_registry" else _non_ready_blocker(record, status, strategy_type),
        "minimal_fix": [] if status == "ready_for_candidate_registry" else _as_list(record.get("minimal_fix")),
        "no_feedback_check": "strategy_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    validate_strategy_record(output)
    return output


def validate_strategy_record(record: dict[str, Any]) -> None:
    if record.get("current_stage") != CURRENT_STAGE:
        raise ValueError("current_stage must be StrategyHypothesis")
    strategy = record.get("strategy_hypothesis")
    if not isinstance(strategy, dict):
        raise ValueError("strategy_hypothesis must be an object")
    required_keys = {
        "strategy_hypothesis_id",
        "linked_research_id",
        "title",
        "strategy_type",
        "signal_definition",
        "signal_calculation_window",
        "entry_rule",
        "exit_rule",
        "holding_period",
        "rebalance_rule",
        "universe_filter",
        "position_sizing",
        "risk_control",
        "transaction_cost_assumption",
        "benchmark",
        "primary_metric",
        "secondary_metrics",
        "null_hypothesis",
        "expected_positive_pattern",
        "expected_failure_case",
        "data_requirements",
        "implementation_notes",
        "conversion_status",
        "reason_for_status",
    }
    missing = sorted(required_keys - set(strategy))
    if missing:
        raise ValueError(f"strategy_hypothesis missing keys: {missing}")
    if strategy["strategy_type"] not in STRATEGY_TYPES:
        raise ValueError(f"invalid strategy_type: {strategy['strategy_type']}")
    if strategy["conversion_status"] not in CONVERSION_STATUSES:
        raise ValueError(f"invalid conversion_status: {strategy['conversion_status']}")
    if strategy["conversion_status"] == "ready_for_candidate_registry" and not record.get("next_stage_input"):
        raise ValueError("ready strategy requires next_stage_input")
    if strategy["conversion_status"] != "ready_for_candidate_registry" and not record.get("blocker"):
        raise ValueError("non-ready strategy requires blocker")
    if "trading recommendation" not in str(record.get("strategy_boundary", "")):
        raise ValueError("strategy boundary disclaimer is missing")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    strategy = record["strategy_hypothesis"]
    return {
        "schema_version": record["schema_version"],
        "current_stage": record["current_stage"],
        "strategy_boundary": record["strategy_boundary"],
        **strategy,
        "linked_research_hypothesis": record["linked_research_hypothesis"],
        "testable_rules": record["testable_rules"],
        "evaluation_plan": record["evaluation_plan"],
        "failure_definition": record["failure_definition"],
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


def build_rule_groups(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        strategy = record["strategy_hypothesis"]
        grouped[strategy["strategy_type"]].append(record)

    groups: dict[str, Any] = {}
    for strategy_type, group_records in sorted(grouped.items()):
        template = _rule_template(strategy_type)
        status_counts = Counter(record["strategy_hypothesis"]["conversion_status"] for record in group_records)
        ready_ids = [
            record["strategy_hypothesis"]["strategy_hypothesis_id"]
            for record in group_records
            if record["strategy_hypothesis"]["conversion_status"] == "ready_for_candidate_registry"
        ]
        groups[strategy_type] = {
            "strategy_type": strategy_type,
            "record_count": len(group_records),
            "conversion_status_counts": dict(sorted(status_counts.items())),
            "ready_strategy_hypothesis_ids": ready_ids,
            "ml_rule_family": {
                "candidate_feature_template": template["signal_definition"],
                "label_horizon": template["holding_period"],
                "rebalance_rule": template["rebalance_rule"],
                "benchmark": "Equal-weight approved KOSPI200 daily OHLCV universe and passive KOSPI200 proxy where available.",
                "primary_metric": template["primary_metric"],
                "null_hypothesis": "No evidence-only advantage versus benchmark after costs and bias checks.",
            },
            "boundary": "candidate_only_ml_evaluator_input_not_production_model_feature",
        }
    return {
        "schema_version": "v0_3_strategy_ml_rule_groups_0_1",
        "current_stage": CURRENT_STAGE,
        "record_count": len(records),
        "groups": groups,
        "no_feedback_check": "strategy_rule_groups_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_manifest(
    records: list[dict[str, Any]],
    rule_groups: dict[str, Any],
    *,
    source_path: Path,
    run_id: str,
) -> dict[str, Any]:
    strategies = [record["strategy_hypothesis"] for record in records]
    return {
        "schema_version": "v0_3_strategy_hypotheses_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "conversion_status_counts": dict(sorted(Counter(item["conversion_status"] for item in strategies).items())),
        "strategy_type_counts": dict(sorted(Counter(item["strategy_type"] for item in strategies).items())),
        "ready_for_candidate_registry_count": sum(
            item["conversion_status"] == "ready_for_candidate_registry" for item in strategies
        ),
        "rule_group_count": len(rule_groups["groups"]),
        "strategy_boundary": STRATEGY_BOUNDARY,
        "no_feedback_check": "strategy_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_strategy_hypotheses(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    research_records = _read_jsonl(input_path)
    records = [research_record_to_strategy_record(record) for record in research_records]
    rule_groups = build_rule_groups(records)
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    rule_groups_path = output_dir / DEFAULT_RULE_GROUPS_NAME
    _write_jsonl(jsonl_path, records)
    rule_groups_path.write_text(
        json.dumps(rule_groups, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = build_manifest(records, rule_groups, source_path=input_path, run_id=run_id)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    paths = {"jsonl": jsonl_path, "manifest": manifest_path, "rule_groups": rule_groups_path}
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
        default=datetime.now(timezone.utc).strftime("strategy_hypotheses_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_strategy_hypotheses(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
