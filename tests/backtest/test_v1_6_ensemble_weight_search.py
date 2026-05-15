from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.ensemble_weight_search_v1_6 import (  # noqa: E402
    EnsembleWeightSearchConfig,
    run_v1_6_ensemble_weight_search,
    validate_v1_6_ensemble_weight_search_artifacts,
)


def _rows() -> list[dict[str, object]]:
    returns = {
        "model_a": [0.02, 0.01, 0.03, 0.01, 0.04, 0.03],
        "model_b": [0.01, 0.02, 0.02, 0.06, 0.05, 0.04],
        "model_c": [-0.01, 0.00, 0.01, 0.00, -0.02, 0.01],
    }
    dates = [
        "2025-01-31",
        "2025-02-28",
        "2025-03-31",
        "2025-04-30",
        "2025-05-31",
        "2025-06-30",
    ]
    splits = ["train", "train", "train", "validation", "validation", "test"]
    rows: list[dict[str, object]] = []
    for index, date in enumerate(dates):
        for model_id, values in returns.items():
            rows.append(
                {
                    "model_id": model_id,
                    "evaluation_date": date,
                    "net_return": values[index],
                    "split": splits[index],
                    "source_ref": "fixture_model_return",
                    "leakage_check_status": "pass",
                    "no_lookahead_check_status": "pass",
                }
            )
    return rows


def test_v1_6_ensemble_weight_search_retains_top_n_by_validation_return() -> None:
    artifacts = run_v1_6_ensemble_weight_search(
        _rows(),
        config=EnsembleWeightSearchConfig(top_n_ensembles=2, weight_step=0.5),
    )

    validate_v1_6_ensemble_weight_search_artifacts(artifacts)
    report = artifacts["v1_6_retained_ensemble_weight_report"]
    retained = report["retained_ensembles"]

    assert report["top_n_ensembles"] == 2
    assert report["retained_ensemble_count"] == 2
    assert retained[0]["weights"]["model_b"] == pytest.approx(1.0)
    assert retained[0]["validation_metrics"]["cumulative_return"] > retained[0]["train_metrics"]["cumulative_return"]
    assert retained[0]["test_split_role"] == "untouched_final_review_only"


def test_v1_6_ensemble_weight_search_records_leakage_separation() -> None:
    artifacts = run_v1_6_ensemble_weight_search(
        _rows(),
        config=EnsembleWeightSearchConfig(top_n_ensembles=3, weight_step=0.5),
    )

    audit = artifacts["v1_6_ensemble_leakage_audit"]
    manifest = artifacts["v1_6_ensemble_weight_search_manifest"]

    assert audit["leakage_audit_status"] == "pass"
    assert audit["predeclared_weight_grid_used"] is True
    assert audit["validation_selects_retained_ensembles"] is True
    assert audit["test_split_not_used_for_weight_selection"] is True
    assert manifest["weight_grid_policy"] == "predeclared_non_negative_sum_to_one_grid"
    assert manifest["selection_split"] == "validation"
    assert manifest["test_split_role"] == "untouched_final_review_only"


def test_v1_6_ensemble_weight_search_supports_chronological_auto_split() -> None:
    rows = [{key: value for key, value in row.items() if key != "split"} for row in _rows()]

    artifacts = run_v1_6_ensemble_weight_search(
        rows,
        config=EnsembleWeightSearchConfig(top_n_ensembles=1, weight_step=1.0),
    )

    manifest = artifacts["v1_6_ensemble_weight_search_manifest"]

    assert manifest["split_counts"] == {"test": 2, "train": 3, "validation": 1}
    assert manifest["retained_ensemble_count"] == 1


def test_v1_6_ensemble_weight_search_rejects_failed_guardrail_status() -> None:
    rows = _rows()
    rows[0]["no_lookahead_check_status"] = "fail"

    with pytest.raises(ValueError, match="no_lookahead_check_status=pass"):
        run_v1_6_ensemble_weight_search(rows)


def test_v1_6_ensemble_weight_search_rejects_forbidden_input_fields() -> None:
    rows = _rows()
    rows[0]["future_return"] = 0.99

    with pytest.raises(ValueError, match="forbidden fields"):
        run_v1_6_ensemble_weight_search(rows)


def test_v1_6_ensemble_weight_search_rejects_mixed_split_policy() -> None:
    rows = _rows()
    del rows[0]["split"]

    with pytest.raises(ValueError, match="all explicit splits or none"):
        run_v1_6_ensemble_weight_search(rows)


def test_v1_6_ensemble_weight_search_rejects_missing_model_date_rows() -> None:
    rows = _rows()
    rows = [row for row in rows if not (row["model_id"] == "model_c" and row["evaluation_date"] == "2025-06-30")]

    with pytest.raises(ValueError, match="missing model rows"):
        run_v1_6_ensemble_weight_search(rows)


def test_v1_6_ensemble_weight_search_artifacts_are_json_serializable() -> None:
    artifacts = run_v1_6_ensemble_weight_search(
        _rows(),
        config=EnsembleWeightSearchConfig(top_n_ensembles=2, weight_step=0.5),
    )

    text = json.dumps(artifacts, sort_keys=True)

    assert "v1_6_ensemble_weight_search_manifest" in text
    assert "brokerage_integration_enabled" in text
