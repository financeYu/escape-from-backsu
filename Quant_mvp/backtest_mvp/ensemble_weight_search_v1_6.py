"""v1.6 leakage-aware ensemble weight search.

This module searches model-mixture weights for historical or simulated
candidate evidence. It keeps predeclared candidate weights, validation
selection, and test reporting separated across chronological splits and does
not update production ranking or create execution instructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from statistics import fmean
from typing import Any
import json
import re


RUNNER_VERSION = "v1_6_ensemble_weight_search_v1_0"
SEARCH_MANIFEST_VERSION = "v1_6_ensemble_weight_search_manifest_v1_0"
LEAKAGE_AUDIT_VERSION = "v1_6_ensemble_weight_leakage_audit_v1_0"
DEFAULT_CREATED_AT = "2026-05-16T00:00:00+00:00"
EVIDENCE_ONLY_NOTICE = (
    "v1.6 ensemble weight search outputs are historical or simulated model "
    "evaluation evidence for manual review support"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic rebalance "
    "instructions, move-to-cash commands, future-return guarantees, proven-alpha claims, "
    "production ranking replacement, and valuation/fundamental active scoring"
)
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
REQUIRED_INPUT_FIELDS = frozenset(
    {
        "model_id",
        "evaluation_date",
        "net_return",
        "leakage_check_status",
        "no_lookahead_check_status",
    }
)
FORBIDDEN_INPUT_FIELDS = frozenset(
    {
        "future_return",
        "forward_return",
        "expected_return",
        "predicted_return",
        "production_rank",
        "production_ranking",
        "trade_signal",
        "order_instruction",
        "automatic_rebalance_instruction",
        "valuation_score",
        "fundamental_score",
        "final_composite_score",
        "technical_composite_score",
    }
)
ALLOWED_SPLITS = frozenset({"train", "validation", "test"})


@dataclass(frozen=True)
class EnsembleWeightSearchConfig:
    """Config for reusable leakage-aware ensemble weight search."""

    top_n_ensembles: int = 5
    weight_step: float = 0.25
    train_fraction: float = 0.50
    validation_fraction: float = 0.25
    minimum_model_count: int = 2
    minimum_train_periods: int = 1
    minimum_validation_periods: int = 1
    minimum_test_periods: int = 1
    max_weight_vectors: int = 5000
    created_at: str = DEFAULT_CREATED_AT
    config_ref: str = "Quant_mvp/backtest_mvp/ensemble_weight_search_v1_6.py"

    def __post_init__(self) -> None:
        if self.top_n_ensembles < 1:
            raise ValueError("v1.6 top_n_ensembles must be at least 1")
        if self.minimum_model_count < 2:
            raise ValueError("v1.6 minimum_model_count must be at least 2")
        if self.weight_step <= 0 or self.weight_step > 1:
            raise ValueError("v1.6 weight_step must be in (0, 1]")
        units = 1.0 / self.weight_step
        if abs(units - round(units)) > 1e-9:
            raise ValueError("v1.6 weight_step must divide 1.0 exactly")
        if not 0 < self.train_fraction < 1:
            raise ValueError("v1.6 train_fraction must be in (0, 1)")
        if not 0 < self.validation_fraction < 1:
            raise ValueError("v1.6 validation_fraction must be in (0, 1)")
        if self.train_fraction + self.validation_fraction >= 1:
            raise ValueError("v1.6 train_fraction plus validation_fraction must leave a test split")
        if min(self.minimum_train_periods, self.minimum_validation_periods, self.minimum_test_periods) < 1:
            raise ValueError("v1.6 minimum split periods must be at least 1")
        if self.max_weight_vectors < 1:
            raise ValueError("v1.6 max_weight_vectors must be at least 1")


def run_v1_6_ensemble_weight_search(
    model_return_rows: Sequence[Mapping[str, Any]],
    *,
    config: EnsembleWeightSearchConfig | None = None,
) -> dict[str, Any]:
    """Search ensemble weights with train/validation/test separation."""

    cfg = config or EnsembleWeightSearchConfig()
    rows = _normalize_rows(model_return_rows)
    model_ids = tuple(sorted({row["model_id"] for row in rows}))
    if len(model_ids) < cfg.minimum_model_count:
        raise ValueError("v1.6 ensemble weight search requires at least two models")
    split_by_date = _split_by_date(rows, cfg)
    returns_by_date_model = _returns_by_date_model(rows, model_ids)
    weight_vectors = _weight_vectors(model_ids, cfg)
    scored = [
        _score_weight_vector(weights, returns_by_date_model, split_by_date)
        for weights in weight_vectors
    ]
    scored.sort(
        key=lambda item: (
            -item["validation_metrics"]["cumulative_return"],
            -item["train_metrics"]["cumulative_return"],
            item["weight_vector_id"],
        )
    )
    retained = scored[: max(1, min(cfg.top_n_ensembles, len(scored)))]
    manifest = _search_manifest(cfg, model_ids, split_by_date, retained, len(scored))
    leakage_audit = _leakage_audit(rows, split_by_date, retained)
    artifacts = {
        "v1_6_ensemble_weight_search_manifest": manifest,
        "v1_6_ensemble_weight_candidates": scored,
        "v1_6_retained_ensemble_weight_report": _retained_report(cfg, retained),
        "v1_6_ensemble_leakage_audit": leakage_audit,
    }
    validate_v1_6_ensemble_weight_search_artifacts(artifacts)
    return artifacts


def validate_v1_6_ensemble_weight_search_artifacts(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_6_ensemble_weight_search_manifest",
        "v1_6_ensemble_weight_candidates",
        "v1_6_retained_ensemble_weight_report",
        "v1_6_ensemble_leakage_audit",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.6 ensemble artifacts missing: {', '.join(missing)}")
    manifest = artifacts["v1_6_ensemble_weight_search_manifest"]
    if manifest.get("manifest_version") != SEARCH_MANIFEST_VERSION:
        raise ValueError("unsupported v1.6 ensemble manifest version")
    audit = artifacts["v1_6_ensemble_leakage_audit"]
    if audit.get("audit_version") != LEAKAGE_AUDIT_VERSION:
        raise ValueError("unsupported v1.6 ensemble leakage audit version")
    if audit.get("leakage_audit_status") != "pass":
        raise ValueError("v1.6 ensemble leakage audit must pass")
    for payload in (manifest, artifacts["v1_6_retained_ensemble_weight_report"], audit):
        _validate_flags_false(payload, "v1.6 ensemble artifact")
    _reject_prohibited_language(artifacts)


def _normalize_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("v1.6 ensemble weight search requires model return rows")
    normalized = []
    for row in rows:
        payload = dict(row)
        forbidden = sorted(set(payload).intersection(FORBIDDEN_INPUT_FIELDS))
        if forbidden:
            raise ValueError(f"v1.6 ensemble input contains forbidden fields: {', '.join(forbidden)}")
        missing = sorted(REQUIRED_INPUT_FIELDS.difference(payload))
        if missing:
            raise ValueError(f"v1.6 ensemble input missing fields: {', '.join(missing)}")
        if str(payload["leakage_check_status"]) != "pass":
            raise ValueError("v1.6 ensemble input requires leakage_check_status=pass")
        if str(payload["no_lookahead_check_status"]) != "pass":
            raise ValueError("v1.6 ensemble input requires no_lookahead_check_status=pass")
        net_return = _finite_float(payload["net_return"], "net_return")
        if net_return <= -1.0:
            raise ValueError("v1.6 ensemble net_return must be greater than -1")
        split = str(payload.get("split") or "").strip().lower()
        if split and split not in ALLOWED_SPLITS:
            raise ValueError("v1.6 ensemble split must be train, validation, or test")
        normalized.append(
            {
                "model_id": _required_text(payload, "model_id"),
                "evaluation_date": _required_text(payload, "evaluation_date"),
                "net_return": net_return,
                "split": split or None,
                "source_ref": str(payload.get("source_ref") or ""),
                "leakage_check_status": "pass",
                "no_lookahead_check_status": "pass",
            }
        )
    normalized.sort(key=lambda item: (item["evaluation_date"], item["model_id"]))
    return normalized


def _split_by_date(
    rows: Sequence[Mapping[str, Any]],
    config: EnsembleWeightSearchConfig,
) -> dict[str, str]:
    explicit = {str(row.get("split") or "") for row in rows}
    dates = sorted({str(row["evaluation_date"]) for row in rows})
    if explicit == {""} or explicit == {None, ""}:
        return _chronological_split(dates, config)
    if "" in explicit or None in explicit:
        raise ValueError("v1.6 ensemble input must use all explicit splits or none")
    split_by_date: dict[str, str] = {}
    for row in rows:
        date_key = str(row["evaluation_date"])
        split = str(row["split"])
        existing = split_by_date.get(date_key)
        if existing is not None and existing != split:
            raise ValueError("v1.6 ensemble split must be consistent for each evaluation_date")
        split_by_date[date_key] = split
    _validate_split_counts(split_by_date, config)
    return split_by_date


def _chronological_split(
    dates: Sequence[str],
    config: EnsembleWeightSearchConfig,
) -> dict[str, str]:
    total = len(dates)
    train_count = max(config.minimum_train_periods, int(total * config.train_fraction))
    validation_count = max(config.minimum_validation_periods, int(total * config.validation_fraction))
    test_count = total - train_count - validation_count
    if test_count < config.minimum_test_periods:
        raise ValueError("v1.6 ensemble input has insufficient chronological test periods")
    split_by_date = {}
    for index, date_key in enumerate(dates):
        if index < train_count:
            split_by_date[date_key] = "train"
        elif index < train_count + validation_count:
            split_by_date[date_key] = "validation"
        else:
            split_by_date[date_key] = "test"
    _validate_split_counts(split_by_date, config)
    return split_by_date


def _validate_split_counts(
    split_by_date: Mapping[str, str],
    config: EnsembleWeightSearchConfig,
) -> None:
    counts = {split: list(split_by_date.values()).count(split) for split in ALLOWED_SPLITS}
    if counts["train"] < config.minimum_train_periods:
        raise ValueError("v1.6 ensemble train split has insufficient periods")
    if counts["validation"] < config.minimum_validation_periods:
        raise ValueError("v1.6 ensemble validation split has insufficient periods")
    if counts["test"] < config.minimum_test_periods:
        raise ValueError("v1.6 ensemble test split has insufficient periods")


def _returns_by_date_model(
    rows: Sequence[Mapping[str, Any]],
    model_ids: Sequence[str],
) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        date_key = str(row["evaluation_date"])
        model_id = str(row["model_id"])
        grouped.setdefault(date_key, {})
        if model_id in grouped[date_key]:
            raise ValueError("v1.6 ensemble input has duplicate model/date rows")
        grouped[date_key][model_id] = float(row["net_return"])
    for date_key, returns in grouped.items():
        missing = sorted(set(model_ids).difference(returns))
        if missing:
            raise ValueError(f"v1.6 ensemble input missing model rows for {date_key}: {', '.join(missing)}")
    return grouped


def _weight_vectors(
    model_ids: Sequence[str],
    config: EnsembleWeightSearchConfig,
) -> list[dict[str, float]]:
    denominator = int(round(1.0 / config.weight_step))
    vectors = [
        {model_id: units / denominator for model_id, units in zip(model_ids, unit_vector)}
        for unit_vector in _integer_weight_units(len(model_ids), denominator)
    ]
    if len(vectors) > config.max_weight_vectors:
        raise ValueError("v1.6 ensemble weight grid exceeds max_weight_vectors")
    return vectors


def _integer_weight_units(model_count: int, remaining: int) -> list[tuple[int, ...]]:
    if model_count == 1:
        return [(remaining,)]
    vectors = []
    for units in range(remaining + 1):
        for suffix in _integer_weight_units(model_count - 1, remaining - units):
            vectors.append((units, *suffix))
    return vectors


def _score_weight_vector(
    weights: Mapping[str, float],
    returns_by_date_model: Mapping[str, Mapping[str, float]],
    split_by_date: Mapping[str, str],
) -> dict[str, Any]:
    period_returns = [
        {
            "evaluation_date": date_key,
            "split": split_by_date[date_key],
            "ensemble_net_return": round(
                sum(weights[model_id] * returns[model_id] for model_id in weights),
                10,
            ),
        }
        for date_key, returns in sorted(returns_by_date_model.items())
    ]
    split_returns = {
        split: [row["ensemble_net_return"] for row in period_returns if row["split"] == split]
        for split in ALLOWED_SPLITS
    }
    weight_vector_id = _weight_vector_id(weights)
    return {
        "weight_vector_id": weight_vector_id,
        "weights": {model_id: round(float(weight), 8) for model_id, weight in sorted(weights.items())},
        "train_metrics": _return_metrics(split_returns["train"]),
        "validation_metrics": _return_metrics(split_returns["validation"]),
        "test_metrics": _return_metrics(split_returns["test"]),
        "period_returns": period_returns,
        "weight_grid_policy": "predeclared_non_negative_sum_to_one_grid",
        "selected_on_split": "validation",
        "test_split_role": "untouched_final_review_only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _return_metrics(returns: Sequence[float]) -> dict[str, Any]:
    cumulative = 1.0
    for value in returns:
        cumulative *= 1.0 + value
    cumulative_return = cumulative - 1.0
    mean_return = fmean(returns) if returns else 0.0
    volatility = _population_volatility(returns)
    return {
        "period_count": len(returns),
        "cumulative_return": round(cumulative_return, 8),
        "mean_period_return": round(mean_return, 8),
        "period_volatility": round(volatility, 8),
        "sharpe_like_summary": round(mean_return / volatility, 8) if volatility > 0 else None,
        "hit_rate": round(sum(1 for value in returns if value > 0) / len(returns), 8) if returns else 0.0,
    }


def _population_volatility(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = fmean(values)
    return (sum((value - mean_value) ** 2 for value in values) / len(values)) ** 0.5


def _search_manifest(
    config: EnsembleWeightSearchConfig,
    model_ids: Sequence[str],
    split_by_date: Mapping[str, str],
    retained: Sequence[Mapping[str, Any]],
    candidate_count: int,
) -> dict[str, Any]:
    split_counts = {split: list(split_by_date.values()).count(split) for split in sorted(ALLOWED_SPLITS)}
    return {
        "manifest_version": SEARCH_MANIFEST_VERSION,
        "runner_version": RUNNER_VERSION,
        "created_at": config.created_at,
        "model_ids": list(model_ids),
        "candidate_weight_vector_count": candidate_count,
        "retained_ensemble_count": len(retained),
        "top_n_ensembles": config.top_n_ensembles,
        "weight_step": config.weight_step,
        "split_counts": split_counts,
        "weight_grid_policy": "predeclared_non_negative_sum_to_one_grid",
        "selection_split": "validation",
        "test_split_role": "untouched_final_review_only",
        "best_retained_weight_vector_id": retained[0]["weight_vector_id"] if retained else None,
        "config_snapshot": config.__dict__,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _retained_report(
    config: EnsembleWeightSearchConfig,
    retained: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "report_name": "v1_6_retained_ensemble_weight_report",
        "selection_policy": (
            "retain top_n_ensembles by validation cumulative return from a "
            "predeclared non-negative sum-to-one weight grid"
        ),
        "top_n_ensembles": config.top_n_ensembles,
        "retained_ensemble_count": len(retained),
        "retained_ensembles": [
            {
                "validation_rank": index,
                "weight_vector_id": item["weight_vector_id"],
                "weights": item["weights"],
                "train_metrics": item["train_metrics"],
                "validation_metrics": item["validation_metrics"],
                "test_metrics": item["test_metrics"],
                "test_split_role": item["test_split_role"],
            }
            for index, item in enumerate(retained, start=1)
        ],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _leakage_audit(
    rows: Sequence[Mapping[str, Any]],
    split_by_date: Mapping[str, str],
    retained: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    split_counts = {split: list(split_by_date.values()).count(split) for split in sorted(ALLOWED_SPLITS)}
    return {
        "audit_version": LEAKAGE_AUDIT_VERSION,
        "leakage_audit_status": "pass",
        "input_row_count": len(rows),
        "split_counts": split_counts,
        "leakage_check_status": "pass",
        "no_lookahead_check_status": "pass",
        "predeclared_weight_grid_used": True,
        "validation_selects_retained_ensembles": True,
        "test_split_not_used_for_weight_selection": True,
        "retained_weight_vector_ids": [item["weight_vector_id"] for item in retained],
        "blocked_reasons": [],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _weight_vector_id(weights: Mapping[str, float]) -> str:
    digest = sha256(json.dumps(dict(sorted(weights.items())), sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_6_ensemble_weights_{digest}"


def _finite_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"v1.6 ensemble requires numeric {field_name}") from exc
    if not isfinite(parsed):
        raise ValueError(f"v1.6 ensemble requires finite {field_name}")
    return parsed


def _required_text(values: Mapping[str, Any], field_name: str) -> str:
    text = str(values.get(field_name) or "").strip()
    if not text:
        raise ValueError(f"v1.6 ensemble requires {field_name}")
    return text


def _blocked_flags() -> dict[str, bool]:
    return {flag: False for flag in PROHIBITED_FLAGS}


def _validate_flags_false(payload: Mapping[str, Any], label: str) -> None:
    for flag in PROHIBITED_FLAGS:
        if bool(payload.get(flag)):
            raise ValueError(f"{label} blocked flag must remain false: {flag}")


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice"}
    text = json.dumps(
        _drop_allowed_notice_fields(payload, allowed_fields),
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    blocked_patterns = (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\btrade signal\b",
        r"\border instruction\b",
        r"\bautomatic rebalance instruction\b",
        r"\bmove to cash\b",
        r"\bfuture[-_ ]return guarantee",
        r"\bproven[-_ ]alpha\b",
        r"\bproduction ranking replacement\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.6 ensemble artifacts contain prohibited language: {pattern}")


def _drop_allowed_notice_fields(value: Any, allowed_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _drop_allowed_notice_fields(item, allowed_fields)
            for key, item in value.items()
            if key not in allowed_fields
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_drop_allowed_notice_fields(item, allowed_fields) for item in value]
    return value


__all__ = (
    "EnsembleWeightSearchConfig",
    "RUNNER_VERSION",
    "run_v1_6_ensemble_weight_search",
    "validate_v1_6_ensemble_weight_search_artifacts",
)
