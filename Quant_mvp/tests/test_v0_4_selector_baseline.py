from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "ml" / "train_v0_4_selector_baseline.py"
SCORE_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "ml" / "score_v0_4_selector_candidates.py"

TRAIN_SPEC = importlib.util.spec_from_file_location("train_v0_4_selector_baseline", TRAIN_SCRIPT)
assert TRAIN_SPEC is not None
trainer = importlib.util.module_from_spec(TRAIN_SPEC)
assert TRAIN_SPEC.loader is not None
TRAIN_SPEC.loader.exec_module(trainer)

SCORE_SPEC = importlib.util.spec_from_file_location("score_v0_4_selector_candidates", SCORE_SCRIPT)
assert SCORE_SPEC is not None
scorer = importlib.util.module_from_spec(SCORE_SPEC)
assert SCORE_SPEC.loader is not None
SCORE_SPEC.loader.exec_module(scorer)


FEATURES = [
    "total_return",
    "excess_return_vs_proxy",
    "max_drawdown_abs",
    "sharpe",
    "turnover",
    "volatility",
]


class FakeLogisticRegression:
    classes_ = [0, 1]

    def __init__(self) -> None:
        self.fitted = False

    def fit(self, x_values: list[list[float]], y_values: list[int]) -> "FakeLogisticRegression":
        assert len(x_values) == len(y_values)
        assert {0, 1} <= set(y_values)
        self.fitted = True
        return self

    def predict_proba(self, x_values: list[list[float]]) -> list[list[float]]:
        assert self.fitted
        return [[0.4, 0.6] for _ in x_values]


def make_row(
    candidate_id: str,
    label: int | None,
    *,
    total_return: float = 0.1,
    excess_return_vs_proxy: float = 0.02,
    max_drawdown: float = -0.08,
    sharpe: float = 1.1,
    turnover: float = 0.4,
    volatility: float = 0.2,
    training_eligible: bool = True,
    metric_subject_type: str = "strategy_candidate",
    candidate_metric_match: bool = True,
    extra_feature_values: dict[str, object] | None = None,
) -> dict[str, object]:
    feature_values: dict[str, object] = {
        "total_return": total_return,
        "excess_return_vs_proxy": excess_return_vs_proxy,
        "max_drawdown_abs": abs(max_drawdown),
        "sharpe": sharpe,
        "turnover": turnover,
        "volatility": volatility,
    }
    if extra_feature_values:
        feature_values.update(extra_feature_values)
    return {
        "schema_version": "v0_3_selector_feature_matrix_v1_0",
        "candidate_id": candidate_id,
        "evidence_id": f"ee:{candidate_id}",
        "metric_subject_type": metric_subject_type,
        "metric_subject_id": candidate_id,
        "candidate_metric_match": candidate_metric_match,
        "metric_role": "candidate_specific",
        "training_eligible": training_eligible,
        "training_exclusion_reason": None if training_eligible else "blocked_not_candidate_level_metric",
        "label_review_preferred": label,
        "label_status": "eligible" if label is not None else None,
        "label_reason_code": "test",
        "strategy_family": "momentum",
        "signal_family": "momentum",
        "max_drawdown": max_drawdown,
        "max_drawdown_abs": abs(max_drawdown),
        "feature_values": feature_values,
        **feature_values,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def config_payload(
    tmp_path: Path,
    rows: list[dict[str, object]],
    *,
    correlation: float = 0.99,
    training_features: list[str] | None = None,
) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    feature_path = data_dir / "feature_matrix.jsonl"
    manifest_path = data_dir / "manifest.json"
    train_dir = data_dir / "training"
    score_dir = data_dir / "scores"
    write_jsonl(feature_path, rows)
    write_json(
        manifest_path,
        {
            "feature_matrix_version": "v0_3_selector_feature_matrix_v1_0",
            "matrix_intent": "post_evaluation_selector_rule_replication_audit",
            "total_rows": len(rows),
            "candidate_level_metric_count": sum(
                row["metric_subject_type"] == "strategy_candidate"
                and row["candidate_metric_match"] is True
                for row in rows
            ),
            "null_label_rows": sum(row["label_review_preferred"] is None for row in rows),
            "excluded_rows": 0,
            "leakage_excluded_columns": sorted(trainer.DEFAULT_LEAKAGE_COLUMNS),
            "total_return_excess_return_correlation": correlation,
        },
    )
    config_path = tmp_path / "v0_4_selector_model.toml"
    configured_features = training_features or FEATURES
    feature_list = ", ".join(f'"{feature}"' for feature in configured_features)
    config_path.write_text(
        f'''
selector_model_version = "v0_4_selector_baseline_v0_1"
model_stage = "v0_4_ml_selector_application"
default_mode = "trainability_check_first"
baseline_model = "logistic_regression"
fallback_selector = "rule_only"
training_feature_columns = [{feature_list}]

[paths]
feature_matrix_jsonl = "{feature_path.as_posix()}"
feature_matrix_manifest = "{manifest_path.as_posix()}"
training_output_dir = "{train_dir.as_posix()}"
score_output_dir = "{score_dir.as_posix()}"

[model_defaults]
class_weight = "balanced"
max_iter = 1000
limited_training_rows_threshold = 100
high_feature_correlation_threshold = 0.95

[boundaries]
allowed_use = "AdoptionCandidate review prioritization only"
prediction_claim = "none"
trade_signal_claim = "none"
'''.lstrip(),
        encoding="utf-8",
    )
    return config_path, train_dir


def fake_model_factory(_config: dict[str, object]) -> FakeLogisticRegression:
    return FakeLogisticRegression()


def test_positive_zero_blocks_training(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("n1", 0), make_row("n2", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_no_positive_negative_classes"
    assert manifest["model_artifact_created"] is False
    assert manifest["prediction_value_row_count"] == 0


def test_negative_zero_blocks_training(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("p2", 1)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_no_positive_negative_classes"
    assert manifest["negative_rows"] == 0
    assert manifest["prediction_value_row_count"] == 0


def test_positive_negative_guard_trains_with_fake_model(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "trained_logistic_regression_baseline"
    assert manifest["readiness_status"] == "trained_logistic_regression_baseline"
    assert manifest["training_eligible_rows"] == 2
    assert manifest["positive_rows"] == 1
    assert manifest["negative_rows"] == 1
    assert manifest["training_feature_columns"] == FEATURES
    assert "limited_insufficient_training_rows" in manifest["warnings"]
    assert "high_feature_correlation_warning" in manifest["warnings"]


def test_only_six_features_are_used_and_family_columns_are_audit_only(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["training_feature_columns"] == FEATURES
    assert "strategy_family" not in manifest["training_feature_columns"]
    assert "signal_family" not in manifest["training_feature_columns"]


def test_max_drawdown_original_is_audit_and_abs_feature_is_checked(tmp_path: Path) -> None:
    row = make_row("p1", 1, max_drawdown=-0.12)
    assert row["max_drawdown"] == -0.12
    assert row["feature_values"]["max_drawdown_abs"] == 0.12
    config_path, _ = config_payload(tmp_path, [row, make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["bad_max_drawdown_abs_rows"] == 0
    assert manifest["train_status"] == "trained_logistic_regression_baseline"


def test_leakage_columns_in_feature_values_block_training(tmp_path: Path) -> None:
    config_path, _ = config_payload(
        tmp_path,
        [
            make_row("p1", 1, extra_feature_values={"selector_score": 0.9}),
            make_row("n1", 0),
        ],
    )

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert manifest["feature_value_leak_rows"] == 1


def test_leakage_columns_in_config_features_block_training(tmp_path: Path) -> None:
    config_path, _ = config_payload(
        tmp_path,
        [make_row("p1", 1), make_row("n1", 0)],
        training_features=[
            "total_return",
            "excess_return_vs_proxy",
            "max_drawdown_abs",
            "sharpe",
            "turnover",
            "label_review_preferred",
        ],
    )

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert manifest["train_blocked_reason"] == "blocked_label_leakage_columns_found"
    assert manifest["model_artifact_created"] is False
    assert manifest["prediction_value_row_count"] == 0
    assert manifest["feature_config_leak_columns"] == ["label_review_preferred"]
    assert manifest["feature_config_matches_expected"] is False


def test_feature_values_are_the_only_training_feature_source(tmp_path: Path) -> None:
    missing_feature_row = make_row("p1", 1)
    del missing_feature_row["feature_values"]["sharpe"]
    assert missing_feature_row["sharpe"] == 1.1
    config_path, _ = config_payload(tmp_path, [missing_feature_row, make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_missing_required_core_feature"
    assert manifest["missing_required_feature_rows"] == 1


def test_sklearn_missing_blocks_after_class_distribution_passes(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=False,
        model_factory=fake_model_factory,
    )

    assert manifest["positive_rows"] == 1
    assert manifest["negative_rows"] == 1
    assert manifest["train_status"] == "blocked_missing_ml_dependency"
    assert manifest["model_artifact_created"] is False


def test_high_correlation_warning_is_not_a_blocker(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)], correlation=0.999)

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert "high_feature_correlation_warning" in manifest["warnings"]
    assert manifest["train_status"] == "trained_logistic_regression_baseline"


def test_blocked_scorer_keeps_prediction_count_zero(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=False,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "blocked_train_status"
    assert score_manifest["blocked_reason"] == "blocked_missing_ml_dependency"
    assert score_manifest["prediction_value_row_count"] == 0
