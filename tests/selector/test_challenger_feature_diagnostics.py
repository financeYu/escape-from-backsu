from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_challenger_feature_diagnostics import (  # noqa: E402
    evaluate_challenger_features,
    load_feature_candidates,
    load_rows,
)


FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "challenger_feature_diagnostics"


def _report(
    *,
    rows: list[dict] | None = None,
    candidates: list[dict] | None = None,
) -> dict:
    return evaluate_challenger_features(
        rows if rows is not None else load_rows(FIXTURE_DIR / "feature_rows.jsonl"),
        candidates if candidates is not None else load_feature_candidates(FIXTURE_DIR / "feature_candidates.json"),
        baseline_score_column="selector_score",
        challenger_score_column="challenger_diagnostic_score",
        label_column="target_label",
        label_asof_column="label_asof_date",
        split_column="split_id",
        random_seed=24,
    )


def _candidate(report: dict, feature_name: str) -> dict:
    return next(
        candidate
        for candidate in report["feature_candidates"]
        if candidate["feature_name"] == feature_name
    )


def test_feature_candidate_classification_excludes_high_risk_and_forbidden_sources() -> None:
    report = _report()

    coverage = _candidate(report, "coverage_ratio")
    target = _candidate(report, "target_label")
    future = _candidate(report, "future_return")
    composite = _candidate(report, "final_composite_score")

    assert coverage["classification"] == "SAFE_DIAGNOSTIC"
    assert coverage["diagnostic_inclusion_status"] == "included"
    assert target["classification"] == "HIGH_LEAKAGE_RISK"
    assert target["diagnostic_inclusion_status"] == "excluded"
    assert target["feature_label_separation_violation_count"] > 0
    assert future["classification"] == "FORBIDDEN"
    assert future["diagnostic_inclusion_status"] == "excluded"
    assert composite["classification"] == "FORBIDDEN"
    assert composite["diagnostic_inclusion_status"] == "excluded"


def test_no_lookahead_violations_are_counted_and_missing_asof_is_not_silent_pass() -> None:
    rows = load_rows(FIXTURE_DIR / "feature_rows.jsonl")
    candidates = [
        {
            "feature_name": "coverage_ratio",
            "feature_group": "coverage_readiness_missingness",
            "source_artifact": "fixture_feature_rows",
            "source_layer": "fixture",
            "asof_column": "future_asof_date",
            "required_input_columns": ["coverage_ratio", "future_asof_date"],
            "allowed_for_diagnostic_only": True,
            "leakage_risk_level": "SAFE_DIAGNOSTIC",
        },
        {
            "feature_name": "valid_observation_count",
            "feature_group": "coverage_readiness_missingness",
            "source_artifact": "fixture_feature_rows",
            "source_layer": "fixture",
            "asof_column": None,
            "required_input_columns": ["valid_observation_count"],
            "allowed_for_diagnostic_only": True,
            "leakage_risk_level": "SAFE_DIAGNOSTIC",
        },
    ]

    report = _report(rows=rows, candidates=candidates)
    lookahead = _candidate(report, "coverage_ratio")
    missing_asof = _candidate(report, "valid_observation_count")

    assert lookahead["no_lookahead_violation_count"] == 1
    assert lookahead["no_lookahead_status"] == "blocked_lookahead_violation"
    assert lookahead["diagnostic_inclusion_status"] == "excluded"
    assert missing_asof["no_lookahead_status"] == "unknown_missing_asof_metadata"
    assert missing_asof["diagnostic_inclusion_status"] == "excluded"


def test_feature_quality_metrics_cover_missing_constant_null_and_low_cardinality() -> None:
    report = _report()
    metrics = report["feature_quality_metrics"]

    coverage = metrics["coverage_ratio"]
    assert coverage["coverage_ratio"] == 0.833333
    assert coverage["missing_share"] == 0.166667
    assert coverage["valid_n"] == 5
    assert coverage["n_unique"] == 5
    assert coverage["entropy"] == 1.609438
    assert coverage["per_split_valid_n"] == {"test": 3, "train": 2}

    constant = metrics["constant_feature"]
    assert constant["constant_feature"] is True
    assert constant["zero_or_constant_share"] == 1.0
    assert constant["std"] == 0.0
    assert constant["iqr"] == 0.0

    all_null = metrics["all_null_feature"]
    assert all_null["all_null_feature"] is True
    assert all_null["missing_share"] == 1.0
    assert all_null["valid_n"] == 0

    low_cardinality = metrics["low_cardinality_feature"]
    assert low_cardinality["low_cardinality_feature"] is True
    assert low_cardinality["n_unique"] == 2


def test_score_diversity_comparison_does_not_change_existing_scores() -> None:
    rows = load_rows(FIXTURE_DIR / "feature_rows.jsonl")
    before = deepcopy(rows)

    report = _report(rows=rows)
    diversity = report["score_diversity_comparison"]

    assert rows == before
    assert diversity["baseline_n_unique_scores"] == 3
    assert diversity["baseline_top_tie_group_size"] == 2
    assert diversity["baseline_score_entropy"] == 1.098612
    assert diversity["challenger_n_unique_scores"] == 6
    assert diversity["challenger_top_tie_group_size"] == 1
    assert diversity["tie_group_reduction"] == 1
    assert diversity["effective_score_bins"] == 3.0
    assert report["selector_score_update_enabled"] is False
    assert report["confidence_score_update_enabled"] is False
    assert report["production_ranking_update_enabled"] is False
    assert report["final_composite_score_update_enabled"] is False
    assert report["technical_composite_score_update_enabled"] is False


def test_stability_and_shuffle_sanity_are_deterministic() -> None:
    first = _report()
    second = _report()

    assert json.dumps(first["stability_sanity_metrics"], sort_keys=True) == json.dumps(
        second["stability_sanity_metrics"],
        sort_keys=True,
    )
    sanity = first["stability_sanity_metrics"]["sanity_status_by_feature_group"]
    per_feature = first["stability_sanity_metrics"]["per_feature"]

    assert per_feature["strong_feature"]["feature_label_metric"] > 0.9
    assert sanity["split_stability_diagnostic"] == "diagnostic_signal_above_shuffle"
    assert per_feature["constant_feature"]["feature_label_metric"] == 0.0
    assert sanity["noninformative_control"] == "noise_like_or_unreliable"
