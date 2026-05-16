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
    coef_ = [[0.1, -0.2, 0.3, 0.4, -0.5, 0.6]]
    intercept_ = [0.0]

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


class FakeLogisticRanker(FakeLogisticRegression):
    def predict_proba(self, x_values: list[list[float]]) -> list[list[float]]:
        assert self.fitted
        values: list[list[float]] = []
        for features in x_values:
            probability = 0.8 if features[0] < 0.1 else 0.2
            values.append([1.0 - probability, probability])
        return values


class FakeRandomForestClassifier:
    classes_ = [0, 1]

    def __init__(self) -> None:
        self.fitted = False

    def fit(self, x_values: list[list[float]], y_values: list[int]) -> "FakeRandomForestClassifier":
        assert len(x_values) == len(y_values)
        assert {0, 1} <= set(y_values)
        self.fitted = True
        return self

    def predict_proba(self, x_values: list[list[float]]) -> list[list[float]]:
        assert self.fitted
        values: list[list[float]] = []
        for features in x_values:
            probability = 0.8 if features[0] >= 0.1 else 0.3
            values.append([1.0 - probability, probability])
        return values


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
random_state = 0
solver = "lbfgs"
limited_training_rows_threshold = 100
high_feature_correlation_threshold = 0.95

[random_forest_defaults]
class_weight = "balanced"
max_depth = 3
min_samples_leaf = 1
n_estimators = 100
random_state = 0

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


def fake_logistic_ranker_factory(_config: dict[str, object]) -> FakeLogisticRanker:
    return FakeLogisticRanker()


def fake_random_forest_factory(_config: dict[str, object]) -> FakeRandomForestClassifier:
    return FakeRandomForestClassifier()


def test_v0_4_trainability_diagnostics_separate_target_and_feature_variance(tmp_path: Path) -> None:
    rows = [
        make_row("p1", 1, turnover=0.4),
        make_row("p2", 1, turnover=0.4),
        make_row("n1", 0, turnover=0.4),
        make_row("n2", 0, turnover=0.4),
    ]
    rows[0]["feature_as_of_date"] = "2024-02-02"
    rows[0]["label_target_date"] = "2024-02-01"
    config_path, _ = config_payload(tmp_path, rows)

    manifest = trainer.build_trainability_manifest(
        rows,
        trainer.read_json(trainer.resolve_path(trainer.load_config(config_path)["paths"]["feature_matrix_manifest"])),
        trainer.load_config(config_path),
        has_ml_dependencies=True,
        model_artifact_path=tmp_path / "model.pkl",
    )[0]

    diagnostics = manifest["score_discrimination_diagnostics"]
    assert diagnostics["target_unique_count"] == 2
    assert diagnostics["target_value_counts"] == {"0": 2, "1": 2}
    assert diagnostics["low_variance_feature_count"] >= 1
    assert diagnostics["feature_unique_count_summary"]["turnover"] == 1
    assert diagnostics["feature_label_date_violation_count"] == 1
    assert diagnostics["feature_label_date_check_status"] == "diagnostic_violation_present"


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


def test_v0_4_selector_model_manifest_records_logistic_regression_baseline(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    model_manifest = json.loads((train_dir / trainer.DEFAULT_MODEL_MANIFEST).read_text(encoding="utf-8"))
    assert model_manifest["model_type"] == "logistic_regression"
    assert model_manifest["model_family"] == "logistic_regression"
    assert model_manifest["baseline_model"] == "logistic_regression"
    assert model_manifest["model_library"] == "scikit-learn"
    assert model_manifest["model_library_version"]
    assert model_manifest["label_column"] == "label_review_preferred"
    assert model_manifest["deterministic_training"] is True
    assert model_manifest["random_state"] == 0


def test_v0_4_selector_model_manifest_records_training_rows_features_and_warnings(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    model_manifest = json.loads((train_dir / trainer.DEFAULT_MODEL_MANIFEST).read_text(encoding="utf-8"))
    assert model_manifest["training_row_count"] == 2
    assert model_manifest["feature_column_count"] == len(FEATURES)
    assert model_manifest["feature_columns"] == FEATURES
    assert "limited_insufficient_training_rows" in model_manifest["warnings"]
    assert "high_feature_correlation_warning" in model_manifest["warnings"]
    assert model_manifest["performance_claim_allowed"] is False
    assert model_manifest["evaluation_mode"] == "baseline_diagnostic_only"


def test_v0_4_selector_model_manifest_records_artifact_and_dependency_metadata(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    model_manifest = json.loads((train_dir / trainer.DEFAULT_MODEL_MANIFEST).read_text(encoding="utf-8"))
    assert model_manifest["artifact_path"].endswith(trainer.DEFAULT_MODEL_ARTIFACT)
    assert model_manifest["model_artifact_path"].endswith(trainer.DEFAULT_MODEL_ARTIFACT)
    assert model_manifest["trainability_manifest_path"].endswith(trainer.DEFAULT_TRAINABILITY_MANIFEST)
    assert model_manifest["has_ml_dependencies"] is True
    assert model_manifest["model_artifact_created"] is True
    assert len(model_manifest["training_input_digest_sha256"]) == 64


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


def test_v0_4_selector_feature_matrix_excludes_label_columns(tmp_path: Path) -> None:
    config_path, _ = config_payload(
        tmp_path,
        [
            make_row("p1", 1, extra_feature_values={"label": 1}),
            make_row("n1", 0),
        ],
    )

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert "label" in manifest["feature_value_forbidden_columns_found"]
    assert manifest["leakage_check_result"] == "fail"


def test_v0_4_selector_feature_matrix_excludes_review_decision_columns(tmp_path: Path) -> None:
    config_path, _ = config_payload(
        tmp_path,
        [
            make_row("p1", 1, extra_feature_values={"review_decision": "adopted"}),
            make_row("n1", 0),
        ],
    )

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert "review_decision" in manifest["feature_value_forbidden_columns_found"]


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


def test_v0_4_selector_training_rejects_forbidden_feature_columns(tmp_path: Path) -> None:
    config_path, _ = config_payload(
        tmp_path,
        [make_row("p1", 1), make_row("n1", 0)],
        training_features=[
            "total_return",
            "excess_return_vs_proxy",
            "max_drawdown_abs",
            "sharpe",
            "turnover",
            "prediction_value",
        ],
    )

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert manifest["feature_config_leak_columns"] == ["prediction_value"]


def test_v0_4_selector_training_records_leakage_guard_result(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    leakage_manifest = json.loads((train_dir / trainer.DEFAULT_LEAKAGE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["leakage_check_result"] == "pass"
    assert leakage_manifest["checked"] is True
    assert leakage_manifest["result"] == "pass"
    assert leakage_manifest["forbidden_columns_found"] == []
    assert leakage_manifest["allowed_feature_column_count"] == len(FEATURES)


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


def test_v0_4_selector_baseline_records_limited_training_rows_warning(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert "limited_insufficient_training_rows" in manifest["warnings"]
    assert manifest["warning_policy"]["limited_insufficient_training_rows"] == "performance_claim_allowed_false"


def test_v0_4_selector_baseline_records_high_feature_correlation_warning(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)], correlation=0.999)

    manifest = trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    assert "high_feature_correlation_warning" in manifest["warnings"]
    assert (
        manifest["warning_policy"]["high_feature_correlation_warning"]
        == "coefficient_interpretation_diagnostic_only"
    )
    assert "correlated features may make individual coefficients unstable" in manifest["interpretation_limits"]


def test_v0_4_selector_baseline_does_not_claim_performance_with_limited_rows(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    model_manifest = json.loads((train_dir / trainer.DEFAULT_MODEL_MANIFEST).read_text(encoding="utf-8"))
    assert "limited_insufficient_training_rows" in model_manifest["warnings"]
    assert model_manifest["performance_claim_allowed"] is False
    assert model_manifest["prediction_claim"] == "none"


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


def test_v0_4_scorer_uses_ml_model_when_artifact_exists(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "ml_model"
    assert score_manifest["fallback_used"] is False


def test_v0_4_scorer_diagnostics_expose_ties_without_changing_scores(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)
    score_rows_path = trainer.resolve_path(score_manifest["score_rows_path"])
    score_rows = [json.loads(line) for line in score_rows_path.read_text(encoding="utf-8").splitlines()]

    assert [row["selector_score"] for row in score_rows] == [0.6, 0.6]
    assert {row["tie_group_size"] for row in score_rows} == {2}
    assert sorted(row["rank_within_score_bucket"] for row in score_rows) == [1, 2]
    assert {tuple(row["tie_break_keys"]) for row in score_rows} == {("selector_score", "candidate_id")}
    diagnostics = score_manifest["score_discrimination_diagnostics"]
    assert diagnostics["selector_score_source"] == "model_prediction"
    assert diagnostics["selector_score_unique_count"] == 1
    assert diagnostics["max_tie_group_size"] == 2
    assert diagnostics["deterministic_sort_fields"] == ["selector_score", "candidate_id"]


def test_v0_4_selector_score_manifest_records_ml_model_source(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "ml_model"
    assert score_manifest["warnings"] == [
        "limited_insufficient_training_rows",
        "high_feature_correlation_warning",
    ]


def test_v0_4_selector_score_manifest_records_scored_and_prediction_row_counts(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["scored_candidate_count"] == 2
    assert score_manifest["prediction_value_row_count"] == 2


def test_v0_4_selector_score_manifest_links_model_artifact_and_score_rows(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["model_artifact_path"].endswith(trainer.DEFAULT_MODEL_ARTIFACT)
    assert score_manifest["model_manifest_path"].endswith(trainer.DEFAULT_MODEL_MANIFEST)
    assert score_manifest["score_rows_path"].endswith(scorer.DEFAULT_SCORE_JSONL)


def test_v0_4_scorer_falls_back_when_model_artifact_missing(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )
    (train_dir / trainer.DEFAULT_MODEL_ARTIFACT).unlink()

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "rule_only"
    assert score_manifest["fallback_used"] is True
    assert score_manifest["fallback_reason"] == "rule_only_available_no_model_artifact"
    assert score_manifest["prediction_value_row_count"] == 0
    diagnostics = score_manifest["score_discrimination_diagnostics"]
    assert diagnostics["selector_score_source"] == "fallback"
    assert diagnostics["fallback_used"] is True
    assert diagnostics["fallback_reason"] == "rule_only_available_no_model_artifact"


def test_v0_4_scorer_fails_or_warns_on_model_manifest_mismatch(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )
    model_manifest_path = train_dir / trainer.DEFAULT_MODEL_MANIFEST
    model_manifest = json.loads(model_manifest_path.read_text(encoding="utf-8"))
    model_manifest["selector_model_version"] = "wrong_version"
    write_json(model_manifest_path, model_manifest)

    score_manifest = scorer.score_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "rule_only"
    assert score_manifest["fallback_used"] is True
    assert score_manifest["blocked_reason"] == "model_manifest_mismatch"
    assert "selector_model_version_mismatch" in score_manifest["model_manifest_mismatch_reasons"]
    assert "model_manifest_mismatch_fallback" in score_manifest["warnings"]


def test_v0_4_scorer_records_score_source_for_every_row(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )
    scorer.score_candidates(config_path=config_path)
    score_manifest = scorer.score_candidates(config_path=config_path)
    score_rows_path = trainer.resolve_path(score_manifest["score_rows_path"])
    score_rows = [json.loads(line) for line in score_rows_path.read_text(encoding="utf-8").splitlines()]

    assert score_rows
    assert {row["selector_score_source"] for row in score_rows} == {"ml_model"}


def test_v0_4_selector_logistic_coefficients_artifact_records_diagnostics(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
    )

    coefficients = json.loads((train_dir / trainer.DEFAULT_COEFFICIENTS_ARTIFACT).read_text(encoding="utf-8"))
    assert coefficients["model_type"] == "logistic_regression"
    assert len(coefficients["coefficients"]) == len(FEATURES)
    assert "high_feature_correlation_warning" in coefficients["warnings"]
    assert "limited training rows prevent strong predictive claims" in coefficients["interpretation_limits"]


def test_v0_4_random_forest_manifest_records_challenger_metadata(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])

    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )

    model_manifest = json.loads(
        (train_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_MANIFEST).read_text(encoding="utf-8")
    )
    assert model_manifest["model_type"] == "random_forest_classifier"
    assert model_manifest["model_family"] == "random_forest"
    assert model_manifest["model_role"] == "nonlinear_challenger"
    assert model_manifest["challenger_only"] is True
    assert model_manifest["baseline_replacement"] is False
    assert model_manifest["frozen_baseline_model"] == "logistic_regression"
    assert model_manifest["n_estimators"] == 100
    assert model_manifest["max_depth"] == 3
    assert model_manifest["random_state"] == 0
    assert "limited_insufficient_training_rows" in model_manifest["warnings"]
    assert model_manifest["evaluation_mode"] == "diagnostic_comparison_only"


def test_v0_4_random_forest_score_rows_link_to_candidates(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )

    score_manifest = scorer.score_random_forest_candidates(config_path=config_path)
    score_rows_path = trainer.resolve_path(score_manifest["score_rows_path"])
    score_rows = [json.loads(line) for line in score_rows_path.read_text(encoding="utf-8").splitlines()]

    assert score_manifest["selector_score_source"] == "random_forest_challenger"
    assert score_manifest["scored_candidate_count"] == 2
    assert score_manifest["prediction_value_row_count"] == 2
    assert {row["candidate_id"] for row in score_rows} == {"p1", "n1"}
    assert {row["selector_score_source"] for row in score_rows} == {"random_forest_challenger"}
    assert all(row["random_forest_prediction_value"] == row["prediction_value"] for row in score_rows)


def test_v0_4_lr_rf_comparison_aligns_rows_and_calculates_deltas(tmp_path: Path) -> None:
    rows = [
        make_row("high_candidate", 1, total_return=0.2),
        make_row("low_candidate", 0, total_return=0.05),
    ]
    config_path, _ = config_payload(tmp_path, rows)
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_logistic_ranker_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    scorer.score_candidates(config_path=config_path)
    scorer.score_random_forest_candidates(config_path=config_path)

    comparison_manifest = scorer.compare_logistic_regression_random_forest_scores(config_path=config_path)
    comparison_rows_path = trainer.resolve_path(comparison_manifest["comparison_rows_path"])
    comparison_rows = [json.loads(line) for line in comparison_rows_path.read_text(encoding="utf-8").splitlines()]
    by_candidate = {row["candidate_id"]: row for row in comparison_rows}

    assert comparison_manifest["summary"]["compared_candidate_count"] == 2
    assert set(by_candidate) == {"high_candidate", "low_candidate"}
    assert by_candidate["high_candidate"]["logistic_regression_prediction_value"] == 0.2
    assert by_candidate["high_candidate"]["random_forest_prediction_value"] == 0.8
    assert by_candidate["high_candidate"]["score_delta"] == 0.6000000000000001
    assert by_candidate["high_candidate"]["score_rank_lr"] == 2
    assert by_candidate["high_candidate"]["score_rank_rf"] == 1
    assert by_candidate["high_candidate"]["rank_delta"] == -1
    assert round(comparison_manifest["summary"]["mean_abs_score_delta"], 2) == 0.55
    assert comparison_manifest["summary"]["max_abs_score_delta"] == 0.6000000000000001
    assert comparison_manifest["summary"]["top_n_overlap"] == 2
    assert comparison_manifest["ranking_manifest_path"].endswith(scorer.DEFAULT_RANKING_MANIFEST)
    assert comparison_manifest["summary"]["ranking_top_k_overlap"]["5"]["random_forest"]["overlap_count"] == 2


def test_v0_4_comparison_summary_is_diagnostic_only_and_policy_unchanged(tmp_path: Path) -> None:
    config_path, _ = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    lr_manifest = scorer.score_candidates(config_path=config_path)
    rf_manifest = scorer.score_random_forest_candidates(config_path=config_path)
    comparison_manifest = scorer.compare_logistic_regression_random_forest_scores(config_path=config_path)

    assert lr_manifest["selector_score_source"] == "ml_model"
    assert rf_manifest["selector_score_source"] == "random_forest_challenger"
    assert comparison_manifest["baseline_replacement"] is False
    assert comparison_manifest["selector_score_source_default_changed"] is False
    assert comparison_manifest["performance_claim_allowed"] is False
    assert comparison_manifest["trading_signal_allowed"] is False
    assert comparison_manifest["adoption_auto_decision_allowed"] is False
    assert comparison_manifest["diagnostic_reference_only"] is True
    assert comparison_manifest["evaluation_mode"] == "diagnostic_comparison_only"
    assert "limited_insufficient_training_rows" in comparison_manifest["warnings"]


def test_v0_4_1_ml_score_ranking_manifest_is_diagnostic_only(tmp_path: Path) -> None:
    rows = [
        make_row("high_candidate", 1, total_return=0.2),
        make_row("low_candidate", 0, total_return=0.05),
    ]
    config_path, _ = config_payload(tmp_path, rows)
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_logistic_ranker_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    scorer.score_candidates(config_path=config_path)
    scorer.score_random_forest_candidates(config_path=config_path)

    ranking_manifest = scorer.build_ml_score_ranking(config_path=config_path)

    assert ranking_manifest["evaluation_mode"] == "diagnostic_ranking_only"
    assert ranking_manifest["baseline_model_id"] == "logistic_regression"
    assert ranking_manifest["compared_model_ids"] == ["logistic_regression", "random_forest"]
    assert ranking_manifest["candidate_count"] == 2
    assert ranking_manifest["per_model_score_available_count"] == {
        "logistic_regression": 2,
        "random_forest": 2,
    }
    assert ranking_manifest["ranking_schema_version"] == scorer.RANKING_SCHEMA_VERSION
    assert ranking_manifest["selector_score_source_unchanged"] is True
    assert ranking_manifest["performance_claim_allowed"] is False
    assert ranking_manifest["trading_signal_allowed"] is False
    assert ranking_manifest["adoption_auto_decision_allowed"] is False


def test_v0_4_1_ml_score_ranking_rows_keep_baseline_relative_fields(tmp_path: Path) -> None:
    rows = [
        make_row("high_candidate", 1, total_return=0.2),
        make_row("low_candidate", 0, total_return=0.05),
    ]
    config_path, _ = config_payload(tmp_path, rows)
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_logistic_ranker_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    scorer.score_candidates(config_path=config_path)
    scorer.score_random_forest_candidates(config_path=config_path)

    ranking_manifest = scorer.build_ml_score_ranking(config_path=config_path)
    ranking_rows_path = trainer.resolve_path(ranking_manifest["ranking_rows_path"])
    ranking_rows = [json.loads(line) for line in ranking_rows_path.read_text(encoding="utf-8").splitlines()]
    by_candidate = {row["candidate_id"]: row for row in ranking_rows}

    high = by_candidate["high_candidate"]
    assert high["logistic_regression_score"] == 0.2
    assert high["random_forest_score"] == 0.8
    assert high["logistic_regression_rank"] == 2
    assert high["random_forest_rank"] == 1
    assert high["random_forest_score_delta_vs_logistic_regression"] == 0.6000000000000001
    assert high["random_forest_rank_delta_vs_logistic_regression"] == -1
    assert high["baseline_model_id"] == "logistic_regression"
    assert high["selector_score_source_unchanged"] is True
    assert high["evaluation_mode"] == "diagnostic_ranking_only"


def test_v0_4_1_ml_score_ranking_uses_same_candidate_set(tmp_path: Path) -> None:
    rows = [
        make_row("high_candidate", 1, total_return=0.2),
        make_row("low_candidate", 0, total_return=0.05),
    ]
    config_path, _ = config_payload(tmp_path, rows)
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_logistic_ranker_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    scorer.score_candidates(config_path=config_path)
    rf_manifest = scorer.score_random_forest_candidates(config_path=config_path)
    rf_rows_path = trainer.resolve_path(rf_manifest["score_rows_path"])
    rf_rows = [
        json.loads(line)
        for line in rf_rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    write_jsonl(
        rf_rows_path,
        [row for row in rf_rows if row["candidate_id"] == "high_candidate"],
    )

    ranking_manifest = scorer.build_ml_score_ranking(config_path=config_path)
    ranking_rows_path = trainer.resolve_path(ranking_manifest["ranking_rows_path"])
    ranking_rows = [json.loads(line) for line in ranking_rows_path.read_text(encoding="utf-8").splitlines()]

    assert ranking_manifest["candidate_set_policy"] == "same_candidate_set_intersection_of_compared_model_scores"
    assert ranking_manifest["all_scored_candidate_count"] == 2
    assert ranking_manifest["candidate_count"] == 1
    assert ranking_manifest["per_model_score_available_count"] == {
        "logistic_regression": 2,
        "random_forest": 1,
    }
    assert ranking_manifest["per_model_score_missing_from_same_set_count"] == {
        "logistic_regression": 0,
        "random_forest": 1,
    }
    assert ranking_manifest["per_model_score_excluded_from_ranking_count"] == {
        "logistic_regression": 1,
        "random_forest": 0,
    }
    assert [row["candidate_id"] for row in ranking_rows] == ["high_candidate"]
    assert ranking_rows[0]["logistic_regression_available"] is True
    assert ranking_rows[0]["random_forest_available"] is True


def test_v0_4_lr_rf_comparison_top_n_uses_same_candidate_set(tmp_path: Path) -> None:
    rows = [
        make_row("high_candidate", 1, total_return=0.2),
        make_row("low_candidate", 0, total_return=0.05),
    ]
    config_path, _ = config_payload(tmp_path, rows)
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_logistic_ranker_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    scorer.score_candidates(config_path=config_path)
    rf_manifest = scorer.score_random_forest_candidates(config_path=config_path)
    rf_rows_path = trainer.resolve_path(rf_manifest["score_rows_path"])
    rf_rows = [
        json.loads(line)
        for line in rf_rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    write_jsonl(
        rf_rows_path,
        [row for row in rf_rows if row["candidate_id"] == "high_candidate"],
    )

    comparison_manifest = scorer.compare_logistic_regression_random_forest_scores(config_path=config_path)

    assert comparison_manifest["summary"]["compared_candidate_count"] == 1
    assert comparison_manifest["summary"]["lr_score_available_count"] == 2
    assert comparison_manifest["summary"]["rf_score_available_count"] == 1
    assert comparison_manifest["summary"]["top_n_overlap"] == 1
    assert comparison_manifest["summary"]["top_n_overlap_ratio"] == 1.0


def test_v0_4_random_forest_reuses_leakage_guard(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(
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
        random_forest_model_factory=fake_random_forest_factory,
    )

    assert manifest["train_status"] == "blocked_label_leakage_columns_found"
    assert not (train_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_MANIFEST).exists()
    assert not (train_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_ARTIFACT).exists()


def test_v0_4_random_forest_scorer_blocks_when_artifact_missing(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    (train_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_ARTIFACT).unlink()

    score_manifest = scorer.score_random_forest_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "random_forest_challenger_blocked"
    assert score_manifest["blocked_reason"] == "random_forest_model_artifact_missing"
    assert score_manifest["fallback_used"] is False
    assert score_manifest["prediction_value_row_count"] == 0


def test_v0_4_random_forest_scorer_blocks_on_manifest_mismatch(tmp_path: Path) -> None:
    config_path, train_dir = config_payload(tmp_path, [make_row("p1", 1), make_row("n1", 0)])
    trainer.train_selector_baseline(
        config_path=config_path,
        dependency_available=True,
        model_factory=fake_model_factory,
        random_forest_model_factory=fake_random_forest_factory,
    )
    model_manifest_path = train_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_MANIFEST
    model_manifest = json.loads(model_manifest_path.read_text(encoding="utf-8"))
    model_manifest["model_family"] = "logistic_regression"
    write_json(model_manifest_path, model_manifest)

    score_manifest = scorer.score_random_forest_candidates(config_path=config_path)

    assert score_manifest["selector_score_source"] == "random_forest_challenger_blocked"
    assert score_manifest["blocked_reason"] == "random_forest_model_manifest_mismatch"
    assert "model_family_mismatch" in score_manifest["model_manifest_mismatch_reasons"]
