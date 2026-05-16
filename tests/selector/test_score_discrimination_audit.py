from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_review_priority_score_discrimination import (  # noqa: E402
    audit_score_discrimination,
    load_score_rows,
)


FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "score_discrimination"


def test_all_zero_score_reports_full_tie_share() -> None:
    rows = load_score_rows(FIXTURE_DIR / "all_zero_selector_scores.jsonl")

    report = audit_score_discrimination(rows, score_column="selector_score")

    assert report["record_count"] == 3
    assert report["max_tie_group_size"] == 3
    assert report["max_tie_group_share"] == 1.0
    assert report["zero_score_share"] == 1.0


def test_binary_score_reports_two_unique_scores() -> None:
    rows = load_score_rows(FIXTURE_DIR / "binary_selector_scores.jsonl")

    report = audit_score_discrimination(rows, score_column="selector_score")

    assert report["n_unique_scores"] == 2
    assert "binary_probability_output" in report["root_cause_candidates"]


def test_component_missing_share_records_root_cause_candidate() -> None:
    rows = load_score_rows(FIXTURE_DIR / "component_missing_scores.jsonl")

    report = audit_score_discrimination(
        rows,
        score_column="selector_score",
        component_columns=["coverage", "stability"],
    )

    assert report["component_missing_share"] == {"coverage": 0.666667, "stability": 1.0}
    assert "missing_components_collapsed_to_zero" in report["root_cause_candidates"]


def test_null_score_and_zero_score_are_separate() -> None:
    rows = load_score_rows(FIXTURE_DIR / "null_vs_zero_scores.jsonl")

    report = audit_score_discrimination(rows, score_column="selector_score")

    assert report["zero_score_share"] == 0.25
    assert report["null_score_share"] == 0.5
    tie_values = {group["score_value"] for group in report["top_tie_groups"]}
    assert None in tie_values
    assert "0" in tie_values


def test_audit_output_is_deterministic() -> None:
    rows = load_score_rows(FIXTURE_DIR / "deterministic_scores.jsonl")

    first = audit_score_discrimination(
        rows,
        score_column="selector_score",
        component_columns=["coverage"],
        deterministic_sort_fields=["candidate_id"],
    )
    second = audit_score_discrimination(
        rows,
        score_column="selector_score",
        component_columns=["coverage"],
        deterministic_sort_fields=["candidate_id"],
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["deterministic_sort_fields"] == ["candidate_id"]
    assert first["production_ranking_update_enabled"] is False
    assert first["valuation_fundamental_active_scoring_enabled"] is False


def test_manifest_score_rows_path_loading() -> None:
    rows = load_score_rows(FIXTURE_DIR / "manifest_score_rows_path.json")
    report = audit_score_discrimination(rows)

    assert [row["candidate_id"] for row in rows] == ["A", "B"]
    assert report["score_column"] == "selector_score"
    assert report["n_unique_scores"] == 2
