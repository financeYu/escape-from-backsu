"""Build a v0.3 EvaluationEvidence readiness review packet.

The packet summarizes the existing momentum cohort dry-run preflight for
StrategyCandidate evaluation-period and local-price coverage review. It writes
no EvaluationEvidence files, mutates no registry records, and does not adjust
candidate test periods or effective max dates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.run_v0_3_momentum_evaluation_evidence_cohort import (
    DEFAULT_COHORT_ID,
    DEFAULT_PRICE_GLOB,
    DEFAULT_PRICES_DIR,
    DRY_RUN_ADJUSTMENT_BOUNDARY,
    dry_run_momentum_evaluation_evidence_cohort,
)
from Quant_mvp.scripts.build_v0_3_momentum_evaluation_evidence_packets import (
    DEFAULT_REGISTRY,
    load_registry,
    select_momentum_evaluable_candidates,
)


SCHEMA_VERSION = "v0_3_evaluation_readiness_review_packet_0_1"
ROUTE = "active_v0_3_research_to_strategy_adoption"
ARTIFACT_TYPE = "strategy_candidate_evaluation_readiness_review_packet"
SELECTION_UNAVAILABLE = "selection unavailable / evidence insufficient"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT_ID)
    parser.add_argument("--created-at", default=date.today().isoformat(), help="YYYY-MM-DD packet date.")
    parser.add_argument("--max-date", help="Optional YYYY-MM-DD upper bound for price rows.")
    parser.add_argument("--expected-count", type=int, help="Optional selected-candidate count guard.")
    parser.add_argument("--price-glob", default=DEFAULT_PRICE_GLOB)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--max-candidate-examples",
        type=int,
        default=5,
        help="Maximum candidate examples to include in the review packet.",
    )
    return parser.parse_args(argv)


def _candidate_preflights(dry_run: dict[str, Any]) -> list[dict[str, Any]]:
    preflights: list[dict[str, Any]] = []
    for summary in dry_run.get("candidate_summaries", []):
        preflight = summary.get("preflight") if isinstance(summary, dict) else None
        if isinstance(preflight, dict):
            preflights.append(preflight)
    for blocked in dry_run.get("blocked_candidates", []):
        preflight = blocked.get("preflight") if isinstance(blocked, dict) else None
        if isinstance(preflight, dict):
            preflights.append(preflight)
    return preflights


def _sorted_counts(values: list[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _effective_max_date_summary(preflights: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = [
        preflight.get("effective_max_date_inputs")
        for preflight in preflights
        if isinstance(preflight.get("effective_max_date_inputs"), dict)
    ]
    return {
        "count_by_effective_max_date": _sorted_counts(
            [preflight.get("effective_max_date") for preflight in preflights]
        ),
        "count_by_candidate_test_period_end": _sorted_counts(
            [item.get("test_period_end") for item in inputs]
        ),
        "count_by_requested_max_date": _sorted_counts(
            [item.get("requested_max_date") for item in inputs]
        ),
        "auto_adjustment_counts": _sorted_counts(
            [item.get("auto_adjustment") for item in inputs]
        ),
        "rule": "min(created_at, requested_max_date_if_any, StrategyCandidate_test_period_end_if_any)",
        "auto_adjustment_policy": "not_performed_requires_explicit_approval",
    }


def _candidate_examples(dry_run: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for summary in dry_run.get("candidate_summaries", []):
        preflight = summary.get("preflight", {})
        examples.append(
            {
                "candidate_id": summary.get("candidate_id"),
                "readiness_status": "ready_for_actual_run_after_separate_owner_approval",
                "dry_run_status": summary.get("status"),
                "label_use_status": summary.get("label_use_status"),
                "valid_security_count": summary.get("valid_security_count"),
                "coverage_status": preflight.get("coverage_status"),
                "coverage_blocker": preflight.get("coverage_blocker"),
                "effective_max_date": preflight.get("effective_max_date"),
                "required_rows_per_ticker": preflight.get("required_rows_per_ticker"),
                "tickers_meeting_required_rows": preflight.get("tickers_meeting_required_rows"),
                "candidate_price": preflight.get("candidate_price"),
            }
        )
    for blocked in dry_run.get("blocked_candidates", []):
        preflight = blocked.get("preflight", {})
        examples.append(
            {
                "candidate_id": blocked.get("candidate_id"),
                "readiness_status": "blocked_for_actual_run",
                "dry_run_status": blocked.get("status"),
                "blocked_reason": blocked.get("blocked_reason"),
                "coverage_status": preflight.get("coverage_status"),
                "coverage_blocker": preflight.get("coverage_blocker"),
                "effective_max_date": preflight.get("effective_max_date"),
                "required_rows_per_ticker": preflight.get("required_rows_per_ticker"),
                "max_rows_per_ticker": preflight.get("max_rows_per_ticker"),
                "tickers_meeting_required_rows": preflight.get("tickers_meeting_required_rows"),
                "candidate_price": preflight.get("candidate_price"),
            }
        )
    return examples[: max(0, limit)]


def _recommended_next_action(dry_run: dict[str, Any]) -> str:
    if int(dry_run.get("blocked_count") or 0):
        return (
            "root_quant_review_required: keep blocked candidates contract_only until existing "
            "local price coverage satisfies the current StrategyCandidate test_period/"
            "effective_max_date, or approve a separate candidate-contract adjustment."
        )
    return (
        "owner_lane_approval_required: dry-run coverage is ready, but selector labels remain "
        "unavailable until a separately approved actual EvaluationEvidence run records "
        "allowlisted evidence summaries."
    )


def _missing_price_input_packet(
    *,
    registry: Path,
    prices_dir: Path,
    cohort_id: str,
    created_at: str,
    price_glob: str,
    max_date: str | None,
    expected_count: int | None,
    error: ValueError,
) -> dict[str, Any]:
    registry_rows = load_registry(registry)
    selected = select_momentum_evaluable_candidates(registry_rows)
    if expected_count is not None and len(selected) != expected_count:
        raise ValueError(f"expected {expected_count} momentum evaluable candidates, found {len(selected)}")
    return {
        "schema_version": SCHEMA_VERSION,
        "route": ROUTE,
        "artifact_type": ARTIFACT_TYPE,
        "output_written": False,
        "input_refs": {
            "registry": str(registry),
            "prices_dir": str(prices_dir),
            "price_glob": price_glob,
            "cohort_id": cohort_id,
            "created_at": created_at,
            "max_date": max_date,
            "expected_count": expected_count,
            "dry_run_helper": (
                "Quant_mvp.scripts.run_v0_3_momentum_evaluation_evidence_cohort."
                "dry_run_momentum_evaluation_evidence_cohort"
            ),
        },
        "candidate_count": len(selected),
        "ready_for_actual_run_count": 0,
        "blocked_count": len(selected),
        "price_coverage": {
            "row_count": 0,
            "ticker_count": 0,
            "date_start": None,
            "date_end": None,
        },
        "effective_max_date_summary": {
            "count_by_effective_max_date": {},
            "count_by_candidate_test_period_end": {},
            "count_by_requested_max_date": {},
            "auto_adjustment_counts": {},
            "rule": "not_evaluated_missing_quant_local_price_inputs",
            "auto_adjustment_policy": "not_performed_requires_explicit_approval",
        },
        "coverage_status_counts": {
            "blocked_missing_quant_local_price_inputs": len(selected),
        },
        "coverage_blocker_counts": {
            str(error): len(selected),
        },
        "candidate_examples": [],
        "selection_status": SELECTION_UNAVAILABLE,
        "selection_reason": "missing_quant_local_price_inputs_for_recorded_EvaluationEvidence",
        "label_readiness": {
            "selector_label_eligible": False,
            "recorded_evaluation_evidence_label_count": 0,
            "dry_run_metric_summary_count": 0,
            "blocked_candidate_count": len(selected),
            "status": "no_recorded_selector_labels",
            "contract_only_missing_actual_metrics_are_not_labels": True,
            "dry_run_metric_summaries_are_not_recorded_labels": True,
            "not_label_fields": [
                "contract_only",
                "missing_actual_metrics",
                "missing_quant_local_price_inputs",
            ],
        },
        "recommended_next_action": (
            "provide approved Quant-local daily price CSV inputs under "
            f"{prices_dir} matching {price_glob}, then rerun this readiness packet before "
            "writing EvaluationEvidence"
        ),
        "approval_boundary": {
            "candidate_registry_mutation": False,
            "market_data_ingestion": False,
            "evaluation_evidence_file_write": False,
            "auto_adjust_StrategyCandidate_test_period": False,
            "auto_adjust_effective_max_date": False,
            "adjustment_boundary": DRY_RUN_ADJUSTMENT_BOUNDARY,
            "candidate_contract_adjustment_requires_separate_approval": True,
            "actual_EvaluationEvidence_run_requires_owner_lane_approval": True,
        },
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
        "model_training_status": "not_run_review_packet_only",
        "raw_dry_run_status": {
            "mode": "blocked_before_dry_run",
            "advisory": "missing Quant-local price inputs; do not read external project price paths",
            "next_evaluation_condition": "add approved Quant-local *_daily_prices.csv inputs",
            "evidence_status_counts": {},
            "label_use_status_counts": {},
        },
    }


def build_review_packet(
    *,
    registry: Path,
    prices_dir: Path,
    cohort_id: str,
    created_at: str,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
    expected_count: int | None = None,
    max_candidate_examples: int = 5,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    try:
        dry_run = dry_run_momentum_evaluation_evidence_cohort(
            registry=registry,
            prices_dir=prices_dir,
            cohort_id=cohort_id,
            created_at=created_at,
            price_glob=price_glob,
            max_date=max_date,
            expected_count=expected_count,
            project_root=project_root,
        )
    except ValueError as exc:
        if "no daily price rows found" not in str(exc):
            raise
        return _missing_price_input_packet(
            registry=registry,
            prices_dir=prices_dir,
            cohort_id=cohort_id,
            created_at=created_at,
            price_glob=price_glob,
            max_date=max_date,
            expected_count=expected_count,
            error=exc,
        )
    price_input_blocker = str(dry_run.get("price_input_blocker") or "")
    if "no daily price rows found" in price_input_blocker:
        return _missing_price_input_packet(
            registry=registry,
            prices_dir=prices_dir,
            cohort_id=cohort_id,
            created_at=created_at,
            price_glob=price_glob,
            max_date=max_date,
            expected_count=expected_count,
            error=ValueError(price_input_blocker),
        )
    preflights = _candidate_preflights(dry_run)
    coverage_blockers = [
        preflight.get("coverage_blocker") or "none"
        for preflight in preflights
    ]
    ready_count = int(dry_run.get("recorded_count") or 0)
    blocked_count = int(dry_run.get("blocked_count") or 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "route": ROUTE,
        "artifact_type": ARTIFACT_TYPE,
        "output_written": False,
        "input_refs": {
            "registry": str(registry),
            "prices_dir": str(prices_dir),
            "price_glob": price_glob,
            "cohort_id": cohort_id,
            "created_at": created_at,
            "max_date": max_date,
            "expected_count": expected_count,
            "dry_run_helper": (
                "Quant_mvp.scripts.run_v0_3_momentum_evaluation_evidence_cohort."
                "dry_run_momentum_evaluation_evidence_cohort"
            ),
        },
        "candidate_count": int(dry_run.get("candidate_count") or 0),
        "ready_for_actual_run_count": ready_count,
        "blocked_count": blocked_count,
        "price_coverage": dry_run.get("price_coverage", {}),
        "effective_max_date_summary": _effective_max_date_summary(preflights),
        "coverage_status_counts": _sorted_counts(
            [preflight.get("coverage_status") for preflight in preflights]
        ),
        "coverage_blocker_counts": _sorted_counts(coverage_blockers),
        "candidate_examples": _candidate_examples(
            dry_run,
            limit=max_candidate_examples,
        ),
        "selection_status": SELECTION_UNAVAILABLE,
        "selection_reason": (
            "review_packet_is_pre_selector_and_writes_no_recorded_EvaluationEvidence_labels"
            if not blocked_count
            else "blocked_candidates_or_missing_recorded_EvaluationEvidence_labels"
        ),
        "label_readiness": {
            "selector_label_eligible": False,
            "recorded_evaluation_evidence_label_count": 0,
            "dry_run_metric_summary_count": ready_count,
            "blocked_candidate_count": blocked_count,
            "status": "no_recorded_selector_labels",
            "contract_only_missing_actual_metrics_are_not_labels": True,
            "dry_run_metric_summaries_are_not_recorded_labels": True,
            "not_label_fields": [
                "contract_only",
                "missing_actual_metrics",
                "dry_run_metric_summaries_without_written_EvaluationEvidence",
            ],
        },
        "recommended_next_action": _recommended_next_action(dry_run),
        "approval_boundary": {
            "candidate_registry_mutation": False,
            "market_data_ingestion": False,
            "evaluation_evidence_file_write": False,
            "auto_adjust_StrategyCandidate_test_period": False,
            "auto_adjust_effective_max_date": False,
            "adjustment_boundary": DRY_RUN_ADJUSTMENT_BOUNDARY,
            "candidate_contract_adjustment_requires_separate_approval": True,
            "actual_EvaluationEvidence_run_requires_owner_lane_approval": True,
        },
        "no_feedback_check": dry_run.get("no_feedback_check"),
        "production_boundary_check": dry_run.get("production_boundary_check"),
        "model_training_status": "not_run_review_packet_only",
        "raw_dry_run_status": {
            "mode": dry_run.get("mode"),
            "advisory": dry_run.get("advisory"),
            "next_evaluation_condition": dry_run.get("next_evaluation_condition"),
            "evidence_status_counts": dry_run.get("evidence_status_counts", {}),
            "label_use_status_counts": dry_run.get("label_use_status_counts", {}),
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_review_packet(
        registry=args.registry,
        prices_dir=args.prices_dir,
        cohort_id=args.cohort_id,
        created_at=args.created_at,
        price_glob=args.price_glob,
        max_date=args.max_date,
        expected_count=args.expected_count,
        max_candidate_examples=args.max_candidate_examples,
        project_root=args.project_root,
    )
    print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
