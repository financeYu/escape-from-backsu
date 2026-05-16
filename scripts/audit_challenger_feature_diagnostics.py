"""Evaluate diagnostic-only challenger feature candidates.

The evaluator is intentionally separate from selector and confidence scoring
paths. It reads caller-provided rows and candidate metadata, then returns
manual-review diagnostics for coverage, variance, leakage risk, as-of checks,
score diversity, and simple sanity baselines.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


CHALLENGER_DIAGNOSTIC_VERSION = "challenger_feature_diagnostics_v1_0"
MANUAL_REVIEW_NOTICE = (
    "challenger feature diagnostics are manual-review evidence support only; "
    "they do not update selector_score, confidence_score, production ranking, "
    "final_composite_score, or technical_composite_score"
)
SAFE_RISK_LEVELS = {
    "SAFE_DIAGNOSTIC",
    "NEEDS_ASOF_CHECK",
    "NEEDS_LINEAGE_CHECK",
}
EXCLUDED_RISK_LEVELS = {
    "HIGH_LEAKAGE_RISK",
    "FORBIDDEN",
}
FORBIDDEN_NAME_TOKENS = (
    "future",
    "forward",
    "realized",
    "return_after",
    "label_outcome",
    "target_value",
    "production_rank",
    "rank",
    "final_composite_score",
    "technical_composite_score",
    "selector_score",
    "confidence_score",
    "adoption_outcome",
    "manual_review_outcome",
    "post_label",
    "backtest",
)
TARGET_OR_LABEL_TOKENS = (
    "label",
    "target",
)
DEFAULT_SCORE_COLUMNS = (
    "selector_score",
    "confidence_score",
    "review_priority_score",
    "manual_review_priority_score",
)


def evaluate_challenger_features(
    rows: list[dict[str, Any]],
    feature_candidates: list[dict[str, Any]],
    *,
    baseline_score_column: str | None = None,
    challenger_score_column: str | None = None,
    label_column: str | None = None,
    label_asof_column: str | None = None,
    split_column: str | None = None,
    random_seed: int = 17,
) -> dict[str, Any]:
    """Return deterministic diagnostics for challenger feature candidates."""

    source_rows = deepcopy(rows)
    normalized_rows = [_normalize_row(row) for row in rows]
    candidates = [_normalize_candidate(candidate) for candidate in feature_candidates]

    feature_reports = [
        _evaluate_candidate(
            normalized_rows,
            candidate,
            label_asof_column=label_asof_column,
            split_column=split_column,
        )
        for candidate in candidates
    ]
    included_reports = [
        report
        for report in feature_reports
        if report["diagnostic_inclusion_status"] == "included"
    ]

    metrics_by_feature = {
        report["feature_name"]: report["quality_metrics"]
        for report in feature_reports
    }
    stability = _stability_and_sanity_metrics(
        normalized_rows,
        included_reports,
        label_column=label_column,
        split_column=split_column,
        random_seed=random_seed,
    )
    score_diversity = _score_diversity_comparison(
        normalized_rows,
        baseline_score_column=baseline_score_column,
        challenger_score_column=challenger_score_column,
    )

    report = {
        "schema_version": CHALLENGER_DIAGNOSTIC_VERSION,
        "manual_review_only": True,
        "manual_review_only_notice": MANUAL_REVIEW_NOTICE,
        "record_count": len(normalized_rows),
        "feature_candidate_count": len(candidates),
        "included_feature_count": len(included_reports),
        "excluded_feature_count": len(feature_reports) - len(included_reports),
        "feature_candidates": feature_reports,
        "feature_quality_metrics": metrics_by_feature,
        "score_diversity_comparison": score_diversity,
        "stability_sanity_metrics": stability,
        "diagnostic_output_only": True,
        "production_ranking_update_enabled": False,
        "selector_score_update_enabled": False,
        "confidence_score_update_enabled": False,
        "final_composite_score_update_enabled": False,
        "technical_composite_score_update_enabled": False,
    }
    if source_rows != rows:
        raise AssertionError("challenger diagnostics mutated input rows")
    return report


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if isinstance(payload, dict):
            for key in ("rows", "feature_rows", "score_rows"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [dict(item) for item in value]
        raise ValueError("JSON input must contain a row list")
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError(f"unsupported row input format: {source}")


def load_feature_candidates(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("feature_candidates"), list):
        return [dict(item) for item in payload["feature_candidates"]]
    raise ValueError("candidate manifest must be a list or contain feature_candidates")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items()}


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    required_defaults = {
        "feature_name": "",
        "feature_group": "unknown",
        "source_artifact": "unknown",
        "source_layer": "unknown",
        "asof_column": None,
        "required_input_columns": [],
        "allowed_for_diagnostic_only": False,
        "leakage_risk_level": "FORBIDDEN",
        "exclusion_reason": None,
    }
    normalized = required_defaults | {str(key): value for key, value in candidate.items()}
    if isinstance(normalized["required_input_columns"], str):
        normalized["required_input_columns"] = [
            item.strip()
            for item in normalized["required_input_columns"].split(",")
            if item.strip()
        ]
    return normalized


def _evaluate_candidate(
    rows: list[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    label_asof_column: str | None,
    split_column: str | None,
) -> dict[str, Any]:
    feature_name = str(candidate["feature_name"])
    quality = _feature_quality_metrics(rows, feature_name, split_column=split_column)
    classification = _classify_candidate(candidate)
    no_lookahead = _no_lookahead_diagnostics(
        rows,
        feature_asof_column=candidate.get("asof_column"),
        label_asof_column=label_asof_column,
    )
    separation_violations = _feature_label_separation_violation_count(candidate)
    missing_required = [
        column
        for column in candidate.get("required_input_columns", [])
        if not any(column in row for row in rows)
    ]
    inclusion_status, inclusion_reason = _inclusion_status(
        classification=classification,
        candidate=candidate,
        missing_required_columns=missing_required,
        no_lookahead=no_lookahead,
        separation_violations=separation_violations,
    )

    metadata = {
        key: candidate.get(key)
        for key in (
            "feature_name",
            "feature_group",
            "source_artifact",
            "source_layer",
            "asof_column",
            "required_input_columns",
            "allowed_for_diagnostic_only",
            "leakage_risk_level",
            "exclusion_reason",
        )
    }
    return {
        **metadata,
        "classification": classification,
        "diagnostic_inclusion_status": inclusion_status,
        "diagnostic_inclusion_reason": inclusion_reason,
        "missing_required_input_columns": missing_required,
        "no_lookahead_violation_count": no_lookahead["violation_count"],
        "no_lookahead_status": no_lookahead["status"],
        "feature_label_separation_violation_count": separation_violations,
        "quality_metrics": quality,
    }


def _classify_candidate(candidate: dict[str, Any]) -> str:
    feature_name = str(candidate.get("feature_name") or "").lower()
    risk_level = str(candidate.get("leakage_risk_level") or "").upper()
    if risk_level in EXCLUDED_RISK_LEVELS:
        return risk_level
    if _matches_any_token(feature_name, FORBIDDEN_NAME_TOKENS):
        return "FORBIDDEN"
    if _matches_any_token(feature_name, TARGET_OR_LABEL_TOKENS):
        return "HIGH_LEAKAGE_RISK"
    for column in candidate.get("required_input_columns", []):
        lowered = str(column).lower()
        if _matches_any_token(lowered, FORBIDDEN_NAME_TOKENS):
            return "FORBIDDEN"
        if _matches_any_token(lowered, TARGET_OR_LABEL_TOKENS):
            return "HIGH_LEAKAGE_RISK"
    if risk_level in SAFE_RISK_LEVELS:
        return risk_level
    return "FORBIDDEN"


def _matches_any_token(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in tokens)


def _inclusion_status(
    *,
    classification: str,
    candidate: dict[str, Any],
    missing_required_columns: list[str],
    no_lookahead: dict[str, Any],
    separation_violations: int,
) -> tuple[str, str]:
    if not candidate.get("allowed_for_diagnostic_only"):
        return "excluded", "not_allowed_for_diagnostic_only"
    if classification in EXCLUDED_RISK_LEVELS:
        return "excluded", f"leakage_risk_level:{classification}"
    if missing_required_columns:
        return "excluded", "missing_required_input_columns"
    if separation_violations:
        return "excluded", "feature_label_separation_violation"
    if no_lookahead["status"] in {"blocked_lookahead_violation", "unknown_missing_asof_metadata"}:
        return "excluded", no_lookahead["status"]
    return "included", "passed_diagnostic_candidate_checks"


def _feature_quality_metrics(
    rows: list[dict[str, Any]],
    feature_name: str,
    *,
    split_column: str | None,
) -> dict[str, Any]:
    values = [row.get(feature_name) for row in rows]
    non_missing = [value for value in values if not _is_missing(value)]
    numeric = [_to_float(value) for value in non_missing]
    numeric_values = [value for value in numeric if value is not None]
    value_keys = [_value_key(value) for value in non_missing]
    counts = Counter(value_keys)
    n_unique = len(counts)
    max_group_share = _share(max(counts.values(), default=0), len(non_missing))
    zero_share = _share(sum(1 for value in numeric_values if value == 0.0), len(numeric_values))

    return {
        "coverage_ratio": _share(len(non_missing), len(rows)),
        "missing_share": _share(len(rows) - len(non_missing), len(rows)),
        "valid_n": len(non_missing),
        "numeric_valid_n": len(numeric_values),
        "n_unique": n_unique,
        "entropy": round(_entropy(counts), 6),
        "std": _rounded(pstdev(numeric_values)) if len(numeric_values) >= 2 else 0.0 if len(numeric_values) == 1 else None,
        "iqr": _iqr(numeric_values),
        "zero_or_constant_share": round(max(zero_share, max_group_share), 6),
        "all_null_feature": len(non_missing) == 0,
        "constant_feature": len(non_missing) > 0 and n_unique <= 1,
        "low_cardinality_feature": 0 < n_unique <= 2,
        "per_split_valid_n": _per_split_valid_n(rows, feature_name, split_column),
    }


def _per_split_valid_n(
    rows: list[dict[str, Any]],
    feature_name: str,
    split_column: str | None,
) -> dict[str, int] | None:
    if not split_column or not any(split_column in row for row in rows):
        return None
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        split = str(row.get(split_column) or "missing")
        if not _is_missing(row.get(feature_name)):
            counts[split] += 1
    return dict(sorted(counts.items()))


def _no_lookahead_diagnostics(
    rows: list[dict[str, Any]],
    *,
    feature_asof_column: Any,
    label_asof_column: str | None,
) -> dict[str, Any]:
    if not feature_asof_column or not label_asof_column:
        return {
            "status": "unknown_missing_asof_metadata",
            "violation_count": 0,
            "checked_row_count": 0,
            "unknown_row_count": len(rows),
        }
    feature_column = str(feature_asof_column)
    violation_count = 0
    checked_count = 0
    unknown_count = 0
    for row in rows:
        feature_date = _parse_date(row.get(feature_column))
        label_date = _parse_date(row.get(label_asof_column))
        if feature_date is None or label_date is None:
            unknown_count += 1
            continue
        checked_count += 1
        if feature_date > label_date:
            violation_count += 1
    if violation_count:
        status = "blocked_lookahead_violation"
    elif unknown_count:
        status = "unknown_partial_asof_metadata"
    else:
        status = "pass"
    return {
        "status": status,
        "violation_count": violation_count,
        "checked_row_count": checked_count,
        "unknown_row_count": unknown_count,
    }


def _feature_label_separation_violation_count(candidate: dict[str, Any]) -> int:
    feature_name = str(candidate.get("feature_name") or "").lower()
    columns = [feature_name] + [
        str(column).lower()
        for column in candidate.get("required_input_columns", [])
    ]
    return sum(1 for column in columns if _matches_any_token(column, TARGET_OR_LABEL_TOKENS))


def _score_diversity_comparison(
    rows: list[dict[str, Any]],
    *,
    baseline_score_column: str | None,
    challenger_score_column: str | None,
) -> dict[str, Any]:
    baseline_column = baseline_score_column or _detect_score_column(rows)
    baseline = _score_diversity_metrics(rows, baseline_column)
    challenger = _score_diversity_metrics(rows, challenger_score_column)
    tie_reduction = None
    if baseline["top_tie_group_size"] is not None and challenger["top_tie_group_size"] is not None:
        tie_reduction = baseline["top_tie_group_size"] - challenger["top_tie_group_size"]
    return {
        "baseline_score_column": baseline_column,
        "baseline_score_entropy": baseline["score_entropy"],
        "baseline_n_unique_scores": baseline["n_unique_scores"],
        "baseline_top_tie_group_size": baseline["top_tie_group_size"],
        "challenger_score_column": challenger_score_column,
        "challenger_score_entropy": challenger["score_entropy"],
        "challenger_n_unique_scores": challenger["n_unique_scores"],
        "challenger_top_tie_group_size": challenger["top_tie_group_size"],
        "tie_group_reduction": tie_reduction,
        "effective_score_bins": baseline["effective_score_bins"],
        "challenger_effective_score_bins": challenger["effective_score_bins"],
    }


def _detect_score_column(rows: list[dict[str, Any]]) -> str | None:
    for column in DEFAULT_SCORE_COLUMNS:
        if any(column in row for row in rows):
            return column
    return None


def _score_diversity_metrics(rows: list[dict[str, Any]], score_column: str | None) -> dict[str, Any]:
    if not score_column:
        return {
            "score_entropy": None,
            "n_unique_scores": None,
            "top_tie_group_size": None,
            "effective_score_bins": None,
        }
    scores = [_to_float(row.get(score_column)) for row in rows]
    non_null = [score for score in scores if score is not None]
    counts = Counter(_value_key(score) for score in non_null)
    entropy = _entropy(counts)
    return {
        "score_entropy": round(entropy, 6),
        "n_unique_scores": len(counts),
        "top_tie_group_size": max(counts.values(), default=0),
        "effective_score_bins": round(math.exp(entropy), 6) if non_null else 0.0,
    }


def _stability_and_sanity_metrics(
    rows: list[dict[str, Any]],
    included_reports: list[dict[str, Any]],
    *,
    label_column: str | None,
    split_column: str | None,
    random_seed: int,
) -> dict[str, Any]:
    labels = [_to_float(row.get(label_column)) for row in rows] if label_column else []
    group_metrics: dict[str, list[float]] = defaultdict(list)
    group_shuffled_label: dict[str, list[float]] = defaultdict(list)
    group_shuffled_feature: dict[str, list[float]] = defaultdict(list)
    per_feature: dict[str, dict[str, Any]] = {}

    for index, report in enumerate(included_reports):
        feature_name = report["feature_name"]
        group = report["feature_group"]
        values = [_to_float(row.get(feature_name)) for row in rows]
        metric = _association_metric(values, labels)
        shuffled_label_metric = _association_metric(
            values,
            _deterministic_shuffle(labels, random_seed + index),
        )
        shuffled_feature_metric = _association_metric(
            _deterministic_shuffle(values, random_seed + 1000 + index),
            labels,
        )
        split_means = _per_split_means(rows, feature_name, split_column)
        per_feature[feature_name] = {
            "feature_group": group,
            "per_split_metric_mean": _rounded(mean(split_means.values())) if split_means else None,
            "per_split_metric_std": _rounded(pstdev(split_means.values())) if len(split_means) >= 2 else 0.0 if split_means else None,
            "per_split_sign_consistency": _sign_consistency(split_means.values()) if split_means else None,
            "feature_label_metric": metric,
            "shuffled_label_metric": shuffled_label_metric,
            "shuffled_feature_metric": shuffled_feature_metric,
        }
        if metric is not None:
            group_metrics[group].append(metric)
        if shuffled_label_metric is not None:
            group_shuffled_label[group].append(shuffled_label_metric)
        if shuffled_feature_metric is not None:
            group_shuffled_feature[group].append(shuffled_feature_metric)

    ablation_delta = {}
    sanity_status = {}
    group_metric_summary = {group: _rounded(mean(values)) for group, values in group_metrics.items() if values}
    for group, group_metric in sorted(group_metric_summary.items()):
        other_metrics = [
            metric
            for other_group, metric in group_metric_summary.items()
            if other_group != group
        ]
        baseline_without_group = mean(other_metrics) if other_metrics else 0.0
        ablation_delta[group] = _rounded(group_metric - baseline_without_group)
        shuffle_floor = max(
            mean(group_shuffled_label[group]) if group_shuffled_label[group] else 0.0,
            mean(group_shuffled_feature[group]) if group_shuffled_feature[group] else 0.0,
        )
        sanity_status[group] = (
            "diagnostic_signal_above_shuffle"
            if group_metric > shuffle_floor + 1e-12
            else "noise_like_or_unreliable"
        )

    return {
        "label_column": label_column,
        "split_column": split_column,
        "per_feature": per_feature,
        "group_metric_mean": group_metric_summary,
        "ablation_delta_by_feature_group": ablation_delta,
        "shuffled_label_metric": {
            group: _rounded(mean(values))
            for group, values in sorted(group_shuffled_label.items())
            if values
        },
        "shuffled_feature_metric": {
            group: _rounded(mean(values))
            for group, values in sorted(group_shuffled_feature.items())
            if values
        },
        "sanity_status_by_feature_group": sanity_status,
    }


def _per_split_means(
    rows: list[dict[str, Any]],
    feature_name: str,
    split_column: str | None,
) -> dict[str, float]:
    if not split_column or not any(split_column in row for row in rows):
        return {}
    by_split: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = _to_float(row.get(feature_name))
        if value is None:
            continue
        by_split[str(row.get(split_column) or "missing")].append(value)
    return {
        split: mean(values)
        for split, values in sorted(by_split.items())
        if values
    }


def _association_metric(values: list[float | None], labels: list[float | None]) -> float | None:
    pairs = [
        (value, label)
        for value, label in zip(values, labels)
        if value is not None and label is not None
    ]
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = mean(xs)
    y_mean = mean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_denominator = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    y_denominator = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    denominator = x_denominator * y_denominator
    if denominator == 0.0:
        return 0.0
    return _rounded(abs(numerator / denominator))


def _deterministic_shuffle(values: list[float | None], seed: int) -> list[float | None]:
    shuffled = list(values)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def _sign_consistency(values: Any) -> str:
    signs = {
        1 if value > 0 else -1 if value < 0 else 0
        for value in values
    }
    signs.discard(0)
    if not signs:
        return "all_zero_or_missing"
    return "consistent" if len(signs) == 1 else "mixed"


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _value_key(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is not None:
        return f"{numeric:.12g}"
    return str(value)


def _share(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if not total:
        return 0.0
    result = 0.0
    for count in counts.values():
        probability = count / total
        result -= probability * math.log(probability)
    return result


def _iqr(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    return _rounded(_percentile(sorted_values, 0.75) - _percentile(sorted_values, 0.25))


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate diagnostic-only challenger feature candidates.",
    )
    parser.add_argument("--input", required=True, help="JSON, JSONL, or CSV rows")
    parser.add_argument("--candidates", required=True, help="Feature candidate manifest JSON")
    parser.add_argument("--output", required=True, help="Output diagnostic JSON path")
    parser.add_argument("--baseline-score-column", default=None)
    parser.add_argument("--challenger-score-column", default=None)
    parser.add_argument("--label-column", default=None)
    parser.add_argument("--label-asof-column", default=None)
    parser.add_argument("--split-column", default=None)
    parser.add_argument("--random-seed", type=int, default=17)
    args = parser.parse_args(argv)

    report = evaluate_challenger_features(
        load_rows(args.input),
        load_feature_candidates(args.candidates),
        baseline_score_column=args.baseline_score_column,
        challenger_score_column=args.challenger_score_column,
        label_column=args.label_column,
        label_asof_column=args.label_asof_column,
        split_column=args.split_column,
        random_seed=args.random_seed,
    )
    write_json(args.output, report)
    print(
        json.dumps(
            {
                "output": args.output,
                "record_count": report["record_count"],
                "included_feature_count": report["included_feature_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
