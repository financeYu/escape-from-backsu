"""Build the v0.4.2 EvaluationEvidence coverage cohort.

The cohort records candidate-level evidence gaps without converting draft or
blocked StrategyCandidates into recorded metrics. Outputs are evidence-only
coverage packets and a compact v0.4.2 manifest for the selector route.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.candidate_rank_adapter import SUPPORTED_STRATEGY_TYPES
from Quant_mvp.backtest_mvp.evaluation_evidence import (
    build_needs_more_evidence_packet,
    strategy_candidate_payload,
    write_evaluation_evidence_markdown,
)
from Quant_mvp.scripts.artifact_io import (
    parse_json_fenced_markdown,
    read_json,
    read_jsonl,
)


DEFAULT_REGISTRY = Path("Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl")
DEFAULT_EVIDENCE_DIR = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence")
DEFAULT_OUTPUT_DIR = DEFAULT_EVIDENCE_DIR / "v0_4_2_coverage_cohort_1"
DEFAULT_COVERAGE_MANIFEST_DIR = Path("Quant_mvp/data/v0_4/evaluation_evidence_coverage")
DEFAULT_COVERAGE_MANIFEST_NAME = "v0_4_2_evaluation_evidence_coverage_manifest.json"
DEFAULT_ML_READY_MANIFEST = Path(
    "Quant_mvp/data/v0_3/ml_ready_candidate_inputs/v0_3_ml_ready_candidate_input_manifest.json"
)
DEFAULT_FEATURE_MANIFEST = Path(
    "Quant_mvp/data/v0_3/selector_feature_matrix/v0_3_selector_feature_matrix_manifest.json"
)
DEFAULT_TRAINABILITY_MANIFEST = Path(
    "Quant_mvp/data/v0_4/selector_model_training/v0_4_selector_trainability_manifest.json"
)
DEFAULT_COHORT_ID = "v0_4_2_manual_review_gap_cohort_1"
DEFAULT_CREATED_AT = "2026-05-07"
ALLOWED_BLOCKER_SETS = (frozenset({"manual_review_required"}),)
FORBIDDEN_BLOCKERS = {
    "blocked_by_data",
    "point_in_time_fundamentals_required",
    "valuation_lane",
    "hybrid_split_required",
    "out_of_scope_or_rejected",
    "language_guardrail_violation",
}
KOSPI_BOUNDARY_MARKERS = ("KOSPI", "KOSPI200", "Korean equity")
FORBIDDEN_UNIVERSE_SOURCE_MARKERS = (
    "source target noted as options",
    "source target noted as futures",
    "source target noted as crypto",
    "source target noted as nasdaq",
    "source target noted as overseas",
    "source target noted as multi",
)
ALLOWED_UNIVERSE_SOURCE_MARKERS = (
    "source target noted as equity",
    "source target noted as korea; equity",
    "source target noted as korean equity",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--coverage-manifest-dir", type=Path, default=DEFAULT_COVERAGE_MANIFEST_DIR)
    parser.add_argument("--coverage-manifest-name", default=DEFAULT_COVERAGE_MANIFEST_NAME)
    parser.add_argument("--ml-ready-manifest", type=Path, default=DEFAULT_ML_READY_MANIFEST)
    parser.add_argument("--feature-manifest", type=Path, default=DEFAULT_FEATURE_MANIFEST)
    parser.add_argument("--trainability-manifest", type=Path, default=DEFAULT_TRAINABILITY_MANIFEST)
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT_ID)
    parser.add_argument("--created-at", default=DEFAULT_CREATED_AT)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def existing_evidence_candidate_ids(evidence_dir: Path, ignored_dirs: tuple[Path, ...] = ()) -> set[str]:
    if not evidence_dir.exists():
        return set()
    ids: set[str] = set()
    ignored = tuple(path.resolve() for path in ignored_dirs)
    for path in evidence_dir.rglob("ee_v0_3_*.md"):
        if any(_is_within(path, ignored_dir) for ignored_dir in ignored):
            continue
        payload = parse_json_fenced_markdown(path, required=False)
        if payload and payload.get("candidate_id"):
            ids.add(str(payload["candidate_id"]))
    return ids


def _candidate_blockers(candidate: dict[str, Any]) -> frozenset[str]:
    blockers: list[Any] = []
    for key in ("blocking_issues", "blocked_by"):
        value = candidate.get(key)
        if isinstance(value, list):
            blockers.extend(value)
        elif value:
            blockers.append(value)
    return frozenset(str(item) for item in blockers if item)


def _strategy_type(candidate: dict[str, Any]) -> str:
    scope = candidate.get("experiment_scope")
    if isinstance(scope, dict) and scope.get("strategy_type"):
        return str(scope["strategy_type"])
    return str(candidate.get("strategy_type") or "other")


def _universe_text(candidate: dict[str, Any]) -> str:
    return str(candidate.get("target_universe") or candidate.get("universe") or "")


def _kospi_boundary_status(universe: str) -> tuple[bool, str]:
    normalized = universe.lower()
    if any(marker in normalized for marker in FORBIDDEN_UNIVERSE_SOURCE_MARKERS):
        return (False, "excluded_forbidden_universe_source_target")
    if not any(marker.lower() in normalized for marker in KOSPI_BOUNDARY_MARKERS):
        return (False, "excluded_non_kospi_boundary")
    if "source target noted as" in normalized and not any(
        marker in normalized for marker in ALLOWED_UNIVERSE_SOURCE_MARKERS
    ):
        return (False, "excluded_non_equity_source_target")
    return (True, "selected_kospi_equity_boundary")


def _selection_status(candidate: dict[str, Any], existing_ids: set[str]) -> tuple[bool, str]:
    candidate_id = str(candidate.get("candidate_id") or "")
    blockers = _candidate_blockers(candidate)
    data_requirements = {str(item) for item in candidate.get("data_requirements") or []}
    strategy_type = _strategy_type(candidate)
    universe = _universe_text(candidate)
    if candidate_id in existing_ids:
        return (False, "excluded_existing_evaluation_evidence")
    if candidate.get("status") != "draft":
        return (False, f"excluded_candidate_status_{candidate.get('status')}")
    if strategy_type not in SUPPORTED_STRATEGY_TYPES:
        return (False, f"excluded_unsupported_strategy_type_{strategy_type}")
    if "daily_ohlcv" not in data_requirements and "daily_ohlcv_candidate_review_only" not in data_requirements:
        return (False, "excluded_missing_daily_ohlcv_requirement")
    boundary_ok, boundary_reason = _kospi_boundary_status(universe)
    if not boundary_ok:
        return (False, boundary_reason)
    if blockers & FORBIDDEN_BLOCKERS:
        return (False, "excluded_forbidden_blocker_" + "_".join(sorted(blockers & FORBIDDEN_BLOCKERS)))
    if blockers not in ALLOWED_BLOCKER_SETS:
        return (False, "excluded_requires_nontrivial_candidate_refinement")
    return (True, "selected_manual_review_gap_needs_more_evidence")


def _baseline_counts(
    ml_ready_manifest: dict[str, Any],
    feature_manifest: dict[str, Any],
    trainability_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ml_ready": {
            "total_rows": ml_ready_manifest.get("total_rows"),
            "candidate_level_metric_count": ml_ready_manifest.get("candidate_level_metric_count"),
            "training_eligible_rows": feature_manifest.get("training_eligible_rows"),
            "positive_rows": ml_ready_manifest.get("label_positive"),
            "negative_rows": ml_ready_manifest.get("label_negative"),
            "null_label_rows": feature_manifest.get("null_label_rows"),
            "missing_evaluation_evidence": (
                ml_ready_manifest.get("evaluation_status_counts", {}).get("missing_evaluation_evidence")
            ),
            "strategy_family_distribution": ml_ready_manifest.get("strategy_type_counts", {}),
        },
        "v0_4_trainability_warnings": trainability_manifest.get("warnings", []),
        "v0_4_trainability_status": trainability_manifest.get("readiness_status"),
    }


def build_coverage(
    *,
    registry: Path,
    evidence_dir: Path,
    output_dir: Path,
    coverage_manifest_dir: Path,
    coverage_manifest_name: str,
    ml_ready_manifest_path: Path,
    feature_manifest_path: Path,
    trainability_manifest_path: Path,
    cohort_id: str,
    created_at: str,
    max_candidates: int,
    dry_run: bool,
) -> dict[str, Any]:
    registry_rows = read_jsonl(registry)
    existing_ids = existing_evidence_candidate_ids(evidence_dir, ignored_dirs=(output_dir,))
    ml_ready_manifest = read_json(ml_ready_manifest_path)
    feature_manifest = read_json(feature_manifest_path)
    trainability_manifest = read_json(trainability_manifest_path)

    selected: list[tuple[dict[str, Any], str]] = []
    exclusion_reasons: Counter[str] = Counter()
    for row in registry_rows:
        candidate = dict(strategy_candidate_payload(row))
        is_selected, reason = _selection_status(candidate, existing_ids)
        if is_selected:
            selected.append((row, reason))
        else:
            exclusion_reasons[reason] += 1

    selected = sorted(
        selected,
        key=lambda item: str(strategy_candidate_payload(item[0]).get("candidate_id") or ""),
    )[:max_candidates]

    evidence_records: list[dict[str, Any]] = []
    packet_paths: list[str] = []
    for row, reason in selected:
        candidate = dict(strategy_candidate_payload(row))
        packet = build_needs_more_evidence_packet(
            row,
            created_at=created_at,
            cohort_id=cohort_id,
            selection_reason=reason,
            exclusion_reason="manual_review_required_before_evidence_recorded",
        )
        evidence_records.append(packet)
        packet_path = output_dir / f"{packet['evaluation_id']}.md"
        if not dry_run:
            written = write_evaluation_evidence_markdown(packet, packet_path, project_root=PROJECT_ROOT)
            packet_paths.append(str(written.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/"))
        else:
            packet_paths.append(str(packet_path).replace("\\", "/"))

    baseline = _baseline_counts(ml_ready_manifest, feature_manifest, trainability_manifest)
    selected_count = len(evidence_records)
    manifest = {
        "schema_version": "v0_4_2_evaluation_evidence_coverage_manifest_v1_0",
        "cohort_id": cohort_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "dry_run" if dry_run else "write",
        "baseline_counts_before_v0_4_2": baseline,
        "selection_criteria": {
            "candidate_status": "draft",
            "allowed_blocker_sets": [sorted(items) for items in ALLOWED_BLOCKER_SETS],
            "required_data_requirement": "daily_ohlcv",
            "strategy_type_policy": "supported_by_existing_KOSPI_OHLCV_candidate_adapter",
            "universe_boundary": "KOSPI_or_KOSPI200_equity_source_target_required",
            "new_market_data_ingestion_required": False,
            "universe_expansion_required": False,
        },
        "selected_candidate_count": selected_count,
        "selected_candidate_ids": [str(record["candidate_id"]) for record in evidence_records],
        "selected_strategy_type_counts": dict(
            sorted(Counter(str(record["coverage_selection"]["strategy_type"]) for record in evidence_records).items())
        ),
        "selected_candidate_status_counts": dict(
            sorted(Counter(str(record["coverage_selection"]["candidate_status"]) for record in evidence_records).items())
        ),
        "coverage_packet_status_counts": dict(sorted(Counter(str(record["status"]) for record in evidence_records).items())),
        "exclusion_reason_counts": dict(sorted(exclusion_reasons.items())),
        "packet_paths": packet_paths,
        "expected_manifest_delta_after_regeneration": {
            "candidate_level_metric_count": 0,
            "training_eligible_rows": 0,
            "positive_rows": 0,
            "negative_rows": 0,
            "null_label_rows": 0,
            "missing_evaluation_evidence": -selected_count,
            "needs_more_evidence_rows": selected_count,
        },
        "label_generation_status": "not_generated_no_synthetic_label",
        "candidate_level_metric_status": "unchanged_until_approved_evidence_recorded_run",
        "defensive_alternative_policy": {
            "defensive_alternative": "cash_hold",
            "defensive_alternative_assumption": "cash_hold_zero_nominal_return",
            "defensive_no_action_check": "review_finding_only_no_runtime_signal",
        },
        "guardrails": {
            "historical_evidence_only": True,
            "performance_claim_allowed": False,
            "trading_signal_allowed": False,
            "adoption_auto_decision_allowed": False,
            "new_market_data_ingestion_allowed": False,
            "universe_expansion_allowed": False,
        },
        "no_feedback_check": "coverage_packets_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
    }
    if not dry_run:
        coverage_manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = coverage_manifest_dir / coverage_manifest_name
        selected_paths = {Path(path) for path in packet_paths}
        for stale_path in output_dir.glob("ee_v0_3_*.md"):
            relative_path = Path(str(stale_path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/"))
            if relative_path not in selected_paths:
                stale_path.unlink()
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest["manifest_path"] = str(manifest_path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_coverage(
        registry=args.registry,
        evidence_dir=args.evidence_dir,
        output_dir=args.output_dir,
        coverage_manifest_dir=args.coverage_manifest_dir,
        coverage_manifest_name=args.coverage_manifest_name,
        ml_ready_manifest_path=args.ml_ready_manifest,
        feature_manifest_path=args.feature_manifest,
        trainability_manifest_path=args.trainability_manifest,
        cohort_id=args.cohort_id,
        created_at=args.created_at,
        max_candidates=args.max_candidates,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
