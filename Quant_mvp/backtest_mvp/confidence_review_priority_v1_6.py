"""v1.6 confidence, robustness, and manual review priority contracts.

This module defines contract constants and schema guards only. It does not run
the v1.6 integration layer, calculate valuation/fundamental scores, change
production ranking, or create execution instructions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType


CONTRACT_VERSION = "v1_6_confidence_review_priority_contract_v1_0"
DEFAULT_OUTPUT_DIR = "Quant_mvp/data/v1_6/review_priority"
EVIDENCE_ONLY_NOTICE = (
    "v1.6 outputs are confidence, robustness, and manual review priority "
    "support only"
)
MANUAL_REVIEW_ONLY_NOTICE = (
    "manual_review_priority is a human review queue category, not an automated "
    "ordering or action instruction"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order "
    "generation, buy/sell/hold recommendations, trade-signal framing, "
    "rebalance instructions, expected-return claims, future-return claims, "
    "proven-alpha claims, production ranking replacement, valuation scoring, "
    "and fundamental scoring"
)

PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)

ALLOWED_INPUT_STATUS_VALUES = frozenset(
    {
        "after_evaluation_date",
        "available",
        "block",
        "blocked_by_reconciliation",
        "candidate_only",
        "config_missing",
        "diagnostic_only",
        "diagnostic_ready",
        "insufficient_data",
        "manual_review_required",
        "missing_artifact",
        "partial",
        "partial_diagnostic_ready",
        "pass",
        "pending_data",
        "reference_only",
        "reference_only_after_evaluation_date",
        "skipped_insufficient_pit_fundamentals",
        "skipped_missing_baseline_artifacts",
        "unavailable",
        "vendor_reference_only",
        "warn",
    }
)

FORBIDDEN_COLUMN_NAMES = frozenset(
    {
        "active_valuation_score",
        "automatic_rebalance_instruction",
        "brokerage_order_instruction",
        "alpha",
        "expected_return",
        "final_composite_score",
        "forward_return",
        "fundamental_score",
        "future_return",
        "live_trading_instruction",
        "order_instruction",
        "predicted_return",
        "production_rank",
        "production_ranking",
        "proven_alpha",
        "rebalance_instruction",
        "signal",
        "target_price",
        "technical_composite_score",
        "trade_signal",
        "valuation_score",
    }
)

ALLOWED_REASON_CODES = frozenset(
    {
        "blocked_by_upstream_reconciliation",
        "config_missing",
        "insufficient_baseline_artifact",
        "limited_quality_evidence",
        "manual_review_only",
        "missing_artifact",
        "redundant_layer_warning",
        "stable_across_horizons",
        "stable_across_splits",
        "strong_multi_layer_coverage",
    }
)

READINESS_VERDICTS = frozenset(
    {
        "V2_0_READY_FOR_LIMITED_REVIEW",
        "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY",
        "V2_0_NOT_READY",
    }
)

CONFIG_DIAGNOSTIC_VALUES = frozenset({"config_present", "config_missing", "not_required"})
THRESHOLD_CONFIG_CANDIDATES = (
    "config/thresholds.toml",
    "Quant_mvp/config/thresholds.toml",
)
THRESHOLD_POLICY = (
    "v1.6 contract defines no fallback numeric thresholds; threshold-dependent "
    "runner behavior must emit config_missing when approved config is absent"
)

COMMON_REQUIRED_FIELDS = (
    "schema_version",
    "created_at",
    "contract_version",
    "artifact_key",
    "manual_review_only_notice",
    "prohibited_actions_notice",
    "evidence_only_notice",
    *PROHIBITED_FLAGS,
)

OUTPUT_SCHEMAS = MappingProxyType(
    {
        "v1_6_confidence_score_manifest": (
            *COMMON_REQUIRED_FIELDS,
            "confidence_manifest_id",
            "source_artifact_refs",
            "allowed_status_values",
            "candidate_count",
            "confidence_support_status_counts",
            "confidence_bucket_vocabulary",
            "rows",
        ),
        "v1_6_horizon_stability_report": (
            *COMMON_REQUIRED_FIELDS,
            "horizon_stability_report_id",
            "source_artifact_refs",
            "horizon_status_vocabulary",
            "candidate_count",
            "stable_horizon_candidate_count",
            "horizon_gap_summary",
            "rows",
        ),
        "v1_6_split_stability_report": (
            *COMMON_REQUIRED_FIELDS,
            "split_stability_report_id",
            "source_artifact_refs",
            "split_status_vocabulary",
            "candidate_count",
            "stable_split_candidate_count",
            "split_gap_summary",
            "rows",
        ),
        "v1_6_layer_redundancy_report": (
            *COMMON_REQUIRED_FIELDS,
            "layer_redundancy_report_id",
            "source_artifact_refs",
            "layer_status_vocabulary",
            "candidate_count",
            "redundant_layer_warning_count",
            "redundancy_gap_summary",
            "rows",
        ),
        "v1_6_composite_review_priority_manifest": (
            *COMMON_REQUIRED_FIELDS,
            "review_priority_manifest_id",
            "source_artifact_refs",
            "reason_code_vocabulary",
            "readiness_verdict_vocabulary",
            "candidate_count",
            "manual_review_priority_vocabulary",
            "rows",
        ),
        "v1_6_v2_0_readiness_packet": (
            *COMMON_REQUIRED_FIELDS,
            "v2_0_readiness_packet_id",
            "source_artifact_refs",
            "readiness_verdict",
            "readiness_verdict_vocabulary",
            "blocking_reason_codes",
            "manual_review_priority_summary",
            "next_required_artifact",
        ),
    }
)

GENERATED_OUTPUT_PATHS = MappingProxyType(
    {
        "v1_6_confidence_score_manifest": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_confidence_score_manifest_latest.csv"
        ),
        "v1_6_horizon_stability_report": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_horizon_stability_report_latest.csv"
        ),
        "v1_6_split_stability_report": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_split_stability_report_latest.csv"
        ),
        "v1_6_layer_redundancy_report": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_layer_redundancy_report_latest.csv"
        ),
        "v1_6_composite_review_priority_manifest": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_composite_review_priority_manifest_latest.csv"
        ),
        "v1_6_v2_0_readiness_packet": (
            f"{DEFAULT_OUTPUT_DIR}/v1_6_v2_0_readiness_packet_latest.json"
        ),
    }
)

REQUIRED_INPUT_COLUMNS = frozenset(
    {
        "candidate_id",
        "evaluation_date",
        "ticker",
    }
)

OPTIONAL_INPUT_COLUMNS = frozenset(
    {
        "allowed_use",
        "average_traded_value",
        "blocked_reason",
        "capacity_reference_amount",
        "coverage",
        "data_quality",
        "dividend_yield_status",
        "evidence_id",
        "evidence_status",
        "evidence_value",
        "feature_readiness_status",
        "field_name",
        "formula_match_status",
        "horizon_id",
        "incremental_evidence_status",
        "candidate_overall_readiness_status",
        "layer_id",
        "limitations",
        "liquidity_proxy_source_ref",
        "lineage_ref",
        "manual_review_required",
        "market_cap_proxy",
        "overall_quality_profitability_status",
        "overall_valuation_status",
        "pit_availability_status",
        "price_to_book_canonical_formula_status",
        "price_to_book_vendor_reference_status",
        "price_to_earnings_canonical_formula_status",
        "price_to_earnings_vendor_reference_status",
        "reason_code",
        "seed",
        "selector_score_source",
        "source_artifact",
        "source_lineage_status",
        "split_id",
        "stability",
        "technical_ml_baseline_status",
    }
)


def find_forbidden_column_names(columns: Iterable[str]) -> tuple[str, ...]:
    """Return forbidden v1.6 input or output column names."""

    normalized = {str(column).strip().lower() for column in columns}
    return tuple(sorted(normalized.intersection(FORBIDDEN_COLUMN_NAMES)))


def validate_v1_6_columns(columns: Iterable[str]) -> None:
    """Fail closed when a v1.6 schema attempts to use forbidden columns."""

    forbidden = find_forbidden_column_names(columns)
    if forbidden:
        raise ValueError(f"v1.6 forbidden column names present: {', '.join(forbidden)}")


def validate_v1_6_output_schemas(schemas: Mapping[str, Iterable[str]] | None = None) -> None:
    """Validate required artifact schemas and guardrail fields."""

    payload = schemas or OUTPUT_SCHEMAS
    missing_artifacts = sorted(set(OUTPUT_SCHEMAS).difference(payload))
    if missing_artifacts:
        raise ValueError(f"missing v1.6 output schemas: {', '.join(missing_artifacts)}")
    for artifact_key, columns in payload.items():
        column_tuple = tuple(columns)
        validate_v1_6_columns(column_tuple)
        missing_common = [field for field in COMMON_REQUIRED_FIELDS if field not in column_tuple]
        if missing_common:
            raise ValueError(f"{artifact_key} missing common guardrail fields: {', '.join(missing_common)}")


def validate_v1_6_status_values(status_values: Iterable[str]) -> None:
    """Ensure status values are part of the v1.6 contract vocabulary."""

    unknown = sorted({str(value) for value in status_values}.difference(ALLOWED_INPUT_STATUS_VALUES))
    if unknown:
        raise ValueError(f"unknown v1.6 status values: {', '.join(unknown)}")


def validate_v1_6_reason_codes(reason_codes: Iterable[str]) -> None:
    """Ensure reason codes are part of the v1.6 contract vocabulary."""

    unknown = sorted({str(value) for value in reason_codes}.difference(ALLOWED_REASON_CODES))
    if unknown:
        raise ValueError(f"unknown v1.6 reason codes: {', '.join(unknown)}")


def validate_v1_6_readiness_verdict(verdict: str) -> None:
    """Ensure the v2.0 readiness verdict is an allowed review verdict."""

    if verdict not in READINESS_VERDICTS:
        raise ValueError(f"unknown v1.6 readiness verdict: {verdict}")
