"""Step 15 latest ranking output builder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeInputSpec,
)
from src.scanner.latest_ranking_policy import (
    DEFAULT_STEP15_RANKING_POLICY,
    STEP15_BLOCKING_ROW_COVERAGE_STATUSES,
    Step15CoverageStatus,
    Step15RankingPolicy,
    Step15ValidityFlag,
)
from src.scanner.latest_ranking_validation import (
    validate_step15_inputs,
    validate_step15_latest_ranking_output,
)
from src.scores.schema import IDENTITY_COLUMNS


def build_latest_ranking_output(
    normalized_scores: pd.DataFrame,
    adoption_synthesis: pd.DataFrame,
    *,
    as_of_date: object | None = None,
    max_allowed_date: object | None = None,
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

    latest_frame = _latest_date_frame(
        normalized_frame,
        as_of_date=as_of_date,
        max_allowed_date=max_allowed_date,
    )
    latest_frame["ticker"] = latest_frame["ticker"].map(policy.symbol_policy.normalize)
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
        working[family_column] = (
            working[score_columns].fillna(policy.neutral_score_value).mean(axis=1)
        )

    valid_score_count = _valid_score_count(valid_masks, index=working.index)
    expected_score_count = len(ranking_specs)
    coverage_metric = valid_score_count / float(expected_score_count)

    working["technical_composite_score"] = working[family_columns].mean(axis=1, skipna=True)
    blocked = valid_score_count < policy.minimum_valid_score_count
    working.loc[blocked, "technical_composite_score"] = np.nan
    working["final_composite_score"] = working["technical_composite_score"]
    working["coverage_metric"] = coverage_metric
    working["warmup_status"] = _source_warmup_status(latest_frame)
    working["coverage_status"] = _coverage_status(
        valid_score_count,
        expected_score_count=expected_score_count,
    )
    working["ranking_validity_flag"] = _validity_flag(working["coverage_status"])
    working["data_quality_flag"] = working["ranking_validity_flag"]
    working["valid_score_count"] = valid_score_count.astype("int64")
    working["expected_score_count"] = expected_score_count
    working["neutral_shrinkage_count"] = (
        expected_score_count - valid_score_count
    ).astype("int64")
    working["review_routed_score_count"] = review_routed_score_count
    working["final_score_policy"] = policy.final_score_policy
    working["technical_only_notice"] = policy.technical_only_notice

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
    validate_step15_latest_ranking_output(output, policy=policy)
    return output


def _latest_date_frame(
    frame: pd.DataFrame,
    *,
    as_of_date: object | None,
    max_allowed_date: object | None,
) -> pd.DataFrame:
    date_key = pd.to_datetime(frame["date"], errors="raise")
    max_allowed = (
        pd.Timestamp.today().normalize()
        if max_allowed_date is None
        else pd.to_datetime(max_allowed_date, errors="raise").normalize()
    )
    future_dates = date_key.dt.normalize().gt(max_allowed)
    if future_dates.any():
        raise ValueError(
            "Step 15 normalized input contains future dates beyond max_allowed_date."
        )
    selected_date = (
        pd.to_datetime(as_of_date, errors="raise")
        if as_of_date is not None
        else date_key.max()
    )
    if selected_date.normalize() > max_allowed:
        raise ValueError("Step 15 as_of_date cannot be in the future.")
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


def _source_warmup_status(frame: pd.DataFrame) -> pd.Series:
    warmup = _normalized_status(frame["score_warmup_state"])
    return pd.Series(
        np.where(warmup.eq("ready"), "ready", "blocked"),
        index=frame.index,
        dtype="string",
    )


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
        "rank",
        "technical_composite_score",
        "final_composite_score",
        "coverage_metric",
        "data_quality_flag",
        "warmup_status",
        *score_columns,
        *family_columns,
        "coverage_status",
        "ranking_validity_flag",
        "valid_score_count",
        "expected_score_count",
        "neutral_shrinkage_count",
        "review_routed_score_count",
        "final_score_policy",
        "technical_only_notice",
    )


def _normalized_status(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def _finite_mask(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return pd.Series(np.isfinite(numeric), index=values.index)


__all__ = ("build_latest_ranking_output",)
