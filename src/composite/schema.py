"""Step 11 composite schema validation helpers.

The helpers here only validate contracts for later composite design. They do
not create composite scores, rankings, trading signals, valuation fields,
future-return labels, or backtest outputs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
import tomllib

import pandas as pd

from src.scores.schema import (
    IDENTITY_COLUMNS,
    SCORE_METADATA_COLUMNS,
    find_valuation_fundamental_columns,
    require_columns,
)

from .contracts import (
    CONTEXT_OR_DIAGNOSTIC_SCORE_NAMES,
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    DEFAULT_STATUS_PROPAGATION_CONTRACT,
    MVP_SCORE_NAMES,
    CompositeEligibility,
    CompositeInputSpec,
    CompositeRole,
    StatusPropagationContract,
)


ALLOWED_SCORE_BRANCHES = frozenset({"technical", "diagnostic"})
ALLOWED_COMPOSITE_FAMILIES = frozenset(
    {
        "mean_reversion",
        "trend_breakout",
        "volatility_context",
        "volume_flow",
    }
)
EXPECTED_COMPOSITE_POLICY = {
    "short_term_overreaction": (
        "mean_reversion",
        CompositeRole.CANDIDATE_SIGNAL,
        CompositeEligibility.ELIGIBLE,
    ),
    "atr_adjusted_oversold_distance": (
        "mean_reversion",
        CompositeRole.CANDIDATE_SIGNAL,
        CompositeEligibility.CONDITIONAL,
    ),
    "donchian_breakout_distance": (
        "trend_breakout",
        CompositeRole.CANDIDATE_SIGNAL,
        CompositeEligibility.ELIGIBLE,
    ),
    "bollinger_width_squeeze": (
        "volatility_context",
        CompositeRole.SETUP_CONTEXT,
        CompositeEligibility.CONDITIONAL,
    ),
    "cmf_confirmation": (
        "volume_flow",
        CompositeRole.CONFIRMATION,
        CompositeEligibility.CONDITIONAL,
    ),
    "rsi_price_divergence": (
        "mean_reversion",
        CompositeRole.CANDIDATE_SIGNAL,
        CompositeEligibility.CONDITIONAL,
    ),
    "realized_vol_percentile": (
        "volatility_context",
        CompositeRole.DIAGNOSTIC_CONTEXT,
        CompositeEligibility.DIAGNOSTIC_ONLY,
    ),
    "efficiency_ratio_trend": (
        "trend_breakout",
        CompositeRole.CANDIDATE_SIGNAL,
        CompositeEligibility.ELIGIBLE,
    ),
}

STEP11_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "composite_score",
        "family_weighted_score",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "alpha_signal",
        "recommendation",
        "fundamental_score",
        "valuation_score",
    }
)
STEP11_FORBIDDEN_PREFIXES = (
    "forward_return",
    "future_return",
    "next_period_return",
    "backtest_",
)
STEP11_FORBIDDEN_SUFFIXES = (
    "_rank",
    "_ranking",
    "_signal",
)
VALUATION_FIELD_TOKENS = frozenset(
    {
        "per",
        "pbr",
        "roe",
        "eps",
        "bps",
        "book",
        "earnings",
        "revenue",
        "sales",
        "income",
        "financial",
        "fundamental",
        "valuation",
    }
)
PRODUCTION_DISABLED_REGISTRY_FLAGS = (
    "ranking_generation_enabled",
    "composite_scoring_enabled",
    "backtest_enabled",
    "valuation_branch_enabled",
    "runtime_enabled",
)
ROOT_DISABLED_STATUS_FLAGS = (
    "active_composite_score",
    "active_valuation_scores",
    "active_fundamental_scores",
)


def find_forbidden_step11_output_columns(columns: Iterable[str]) -> list[str]:
    """Return columns Step 11 must not emit or accept as composite outputs."""

    forbidden: list[str] = []
    for column in columns:
        normalized = column.lower()
        if (
            normalized in STEP11_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP11_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP11_FORBIDDEN_SUFFIXES)
            or normalized.startswith("latest_rank")
        ):
            forbidden.append(column)
    return forbidden


def assert_no_forbidden_step11_output_columns(
    frame: pd.DataFrame,
    *,
    context: str = "Step 11 composite schema",
) -> None:
    forbidden = find_forbidden_step11_output_columns(frame.columns)
    if forbidden:
        raise ValueError(f"{context} contains forbidden Step 11 output columns: {', '.join(forbidden)}")


def find_registry_valuation_fundamental_columns(
    registry: Sequence[CompositeInputSpec],
) -> list[str]:
    flagged: list[str] = []
    names = []
    for spec in registry:
        names.extend([spec.score_name, spec.raw_column, spec.normalized_column])
    flagged.extend(find_valuation_fundamental_columns(names))
    for name in names:
        normalized = name.lower()
        tokens = normalized.split("_")
        if any(token in VALUATION_FIELD_TOKENS for token in tokens):
            flagged.append(name)
    return sorted(set(flagged))


def validate_composite_input_registry(
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> None:
    """Validate the Step 11 registry without adopting or calculating scores."""

    names = tuple(spec.score_name for spec in registry)
    if len(names) != len(set(names)):
        raise ValueError("Composite registry contains duplicate score names.")
    if set(names) != set(MVP_SCORE_NAMES):
        raise ValueError("Composite registry must contain only the eight Step 9 MVP scores.")
    if names != MVP_SCORE_NAMES:
        raise ValueError("Composite registry order must match the locked Step 9 MVP score order.")

    valuation_columns = find_registry_valuation_fundamental_columns(registry)
    if valuation_columns:
        raise ValueError(
            "Composite registry contains valuation/fundamental columns: "
            f"{', '.join(valuation_columns)}"
        )

    for spec in registry:
        if spec.family not in ALLOWED_COMPOSITE_FAMILIES:
            raise ValueError(f"{spec.score_name} has unsupported composite family: {spec.family}")
        if spec.branch not in ALLOWED_SCORE_BRANCHES:
            raise ValueError(f"{spec.score_name} has unsupported branch: {spec.branch}")
        if (
            spec.score_name in CONTEXT_OR_DIAGNOSTIC_SCORE_NAMES
            and spec.role is CompositeRole.CANDIDATE_SIGNAL
        ):
            raise ValueError(
                f"{spec.score_name} is diagnostic/context-only and cannot be candidate_signal."
            )
        if spec.branch == "diagnostic" and spec.role is CompositeRole.CANDIDATE_SIGNAL:
            raise ValueError(f"{spec.score_name} diagnostic branch cannot be candidate_signal.")
        if (
            spec.eligibility is CompositeEligibility.DIAGNOSTIC_ONLY
            and spec.role is not CompositeRole.DIAGNOSTIC_CONTEXT
        ):
            raise ValueError(f"{spec.score_name} diagnostic_only eligibility requires diagnostic_context role.")
        expected = EXPECTED_COMPOSITE_POLICY[spec.score_name]
        observed = (spec.family, spec.role, spec.eligibility)
        if observed != expected:
            raise ValueError(
                f"{spec.score_name} does not match Step 11 family/role/eligibility policy."
            )


def candidate_signal_specs(
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> tuple[CompositeInputSpec, ...]:
    """Return direct future-composite candidates after registry validation."""

    validate_composite_input_registry(registry)
    return tuple(
        spec
        for spec in registry
        if spec.role is CompositeRole.CANDIDATE_SIGNAL
        and spec.eligibility in {CompositeEligibility.ELIGIBLE, CompositeEligibility.CONDITIONAL}
    )


def validate_normalized_score_columns(
    frame: pd.DataFrame,
    *,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    status_contract: StatusPropagationContract = DEFAULT_STATUS_PROPAGATION_CONTRACT,
    context: str = "Step 11 normalized score input",
) -> None:
    """Validate Step 10 normalized columns for future composite use.

    This checks identity, source metadata, per-score normalized metadata, and
    forbidden-output boundaries. It intentionally returns no score values.
    """

    validate_composite_input_registry(registry)
    assert_no_forbidden_step11_output_columns(frame, context=context)
    _assert_no_valuation_fundamental_frame_columns(frame, context=context)
    require_columns(frame, IDENTITY_COLUMNS, context=context)
    require_columns(frame, status_contract.source_metadata_columns, context=context)

    missing_required: list[str] = []
    for spec in registry:
        missing_required.extend(
            column for column in spec.required_columns if column not in frame.columns
        )
    if missing_required:
        raise ValueError(
            f"{context} missing normalized registry columns: "
            f"{', '.join(dict.fromkeys(missing_required))}"
        )

    _assert_unique_ticker_date(frame, context=context)
    _assert_status_metadata_visible(frame, registry, status_contract, context=context)


def assert_ticker_date_identity_unchanged(
    source_frame: pd.DataFrame,
    candidate_frame: pd.DataFrame,
    *,
    context: str = "Step 11 identity contract",
) -> None:
    """Ensure downstream candidate data did not reorder or mutate identity keys."""

    require_columns(source_frame, IDENTITY_COLUMNS, context=f"{context} source")
    require_columns(candidate_frame, IDENTITY_COLUMNS, context=f"{context} candidate")
    left = source_frame.loc[:, list(IDENTITY_COLUMNS)].reset_index(drop=True)
    right = candidate_frame.loc[:, list(IDENTITY_COLUMNS)].reset_index(drop=True)
    if not left.equals(right):
        raise ValueError(f"{context} ticker/date identity changed.")


def validate_step11_config_flags(
    *,
    quant_scores_config: str | Path | Mapping[str, object] = "Quant_mvp/config/scores.toml",
    root_scores_config: str | Path | Mapping[str, object] = "config/scores.toml",
) -> None:
    """Validate that Step 11 does not enable production runtime flags."""

    quant_config = _load_config(quant_scores_config)
    root_config = _load_config(root_scores_config)

    registry_status = _mapping(quant_config.get("registry_status", {}))
    enabled_flags = [
        key for key in PRODUCTION_DISABLED_REGISTRY_FLAGS if bool(registry_status.get(key))
    ]
    if enabled_flags:
        raise ValueError(f"Step 11 production flags must remain disabled: {', '.join(enabled_flags)}")

    score_entries = quant_config.get("scores", [])
    if isinstance(score_entries, list):
        enabled_runtime_scores = [
            str(entry.get("score_id") or entry.get("name") or "<unknown>")
            for entry in score_entries
            if isinstance(entry, Mapping) and bool(entry.get("runtime_enabled"))
        ]
        if enabled_runtime_scores:
            raise ValueError(
                "Step 11 score runtime_enabled flags must remain false: "
                f"{', '.join(enabled_runtime_scores)}"
            )

    root_status = _mapping(root_config.get("status", {}))
    enabled_root_status = [
        key for key in ROOT_DISABLED_STATUS_FLAGS if bool(root_status.get(key))
    ]
    if enabled_root_status:
        raise ValueError(
            "Root score runtime status flags must remain disabled: "
            f"{', '.join(enabled_root_status)}"
        )

    composite = _mapping(root_config.get("composite", {}))
    if bool(composite.get("enabled")) or bool(composite.get("implemented")):
        raise ValueError("Root composite enabled/implemented flags must remain false.")


def _assert_no_valuation_fundamental_frame_columns(
    frame: pd.DataFrame,
    *,
    context: str,
) -> None:
    flagged = set(find_valuation_fundamental_columns(frame.columns))
    for column in frame.columns:
        tokens = column.lower().split("_")
        if any(token in VALUATION_FIELD_TOKENS for token in tokens):
            flagged.add(column)
    if flagged:
        raise ValueError(
            f"{context} contains valuation/fundamental columns not allowed in composite inputs: "
            f"{', '.join(sorted(flagged))}"
        )


def _assert_unique_ticker_date(frame: pd.DataFrame, *, context: str) -> None:
    if frame.duplicated(list(IDENTITY_COLUMNS)).any():
        raise ValueError(f"{context} contains duplicate ticker/date rows.")


def _assert_status_metadata_visible(
    frame: pd.DataFrame,
    registry: Sequence[CompositeInputSpec],
    status_contract: StatusPropagationContract,
    *,
    context: str,
) -> None:
    for column in status_contract.source_metadata_columns:
        if frame[column].isna().all():
            raise ValueError(f"{context} must preserve non-empty metadata column: {column}")
    for spec in registry:
        for column in (spec.status_column, spec.quality_flag_column, spec.count_column):
            if frame[column].isna().all():
                raise ValueError(f"{context} must preserve non-empty Step 10 metadata: {column}")


def _load_config(config: str | Path | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(config, Mapping):
        return config
    path = Path(config)
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


__all__ = (
    "PRODUCTION_DISABLED_REGISTRY_FLAGS",
    "ROOT_DISABLED_STATUS_FLAGS",
    "ALLOWED_COMPOSITE_FAMILIES",
    "EXPECTED_COMPOSITE_POLICY",
    "STEP11_FORBIDDEN_EXACT_COLUMNS",
    "assert_no_forbidden_step11_output_columns",
    "assert_ticker_date_identity_unchanged",
    "candidate_signal_specs",
    "find_forbidden_step11_output_columns",
    "find_registry_valuation_fundamental_columns",
    "validate_composite_input_registry",
    "validate_normalized_score_columns",
    "validate_step11_config_flags",
)
