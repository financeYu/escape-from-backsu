"""Step 15 latest ranking policy constants and small policy objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.selection.adoption_synthesis_contracts import Step14AdoptionState


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
    "rank",
    "technical_composite_score",
    "final_composite_score",
    "coverage_metric",
    "data_quality_flag",
    "warmup_status",
    "coverage_status",
    "ranking_validity_flag",
    "valid_score_count",
    "expected_score_count",
    "neutral_shrinkage_count",
    "review_routed_score_count",
    "final_score_policy",
    "technical_only_notice",
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
    neutral_score_value: float = 0.0
    technical_only_notice: str = "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation"

    def __post_init__(self) -> None:
        if self.minimum_valid_score_count < 1:
            raise ValueError("Step 15 minimum_valid_score_count must be at least 1.")


DEFAULT_STEP15_RANKING_POLICY = Step15RankingPolicy()


__all__ = (
    "DEFAULT_STEP15_RANKING_POLICY",
    "STEP15_ALLOWED_COVERAGE_STATUSES",
    "STEP15_ALLOWED_VALIDITY_FLAGS",
    "STEP15_BASE_OUTPUT_COLUMNS",
    "STEP15_BLOCKING_ROW_COVERAGE_STATUSES",
    "STEP15_DIRECT_RANKING_STATES",
    "STEP15_LATEST_RANKING_NOTICE",
    "Step15CoverageStatus",
    "Step15RankingPolicy",
    "Step15ValidityFlag",
)
