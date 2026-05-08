"""Build a v0.3 rule-first selector output from ML-ready candidate rows.

The selector consumes allowlisted candidate/evidence summaries and emits
AdoptionCandidate review input rows only. It does not train models, create
labels, replace runtime ranking, or activate production behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.artifact_io import read_jsonl, write_jsonl

DEFAULT_INPUT = Path("Quant_mvp/data/v0_3/ml_ready_candidate_inputs/v0_3_ml_ready_candidate_input.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/rule_first_selector")
DEFAULT_JSONL_NAME = "v0_3_rule_first_selector.jsonl"
DEFAULT_CSV_NAME = "v0_3_rule_first_selector.csv"
DEFAULT_MANIFEST_NAME = "v0_3_rule_first_selector_manifest.json"

SELECTOR_VERSION = "v0_3_rule_first_selector_0_1"
MANIFEST_SCHEMA_VERSION = "v0_3_rule_first_selector_manifest_0_1"
GENERIC_PROXY_ROLE = "generic_momentum_proxy"
STRATEGY_CANDIDATE = "strategy_candidate"

RULE_ONLY = "rule_only"
ML_MODEL = "ml_model"
HYBRID_ML_RULE = "hybrid_ml_rule"
BLOCKED_INSUFFICIENT_LABELS = "blocked_insufficient_labels"
BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE = "blocked_no_candidate_level_evidence"
SELECTOR_SCORE_SOURCES = {
    RULE_ONLY,
    ML_MODEL,
    HYBRID_ML_RULE,
    BLOCKED_INSUFFICIENT_LABELS,
    BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE,
}

HARD_PASS = "pass"
HARD_EXCLUDED = "excluded"
MINIMUM_PASS = "pass"
MINIMUM_BLOCKED = "blocked"

CRITICAL_FAILURE_TOKENS = (
    "critical",
    "contract_invalid",
    "invalid_contract",
    "leakage",
    "lookahead",
    "no_lookahead_violation",
    "point_in_time_violation",
)

OUTPUT_FIELDS = [
    "selector_version",
    "selector_run_id",
    "candidate_id",
    "candidate_version",
    "evidence_id",
    "metric_subject_type",
    "metric_subject_id",
    "candidate_metric_match",
    "candidate_metric_match_reason",
    "hard_gate_status",
    "hard_gate_reason",
    "minimum_gate_status",
    "minimum_gate_reason",
    "rule_score",
    "ml_selector_score",
    "final_selector_score",
    "selector_score_source",
    "selector_rank",
    "review_priority",
    "actual_metric_source",
    "actual_metric_role",
    "actual_total_return",
    "actual_max_drawdown",
    "actual_sharpe",
    "actual_turnover",
    "actual_volatility",
    "failure_flags",
    "adoption_candidate_boundary",
    "no_feedback_check",
    "activation_boundary",
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        for record in records:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


def _has_critical_failure(flags: list[Any]) -> bool:
    joined = " ".join(str(flag).lower() for flag in flags)
    return any(token in joined for token in CRITICAL_FAILURE_TOKENS)


def _is_generic_proxy_only(record: dict[str, Any]) -> bool:
    return (
        record.get("metric_subject_type") == "generic_proxy"
        or record.get("metric_role") == GENERIC_PROXY_ROLE
        or record.get("metric_subject_id") == GENERIC_PROXY_ROLE
        or record.get("label_decision") == "blocked_generic_proxy_not_candidate_level"
    )


def _has_candidate_level_evidence(record: dict[str, Any]) -> bool:
    return bool(record.get("evaluation_id")) and record.get("evaluation_status") != "missing_evaluation_evidence"


def hard_gate(record: dict[str, Any]) -> tuple[str, str]:
    flags = _as_list(record.get("evaluation_failure_flags"))
    if record.get("excluded_untradable") is True:
        return HARD_EXCLUDED, "excluded_untradable"
    if record.get("excluded_failure") is True:
        return HARD_EXCLUDED, "excluded_failure"
    if _has_critical_failure(flags):
        return HARD_EXCLUDED, "critical_failure_or_leakage_no_lookahead_violation"
    if not _has_candidate_level_evidence(record):
        return HARD_EXCLUDED, "missing_candidate_level_evidence"
    if _is_generic_proxy_only(record):
        return HARD_EXCLUDED, "generic_proxy_only"
    if record.get("metric_subject_type") != STRATEGY_CANDIDATE:
        return HARD_EXCLUDED, "missing_candidate_level_evidence"
    if record.get("metric_subject_id") != record.get("candidate_id"):
        return HARD_EXCLUDED, "metric_subject_id_candidate_id_mismatch"
    if record.get("candidate_metric_match") is not True:
        return HARD_EXCLUDED, "candidate_metric_match_not_true"
    if record.get("actual_metric_summary_available") is False:
        return HARD_EXCLUDED, "invalid_evidence_contract"
    return HARD_PASS, "passed_hard_exclusion"


def _metric_summary_present(record: dict[str, Any]) -> bool:
    if record.get("actual_metric_summary_available") is True:
        return True
    return any(
        _as_float(record.get(column)) is not None
        for column in ("actual_total_return", "actual_max_drawdown", "actual_sharpe", "actual_turnover")
    )


def _benchmark_comparison_present(record: dict[str, Any]) -> bool:
    explicit = record.get("has_benchmark_comparison")
    if explicit is not None:
        return explicit is True or explicit == 1
    return any(
        _as_float(record.get(column)) is not None
        for column in (
            "benchmark_return",
            "proxy_return",
            "excess_return_vs_proxy",
            "actual_benchmark_return",
            "actual_proxy_return",
            "actual_excess_return_vs_proxy",
        )
    )


def _risk_metric_present(record: dict[str, Any]) -> bool:
    return any(
        _as_float(record.get(column)) is not None
        for column in ("actual_max_drawdown", "actual_sharpe", "actual_turnover", "actual_volatility")
    )


def minimum_gate(record: dict[str, Any]) -> tuple[str, str]:
    checks = {
        "metric_subject_type_strategy_candidate": record.get("metric_subject_type") == STRATEGY_CANDIDATE,
        "candidate_metric_match_true": record.get("candidate_metric_match") is True,
        "metric_summary_present": _metric_summary_present(record),
        "benchmark_reference_comparison_present": _benchmark_comparison_present(record),
        "risk_metric_present": _risk_metric_present(record),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        return MINIMUM_BLOCKED, "missing_" + "__".join(failed)
    return MINIMUM_PASS, "passed_minimum_evidence_gate"


def _rule_score(record: dict[str, Any]) -> float:
    total_return = _as_float(record.get("actual_total_return")) or 0.0
    max_drawdown = _as_float(record.get("actual_max_drawdown")) or 0.0
    sharpe = _as_float(record.get("actual_sharpe")) or 0.0
    turnover = _as_float(record.get("actual_turnover")) or 0.0
    volatility = _as_float(record.get("actual_volatility")) or 0.0
    excess_return = (
        _as_float(record.get("excess_return_vs_proxy"))
        if _as_float(record.get("excess_return_vs_proxy")) is not None
        else _as_float(record.get("actual_excess_return_vs_proxy"))
    )
    excess_return = excess_return or 0.0

    return_component = _clip((total_return + 0.25) / 0.75, 0.0, 1.0)
    drawdown_component = _clip(1.0 - abs(max_drawdown) / 0.50, 0.0, 1.0)
    sharpe_component = _clip((sharpe + 0.5) / 2.5, 0.0, 1.0)
    turnover_component = _clip(1.0 - turnover / 2.0, 0.0, 1.0)
    volatility_component = _clip(1.0 - volatility / 0.80, 0.0, 1.0)
    excess_component = _clip((excess_return + 0.20) / 0.60, 0.0, 1.0)
    return round(
        100.0
        * (
            0.22 * return_component
            + 0.18 * drawdown_component
            + 0.22 * sharpe_component
            + 0.12 * turnover_component
            + 0.10 * volatility_component
            + 0.16 * excess_component
        ),
        6,
    )


def _ml_selector_score(record: dict[str, Any]) -> float | None:
    for column in ("ml_selector_score", "selector_score", "model_selector_score"):
        score = _as_float(record.get(column))
        if score is not None:
            return score
    return None


def _selector_source(
    record: dict[str, Any],
    hard_gate_status: str,
    hard_gate_reason: str,
    rule_score: float | None,
    ml_score: float | None,
) -> str:
    if hard_gate_status != HARD_PASS:
        if hard_gate_reason == "missing_candidate_level_evidence":
            return BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE
        return BLOCKED_INSUFFICIENT_LABELS
    if rule_score is not None and ml_score is not None:
        return HYBRID_ML_RULE
    if rule_score is not None:
        return RULE_ONLY
    if ml_score is not None:
        return ML_MODEL
    if record.get("candidate_metric_match") is not True:
        return BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE
    return BLOCKED_INSUFFICIENT_LABELS


def build_selector_rows(records: list[dict[str, Any]], *, run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        hard_status, hard_reason = hard_gate(record)
        minimum_status, minimum_reason = (
            minimum_gate(record) if hard_status == HARD_PASS else (MINIMUM_BLOCKED, "hard_gate_not_passed")
        )
        ml_score = _ml_selector_score(record) if hard_status == HARD_PASS and minimum_status == MINIMUM_PASS else None
        rule_score = _rule_score(record) if hard_status == HARD_PASS and minimum_status == MINIMUM_PASS else None
        if rule_score is not None and ml_score is not None:
            final_score = round((0.70 * rule_score) + (0.30 * ml_score), 6)
        elif rule_score is not None:
            final_score = rule_score
        elif ml_score is not None:
            final_score = ml_score
        else:
            final_score = None
        source = _selector_source(record, hard_status, hard_reason, rule_score, ml_score)
        row = {
            "selector_version": SELECTOR_VERSION,
            "selector_run_id": run_id,
            "candidate_id": record.get("candidate_id"),
            "candidate_version": record.get("candidate_version"),
            "evidence_id": record.get("evaluation_id"),
            "metric_subject_type": record.get("metric_subject_type"),
            "metric_subject_id": record.get("metric_subject_id"),
            "candidate_metric_match": record.get("candidate_metric_match"),
            "candidate_metric_match_reason": record.get("candidate_metric_match_reason"),
            "hard_gate_status": hard_status,
            "hard_gate_reason": hard_reason,
            "minimum_gate_status": minimum_status,
            "minimum_gate_reason": minimum_reason,
            "rule_score": rule_score,
            "ml_selector_score": ml_score,
            "final_selector_score": final_score,
            "selector_score_source": source,
            "selector_rank": None,
            "review_priority": "not_ranked",
            "actual_metric_source": record.get("metric_source") or record.get("actual_label_source"),
            "actual_metric_role": record.get("metric_role") or record.get("actual_label_role"),
            "actual_total_return": record.get("actual_total_return"),
            "actual_max_drawdown": record.get("actual_max_drawdown"),
            "actual_sharpe": record.get("actual_sharpe"),
            "actual_turnover": record.get("actual_turnover"),
            "actual_volatility": record.get("actual_volatility"),
            "failure_flags": _as_list(record.get("evaluation_failure_flags")),
            "adoption_candidate_boundary": "review_input_only_not_adoption_decision",
            "no_feedback_check": "rule_first_selector_must_not_feed_runtime_ranking_reports_backtests_trading_or_auto_adoption",
            "activation_boundary": "production_activation_requires_later_root_approved_gate",
        }
        validate_selector_row(row)
        rows.append(row)

    ranked = sorted(
        (row for row in rows if row.get("final_selector_score") is not None and row.get("hard_gate_status") == HARD_PASS),
        key=lambda row: (-float(row["final_selector_score"]), str(row.get("candidate_id"))),
    )
    for rank, row in enumerate(ranked, start=1):
        row["selector_rank"] = rank
        if rank <= 10:
            row["review_priority"] = "top_review_candidate"
        elif rank <= 25:
            row["review_priority"] = "secondary_review_candidate"
        else:
            row["review_priority"] = "reviewable_candidate"
        validate_selector_row(row)
    validate_selector_rows(rows)
    return rows


def validate_selector_row(row: dict[str, Any]) -> None:
    missing = [field for field in OUTPUT_FIELDS if field not in row]
    if missing:
        raise ValueError(f"selector row missing fields: {missing}")
    if row.get("selector_score_source") not in SELECTOR_SCORE_SOURCES:
        raise ValueError(f"invalid selector_score_source: {row.get('selector_score_source')}")
    if row.get("hard_gate_status") != HARD_PASS:
        if row.get("selector_rank") is not None:
            raise ValueError("hard-excluded rows may not receive selector_rank")
        if row.get("rule_score") is not None or row.get("final_selector_score") is not None:
            raise ValueError("hard-excluded rows may not receive selector scores")
    if row.get("metric_subject_type") == "generic_proxy" or row.get("actual_metric_role") == GENERIC_PROXY_ROLE:
        if row.get("rule_score") is not None or row.get("ml_selector_score") is not None:
            raise ValueError("generic proxy rows may not receive selector scores")
    if row.get("minimum_gate_status") != MINIMUM_PASS and row.get("rule_score") is not None:
        raise ValueError("minimum-gate-blocked rows may not receive rule_score")


def validate_selector_rows(rows: list[dict[str, Any]]) -> None:
    candidate_ids = [str(row.get("candidate_id")) for row in rows]
    duplicates = [candidate_id for candidate_id, count in Counter(candidate_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate candidate_id rows: {sorted(duplicates)}")
    for row in rows:
        validate_selector_row(row)


def build_manifest(rows: list[dict[str, Any]], *, run_id: str, input_ref: Path) -> dict[str, Any]:
    hard_excluded_count = sum(row.get("hard_gate_status") != HARD_PASS for row in rows)
    rule_scored_candidate_count = sum(row.get("rule_score") is not None for row in rows)
    ml_scored_candidate_count = sum(row.get("ml_selector_score") is not None for row in rows)
    ranked_rows = [row for row in rows if row.get("selector_rank") is not None]
    top_review_candidates_count = sum(row.get("review_priority") == "top_review_candidate" for row in rows)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "selector_version": SELECTOR_VERSION,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_ref": str(input_ref),
        "total_candidates": len(rows),
        "hard_excluded_count": hard_excluded_count,
        "rule_scored_candidate_count": rule_scored_candidate_count,
        "ml_scored_candidate_count": ml_scored_candidate_count,
        "ranked_candidate_count": len(ranked_rows),
        "top_review_candidates_count": top_review_candidates_count,
        "selector_score_source_counts": dict(
            sorted(Counter(str(row.get("selector_score_source")) for row in rows).items())
        ),
        "hard_gate_status_counts": dict(sorted(Counter(str(row.get("hard_gate_status")) for row in rows).items())),
        "hard_gate_reason_counts": dict(sorted(Counter(str(row.get("hard_gate_reason")) for row in rows).items())),
        "minimum_gate_status_counts": dict(
            sorted(Counter(str(row.get("minimum_gate_status")) for row in rows).items())
        ),
        "minimum_gate_reason_counts": dict(
            sorted(Counter(str(row.get("minimum_gate_reason")) for row in rows).items())
        ),
        "output_fields": list(OUTPUT_FIELDS),
        "selector_score_sources": sorted(SELECTOR_SCORE_SOURCES),
        "selection_status": (
            "review_candidates_available"
            if top_review_candidates_count > 0
            else "selection_unavailable_evidence_insufficient"
        ),
        "missing_evidence_policy": "missing_candidate_level_evidence_rows_receive_no_score_or_rank",
        "generic_proxy_policy": "generic_momentum_proxy_rows_are_reference_features_only_not_selector_scores",
        "no_feedback_check": "rule_first_selector_must_not_feed_runtime_ranking_reports_backtests_trading_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_rule_first_selector(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    records = read_jsonl(input_path)
    rows = build_selector_rows(records, run_id=run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    write_jsonl(jsonl_path, rows)
    manifest = build_manifest(rows, run_id=run_id, input_ref=input_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths = {"jsonl": jsonl_path, "manifest": manifest_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        write_csv(csv_path, rows)
        paths["csv"] = csv_path
    return paths


def dry_run_rule_first_selector(input_path: Path, *, run_id: str) -> dict[str, Any]:
    records = read_jsonl(input_path)
    rows = build_selector_rows(records, run_id=run_id)
    return {
        "mode": "dry_run",
        "output_written": False,
        "record_count": len(rows),
        "manifest": build_manifest(rows, run_id=run_id, input_ref=input_path),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("rule_first_selector_%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate selector rows, then print the manifest without writing outputs.",
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        result = dry_run_rule_first_selector(args.input, run_id=args.run_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    paths = build_rule_first_selector(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
