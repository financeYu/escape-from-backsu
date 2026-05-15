"""v2.0 evidence readiness gap validation.

The validator checks whether KOSPI200 strategy candidate evidence can be
reviewed by the ML/rule selector as evidence-only AdoptionCandidate material.
It does not change score formulas, ranking behavior, backtest semantics,
valuation/fundamental scoring, or production outputs.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.validation.common import coerce_frame, extract_text_from_frame
from src.validation.text_guardrails import find_forbidden_terms


REPORT_VERSION = "v2_0_evidence_readiness_gap_report_v1"

READY_FOR_LIMITED_SELECTOR_REVIEW = "V2_0_READY_FOR_LIMITED_SELECTOR_REVIEW"
READY_WITH_LIMITATIONS = "V2_0_READY_WITH_LIMITATIONS"
NOT_READY = "V2_0_NOT_READY"

PASS = "pass"
WARN = "warn"
BLOCK = "block"

REQUIRED_COLUMNS = (
    "candidate_id",
    "ticker",
    "evaluation_date",
    "strategy_candidate_ref",
    "evaluation_evidence_ref",
    "adoption_candidate_ref",
    "pit_status",
    "lineage_status",
    "coverage_status",
    "feature_label_separation_status",
    "leakage_check_status",
    "no_lookahead_check_status",
    "cost_liquidity_status",
    "robustness_status",
    "manual_review_priority_status",
    "source_artifact",
    "lineage_ref",
    "manual_review_only",
)

STATUS_COLUMNS = (
    "pit_status",
    "lineage_status",
    "coverage_status",
    "feature_label_separation_status",
    "leakage_check_status",
    "no_lookahead_check_status",
    "cost_liquidity_status",
    "robustness_status",
    "manual_review_priority_status",
)

PASS_STATUSES = frozenset(
    {
        "pass",
        "complete",
        "ready",
        "pit_safe",
        "lineage_present",
        "coverage_complete",
        "separated",
        "manual_review_only",
    }
)
WARN_STATUSES = frozenset(
    {
        "warn",
        "partial",
        "limited",
        "diagnostic_only",
        "diagnostic_ready",
        "partial_diagnostic_ready",
        "vendor_reference_only",
        "limited_ready",
    }
)
BLOCK_STATUSES = frozenset(
    {
        "block",
        "fail",
        "failed",
        "missing",
        "missing_artifact",
        "missing_lineage",
        "insufficient_data",
        "insufficient_coverage",
        "pending_data",
        "after_evaluation_date",
        "reference_only_after_evaluation_date",
        "blocked_by_reconciliation",
        "skipped_missing_baseline_artifacts",
        "leakage_risk",
        "lookahead_risk",
    }
)

FORBIDDEN_COLUMNS = frozenset(
    {
        "valuation_score",
        "fundamental_score",
        "technical_composite_score",
        "final_composite_score",
        "production_rank",
        "production_ranking",
        "trade_signal",
        "signal",
        "order_instruction",
        "rebalance_instruction",
        "forward_return",
        "future_return",
        "expected_return",
        "alpha",
        "proven_alpha",
    }
)

FORBIDDEN_LANGUAGE = frozenset(
    {
        "production ranking",
        "trading recommendation",
        "buy recommendation",
        "sell recommendation",
        "hold recommendation",
        "order instruction",
        "rebalance instruction",
        "expected return",
        "future return",
        "proven alpha",
        "market-beating",
    }
)

FORBIDDEN_FEATURE_COLUMNS = frozenset(
    {
        "forward_return",
        "future_return",
        "expected_return",
        "realized_return",
        "gross_return",
        "net_return",
        "benchmark_return",
        "max_drawdown",
        "sharpe",
        "alpha",
        "label",
        "target",
    }
)

REPORT_CONTRACT = {
    "report_version": REPORT_VERSION,
    "required_input_columns": REQUIRED_COLUMNS,
    "optional_input_columns": ("feature_columns", "label_columns", "reason_codes", "notes"),
    "candidate_row_columns": (
        "candidate_id",
        "ticker",
        "evaluation_date",
        "readiness_status",
        "blockers",
        "warnings",
        "manual_review_only",
        "source_artifact",
        "lineage_ref",
    ),
    "verdicts": (
        READY_FOR_LIMITED_SELECTOR_REVIEW,
        READY_WITH_LIMITATIONS,
        NOT_READY,
    ),
}


def build_readiness_gap_report(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Return a compact v2.0 readiness gap report for candidate evidence rows."""

    frame = coerce_frame(data)
    generated = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    global_blockers = _global_blockers(frame)
    candidate_rows = [_validate_record(record) for record in frame.to_dict(orient="records")]
    verdict = _determine_verdict(global_blockers, candidate_rows)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": generated,
        "scope": "evidence_only_manual_review_support",
        "kospi200_only": True,
        "manual_review_only": True,
        "valuation_fundamental_scoring_activation_allowed": False,
        "production_activation_allowed": False,
        "readiness_verdict": verdict,
        "global_blockers": global_blockers,
        "candidate_rows": candidate_rows,
        "summary": _summary(global_blockers, candidate_rows),
        "contract": REPORT_CONTRACT,
    }


def write_readiness_gap_report(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    output_path: str | Path,
) -> dict[str, Any]:
    """Write the readiness report as JSON and return it."""

    report = build_readiness_gap_report(data)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def validate_readiness_rows(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> bool:
    """Return True only when the report has no blockers or warning limitations."""

    report = build_readiness_gap_report(data)
    return report["readiness_verdict"] == READY_FOR_LIMITED_SELECTOR_REVIEW


def _global_blockers(frame: pd.DataFrame) -> list[str]:
    blockers: list[str] = []
    lowered_columns = {str(column).lower() for column in frame.columns}
    for column in sorted(lowered_columns & FORBIDDEN_COLUMNS):
        blockers.append(f"forbidden_column:{column}")

    text = extract_text_from_frame(frame)
    for term in find_forbidden_terms(text, FORBIDDEN_LANGUAGE | FORBIDDEN_COLUMNS):
        blockers.append(f"forbidden_language:{term}")

    for column in REQUIRED_COLUMNS:
        if column not in frame.columns:
            blockers.append(f"missing_required_column:{column}")
    return blockers


def _validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    for column in REQUIRED_COLUMNS:
        if _is_missing(record.get(column)):
            blockers.append(f"missing_required_value:{column}")

    for column in STATUS_COLUMNS:
        status = _normalize(record.get(column))
        if not status:
            blockers.append(f"missing_status:{column}")
        elif status in WARN_STATUSES:
            warnings.append(f"limited_{column}:{status}")
        elif status in BLOCK_STATUSES:
            blockers.append(f"blocked_{column}:{status}")
        elif status not in PASS_STATUSES:
            blockers.append(f"invalid_status:{column}:{status}")

    if not _truthy(record.get("manual_review_only")):
        blockers.append("manual_review_only_not_confirmed")

    feature_columns = _split_columns(record.get("feature_columns"))
    label_columns = _split_columns(record.get("label_columns"))
    overlap = sorted(set(feature_columns) & set(label_columns))
    if overlap:
        blockers.append("feature_label_overlap:" + ",".join(overlap))
    forbidden_features = sorted(set(feature_columns) & FORBIDDEN_FEATURE_COLUMNS)
    if forbidden_features:
        blockers.append("forbidden_feature_column:" + ",".join(forbidden_features))

    status = BLOCK if blockers else WARN if warnings else PASS
    return {
        "candidate_id": str(record.get("candidate_id", "")),
        "ticker": str(record.get("ticker", "")),
        "evaluation_date": str(record.get("evaluation_date", "")),
        "readiness_status": status,
        "blockers": blockers,
        "warnings": warnings,
        "manual_review_only": _truthy(record.get("manual_review_only")),
        "source_artifact": str(record.get("source_artifact", "")),
        "lineage_ref": str(record.get("lineage_ref", "")),
    }


def _determine_verdict(global_blockers: Sequence[str], candidate_rows: Sequence[Mapping[str, Any]]) -> str:
    if global_blockers or not candidate_rows:
        return NOT_READY
    statuses = [row["readiness_status"] for row in candidate_rows]
    if any(status == BLOCK for status in statuses):
        return NOT_READY
    if any(status == WARN for status in statuses):
        return READY_WITH_LIMITATIONS
    return READY_FOR_LIMITED_SELECTOR_REVIEW


def _summary(global_blockers: Sequence[str], candidate_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(candidate_rows),
        "global_blocker_count": len(global_blockers),
        "pass_count": sum(1 for row in candidate_rows if row["readiness_status"] == PASS),
        "warn_count": sum(1 for row in candidate_rows if row["readiness_status"] == WARN),
        "block_count": sum(1 for row in candidate_rows if row["readiness_status"] == BLOCK),
        "highest_priority_next_task": _highest_priority_next_task(global_blockers, candidate_rows),
    }


def _highest_priority_next_task(
    global_blockers: Sequence[str],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> str:
    if global_blockers:
        return "remove forbidden or missing global readiness fields before selector review"
    for row in candidate_rows:
        blockers = row.get("blockers", [])
        if blockers:
            return str(blockers[0])
    for row in candidate_rows:
        warnings = row.get("warnings", [])
        if warnings:
            return str(warnings[0])
    return "maintain evidence-only manual review readiness packet"


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and not value.strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _normalize(value) in {"true", "1", "yes", "y", "manual_review_only"}


def _split_columns(value: Any) -> tuple[str, ...]:
    if _is_missing(value):
        return ()
    if isinstance(value, str):
        raw_parts = value.replace("|", ",").replace(";", ",").split(",")
    else:
        try:
            raw_parts = list(value)
        except TypeError:
            raw_parts = [value]
    return tuple(part.strip().lower() for part in raw_parts if str(part).strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a v2.0 evidence readiness gap report.")
    parser.add_argument("--input", required=True, help="CSV input with candidate evidence readiness rows.")
    parser.add_argument("--output", required=True, help="JSON report output path.")
    args = parser.parse_args(argv)

    frame = pd.read_csv(args.input)
    report = write_readiness_gap_report(frame, args.output)
    print(json.dumps({"readiness_verdict": report["readiness_verdict"]}, ensure_ascii=False))
    return 1 if report["readiness_verdict"] == NOT_READY else 0


if __name__ == "__main__":
    raise SystemExit(main())
