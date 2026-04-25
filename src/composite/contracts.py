"""Step 11 composite score contracts.

This module defines schema metadata for later composite design validation. It
does not calculate composite scores, rankings, trading signals, forward
returns, valuation scores, or backtest labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.scores.schema import SCORE_METADATA_COLUMNS


class CompositeEligibility(str, Enum):
    """How a normalized score may be treated by a future composite design."""

    ELIGIBLE = "eligible"
    CONDITIONAL = "conditional"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    BLOCKED = "blocked"


class CompositeRole(str, Enum):
    """Step 11 role labels from the composite design document."""

    CANDIDATE_SIGNAL = "candidate_signal"
    CONFIRMATION = "confirmation"
    SETUP_CONTEXT = "setup_context"
    DIAGNOSTIC_CONTEXT = "diagnostic_context"


class NormalizationScope(str, Enum):
    CROSS_SECTIONAL = "cross_sectional"
    TIME_SERIES = "time_series"


MVP_SCORE_NAMES: tuple[str, ...] = (
    "short_term_overreaction",
    "atr_adjusted_oversold_distance",
    "donchian_breakout_distance",
    "bollinger_width_squeeze",
    "cmf_confirmation",
    "rsi_price_divergence",
    "realized_vol_percentile",
    "efficiency_ratio_trend",
)

CONTEXT_OR_DIAGNOSTIC_SCORE_NAMES = frozenset(
    {
        "bollinger_width_squeeze",
        "cmf_confirmation",
        "realized_vol_percentile",
    }
)

DIRECT_CANDIDATE_SCORE_NAMES = frozenset(
    score_name
    for score_name in MVP_SCORE_NAMES
    if score_name not in CONTEXT_OR_DIAGNOSTIC_SCORE_NAMES
)


@dataclass(frozen=True)
class StatusPropagationContract:
    """Columns Step 11 must preserve from Step 9/10 inputs."""

    source_metadata_columns: tuple[str, ...] = SCORE_METADATA_COLUMNS
    cross_sectional_status_suffixes: tuple[str, ...] = (
        "status",
        "quality_flag",
        "valid_count",
    )


DEFAULT_STATUS_PROPAGATION_CONTRACT = StatusPropagationContract()


@dataclass(frozen=True)
class CompositeInputSpec:
    """A normalized Step 10 column candidate for future composite design."""

    score_name: str
    raw_column: str
    family: str
    branch: str
    role: CompositeRole
    eligibility: CompositeEligibility
    normalization_scope: NormalizationScope = NormalizationScope.CROSS_SECTIONAL

    @property
    def normalized_column(self) -> str:
        if self.normalization_scope is NormalizationScope.CROSS_SECTIONAL:
            return f"{self.score_name}_cross_sectional_robust_z"
        return f"{self.score_name}_ts_robust_zscore"

    @property
    def status_column(self) -> str:
        if self.normalization_scope is NormalizationScope.CROSS_SECTIONAL:
            return f"{self.score_name}_cross_sectional_status"
        return f"{self.score_name}_ts_status"

    @property
    def quality_flag_column(self) -> str:
        if self.normalization_scope is NormalizationScope.CROSS_SECTIONAL:
            return f"{self.score_name}_cross_sectional_quality_flag"
        return f"{self.score_name}_ts_data_quality_flag"

    @property
    def coverage_column(self) -> str:
        if self.normalization_scope is NormalizationScope.CROSS_SECTIONAL:
            return "score_coverage_status"
        return f"{self.score_name}_ts_coverage_status"

    @property
    def count_column(self) -> str:
        if self.normalization_scope is NormalizationScope.CROSS_SECTIONAL:
            return f"{self.score_name}_cross_sectional_valid_count"
        return f"{self.score_name}_ts_observation_count"

    @property
    def required_columns(self) -> tuple[str, ...]:
        return (
            self.raw_column,
            self.normalized_column,
            self.status_column,
            self.quality_flag_column,
            self.coverage_column,
            self.count_column,
        )


DEFAULT_COMPOSITE_INPUT_REGISTRY: tuple[CompositeInputSpec, ...] = (
    CompositeInputSpec(
        score_name="short_term_overreaction",
        raw_column="short_term_overreaction_raw",
        family="mean_reversion",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.ELIGIBLE,
    ),
    CompositeInputSpec(
        score_name="atr_adjusted_oversold_distance",
        raw_column="atr_adjusted_oversold_distance_raw",
        family="mean_reversion",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.CONDITIONAL,
    ),
    CompositeInputSpec(
        score_name="donchian_breakout_distance",
        raw_column="donchian_breakout_distance_raw",
        family="trend_breakout",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.ELIGIBLE,
    ),
    CompositeInputSpec(
        score_name="bollinger_width_squeeze",
        raw_column="bollinger_width_squeeze_raw",
        family="volatility_context",
        branch="technical",
        role=CompositeRole.SETUP_CONTEXT,
        eligibility=CompositeEligibility.CONDITIONAL,
    ),
    CompositeInputSpec(
        score_name="cmf_confirmation",
        raw_column="cmf_confirmation_raw",
        family="volume_flow",
        branch="technical",
        role=CompositeRole.CONFIRMATION,
        eligibility=CompositeEligibility.CONDITIONAL,
    ),
    CompositeInputSpec(
        score_name="rsi_price_divergence",
        raw_column="rsi_price_divergence_raw",
        family="mean_reversion",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.CONDITIONAL,
    ),
    CompositeInputSpec(
        score_name="realized_vol_percentile",
        raw_column="realized_vol_percentile_raw",
        family="volatility_context",
        branch="diagnostic",
        role=CompositeRole.DIAGNOSTIC_CONTEXT,
        eligibility=CompositeEligibility.DIAGNOSTIC_ONLY,
    ),
    CompositeInputSpec(
        score_name="efficiency_ratio_trend",
        raw_column="efficiency_ratio_trend_raw",
        family="trend_breakout",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.ELIGIBLE,
    ),
)


__all__ = (
    "CONTEXT_OR_DIAGNOSTIC_SCORE_NAMES",
    "DEFAULT_COMPOSITE_INPUT_REGISTRY",
    "DEFAULT_STATUS_PROPAGATION_CONTRACT",
    "DIRECT_CANDIDATE_SCORE_NAMES",
    "CompositeEligibility",
    "CompositeInputSpec",
    "CompositeRole",
    "MVP_SCORE_NAMES",
    "NormalizationScope",
    "StatusPropagationContract",
)
