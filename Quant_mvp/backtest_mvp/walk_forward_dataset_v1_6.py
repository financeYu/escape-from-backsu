"""Build v1.6-ready walk-forward backtest input artifacts.

The output is evidence-only preparation for later backtest/simulation review.
It does not activate production ranking, valuation scoring, trading, orders, or
automatic adoption.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Quant_mvp.scripts.artifact_io import parse_json_fenced_markdown, write_csv, write_jsonl


SCHEMA_VERSION = "v1_6_walk_forward_backtest_input_v1"
DEFAULT_EVIDENCE_ROOT = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence")
DEFAULT_V1_6_REVIEW_DIR = Path("Quant_mvp/data/v1_6/review_priority")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v1_6/walk_forward_backtest")
DEFAULT_CSV_NAME = "v1_6_walk_forward_backtest_input_latest.csv"
DEFAULT_JSONL_NAME = "v1_6_walk_forward_backtest_input_latest.jsonl"
DEFAULT_MANIFEST_NAME = "v1_6_walk_forward_backtest_manifest_latest.json"

EVIDENCE_ONLY_NOTICE = (
    "v1.6 walk-forward dataset is candidate-only evidence preparation for "
    "backtest review"
)
MANUAL_REVIEW_ONLY_NOTICE = (
    "manual_review_priority is a human review queue category, not an automated "
    "ordering or action instruction"
)
PROHIBITED_ACTIONS_NOTICE = (
    "No live trading, brokerage integration, order generation, automatic "
    "rebalance instruction, production ranking replacement, valuation scoring, "
    "fundamental scoring, expected-return claim, future-return claim, or "
    "proven-alpha claim is created by this artifact."
)

V1_6_FILES = {
    "composite": "v1_6_composite_review_priority_manifest_latest.csv",
    "confidence": "v1_6_confidence_score_manifest_latest.csv",
    "horizon": "v1_6_horizon_stability_report_latest.csv",
    "split": "v1_6_split_stability_report_latest.csv",
    "layer": "v1_6_layer_redundancy_report_latest.csv",
    "readiness": "v1_6_v2_0_readiness_packet_latest.json",
}

OUTPUT_COLUMNS = (
    "schema_version",
    "row_kind",
    "backtest_input_status",
    "candidate_id",
    "ticker",
    "evaluation_id",
    "evidence_source_path",
    "evaluation_window_start",
    "evaluation_window_end",
    "fold_index",
    "fold_start",
    "fold_end",
    "fold_period_count",
    "walk_forward_status",
    "walk_forward_method",
    "strategy_return",
    "reference_return",
    "relative_return",
    "relative_return_positive",
    "valid_security_count",
    "reference_security_count",
    "aggregate_strategy_return",
    "aggregate_reference_return",
    "aggregate_relative_return",
    "walk_forward_fold_count",
    "walk_forward_passing_fold_count",
    "walk_forward_passing_fold_ratio",
    "metric_total_return",
    "metric_annualized_return",
    "metric_max_drawdown",
    "metric_annualized_volatility",
    "metric_sharpe_ratio",
    "metric_turnover_proxy",
    "metric_coverage_ratio",
    "benchmark_comparison",
    "no_lookahead_check",
    "no_feedback_check",
    "production_boundary_check",
    "v1_6_candidate_match_status",
    "v1_6_manual_review_priority",
    "v1_6_confidence_score",
    "v1_6_confidence_support_status",
    "v1_6_horizon_stability_status",
    "v1_6_split_stability_status",
    "v1_6_redundancy_status_summary",
    "v1_6_readiness_verdict",
    "v1_6_missing_dependencies",
    "blocker_codes",
    "manual_review_only_notice",
    "evidence_only_notice",
    "prohibited_actions_notice",
)


def build_v1_6_walk_forward_backtest_dataset(
    *,
    evidence_roots: tuple[str | Path, ...] = (DEFAULT_EVIDENCE_ROOT,),
    v1_6_review_dir: str | Path = DEFAULT_V1_6_REVIEW_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Write fold-level walk-forward input rows plus manifest."""

    review_dir = Path(v1_6_review_dir)
    output_base = Path(output_dir)
    lookups = _load_v1_6_lookups(review_dir)
    readiness_packet = lookups["readiness_packet"]
    evidence_payloads = _load_evidence_payloads(tuple(Path(root) for root in evidence_roots))

    rows: list[dict[str, Any]] = []
    for payload in evidence_payloads:
        rows.extend(_walk_forward_rows(payload, lookups, readiness_packet))

    evidence_candidate_ids = {
        str(payload.get("candidate_id", ""))
        for payload in evidence_payloads
        if str(payload.get("candidate_id", "")).strip()
    }
    for candidate_id, composite in sorted(lookups["composite"].items()):
        if candidate_id in evidence_candidate_ids:
            continue
        rows.append(_missing_walk_forward_row(candidate_id, composite, lookups, readiness_packet))

    rows = [_ordered_row(row) for row in rows]
    output_base.mkdir(parents=True, exist_ok=True)
    csv_path = output_base / DEFAULT_CSV_NAME
    jsonl_path = output_base / DEFAULT_JSONL_NAME
    manifest_path = output_base / DEFAULT_MANIFEST_NAME
    write_csv(csv_path, rows)
    write_jsonl(jsonl_path, rows)
    manifest = _manifest(
        rows=rows,
        evidence_roots=tuple(Path(root) for root in evidence_roots),
        review_dir=review_dir,
        csv_path=csv_path,
        jsonl_path=jsonl_path,
        manifest_path=manifest_path,
        lookups=lookups,
        evidence_payloads=evidence_payloads,
        readiness_packet=readiness_packet,
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _load_v1_6_lookups(review_dir: Path) -> dict[str, Any]:
    return {
        "composite": _read_csv_by_candidate(review_dir / V1_6_FILES["composite"]),
        "confidence": _read_csv_by_candidate(review_dir / V1_6_FILES["confidence"]),
        "horizon": _read_csv_by_candidate(review_dir / V1_6_FILES["horizon"]),
        "split": _read_csv_by_candidate(review_dir / V1_6_FILES["split"]),
        "layer": _read_layer_summary_by_candidate(review_dir / V1_6_FILES["layer"]),
        "readiness_packet": _read_json_if_exists(review_dir / V1_6_FILES["readiness"]),
    }


def _read_csv_by_candidate(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            candidate_id = str(row.get("candidate_id", "")).strip()
            if candidate_id and candidate_id not in rows:
                rows[candidate_id] = dict(row)
        return rows


def _read_layer_summary_by_candidate(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    summary: dict[str, set[str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            candidates = [
                str(row.get("candidate_id", "")).strip(),
                str(row.get("candidate_id_a", "")).strip(),
                str(row.get("candidate_id_b", "")).strip(),
            ]
            status = str(row.get("redundancy_status", "") or row.get("layer_redundancy_status", "")).strip()
            for candidate_id in candidates:
                if candidate_id:
                    summary.setdefault(candidate_id, set()).add(status or "available")
    return {
        candidate_id: {"redundancy_status_summary": ";".join(sorted(statuses))}
        for candidate_id, statuses in summary.items()
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    return payload


def _load_evidence_payloads(evidence_roots: tuple[Path, ...]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for root in evidence_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            payload = parse_json_fenced_markdown(path, required=False)
            if not payload:
                continue
            if not isinstance(payload.get("walk_forward_stability_summary"), dict):
                continue
            payloads.append(payload)
    return payloads


def _walk_forward_rows(
    payload: dict[str, Any],
    lookups: dict[str, Any],
    readiness_packet: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_id = _text(payload.get("candidate_id"))
    summary = payload.get("walk_forward_stability_summary") or {}
    folds = summary.get("folds") if isinstance(summary, dict) else None
    if not isinstance(folds, list) or not folds:
        return []
    base = _base_row(payload, lookups, readiness_packet)
    rows = []
    for fold in folds:
        if not isinstance(fold, dict):
            continue
        row = {
            **base,
            "row_kind": "walk_forward_fold",
            "backtest_input_status": "walk_forward_fold_ready",
            "fold_index": fold.get("fold_index"),
            "fold_start": fold.get("start"),
            "fold_end": fold.get("end"),
            "fold_period_count": fold.get("period_count"),
            "strategy_return": fold.get("strategy_return"),
            "reference_return": fold.get("reference_return"),
            "relative_return": fold.get("relative_return"),
            "relative_return_positive": fold.get("relative_return_positive"),
            "valid_security_count": fold.get("valid_security_count"),
            "reference_security_count": fold.get("reference_security_count"),
        }
        if not candidate_id:
            row["backtest_input_status"] = "blocked_missing_candidate_id"
        rows.append(row)
    return rows


def _base_row(
    payload: dict[str, Any],
    lookups: dict[str, Any],
    readiness_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = _text(payload.get("candidate_id"))
    metric = payload.get("metric_summary") if isinstance(payload.get("metric_summary"), dict) else {}
    risk = payload.get("risk_metric_summary") if isinstance(payload.get("risk_metric_summary"), dict) else {}
    summary = payload.get("walk_forward_stability_summary") or {}
    window = payload.get("evaluation_window") if isinstance(payload.get("evaluation_window"), dict) else {}
    composite = lookups["composite"].get(candidate_id, {})
    confidence = lookups["confidence"].get(candidate_id, {})
    horizon = lookups["horizon"].get(candidate_id, {})
    split = lookups["split"].get(candidate_id, {})
    layer = lookups["layer"].get(candidate_id, {})
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "ticker": _ticker_from_review_rows(composite, confidence, horizon, split),
        "evaluation_id": payload.get("evaluation_id"),
        "evidence_source_path": payload.get("_source_path"),
        "evaluation_window_start": window.get("start"),
        "evaluation_window_end": window.get("end"),
        "walk_forward_status": _first_present(summary.get("status"), metric.get("oos_stability_status")),
        "walk_forward_method": summary.get("method"),
        "aggregate_strategy_return": summary.get("aggregate_strategy_return"),
        "aggregate_reference_return": summary.get("aggregate_reference_return"),
        "aggregate_relative_return": summary.get("aggregate_relative_return"),
        "walk_forward_fold_count": _first_present(summary.get("fold_count"), metric.get("walk_forward_fold_count")),
        "walk_forward_passing_fold_count": _first_present(
            summary.get("passing_fold_count"),
            metric.get("walk_forward_passing_fold_count"),
        ),
        "walk_forward_passing_fold_ratio": _first_present(
            summary.get("passing_fold_ratio"),
            metric.get("walk_forward_passing_fold_ratio"),
        ),
        "metric_total_return": metric.get("total_return"),
        "metric_annualized_return": metric.get("annualized_return"),
        "metric_max_drawdown": _first_present(risk.get("max_drawdown"), metric.get("max_drawdown")),
        "metric_annualized_volatility": _first_present(
            risk.get("annualized_volatility"),
            metric.get("annualized_volatility"),
        ),
        "metric_sharpe_ratio": _first_present(risk.get("sharpe_ratio"), metric.get("sharpe_ratio")),
        "metric_turnover_proxy": _first_present(risk.get("turnover_proxy"), metric.get("turnover_proxy")),
        "metric_coverage_ratio": _first_present(risk.get("coverage_ratio"), metric.get("coverage_ratio")),
        "benchmark_comparison": metric.get("benchmark_comparison"),
        "no_lookahead_check": payload.get("no_lookahead_check"),
        "no_feedback_check": payload.get("no_feedback_check"),
        "production_boundary_check": payload.get("production_boundary_check"),
        "v1_6_candidate_match_status": "matched_v1_6_review_priority" if composite else "missing_v1_6_candidate_match",
        "v1_6_manual_review_priority": composite.get("manual_review_priority"),
        "v1_6_confidence_score": confidence.get("confidence_score") or composite.get("confidence_score"),
        "v1_6_confidence_support_status": confidence.get("confidence_support_status") or composite.get("confidence_support_status"),
        "v1_6_horizon_stability_status": horizon.get("horizon_stability_status") or composite.get("horizon_stability_status"),
        "v1_6_split_stability_status": split.get("split_stability_status") or composite.get("split_stability_status"),
        "v1_6_redundancy_status_summary": layer.get("redundancy_status_summary") or composite.get("redundancy_status_summary"),
        "v1_6_readiness_verdict": readiness_packet.get("readiness_verdict"),
        "v1_6_missing_dependencies": _join(readiness_packet.get("missing_dependencies")),
        "blocker_codes": _join(payload.get("known_limitations")),
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
    }


def _missing_walk_forward_row(
    candidate_id: str,
    composite: dict[str, str],
    lookups: dict[str, Any],
    readiness_packet: dict[str, Any],
) -> dict[str, Any]:
    confidence = lookups["confidence"].get(candidate_id, {})
    horizon = lookups["horizon"].get(candidate_id, {})
    split = lookups["split"].get(candidate_id, {})
    layer = lookups["layer"].get(candidate_id, {})
    return _ordered_row(
        {
            "schema_version": SCHEMA_VERSION,
            "row_kind": "v1_6_candidate_without_walk_forward_folds",
            "backtest_input_status": "missing_walk_forward_evaluation_evidence",
            "candidate_id": candidate_id,
            "ticker": _ticker_from_review_rows(composite, confidence, horizon, split),
            "v1_6_candidate_match_status": "v1_6_candidate_without_walk_forward_folds",
            "v1_6_manual_review_priority": composite.get("manual_review_priority"),
            "v1_6_confidence_score": confidence.get("confidence_score") or composite.get("confidence_score"),
            "v1_6_confidence_support_status": confidence.get("confidence_support_status") or composite.get("confidence_support_status"),
            "v1_6_horizon_stability_status": horizon.get("horizon_stability_status") or composite.get("horizon_stability_status"),
            "v1_6_split_stability_status": split.get("split_stability_status") or composite.get("split_stability_status"),
            "v1_6_redundancy_status_summary": layer.get("redundancy_status_summary") or composite.get("redundancy_status_summary"),
            "v1_6_readiness_verdict": readiness_packet.get("readiness_verdict"),
            "v1_6_missing_dependencies": _join(readiness_packet.get("missing_dependencies")),
            "blocker_codes": "missing_walk_forward_evaluation_evidence",
            "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
            "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
            "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        }
    )


def _manifest(
    *,
    rows: list[dict[str, Any]],
    evidence_roots: tuple[Path, ...],
    review_dir: Path,
    csv_path: Path,
    jsonl_path: Path,
    manifest_path: Path,
    lookups: dict[str, Any],
    evidence_payloads: list[dict[str, Any]],
    readiness_packet: dict[str, Any],
) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    row_kinds: dict[str, int] = {}
    for row in rows:
        statuses[str(row["backtest_input_status"])] = statuses.get(str(row["backtest_input_status"]), 0) + 1
        row_kinds[str(row["row_kind"])] = row_kinds.get(str(row["row_kind"]), 0) + 1
    evidence_candidate_ids = {
        _text(payload.get("candidate_id"))
        for payload in evidence_payloads
        if _text(payload.get("candidate_id"))
    }
    v1_6_candidate_ids = set(lookups["composite"])
    missing_elements = []
    if not evidence_payloads:
        missing_elements.append("missing_walk_forward_evaluation_evidence_payloads")
    missing_elements.extend(sorted(readiness_packet.get("missing_dependencies", [])))
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_csv": str(csv_path),
        "output_jsonl": str(jsonl_path),
        "output_manifest": str(manifest_path),
        "evidence_roots": [str(root) for root in evidence_roots],
        "v1_6_review_dir": str(review_dir),
        "row_count": len(rows),
        "row_kind_counts": row_kinds,
        "backtest_input_status_counts": statuses,
        "walk_forward_fold_row_count": row_kinds.get("walk_forward_fold", 0),
        "walk_forward_candidate_count": len(evidence_candidate_ids),
        "v1_6_candidate_count": len(v1_6_candidate_ids),
        "v1_6_candidates_without_walk_forward_folds": sorted(v1_6_candidate_ids.difference(evidence_candidate_ids)),
        "walk_forward_candidates_without_v1_6_review_rows": sorted(evidence_candidate_ids.difference(v1_6_candidate_ids)),
        "v1_6_readiness_verdict": readiness_packet.get("readiness_verdict", "missing_v1_6_readiness_packet"),
        "missing_or_blocked_elements": sorted(set(str(item) for item in missing_elements if item)),
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
    }


def _ticker_from_review_rows(*rows: dict[str, Any]) -> str:
    for row in rows:
        value = _text(row.get("ticker"))
        if value:
            return value
    return ""


def _ordered_row(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column, "") for column in OUTPUT_COLUMNS}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return ""


def _join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, tuple):
        return ";".join(str(item) for item in value)
    return str(value)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-root",
        action="append",
        dest="evidence_roots",
        default=None,
        help="EvaluationEvidence root directory. May be supplied multiple times.",
    )
    parser.add_argument("--v1-6-review-dir", default=str(DEFAULT_V1_6_REVIEW_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    evidence_roots = tuple(args.evidence_roots or [str(DEFAULT_EVIDENCE_ROOT)])
    manifest = build_v1_6_walk_forward_backtest_dataset(
        evidence_roots=evidence_roots,
        v1_6_review_dir=args.v1_6_review_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
