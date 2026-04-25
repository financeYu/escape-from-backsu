"""Step 13 technical selection review engine.

This module folds Step 11 composite input metadata and Step 12 diagnostic
material into score-level technical review recommendations. It does not create
rankings, composite scores, trading signals, forward-return labels, backtests,
or valuation/fundamental scores.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
import math

import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeEligibility,
    CompositeInputSpec,
    CompositeRole,
)
from src.composite.schema import validate_composite_input_registry
from src.diagnostics.diagnostic_contracts import (
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    Step12DiagnosticStatus,
    validate_step12_coverage_summary,
    validate_step12_pair_diagnostics,
)
from src.scores.schema import find_valuation_fundamental_columns, require_columns
from .technical_selection_contracts import (
    ALLOWED_STEP13_REVIEW_STATUSES,
    STEP13_FORBIDDEN_EXACT_COLUMNS,
    STEP13_FORBIDDEN_PREFIXES,
    STEP13_FORBIDDEN_SUBSTRINGS,
    STEP13_FORBIDDEN_SUFFIXES,
    find_forbidden_step13_output_columns as find_contract_forbidden_step13_output_columns,
    validate_step13_review_table as validate_contract_step13_review_table,
)


STEP13_REVIEW_MATERIAL_NOTICE = "technical selection review material only"

STEP13_REVIEW_TABLE_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "normalized_score_column",
    "score_input_column",
    "coverage_status",
    "redundancy_status",
    "strongest_redundant_peer",
    "max_abs_spearman",
    "complexity_status",
    "regime_fit_status",
    "review_status",
    "review_reason",
    "evidence_sources",
    "manual_review_required",
)


class TechnicalReviewStatus(str, Enum):
    """Step 13 technical recommendation vocabulary.

    These values are review recommendations for Step 14 material. They are not
    final adoption states.
    """

    ADOPT_CANDIDATE = "adopt_candidate"
    CONDITIONAL_CANDIDATE = "conditional_candidate"
    RESEARCH_ONLY = "research_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    REJECT_CANDIDATE = "reject_candidate"
    BLOCKED_BY_DATA = "blocked_by_data"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


ALLOWED_TECHNICAL_REVIEW_STATUSES = ALLOWED_STEP13_REVIEW_STATUSES
FORBIDDEN_STEP13_OUTPUT_COLUMNS = STEP13_FORBIDDEN_EXACT_COLUMNS
FORBIDDEN_STEP13_OUTPUT_PREFIXES = STEP13_FORBIDDEN_PREFIXES
FORBIDDEN_STEP13_OUTPUT_SUFFIXES = STEP13_FORBIDDEN_SUFFIXES
FORBIDDEN_STEP13_OUTPUT_SUBSTRINGS = STEP13_FORBIDDEN_SUBSTRINGS

DATA_BLOCKING_STATUSES = frozenset(
    {
        Step12DiagnosticStatus.INSUFFICIENT_INPUT.value,
        Step12DiagnosticStatus.INSUFFICIENT_DATA.value,
        Step12DiagnosticStatus.CONFIG_MISSING.value,
        "blocked_by_data",
    }
)
DIAGNOSTIC_UNCLEAR_STATUSES = frozenset(
    {
        Step12DiagnosticStatus.UNDEFINED_CORRELATION.value,
        "not_evaluated",
        "unknown",
    }
)
SEVERE_REDUNDANCY_STATUSES = frozenset(
    {
        Step12DiagnosticStatus.BLOCK_CANDIDATE.value,
        Step12DiagnosticStatus.SEVERE_REDUNDANCY.value,
        "severe_redundancy",
    }
)
WARN_REDUNDANCY_STATUSES = frozenset({Step12DiagnosticStatus.WARN.value})
OK_STATUSES = frozenset({Step12DiagnosticStatus.OK.value})

COMPLEXITY_STATUS_BY_SCORE: Mapping[str, str] = {
    "short_term_overreaction": "simple",
    "donchian_breakout_distance": "simple",
    "efficiency_ratio_trend": "simple",
    "realized_vol_percentile": "simple",
    "cmf_confirmation": "moderate",
    "atr_adjusted_oversold_distance": "moderate",
    "bollinger_width_squeeze": "moderate",
    "rsi_price_divergence": "complex",
}


def build_technical_selection_review(
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> pd.DataFrame:
    """Build the score-level Step 13 technical review table.

    The returned table is review material for Step 14 synthesis. It contains no
    scoring calculation, portfolio decision, or downstream runtime output.
    """

    validate_composite_input_registry(registry)
    _validate_step12_inputs(pair_diagnostics=pair_diagnostics, coverage_summary=coverage_summary)

    rows = [
        _build_technical_selection_review_row(
            spec,
            pair_diagnostics=pair_diagnostics,
            coverage_summary=coverage_summary,
        )
        for spec in registry
    ]

    output = pd.DataFrame(rows, columns=STEP13_REVIEW_TABLE_COLUMNS)
    validate_step13_review_table(output)
    return output


def _build_technical_selection_review_row(
    spec: CompositeInputSpec,
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
) -> dict[str, object]:
    evidence = summarize_score_review_evidence(
        spec.score_name,
        pair_diagnostics=pair_diagnostics,
        coverage_summary=coverage_summary,
    )
    review_status = classify_technical_review_status(
        eligibility=spec.eligibility.value,
        role=spec.role.value,
        coverage_status=str(evidence["coverage_status"]),
        redundancy_status=str(evidence["redundancy_status"]),
    )
    return {
        "score_name": spec.score_name,
        "family": spec.family,
        "branch": spec.branch,
        "role": spec.role.value,
        "eligibility": spec.eligibility.value,
        "normalized_score_column": spec.normalized_column,
        "score_input_column": spec.raw_column,
        "coverage_status": evidence["coverage_status"],
        "redundancy_status": evidence["redundancy_status"],
        "strongest_redundant_peer": evidence["strongest_redundant_peer"],
        "max_abs_spearman": evidence["max_abs_spearman"],
        "complexity_status": _complexity_status(spec),
        "regime_fit_status": _regime_fit_status(spec),
        "review_status": review_status.value,
        "review_reason": _review_reason(spec, review_status, evidence),
        "evidence_sources": evidence["evidence_sources"],
        "manual_review_required": _manual_review_required(review_status, evidence),
    }


def summarize_score_review_evidence(
    score_name: str,
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
) -> dict[str, object]:
    """Summarize Step 12 evidence for one score without making a final decision."""

    coverage_status = _coverage_status_for_score(score_name, coverage_summary)
    score_pairs = _pair_rows_for_score(score_name, pair_diagnostics)
    redundancy_status = _redundancy_status_for_score(score_pairs)
    strongest_peer, max_abs_spearman = _strongest_peer(score_name, score_pairs)
    sources = ["step11_registry"]
    if not coverage_summary.empty:
        sources.append("step12_coverage_summary")
    if not pair_diagnostics.empty:
        sources.append("step12_pair_diagnostics")
    return {
        "coverage_status": coverage_status,
        "redundancy_status": redundancy_status,
        "strongest_redundant_peer": strongest_peer,
        "max_abs_spearman": max_abs_spearman,
        "evidence_sources": ";".join(sources),
    }


def classify_technical_review_status(
    *,
    eligibility: str,
    role: str,
    coverage_status: str,
    redundancy_status: str,
) -> TechnicalReviewStatus:
    """Classify a score-level Step 13 technical recommendation conservatively."""

    eligibility_value = _enum_or_string_value(eligibility)
    role_value = _enum_or_string_value(role)
    coverage_value = _enum_or_string_value(coverage_status)
    redundancy_value = _enum_or_string_value(redundancy_status)

    if coverage_value in DATA_BLOCKING_STATUSES:
        return TechnicalReviewStatus.BLOCKED_BY_DATA
    if redundancy_value in DATA_BLOCKING_STATUSES or redundancy_value in DIAGNOSTIC_UNCLEAR_STATUSES:
        return TechnicalReviewStatus.NEEDS_MANUAL_REVIEW
    if eligibility_value == CompositeEligibility.BLOCKED.value:
        return TechnicalReviewStatus.BLOCKED_BY_DATA
    if (
        eligibility_value == CompositeEligibility.DIAGNOSTIC_ONLY.value
        or role_value == CompositeRole.DIAGNOSTIC_CONTEXT.value
    ):
        return TechnicalReviewStatus.DIAGNOSTIC_ONLY
    if role_value in {CompositeRole.CONFIRMATION.value, CompositeRole.SETUP_CONTEXT.value}:
        if redundancy_value in SEVERE_REDUNDANCY_STATUSES:
            return TechnicalReviewStatus.RESEARCH_ONLY
        return TechnicalReviewStatus.CONDITIONAL_CANDIDATE
    if redundancy_value in SEVERE_REDUNDANCY_STATUSES:
        return TechnicalReviewStatus.CONDITIONAL_CANDIDATE
    if redundancy_value in WARN_REDUNDANCY_STATUSES:
        return TechnicalReviewStatus.CONDITIONAL_CANDIDATE
    if (
        eligibility_value == CompositeEligibility.ELIGIBLE.value
        and coverage_value in OK_STATUSES
        and redundancy_value in OK_STATUSES
    ):
        return TechnicalReviewStatus.ADOPT_CANDIDATE
    if eligibility_value == CompositeEligibility.CONDITIONAL.value:
        return TechnicalReviewStatus.CONDITIONAL_CANDIDATE
    return TechnicalReviewStatus.NEEDS_MANUAL_REVIEW


def build_step13_review_bundle(
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> dict[str, pd.DataFrame]:
    """Build Step 13 review table plus compact status-count summaries."""

    review_table = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics,
        coverage_summary=coverage_summary,
        registry=registry,
    )
    status_counts = _count_frame(review_table, "review_status", "score_count")
    coverage_counts = _count_frame(review_table, "coverage_status", "score_count")
    redundancy_counts = _count_frame(review_table, "redundancy_status", "score_count")
    return {
        "review_table": review_table,
        "status_counts": status_counts,
        "coverage_counts": coverage_counts,
        "redundancy_counts": redundancy_counts,
    }


def find_forbidden_step13_output_columns(columns: Iterable[str]) -> list[str]:
    """Return output columns that cross Step 13 hard-stop boundaries."""

    return find_contract_forbidden_step13_output_columns(columns)


def assert_no_forbidden_step13_output_columns(
    frame: pd.DataFrame,
    *,
    context: str = "Step 13 technical selection review output",
) -> None:
    forbidden = find_forbidden_step13_output_columns(frame.columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 13 output columns: "
            f"{', '.join(forbidden)}"
        )


def validate_step13_review_table(
    frame: pd.DataFrame,
    *,
    context: str = "Step 13 technical selection review table",
) -> None:
    """Validate the generated score-level Step 13 review table."""

    require_columns(frame, STEP13_REVIEW_TABLE_COLUMNS, context=context)
    assert_no_forbidden_step13_output_columns(frame, context=context)
    invalid = sorted(set(frame["review_status"].astype("string")).difference(ALLOWED_TECHNICAL_REVIEW_STATUSES))
    if invalid:
        raise ValueError(f"{context} contains unsupported review_status values: {', '.join(invalid)}")
    _assert_no_valuation_fundamental_values(frame, context=context)
    validate_contract_step13_review_table(frame, require_all_scores=False, context=context)


def _validate_step12_inputs(*, pair_diagnostics: pd.DataFrame, coverage_summary: pd.DataFrame) -> None:
    require_columns(pair_diagnostics, STEP12_PAIR_DIAGNOSTIC_COLUMNS, context="Step 13 pair diagnostics input")
    require_columns(coverage_summary, STEP12_COVERAGE_SUMMARY_COLUMNS, context="Step 13 coverage summary input")
    validate_step12_pair_diagnostics(pair_diagnostics)
    validate_step12_coverage_summary(coverage_summary)


def _coverage_status_for_score(score_name: str, coverage_summary: pd.DataFrame) -> str:
    rows = coverage_summary[coverage_summary["score_name"].astype("string").eq(score_name)]
    if rows.empty:
        return Step12DiagnosticStatus.INSUFFICIENT_INPUT.value
    status = _worst_status(
        rows["diagnostic_status"],
        order=(
            Step12DiagnosticStatus.CONFIG_MISSING.value,
            Step12DiagnosticStatus.INSUFFICIENT_INPUT.value,
            Step12DiagnosticStatus.INSUFFICIENT_DATA.value,
            Step12DiagnosticStatus.UNDEFINED_CORRELATION.value,
            Step12DiagnosticStatus.WARN.value,
            Step12DiagnosticStatus.OK.value,
        ),
    )
    if status == Step12DiagnosticStatus.CONFIG_MISSING.value:
        return "blocked_by_data"
    if status == Step12DiagnosticStatus.UNDEFINED_CORRELATION.value:
        return "unknown"
    return status


def _pair_rows_for_score(score_name: str, pair_diagnostics: pd.DataFrame) -> pd.DataFrame:
    return pair_diagnostics[
        pair_diagnostics["score_left"].astype("string").eq(score_name)
        | pair_diagnostics["score_right"].astype("string").eq(score_name)
    ]


def _redundancy_status_for_score(score_pairs: pd.DataFrame) -> str:
    if score_pairs.empty:
        return "unknown"
    statuses = score_pairs["diagnostic_status"].astype("string").fillna("unknown")
    if statuses.isin(SEVERE_REDUNDANCY_STATUSES).any():
        return "severe_redundancy"
    return _worst_status(
        statuses,
        order=(
            Step12DiagnosticStatus.CONFIG_MISSING.value,
            Step12DiagnosticStatus.INSUFFICIENT_INPUT.value,
            Step12DiagnosticStatus.INSUFFICIENT_DATA.value,
            Step12DiagnosticStatus.UNDEFINED_CORRELATION.value,
            Step12DiagnosticStatus.WARN.value,
            Step12DiagnosticStatus.OK.value,
        ),
    )


def _strongest_peer(score_name: str, score_pairs: pd.DataFrame) -> tuple[str, object]:
    if score_pairs.empty:
        return "", pd.NA
    numeric = pd.to_numeric(score_pairs["abs_spearman_correlation"], errors="coerce")
    finite = numeric[numeric.map(_is_finite)]
    if finite.empty:
        row = score_pairs.iloc[0]
        return _peer_name(score_name, row), pd.NA
    index = finite.idxmax()
    row = score_pairs.loc[index]
    return _peer_name(score_name, row), float(numeric.loc[index])


def _peer_name(score_name: str, row: pd.Series) -> str:
    left = str(row["score_left"])
    right = str(row["score_right"])
    return right if left == score_name else left


def _worst_status(values: Iterable[object], *, order: Sequence[str]) -> str:
    observed = {_enum_or_string_value(value) for value in values if not pd.isna(value)}
    for status in order:
        if status in observed:
            return status
    return "unknown"


def _complexity_status(spec: CompositeInputSpec) -> str:
    return COMPLEXITY_STATUS_BY_SCORE.get(spec.score_name, "unknown")


def _regime_fit_status(spec: CompositeInputSpec) -> str:
    if spec.role is CompositeRole.DIAGNOSTIC_CONTEXT:
        return "diagnostic_context"
    if spec.role is CompositeRole.SETUP_CONTEXT:
        return "regime_specific"
    if spec.role is CompositeRole.CONFIRMATION:
        return "regime_specific"
    if spec.family in {"mean_reversion", "trend_breakout"}:
        return "broad"
    return "unknown"


def _review_reason(
    spec: CompositeInputSpec,
    status: TechnicalReviewStatus,
    evidence: Mapping[str, object],
) -> str:
    coverage_status = str(evidence["coverage_status"])
    redundancy_status = str(evidence["redundancy_status"])
    peer = str(evidence["strongest_redundant_peer"] or "")

    if status is TechnicalReviewStatus.BLOCKED_BY_DATA:
        return f"blocked because required Step 12 data status is {coverage_status}"
    if status is TechnicalReviewStatus.NEEDS_MANUAL_REVIEW:
        return f"manual review required because redundancy status is {redundancy_status}"
    if status is TechnicalReviewStatus.DIAGNOSTIC_ONLY:
        return "diagnostic/context role only; not direct Step 14 synthesis input by itself"
    if status is TechnicalReviewStatus.RESEARCH_ONLY:
        return f"context score has severe redundancy review flag with {peer}"
    if status is TechnicalReviewStatus.CONDITIONAL_CANDIDATE:
        if redundancy_status in SEVERE_REDUNDANCY_STATUSES:
            return f"severe redundancy review flag with {peer}; automatic promotion is not allowed"
        if redundancy_status in WARN_REDUNDANCY_STATUSES:
            return f"redundancy warning with {peer}; keep as conditional review material"
        if spec.role in {CompositeRole.CONFIRMATION, CompositeRole.SETUP_CONTEXT}:
            return "context or confirmation role; unconditional promotion is not allowed"
        return "conditional Step 11 eligibility requires explicit Step 14 synthesis review"
    if status is TechnicalReviewStatus.ADOPT_CANDIDATE:
        return "eligible score with adequate coverage and no Step 12 redundancy warning"
    return "technical review status is conservative by default"


def _manual_review_required(
    status: TechnicalReviewStatus,
    evidence: Mapping[str, object],
) -> bool:
    if status in {
        TechnicalReviewStatus.ADOPT_CANDIDATE,
        TechnicalReviewStatus.DIAGNOSTIC_ONLY,
    }:
        return False
    return True


def _count_frame(frame: pd.DataFrame, column: str, count_column: str) -> pd.DataFrame:
    counts = frame[column].value_counts().sort_index()
    return counts.rename_axis(column).reset_index(name=count_column)


def _enum_or_string_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _is_finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _assert_no_valuation_fundamental_values(
    frame: pd.DataFrame,
    *,
    context: str,
) -> None:
    text_columns = [
        column
        for column in frame.columns
        if pd.api.types.is_string_dtype(frame[column]) or frame[column].dtype == object
    ]
    forbidden_tokens = {"per", "pbr", "roe", "eps", "bps", "financial", "fundamental", "valuation"}
    violations: list[str] = []
    for column in text_columns:
        values = frame[column].dropna().astype(str).str.lower()
        for value in values:
            tokens = {token for token in value.replace("-", "_").split("_") if token}
            if tokens.intersection(forbidden_tokens):
                violations.append(column)
                break
    if violations:
        raise ValueError(
            f"{context} contains valuation/fundamental language in values: "
            f"{', '.join(sorted(set(violations)))}"
        )


__all__ = (
    "ALLOWED_TECHNICAL_REVIEW_STATUSES",
    "FORBIDDEN_STEP13_OUTPUT_COLUMNS",
    "STEP13_REVIEW_MATERIAL_NOTICE",
    "STEP13_REVIEW_TABLE_COLUMNS",
    "TechnicalReviewStatus",
    "assert_no_forbidden_step13_output_columns",
    "build_step13_review_bundle",
    "build_technical_selection_review",
    "classify_technical_review_status",
    "find_forbidden_step13_output_columns",
    "summarize_score_review_evidence",
    "validate_step13_review_table",
)
