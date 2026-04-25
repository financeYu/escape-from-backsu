"""Step 15 latest ranking output core.

This module consumes Step 14 adoption synthesis material and Step 10
cross-sectional normalized technical scores to build an in-memory latest
ranking table. It does not write runtime reports, run backtests, use future
returns, create trading signals, or use valuation/fundamental data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeInputSpec,
)
from src.composite.schema import validate_normalized_score_columns
from src.scores.schema import (
    IDENTITY_COLUMNS,
    find_valuation_fundamental_columns,
    require_columns,
)
from src.selection.adoption_synthesis_contracts import (
    Step14AdoptionState,
    validate_adoption_synthesis_table,
)


STEP15_LATEST_RANKING_NOTICE = "latest ranking output material only"

STEP15_DIRECT_RANKING_STATES = frozenset(
    {
        Step14AdoptionState.CORE_ADOPTED.value,
        Step14AdoptionState.TECHNICAL_ONLY.value,
    }
)

STEP15_BASE_OUTPUT_COLUMNS: tuple[str, ...] = (
    "ticker",
    "date",
    "technical_composite_score",
    "final_composite_score",
    "rank",
    "coverage_metric",
    "coverage_status",
    "ranking_validity_flag",
    "valid_score_count",
    "expected_score_count",
    "review_routed_score_count",
    "final_score_policy",
)

STEP15_ALLOWED_COVERAGE_STATUSES = frozenset({"adequate", "partial", "blocked"})
STEP15_ALLOWED_VALIDITY_FLAGS = frozenset({"valid", "partial", "blocked"})

STEP15_BLOCKING_ROW_COVERAGE_STATUSES = frozenset(
    {
        "blocked",
        "blocked_by_data",
        "insufficient_input",
        "insufficient_data",
    }
)

STEP15_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "alpha",
        "alpha_label",
        "signal",
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "trading_signal",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "per",
        "pbr",
        "roe",
    }
)

STEP15_FORBIDDEN_PREFIXES = (
    "forward_return",
    "future_return",
    "next_return",
    "next_period_return",
    "backtest_",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "trading_signal",
    "valuation_",
    "fundamental_",
    "target_price",
    "expected_return",
    "position_size",
    "financial_",
)

STEP15_FORBIDDEN_SUFFIXES = (
    "_alpha",
    "_signal",
    "_buy",
    "_sell",
    "_target_price",
    "_expected_return",
    "_position_size",
)


class Step15CoverageStatus(str, Enum):
    """Coverage status for the Step 15 direct ranking inputs."""

    ADEQUATE = "adequate"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class Step15ValidityFlag(str, Enum):
    """Ranking row validity flag; not a trading signal."""

    VALID = "valid"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Step15RankingPolicy:
    """Small deterministic policy for Step 15 in-memory ranking construction."""

    direct_ranking_states: frozenset[str] = STEP15_DIRECT_RANKING_STATES
    minimum_valid_score_count: int = 1
    final_score_policy: str = "technical_only_no_valuation"

    def __post_init__(self) -> None:
        if self.minimum_valid_score_count < 1:
            raise ValueError("Step 15 minimum_valid_score_count must be at least 1.")


DEFAULT_STEP15_RANKING_POLICY = Step15RankingPolicy()


def build_latest_ranking_output(
    normalized_scores: pd.DataFrame,
    adoption_synthesis: pd.DataFrame,
    *,
    as_of_date: object | None = None,
    top_n: int | None = None,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    policy: Step15RankingPolicy = DEFAULT_STEP15_RANKING_POLICY,
) -> pd.DataFrame:
    """Build a deterministic Step 15 latest ranking output table.

    The output is sorted by `final_composite_score` descending and `ticker`
    ascending. Conditional, diagnostic, research-only, rejected, blocked, or
    manual-review rows from Step 14 are excluded from direct scoring and counted
    in `review_routed_score_count`.
    """

    normalized_frame = normalized_scores.copy()
    adoption_frame = adoption_synthesis.copy()
    validate_step15_inputs(
        normalized_frame,
        adoption_frame,
        registry=registry,
        policy=policy,
    )

    latest_frame = _latest_date_frame(normalized_frame, as_of_date=as_of_date)
    ranking_specs, review_routed_score_count = _direct_ranking_specs(
        adoption_frame,
        registry=registry,
        policy=policy,
    )
    if not ranking_specs:
        raise ValueError(
            "Step 15 ranking requires at least one direct technical adoption "
            "state without manual review."
        )

    working = latest_frame.loc[:, list(IDENTITY_COLUMNS)].copy()
    valid_masks: dict[str, pd.Series] = {}
    for spec in ranking_specs:
        values = pd.to_numeric(latest_frame[spec.normalized_column], errors="coerce")
        score_mask = _valid_score_mask(latest_frame, spec, values)
        valid_masks[spec.score_name] = score_mask
        working[spec.normalized_column] = values.where(score_mask)

    family_columns: list[str] = []
    for family in _families_in_registry_order(ranking_specs):
        family_specs = tuple(spec for spec in ranking_specs if spec.family == family)
        family_column = f"{family}_family_score"
        family_columns.append(family_column)
        score_columns = [spec.normalized_column for spec in family_specs]
        working[family_column] = working[score_columns].mean(axis=1, skipna=True)

    valid_score_count = _valid_score_count(valid_masks, index=working.index)
    expected_score_count = len(ranking_specs)
    coverage_metric = valid_score_count / float(expected_score_count)

    working["technical_composite_score"] = working[family_columns].mean(axis=1, skipna=True)
    blocked = valid_score_count < policy.minimum_valid_score_count
    working.loc[blocked, "technical_composite_score"] = np.nan
    working["final_composite_score"] = working["technical_composite_score"]
    working["coverage_metric"] = coverage_metric
    working["coverage_status"] = _coverage_status(
        valid_score_count,
        expected_score_count=expected_score_count,
    )
    working["ranking_validity_flag"] = _validity_flag(working["coverage_status"])
    working["valid_score_count"] = valid_score_count.astype("int64")
    working["expected_score_count"] = expected_score_count
    working["review_routed_score_count"] = review_routed_score_count
    working["final_score_policy"] = policy.final_score_policy

    output = _sort_and_rank(working)
    ordered_columns = _ordered_output_columns(
        ranking_specs=ranking_specs,
        family_columns=family_columns,
    )
    output = output.loc[:, ordered_columns]
    if top_n is not None:
        if top_n < 1:
            raise ValueError("Step 15 top_n must be at least 1 when provided.")
        output = output.head(top_n).reset_index(drop=True)
    validate_step15_latest_ranking_output(output)
    return output


def validate_step15_inputs(
    normalized_scores: pd.DataFrame,
    adoption_synthesis: pd.DataFrame,
    *,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    policy: Step15RankingPolicy = DEFAULT_STEP15_RANKING_POLICY,
) -> None:
    """Validate Step 15 inputs before any ranking calculation."""

    assert_no_forbidden_step15_columns(
        normalized_scores.columns,
        context="Step 15 normalized input",
    )
    validate_normalized_score_columns(
        normalized_scores,
        registry=registry,
        context="Step 15 normalized input",
    )
    validate_adoption_synthesis_table(
        adoption_synthesis,
        registry=registry,
        require_all_scores=True,
        context="Step 15 adoption synthesis input",
    )
    invalid_states = sorted(
        set(policy.direct_ranking_states).difference(STEP15_DIRECT_RANKING_STATES)
    )
    if invalid_states:
        raise ValueError(
            "Step 15 direct_ranking_states may only include conservative direct "
            f"technical states: {', '.join(invalid_states)}"
        )


def validate_step15_latest_ranking_output(frame: pd.DataFrame) -> None:
    """Validate Step 15 latest ranking output boundaries."""

    require_columns(frame, STEP15_BASE_OUTPUT_COLUMNS, context="Step 15 latest ranking output")
    assert_no_forbidden_step15_columns(frame.columns, context="Step 15 latest ranking output")
    _assert_single_latest_date(frame)
    _assert_unique_ticker_date(frame)
    _assert_allowed_output_status_values(frame)
    _assert_rank_order(frame)


def find_forbidden_step15_columns(
    columns: Iterable[str],
) -> list[str]:
    """Return forbidden Step 15 columns."""

    forbidden: set[str] = set(find_valuation_fundamental_columns(columns))
    for column in columns:
        normalized = str(column).lower()
        if (
            normalized in STEP15_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP15_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP15_FORBIDDEN_SUFFIXES)
        ):
            forbidden.add(str(column))
    return sorted(forbidden)


def assert_no_forbidden_step15_columns(
    columns: Iterable[str],
    *,
    context: str = "Step 15 output",
) -> None:
    """Reject Step 15 columns that imply leakage, trading, or valuation."""

    forbidden = find_forbidden_step15_columns(columns)
    if forbidden:
        raise ValueError(f"{context} contains forbidden Step 15 columns: {', '.join(forbidden)}")


def _latest_date_frame(frame: pd.DataFrame, *, as_of_date: object | None) -> pd.DataFrame:
    date_key = pd.to_datetime(frame["date"], errors="raise")
    selected_date = (
        pd.to_datetime(as_of_date, errors="raise")
        if as_of_date is not None
        else date_key.max()
    )
    mask = date_key.eq(selected_date)
    if not mask.any():
        raise ValueError(
            "Step 15 as_of_date is not present in normalized input: "
            f"{selected_date.date()}"
        )
    latest = frame.loc[mask].copy()
    if latest.empty:
        raise ValueError("Step 15 normalized input has no rows for the selected latest date.")
    return latest.reset_index(drop=True)


def _direct_ranking_specs(
    adoption_frame: pd.DataFrame,
    *,
    registry: Sequence[CompositeInputSpec],
    policy: Step15RankingPolicy,
) -> tuple[tuple[CompositeInputSpec, ...], int]:
    by_name = {spec.score_name: spec for spec in registry}
    adoption_by_score = adoption_frame.set_index("score_name", drop=False)
    selected: list[CompositeInputSpec] = []
    review_routed = 0
    for spec in registry:
        row = adoption_by_score.loc[spec.score_name]
        adoption_state = str(row["adoption_state"])
        manual_review_required = bool(row["manual_review_required"])
        direct_role = (
            str(row["branch"]) == "technical"
            and str(row["role"]) == "candidate_signal"
            and str(row["eligibility"]) == "eligible"
        )
        if (
            spec.score_name in by_name
            and adoption_state in policy.direct_ranking_states
            and not manual_review_required
            and direct_role
        ):
            selected.append(spec)
        else:
            review_routed += 1
    return tuple(selected), review_routed


def _valid_score_mask(
    frame: pd.DataFrame,
    spec: CompositeInputSpec,
    values: pd.Series,
) -> pd.Series:
    base_valid = (
        _normalized_status(frame["score_warmup_state"]).eq("ready")
        & ~_normalized_status(frame["score_coverage_status"]).isin(
            STEP15_BLOCKING_ROW_COVERAGE_STATUSES
        )
        & _normalized_status(frame["score_data_quality_flag"]).eq("valid")
    )
    score_valid = (
        _normalized_status(frame[spec.status_column]).eq("adequate")
        & _normalized_status(frame[spec.quality_flag_column]).eq("valid")
        & _finite_mask(values)
    )
    return base_valid & score_valid


def _families_in_registry_order(specs: Sequence[CompositeInputSpec]) -> tuple[str, ...]:
    families: list[str] = []
    for spec in specs:
        if spec.family not in families:
            families.append(spec.family)
    return tuple(families)


def _valid_score_count(
    valid_masks: Mapping[str, pd.Series],
    *,
    index: pd.Index,
) -> pd.Series:
    if not valid_masks:
        return pd.Series(0, index=index, dtype="int64")
    counts = pd.DataFrame(valid_masks).sum(axis=1)
    return counts.reindex(index).fillna(0).astype("int64")


def _coverage_status(
    valid_score_count: pd.Series,
    *,
    expected_score_count: int,
) -> pd.Series:
    statuses = np.select(
        [
            valid_score_count.eq(expected_score_count),
            valid_score_count.gt(0),
        ],
        [
            Step15CoverageStatus.ADEQUATE.value,
            Step15CoverageStatus.PARTIAL.value,
        ],
        default=Step15CoverageStatus.BLOCKED.value,
    )
    return pd.Series(statuses, index=valid_score_count.index, dtype="string")


def _validity_flag(coverage_status: pd.Series) -> pd.Series:
    mapping = {
        Step15CoverageStatus.ADEQUATE.value: Step15ValidityFlag.VALID.value,
        Step15CoverageStatus.PARTIAL.value: Step15ValidityFlag.PARTIAL.value,
        Step15CoverageStatus.BLOCKED.value: Step15ValidityFlag.BLOCKED.value,
    }
    return coverage_status.map(mapping).astype("string")


def _sort_and_rank(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.sort_values(
        by=["final_composite_score", "ticker"],
        ascending=[False, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    valid = output["final_composite_score"].notna()
    ranks = pd.Series(pd.NA, index=output.index, dtype="Int64")
    ranks.loc[valid] = range(1, int(valid.sum()) + 1)
    output["rank"] = ranks
    return output


def _ordered_output_columns(
    *,
    ranking_specs: Sequence[CompositeInputSpec],
    family_columns: Sequence[str],
) -> tuple[str, ...]:
    score_columns = tuple(spec.normalized_column for spec in ranking_specs)
    return (
        "ticker",
        "date",
        *score_columns,
        *family_columns,
        "technical_composite_score",
        "final_composite_score",
        "rank",
        "coverage_metric",
        "coverage_status",
        "ranking_validity_flag",
        "valid_score_count",
        "expected_score_count",
        "review_routed_score_count",
        "final_score_policy",
    )


def _assert_single_latest_date(frame: pd.DataFrame) -> None:
    dates = pd.to_datetime(frame["date"], errors="raise")
    if dates.nunique(dropna=False) != 1:
        raise ValueError("Step 15 latest ranking output must contain one latest date.")


def _assert_unique_ticker_date(frame: pd.DataFrame) -> None:
    duplicate_keys = frame.duplicated(list(IDENTITY_COLUMNS))
    if duplicate_keys.any():
        raise ValueError("Step 15 latest ranking output contains duplicate ticker/date rows.")


def _assert_allowed_output_status_values(frame: pd.DataFrame) -> None:
    invalid_coverage = sorted(
        set(frame["coverage_status"].astype("string")).difference(
            STEP15_ALLOWED_COVERAGE_STATUSES
        )
    )
    if invalid_coverage:
        raise ValueError(
            "Step 15 latest ranking output contains unsupported coverage_status "
            f"values: {', '.join(invalid_coverage)}"
        )
    invalid_flags = sorted(
        set(frame["ranking_validity_flag"].astype("string")).difference(
            STEP15_ALLOWED_VALIDITY_FLAGS
        )
    )
    if invalid_flags:
        raise ValueError(
            "Step 15 latest ranking output contains unsupported ranking_validity_flag "
            f"values: {', '.join(invalid_flags)}"
        )


def _assert_rank_order(frame: pd.DataFrame) -> None:
    scores = frame["final_composite_score"]
    ranks = frame["rank"]
    valid = scores.notna()
    if valid.any():
        expected_ranks = list(range(1, int(valid.sum()) + 1))
        observed_ranks = [int(value) for value in ranks.loc[valid].tolist()]
        if observed_ranks != expected_ranks:
            raise ValueError("Step 15 rank values must be consecutive for rankable rows.")
        ordered = frame.loc[valid, "final_composite_score"].tolist()
        if ordered != sorted(ordered, reverse=True):
            raise ValueError(
                "Step 15 latest ranking output is not sorted by final_composite_score."
            )
    if ranks.loc[~valid].notna().any():
        raise ValueError("Step 15 blocked rows must not receive rank values.")


def _normalized_status(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def _finite_mask(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return pd.Series(np.isfinite(numeric), index=values.index)


__all__ = (
    "DEFAULT_STEP15_RANKING_POLICY",
    "STEP15_BASE_OUTPUT_COLUMNS",
    "STEP15_DIRECT_RANKING_STATES",
    "STEP15_LATEST_RANKING_NOTICE",
    "Step15CoverageStatus",
    "Step15RankingPolicy",
    "Step15ValidityFlag",
    "assert_no_forbidden_step15_columns",
    "build_latest_ranking_output",
    "find_forbidden_step15_columns",
    "validate_step15_inputs",
    "validate_step15_latest_ranking_output",
)
