"""Audit selector or review-priority score discrimination.

This script reads an existing selector score manifest, JSONL score rows, or
CSV review-priority output and emits manual-review diagnostic metrics only. It
does not change scoring semantics, production ranking, composite scores, or
runtime behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import pvariance
from typing import Any


AUDIT_VERSION = "review_priority_score_discrimination_audit_v1_0"
MANUAL_REVIEW_NOTICE = (
    "score discrimination audit is manual-review evidence support only; it "
    "does not change production ranking, final_composite_score, or "
    "technical_composite_score"
)
DEFAULT_SCORE_COLUMNS = (
    "review_priority_score",
    "selector_score",
    "confidence_score",
    "manual_review_priority_score",
    "diagnostic_tiebreak_score",
)
DEFAULT_STATUS_COLUMNS = (
    "score_status",
    "status",
    "review_priority_bucket",
    "manual_review_priority",
    "confidence_support_status",
    "trainability_status",
)
DEFAULT_SORT_FIELDS = (
    "review_priority_rank",
    "manual_review_priority",
    "review_priority_bucket",
    "candidate_id",
    "evidence_id",
)
IDENTITY_OR_TEXT_FIELDS = {
    "allowed_use",
    "candidate_id",
    "created_at",
    "evaluation_date",
    "evidence_id",
    "evidence_only_notice",
    "lineage_ref",
    "lineage_refs",
    "manual_review_only_notice",
    "priority_version",
    "reason_codes",
    "schema_version",
    "selector_model_version",
    "selector_score_source",
    "source_artifact",
    "source_artifact_refs",
    "ticker",
    "trade_signal_claim",
}
FORBIDDEN_REPORT_TERMS = (
    "buy",
    "sell",
    "hold",
    "expected_return",
    "future_return",
    "proven_alpha",
    "trade_signal",
    "order_instruction",
)


def audit_score_discrimination(
    rows: list[dict[str, Any]],
    *,
    score_column: str | None = None,
    status_column: str | None = None,
    component_columns: list[str] | None = None,
    deterministic_sort_fields: list[str] | None = None,
    top_group_limit: int = 10,
) -> dict[str, Any]:
    """Return deterministic score discrimination diagnostics for score rows."""

    normalized_rows = [_normalize_row(row) for row in rows]
    record_count = len(normalized_rows)
    chosen_score = score_column or _detect_column(normalized_rows, DEFAULT_SCORE_COLUMNS)
    if not chosen_score:
        raise ValueError("could not detect a score column; pass --score-column")
    chosen_status = status_column or _detect_column(normalized_rows, DEFAULT_STATUS_COLUMNS)
    components = component_columns if component_columns is not None else _detect_component_columns(
        normalized_rows,
        chosen_score,
    )
    sort_fields = deterministic_sort_fields if deterministic_sort_fields is not None else [
        field for field in DEFAULT_SORT_FIELDS if any(field in row for row in normalized_rows)
    ]

    numeric_scores = [_to_float(row.get(chosen_score)) for row in normalized_rows]
    score_keys = [_score_key(value) for value in numeric_scores]
    score_counts = Counter(score_keys)
    non_null_scores = [value for value in numeric_scores if value is not None]
    unique_scores = sorted(set(non_null_scores))
    entropy = _entropy(Counter(_score_key(value) for value in non_null_scores))
    max_tie_size = max(score_counts.values(), default=0)
    zero_count = sum(1 for value in numeric_scores if value == 0.0)
    null_count = sum(1 for value in numeric_scores if value is None)

    component_missing = {
        component: _component_missing_share(normalized_rows, component)
        for component in components
    }
    component_variance = {
        component: _component_variance(normalized_rows, component)
        for component in components
    }
    root_causes = _root_cause_candidates(
        record_count=record_count,
        n_unique_scores=len(unique_scores),
        unique_scores=unique_scores,
        zero_score_share=_share(zero_count, record_count),
        max_tie_group_share=_share(max_tie_size, record_count),
        component_missing_share=component_missing,
        component_variance=component_variance,
        status_bucket_counts=_status_counts(normalized_rows, chosen_status),
        deterministic_sort_fields=sort_fields,
    )

    report = {
        "audit_version": AUDIT_VERSION,
        "manual_review_only": True,
        "manual_review_only_notice": MANUAL_REVIEW_NOTICE,
        "record_count": record_count,
        "score_column": chosen_score,
        "n_unique_scores": len(unique_scores),
        "effective_unique_score_count": round(math.exp(entropy), 6) if non_null_scores else 0.0,
        "max_tie_group_size": max_tie_size,
        "max_tie_group_share": _share(max_tie_size, record_count),
        "zero_score_share": _share(zero_count, record_count),
        "null_score_share": _share(null_count, record_count),
        "status_column": chosen_status,
        "status_bucket_counts": _status_counts(normalized_rows, chosen_status),
        "score_entropy": round(entropy, 6),
        "component_columns": components,
        "component_missing_share": component_missing,
        "component_variance": component_variance,
        "top_tie_groups": _top_tie_groups(
            normalized_rows,
            score_keys,
            score_counts,
            record_count,
            limit=top_group_limit,
        ),
        "deterministic_sort_fields": sort_fields,
        "root_cause_candidates": root_causes,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }
    _reject_forbidden_report_terms(report)
    return report


def load_score_rows(path: str | Path) -> list[dict[str, Any]]:
    """Load rows from JSONL, CSV, JSON row lists, or supported manifests."""

    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if not isinstance(payload, dict):
            raise ValueError("JSON audit input must be an object or list")
        for key in ("candidate_review_priorities", "rows", "score_rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value]
        score_rows_path = payload.get("score_rows_path")
        if isinstance(score_rows_path, str) and score_rows_path.strip():
            nested = Path(score_rows_path)
            if not nested.is_absolute():
                nested = source.parent / nested
                if not nested.exists():
                    nested = Path.cwd() / score_rows_path
            return load_score_rows(nested)
    raise ValueError(f"unsupported audit input format: {source}")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items()}


def _detect_column(rows: list[dict[str, Any]], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if any(candidate in row for row in rows):
            return candidate
    return None


def _detect_component_columns(rows: list[dict[str, Any]], score_column: str) -> list[str]:
    columns = sorted({column for row in rows for column in row})
    detected = []
    for column in columns:
        if column == score_column or column in IDENTITY_OR_TEXT_FIELDS:
            continue
        if column.endswith("_rank") or column.endswith("_id") or column.endswith("_ref"):
            continue
        values = [row.get(column) for row in rows if column in row]
        if any(_to_float(value) is not None for value in values):
            detected.append(column)
    return detected


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _score_key(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.12g}"


def _share(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log(probability)
    return entropy


def _status_counts(rows: list[dict[str, Any]], status_column: str | None) -> dict[str, int]:
    if not status_column:
        return {}
    counts = Counter(str(row.get(status_column) or "missing") for row in rows)
    return dict(sorted(counts.items()))


def _component_missing_share(rows: list[dict[str, Any]], component: str) -> float:
    missing = sum(1 for row in rows if _to_float(row.get(component)) is None)
    return _share(missing, len(rows))


def _component_variance(rows: list[dict[str, Any]], component: str) -> float | None:
    values = [_to_float(row.get(component)) for row in rows]
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(pvariance(numeric), 12)


def _top_tie_groups(
    rows: list[dict[str, Any]],
    score_keys: list[str],
    score_counts: Counter[str],
    record_count: int,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    by_score: dict[str, list[dict[str, Any]]] = {}
    for row, key in zip(rows, score_keys):
        by_score.setdefault(key, []).append(row)
    output = []
    for key, count in sorted(score_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        candidate_ids = sorted(str(row.get("candidate_id") or "") for row in by_score[key])
        output.append(
            {
                "score_value": None if key == "null" else key,
                "group_size": count,
                "group_share": _share(count, record_count),
                "candidate_ids_sample": candidate_ids[:10],
            }
        )
    return output


def _root_cause_candidates(
    *,
    record_count: int,
    n_unique_scores: int,
    unique_scores: list[float],
    zero_score_share: float,
    max_tie_group_share: float,
    component_missing_share: dict[str, float],
    component_variance: dict[str, float | None],
    status_bucket_counts: dict[str, int],
    deterministic_sort_fields: list[str],
) -> list[str]:
    candidates: set[str] = set()
    if record_count == 0:
        return ["label_or_feature_matrix_too_sparse"]
    if zero_score_share >= 0.80 and any(value >= 0.50 for value in component_missing_share.values()):
        candidates.add("missing_components_collapsed_to_zero")
    if n_unique_scores <= 2 and set(unique_scores).issubset({0.0, 1.0}):
        candidates.add("binary_probability_output")
    if component_variance and all((value is None or value == 0.0) for value in component_variance.values()):
        candidates.add("insufficient_feature_variance")
    if max_tie_group_share >= 0.50 and deterministic_sort_fields:
        candidates.add("deterministic_string_tiebreak_only")
    if status_bucket_counts:
        largest_status_share = max(status_bucket_counts.values()) / record_count
        if largest_status_share >= 0.80:
            candidates.add("status_bucket_too_coarse")
    if record_count < 3 or not component_variance:
        candidates.add("label_or_feature_matrix_too_sparse")
    return sorted(candidates)


def _reject_forbidden_report_terms(report: dict[str, Any]) -> None:
    allowed_fields = {"manual_review_only_notice"}
    text = json.dumps(
        {key: value for key, value in report.items() if key not in allowed_fields},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for term in FORBIDDEN_REPORT_TERMS:
        if term in text:
            raise ValueError(f"audit report contains forbidden term outside notices: {term}")


def _split_csv_arg(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit manual-review selector score discrimination.",
    )
    parser.add_argument("--input", required=True, help="JSON, JSONL, or CSV score rows/manifest")
    parser.add_argument("--output", required=True, help="Output diagnostic JSON path")
    parser.add_argument("--score-column", default=None, help="Score column to audit")
    parser.add_argument("--status-column", default=None, help="Optional status bucket column")
    parser.add_argument(
        "--component-columns",
        default=None,
        help="Comma-separated component columns for missing/variance diagnostics",
    )
    parser.add_argument(
        "--sort-fields",
        default=None,
        help="Comma-separated deterministic sort fields currently used",
    )
    args = parser.parse_args(argv)
    rows = load_score_rows(args.input)
    report = audit_score_discrimination(
        rows,
        score_column=args.score_column,
        status_column=args.status_column,
        component_columns=_split_csv_arg(args.component_columns),
        deterministic_sort_fields=_split_csv_arg(args.sort_fields),
    )
    write_json(args.output, report)
    print(json.dumps({"output": args.output, "record_count": report["record_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
