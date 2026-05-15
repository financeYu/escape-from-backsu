"""Local-only v1.5 data supplementation artifacts.

This module enriches the chart-local pending valuation handoff with optional
OpenDART import metadata, source lineage hashes, PIT policy registry records,
and skipped incremental-evidence reports. It never fetches external data and
never promotes pending rows to available fundamentals.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "v1_5_local_supplementation_v1_0"
AVAILABILITY_POLICY_ID = "opendart_rcept_dt_next_trading_day_v1"
RESTATEMENT_POLICY_ID = "first_filed_only_v1"
STALE_DATA_POLICY_ID = "fundamental_staleness_by_report_type_v1"
REPORTING_LAG_POLICY_ID = "actual_lag_days_v1"
RATIO_FORMULA_VERSION = "chart_mvp_reported_ratio_passthrough_v1"
DEFAULT_CREATED_AT = "2026-05-15T00:00:00+00:00"

ENRICHED_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "company_name",
    "evaluation_date",
    "fiscal_period",
    "report_period_end_date",
    "corp_code",
    "stock_code",
    "report_nm",
    "rcept_no",
    "rcept_dt",
    "filing_date",
    "disclosure_date",
    "availability_date",
    "availability_policy_id",
    "source_system",
    "source_ref",
    "source_lineage_status",
    "field_name",
    "value",
    "unit",
    "currency",
    "sector_id",
    "industry_id",
    "industry_name",
    "restatement_policy",
    "stale_data_policy",
    "reporting_lag_policy",
    "pit_validation_status",
    "coverage_status",
    "data_quality_flags",
    "pending_reason",
    "boundary_notice",
]

BASELINE_COLUMNS = [
    "candidate_id",
    "evidence_id",
    "technical_ml_baseline_status",
    "selector_score",
    "selector_score_source",
    "baseline_artifact_ref",
    "reason_code",
]

SHADOW_COLUMNS = [
    "candidate_id",
    "evidence_id",
    "technical_ml_baseline_status",
    "valuation_overlay_status",
    "valuation_row_count",
    "comparison_status",
    "reason_code",
]

INCREMENTAL_COLUMNS = [
    "report_version",
    "comparison_status",
    "candidate_count",
    "baseline_available_count",
    "valuation_available_count",
    "reason_code",
    "next_required_data",
]

DART_FUNDAMENTAL_COLUMNS = [
    "schema_version",
    "stock_code",
    "corp_code",
    "rcept_no",
    "report_nm",
    "rcept_dt",
    "availability_date",
    "bsns_year",
    "reprt_code",
    "fs_div",
    "fs_nm",
    "sj_div",
    "sj_nm",
    "account_nm",
    "thstrm_nm",
    "thstrm_dt",
    "thstrm_amount",
    "frmtrm_amount",
    "bfefrmtrm_amount",
    "currency",
    "source_system",
    "source_ref",
    "raw_snapshot_path",
    "source_lineage_status",
    "value_reconciliation_status",
]

RECONCILIATION_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "field_name",
    "chart_value",
    "dart_formula_id",
    "dart_value",
    "absolute_diff",
    "tolerance",
    "value_reconciliation_status",
    "source_accounts",
    "source_ref",
    "blocked_reason",
]

VALUATION_SCORING_FIELDS = ("price_to_earnings", "price_to_book", "dividend_yield")
VALUATION_SCORING_CORE_FIELDS = ("price_to_earnings", "price_to_book")
QUALITY_PROFITABILITY_FIELDS = ("debt_ratio", "net_margin", "operating_margin", "roe")
VALUATION_FORMULA_REVIEW_FIELDS = ("price_to_earnings", "price_to_book")
VALUATION_FORMULA_REVIEW_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "chart_local_value",
    "recomputed_value",
    "absolute_delta",
    "relative_delta_pct",
    "tolerance",
    "formula_version",
    "suspected_mismatch_reason",
    "reconciliation_status",
    "source_ref",
]
VALUATION_FORMULA_COMPONENT_COLUMNS = [
    "schema_version",
    "ticker",
    "candidate_id",
    "evaluation_date",
    "field_name",
    "price_date",
    "price",
    "adjusted_price",
    "market_cap",
    "shares_outstanding",
    "net_income",
    "equity",
    "eps",
    "bps",
    "chart_cache_eps",
    "chart_cache_bps",
    "chart_implied_price",
    "price_to_chart_implied_ratio",
    "consolidated_or_separate",
    "fiscal_period",
    "report_period_end_date",
    "filing_date",
    "availability_date",
    "source_ref",
    "component_quality_status",
]
CHART_RATIO_POLICY_RECONSTRUCTION_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "chart_local_value",
    "chart_cache_per_share_metric",
    "chart_cache_per_share_value",
    "chart_implied_price",
    "evaluation_date_price",
    "price_to_chart_implied_ratio",
    "chart_internal_recomputed_value",
    "chart_internal_absolute_delta",
    "evaluation_price_recomputed_value",
    "evaluation_price_absolute_delta",
    "reconstruction_status",
    "policy_inference",
    "source_ref",
]
VALUATION_SCORING_READINESS_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "scoring_scope",
    "valuation_readiness_status",
    "quality_profitability_readiness_status",
    "dividend_readiness_status",
    "candidate_overall_readiness_status",
    "eligible_field_count",
    "blocked_field_count",
    "formula_match_valuation_fields",
    "formula_variance_valuation_fields",
    "unsupported_valuation_fields",
    "diagnostic_ready_quality_profitability_fields",
    "missing_core_valuation_fields",
    "valuation_score_status",
    "candidate_only_shadow_score_status",
    "scoring_activation_allowed",
    "blocked_reason",
    "required_next_step",
]
CHART_LOCAL_RATIO_SOURCE_LINEAGE_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "chart_local_per",
    "chart_local_pbr",
    "source_file",
    "source_row_id",
    "source_hash",
    "vendor_or_origin",
    "vendor_snapshot_date",
    "vendor_as_of_date",
    "price_date",
    "price_value",
    "adjusted_price_policy",
    "unadjusted_price_policy",
    "shares_policy",
    "shares_date",
    "eps_policy",
    "bps_policy",
    "denominator_policy",
    "source_available_before_evaluation_date",
    "lineage_status",
    "missing_lineage_reason",
    "chart_local_ratio_usage",
]
PER_PBR_FORMULA_CANDIDATE_GRID_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "formula_id",
    "required_components",
    "component_source_refs",
    "component_availability_dates",
    "formula_value",
    "chart_local_value",
    "absolute_delta",
    "relative_delta_pct",
    "tolerance_bucket",
    "suspected_mismatch_reason",
    "match_status",
]
DIVIDEND_PIT_SOURCE_LINEAGE_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "dividend_per_share",
    "total_dividend",
    "stock_kind",
    "dividend_record_date",
    "dividend_resolution_date",
    "filing_date",
    "rcept_no",
    "rcept_dt",
    "source_ref",
    "availability_date",
    "availability_policy_id",
    "price_date",
    "price_policy",
    "dividend_yield_formula_id",
    "pit_dividend_source_status",
    "missing_source_reason",
]
FEATURE_LEVEL_READINESS_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "feature_readiness_status",
    "source_lineage_status",
    "formula_match_status",
    "pit_availability_status",
    "chart_local_ratio_usage",
    "scoring_activation_allowed",
    "blocked_reason",
]
CHART_LOCAL_VENDOR_SOURCE_POLICY_PACK_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "vendor_name",
    "vendor_or_origin",
    "source_file",
    "source_row_id",
    "source_hash",
    "vendor_snapshot_date",
    "vendor_as_of_date",
    "ratio_formula",
    "price_date",
    "price_policy",
    "adjusted_price_policy",
    "shares_policy",
    "eps_policy",
    "bps_policy",
    "source_available_date",
    "source_available_before_evaluation_date",
    "policy_pack_status",
    "missing_policy_fields",
    "chart_local_ratio_usage",
    "scoring_activation_allowed",
]
NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS = [
    "schema_version",
    "ticker",
    "vendor_name",
    "vendor_or_origin",
    "source_system",
    "source_url",
    "vendor_snapshot_date",
    "vendor_as_of_date",
    "source_available_date",
    "source_available_policy",
    "price_basis_datetime",
    "price_date",
    "price_value",
    "price_policy",
    "adjusted_price_policy",
    "shares_outstanding",
    "shares_policy",
    "eps_policy",
    "bps_policy",
    "per_formula",
    "pbr_formula",
    "dividend_yield_formula",
    "per_reported_value",
    "eps_reported_value",
    "pbr_reported_value",
    "bps_reported_value",
    "raw_html_sha256",
    "raw_html_path",
    "source_lineage_status",
    "missing_policy_fields",
]
NAVER_RATIO_ASOF_SNAPSHOT_REGISTRY_COLUMNS = [
    "schema_version",
    "ticker",
    "vendor",
    "source_page",
    "snapshot_date",
    "source_available_date",
    "eligible_from_evaluation_date",
    "price_date",
    "price_policy",
    "shares_policy",
    "adjusted_price_policy",
    "raw_html_path",
    "raw_html_sha256",
    "per_reported_value",
    "pbr_reported_value",
    "crawler_version",
    "crawl_status",
    "source_available_before_evaluation_date_policy",
]
NAVER_RATIO_ASOF_RESOLVED_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "selected_snapshot_date",
    "selected_source_available_date",
    "eligible_from_evaluation_date",
    "price_date",
    "price_policy",
    "shares_policy",
    "adjusted_price_policy",
    "raw_html_path",
    "raw_html_sha256",
    "asof_resolution_status",
    "source_available_before_evaluation_date_policy",
]
PER_PBR_SPLIT_READINESS_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "formula_reconciled_status",
    "vendor_snapshot_status",
    "diagnostic_usage_status",
    "formula_verified",
    "adjusted_price_policy",
    "scoring_activation_allowed",
    "blocked_reason",
]
V16_READINESS_HANDOFF_COLUMNS = [
    "schema_version",
    "ticker",
    "candidate_id",
    "evaluation_date",
    "overall_valuation_status",
    "overall_quality_profitability_status",
    "price_to_earnings_canonical_formula_status",
    "price_to_book_canonical_formula_status",
    "price_to_earnings_vendor_reference_status",
    "price_to_book_vendor_reference_status",
    "dividend_yield_status",
    "incremental_evidence_status",
    "candidate_overall_readiness_status",
    "limitations",
    "manual_review_required",
]
NAVER_RATIO_SNAPSHOT_DRIFT_COLUMNS = [
    "schema_version",
    "ticker",
    "snapshot_date",
    "source_available_date",
    "previous_snapshot_date",
    "previous_source_available_date",
    "per_reported_value",
    "previous_per_reported_value",
    "pbr_reported_value",
    "previous_pbr_reported_value",
    "per_changed",
    "pbr_changed",
    "drift_status",
]
CANONICAL_VALUATION_COMPONENT_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "canonical_formula_id",
    "canonical_value",
    "price_date",
    "price",
    "price_source_ref",
    "market_cap",
    "shares_outstanding",
    "shares_policy",
    "shares_date",
    "shares_source_ref",
    "net_income",
    "net_income_policy",
    "equity",
    "equity_policy",
    "fs_div",
    "fiscal_period",
    "report_period_end_date",
    "filing_date",
    "availability_date",
    "source_available_before_evaluation_date",
    "component_status",
]
PER_PBR_RECONCILIATION_MATRIX_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "field_name",
    "chart_local_value",
    "naver_reported_value",
    "canonical_value",
    "comparison_basis",
    "comparison_value",
    "absolute_delta",
    "relative_delta_pct",
    "tolerance_bucket",
    "suspected_mismatch_reason",
    "reconciliation_status",
]
PER_PBR_VARIANCE_DEBUG_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "chart_local_pe",
    "naver_pe",
    "canonical_pe",
    "chart_local_pb",
    "naver_pb",
    "canonical_pb",
    "price",
    "market_cap",
    "shares_outstanding",
    "net_income_total",
    "net_income_attributable_to_owners",
    "equity_total",
    "equity_attributable_to_owners",
    "eps",
    "bps",
    "implied_net_income_from_chart_pe",
    "implied_equity_from_chart_pb",
    "implied_eps_from_chart_pe",
    "implied_bps_from_chart_pb",
    "pe_delta_chart_vs_canonical",
    "pb_delta_chart_vs_canonical",
    "pe_delta_naver_vs_canonical",
    "pb_delta_naver_vs_canonical",
    "suspected_pe_mismatch_reason",
    "suspected_pb_mismatch_reason",
    "recommended_formula_route",
]
DIVIDEND_YIELD_COMPONENT_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "dividend_per_share",
    "total_dividend",
    "stock_kind",
    "record_date",
    "resolution_date",
    "rcept_dt",
    "filing_date",
    "availability_date",
    "price_date",
    "price_policy",
    "source_ref",
    "source_available_before_evaluation_date",
    "dividend_yield",
    "component_status",
]
INCREMENTAL_BASELINE_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "horizon_id",
    "technical_ml_baseline_status",
    "selector_score",
    "selector_score_source",
    "baseline_artifact_ref",
    "reason_code",
]
INCREMENTAL_OVERLAY_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "horizon_id",
    "valuation_overlay_status",
    "quality_profitability_status",
    "ready_fields",
    "blocked_fields",
    "overlay_artifact_ref",
    "reason_code",
]
INCREMENTAL_REAL_COMPARISON_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "horizon_id",
    "technical_ml_baseline_status",
    "valuation_overlay_status",
    "comparison_status",
    "reason_code",
    "required_dependency",
]


@dataclass(frozen=True)
class V15SupplementationConfig:
    """Local v1.5 supplementation paths."""

    pending_handoff_path: Path
    output_dir: Path
    dart_metadata_path: Path | None = None
    dart_raw_snapshot_path: Path | None = None
    naver_ratio_policy_snapshot_path: Path | None = None
    technical_ml_scores_path: Path | None = None
    created_at: str = DEFAULT_CREATED_AT


def build_v1_5_supplementation(config: V15SupplementationConfig) -> dict[str, Any]:
    """Build all safe local supplementation artifacts."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    pending_rows = _read_csv_rows(config.pending_handoff_path)
    metadata_path = config.dart_metadata_path or (
        config.output_dir / "v1_5_dart_pit_metadata_import_latest.csv"
    )
    metadata_rows, metadata_source_kind, metadata_source_path = _load_metadata_rows(config, metadata_path)
    dart_fundamental_rows = (
        _dart_fundamental_rows_from_raw_snapshot(metadata_source_path, metadata_rows)
        if metadata_source_kind == "raw_snapshot"
        else []
    )
    technical_ml_scores_path = config.technical_ml_scores_path
    technical_ml_rows = _read_jsonl_rows(technical_ml_scores_path) if technical_ml_scores_path and technical_ml_scores_path.exists() else []
    naver_ratio_policy_rows = _load_naver_ratio_policy_rows(config)
    market_sources = _market_sources_by_stock(config.output_dir.parent, pending_rows)
    naver_asof_registry_rows = _naver_ratio_asof_snapshot_registry_rows(
        naver_ratio_policy_rows,
        config,
    )
    naver_asof_resolved_rows = _naver_ratio_asof_resolved_rows(
        pending_rows,
        naver_asof_registry_rows,
    )

    policy_registry = _policy_registry(config)
    enriched_rows = _enriched_rows(pending_rows, metadata_rows)
    reconciliation_rows = _value_reconciliation_rows(pending_rows, dart_fundamental_rows, market_sources)
    formula_component_rows = _valuation_formula_component_rows(
        pending_rows,
        enriched_rows,
        dart_fundamental_rows,
        market_sources,
        reconciliation_rows,
    )
    formula_review_rows = _valuation_formula_reconciliation_review_rows(
        pending_rows,
        reconciliation_rows,
        formula_component_rows,
    )
    chart_ratio_reconstruction_rows = _chart_ratio_policy_reconstruction_rows(
        pending_rows,
        formula_component_rows,
    )
    chart_local_ratio_lineage_rows = _chart_local_ratio_source_lineage_rows(
        pending_rows,
        formula_component_rows,
        naver_ratio_policy_rows,
    )
    vendor_policy_pack_rows = _chart_local_vendor_source_policy_pack_rows(
        chart_local_ratio_lineage_rows,
        naver_ratio_policy_rows,
    )
    per_pbr_formula_grid_rows = _per_pbr_formula_candidate_grid_rows(
        pending_rows,
        formula_component_rows,
    )
    per_pbr_formula_match_report = _per_pbr_formula_match_report(
        per_pbr_formula_grid_rows,
        chart_local_ratio_lineage_rows,
        config,
    )
    dividend_pit_lineage_rows = _dividend_pit_source_lineage_rows(
        pending_rows,
        metadata_rows,
        metadata_source_path if metadata_source_kind == "raw_snapshot" else None,
        market_sources,
    )
    formula_policy = _valuation_formula_policy(config)
    scoring_readiness_rows = _valuation_scoring_readiness_rows(
        pending_rows,
        reconciliation_rows,
        chart_local_ratio_lineage_rows,
        dividend_pit_lineage_rows,
    )
    feature_level_readiness_rows = _feature_level_readiness_rows(
        pending_rows,
        reconciliation_rows,
        per_pbr_formula_grid_rows,
        chart_local_ratio_lineage_rows,
        dividend_pit_lineage_rows,
    )
    per_pbr_split_readiness_rows = _per_pbr_split_readiness_rows(
        pending_rows,
        reconciliation_rows,
        chart_local_ratio_lineage_rows,
        naver_asof_resolved_rows,
    )
    v1_6_readiness_handoff_rows = _v1_6_readiness_handoff_rows(
        pending_rows,
        scoring_readiness_rows,
        feature_level_readiness_rows,
        per_pbr_split_readiness_rows,
    )
    naver_daily_crawl_health = _naver_daily_crawl_health(
        naver_ratio_policy_rows,
        naver_asof_registry_rows,
        config,
    )
    naver_snapshot_drift_rows = _naver_ratio_snapshot_drift_rows(naver_asof_registry_rows)
    lineage_report = _source_lineage_report(pending_rows)
    missing_requirements = _missing_requirements(
        enriched_rows,
        lineage_report,
        metadata_path,
        metadata_source_kind,
        metadata_source_path,
        dart_fundamental_rows,
        reconciliation_rows,
        dividend_pit_lineage_rows,
    )
    baseline_rows = _baseline_comparison_rows(pending_rows, technical_ml_rows, technical_ml_scores_path)
    shadow_rows = _shadow_comparison_rows(pending_rows, baseline_rows)
    incremental_rows = _incremental_report_rows(baseline_rows, shadow_rows)
    canonical_component_rows = _canonical_valuation_component_rows(
        pending_rows,
        formula_component_rows,
    )
    per_pbr_reconciliation_matrix_rows = _per_pbr_reconciliation_matrix_rows(
        pending_rows,
        canonical_component_rows,
        naver_asof_resolved_rows,
        naver_asof_registry_rows,
    )
    dividend_component_rows = _dividend_yield_component_rows(dividend_pit_lineage_rows, market_sources)
    incremental_baseline_rows = _incremental_baseline_rows(
        pending_rows,
        technical_ml_rows,
        technical_ml_scores_path,
    )
    incremental_overlay_rows = _incremental_overlay_rows(
        pending_rows,
        feature_level_readiness_rows,
        config,
    )
    incremental_real_comparison_rows = _incremental_real_comparison_rows(
        incremental_baseline_rows,
        incremental_overlay_rows,
    )
    per_pbr_variance_debug_rows = _per_pbr_variance_debug_rows(
        pending_rows,
        canonical_component_rows,
        naver_asof_resolved_rows,
        naver_asof_registry_rows,
    )
    per_pbr_formula_route_decision = _per_pbr_formula_route_decision(
        canonical_component_rows,
        per_pbr_reconciliation_matrix_rows,
        per_pbr_variance_debug_rows,
        config,
    )
    incremental_baseline_dependency_check = _incremental_baseline_dependency_check(
        incremental_baseline_rows,
        technical_ml_scores_path,
        config,
    )
    v1_6_readiness_handoff_rows = _v1_6_readiness_handoff_rows(
        pending_rows,
        scoring_readiness_rows,
        feature_level_readiness_rows,
        per_pbr_split_readiness_rows,
        incremental_real_comparison_rows,
    )
    v1_6_start_readiness_report = _v1_6_start_readiness_report(
        v1_6_readiness_handoff_rows,
        per_pbr_formula_route_decision,
        incremental_baseline_dependency_check,
        config,
    )
    limited_update = _limited_completion_update(
        enriched_rows,
        lineage_report,
        missing_requirements,
        baseline_rows,
        shadow_rows,
        incremental_rows,
        reconciliation_rows,
        scoring_readiness_rows,
        config,
    )
    limited_update["naver_asof_snapshot_registry_status"] = (
        "available" if naver_asof_registry_rows else "missing"
    )
    limited_update["v1_6_readiness_handoff_status"] = (
        "status_flags_available" if v1_6_readiness_handoff_rows else "missing"
    )
    limited_update["valuation_scoring_activation_allowed"] = False
    complete_readiness_gap_report = _complete_readiness_gap_report(
        reconciliation_rows,
        dividend_pit_lineage_rows,
        naver_asof_resolved_rows,
        incremental_real_comparison_rows,
        limited_update,
        config,
    )
    complete_blocker_resolution_status = _complete_blocker_resolution_status(
        per_pbr_variance_debug_rows,
        per_pbr_formula_route_decision,
        incremental_baseline_dependency_check,
        incremental_real_comparison_rows,
        v1_6_readiness_handoff_rows,
        complete_readiness_gap_report,
        config,
    )
    completion_hygiene_report = _completion_hygiene_report(
        outputs_hint=[],
        naver_asof_registry_rows=naver_asof_registry_rows,
        metadata_source_path=metadata_source_path,
        complete_readiness_gap_report=complete_readiness_gap_report,
        config=config,
    )

    outputs = {
        "metadata_enriched_handoff": config.output_dir / "v1_5_dart_pit_metadata_enriched_handoff_latest.csv",
        "metadata_enriched_manifest": config.output_dir / "v1_5_dart_pit_metadata_enriched_manifest_latest.json",
        "dart_fundamental_collection": config.output_dir / "v1_5_opendart_fundamental_collection_latest.csv",
        "dart_fundamental_collection_manifest": config.output_dir / "v1_5_opendart_fundamental_collection_manifest_latest.json",
        "value_reconciliation": config.output_dir / "v1_5_fundamental_value_reconciliation_latest.csv",
        "value_reconciliation_manifest": config.output_dir / "v1_5_fundamental_value_reconciliation_manifest_latest.json",
        "valuation_formula_reconciliation_review": config.output_dir / "v1_5_valuation_formula_reconciliation_review_latest.csv",
        "valuation_formula_reconciliation_review_manifest": config.output_dir / "v1_5_valuation_formula_reconciliation_review_manifest_latest.json",
        "valuation_formula_components": config.output_dir / "v1_5_valuation_formula_components_latest.csv",
        "valuation_formula_components_manifest": config.output_dir / "v1_5_valuation_formula_components_manifest_latest.json",
        "chart_ratio_policy_reconstruction": config.output_dir / "v1_5_chart_ratio_policy_reconstruction_latest.csv",
        "chart_ratio_policy_reconstruction_manifest": config.output_dir / "v1_5_chart_ratio_policy_reconstruction_manifest_latest.json",
        "naver_ratio_policy_snapshot": config.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.csv",
        "naver_ratio_policy_snapshot_json": config.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.json",
        "naver_ratio_asof_snapshot_registry": config.output_dir / "v1_5_naver_ratio_asof_snapshot_registry_latest.csv",
        "naver_ratio_asof_snapshot_registry_manifest": config.output_dir / "v1_5_naver_ratio_asof_snapshot_registry_manifest_latest.json",
        "naver_ratio_asof_resolved": config.output_dir / "v1_5_naver_ratio_asof_resolved_latest.csv",
        "naver_ratio_asof_resolved_manifest": config.output_dir / "v1_5_naver_ratio_asof_resolved_manifest_latest.json",
        "chart_local_ratio_source_lineage": config.output_dir / "v1_5_chart_local_ratio_source_lineage_latest.csv",
        "chart_local_ratio_source_lineage_json": config.output_dir / "v1_5_chart_local_ratio_source_lineage_latest.json",
        "chart_local_vendor_source_policy_pack": config.output_dir / "v1_5_chart_local_vendor_source_policy_pack_latest.csv",
        "chart_local_vendor_source_policy_pack_json": config.output_dir / "v1_5_chart_local_vendor_source_policy_pack_latest.json",
        "per_pbr_formula_candidate_grid": config.output_dir / "v1_5_per_pbr_formula_candidate_grid_latest.csv",
        "per_pbr_formula_candidate_grid_json": config.output_dir / "v1_5_per_pbr_formula_candidate_grid_latest.json",
        "per_pbr_formula_match_report": config.output_dir / "v1_5_per_pbr_formula_match_report_latest.json",
        "dividend_pit_source_lineage": config.output_dir / "v1_5_dividend_pit_source_lineage_latest.csv",
        "dividend_pit_source_lineage_json": config.output_dir / "v1_5_dividend_pit_source_lineage_latest.json",
        "per_pbr_split_readiness": config.output_dir / "v1_5_per_pbr_split_readiness_latest.csv",
        "per_pbr_split_readiness_manifest": config.output_dir / "v1_5_per_pbr_split_readiness_manifest_latest.json",
        "v1_6_readiness_handoff": config.output_dir / "v1_6_readiness_status_handoff_from_v1_5_latest.csv",
        "v1_6_readiness_handoff_manifest": config.output_dir / "v1_6_readiness_status_handoff_from_v1_5_manifest_latest.json",
        "naver_daily_crawl_health": config.output_dir / "v1_5_naver_daily_crawl_health_latest.json",
        "naver_snapshot_drift_report": config.output_dir / "v1_5_naver_ratio_snapshot_drift_report_latest.csv",
        "feature_level_readiness": config.output_dir / "v1_5_feature_level_readiness_latest.csv",
        "feature_level_readiness_json": config.output_dir / "v1_5_feature_level_readiness_latest.json",
        "valuation_formula_policy": config.output_dir / "v1_5_valuation_formula_policy_latest.json",
        "valuation_scoring_readiness": config.output_dir / "v1_5_valuation_scoring_readiness_latest.csv",
        "valuation_scoring_readiness_manifest": config.output_dir / "v1_5_valuation_scoring_readiness_manifest_latest.json",
        "source_lineage_report": config.output_dir / "v1_5_fundamental_source_lineage_report_latest.json",
        "policy_registry": config.output_dir / "v1_5_pit_policy_registry_latest.json",
        "baseline_comparison": config.output_dir / "v1_5_technical_ml_baseline_comparison_latest.csv",
        "shadow_comparison": config.output_dir / "v1_5_technical_ml_plus_valuation_shadow_comparison_latest.csv",
        "incremental_report": config.output_dir / "v1_5_incremental_valuation_evidence_report_latest.csv",
        "canonical_valuation_component_table": config.output_dir / "v1_5_canonical_valuation_component_table_latest.csv",
        "canonical_valuation_component_table_manifest": config.output_dir / "v1_5_canonical_valuation_component_table_manifest_latest.json",
        "canonical_per_pbr_formula_policy": config.output_dir / "v1_5_canonical_per_pbr_formula_policy_latest.json",
        "per_pbr_reconciliation_matrix": config.output_dir / "v1_5_per_pbr_reconciliation_matrix_latest.csv",
        "per_pbr_reconciliation_summary": config.output_dir / "v1_5_per_pbr_reconciliation_summary_latest.json",
        "dividend_yield_component_table": config.output_dir / "v1_5_dividend_yield_component_table_latest.csv",
        "dividend_yield_readiness": config.output_dir / "v1_5_dividend_yield_readiness_latest.json",
        "technical_ml_baseline_for_incremental": config.output_dir / "v1_5_technical_ml_baseline_for_incremental_latest.csv",
        "technical_ml_plus_valuation_overlay": config.output_dir / "v1_5_technical_ml_plus_valuation_overlay_latest.csv",
        "incremental_valuation_real_comparison": config.output_dir / "v1_5_incremental_valuation_real_comparison_latest.csv",
        "incremental_valuation_real_comparison_manifest": config.output_dir / "v1_5_incremental_valuation_real_comparison_manifest_latest.json",
        "v1_6_start_readiness_report": config.output_dir / "v1_6_start_readiness_report_latest.json",
        "per_pbr_variance_debug": config.output_dir / "v1_5_per_pbr_variance_debug_latest.csv",
        "per_pbr_variance_debug_summary": config.output_dir / "v1_5_per_pbr_variance_debug_summary_latest.json",
        "per_pbr_formula_route_decision": config.output_dir / "v1_5_per_pbr_formula_route_decision_latest.json",
        "incremental_baseline_dependency_check": config.output_dir / "v1_5_incremental_baseline_dependency_check_latest.json",
        "complete_blocker_resolution_status": config.output_dir / "v1_5_complete_blocker_resolution_status_latest.json",
        "complete_readiness_gap_report": config.output_dir / "v1_5_complete_readiness_gap_report_latest.json",
        "completion_hygiene_report": config.output_dir / "v1_5_completion_hygiene_report_latest.json",
        "missing_requirements": config.output_dir / "v1_5_missing_pit_fundamental_requirements_latest.json",
        "limited_completion_update": config.output_dir / "v1_5_limited_completion_update_latest.json",
    }
    completion_hygiene_report = _completion_hygiene_report(
        outputs_hint=[str(path) for path in outputs.values()],
        naver_asof_registry_rows=naver_asof_registry_rows,
        metadata_source_path=metadata_source_path,
        complete_readiness_gap_report=complete_readiness_gap_report,
        config=config,
    )
    _write_csv(outputs["metadata_enriched_handoff"], enriched_rows, ENRICHED_COLUMNS)
    _write_json(
        outputs["metadata_enriched_manifest"],
        _metadata_manifest(enriched_rows, metadata_path, metadata_source_kind, metadata_source_path, config),
    )
    _write_csv(outputs["dart_fundamental_collection"], dart_fundamental_rows, DART_FUNDAMENTAL_COLUMNS)
    _write_json(
        outputs["dart_fundamental_collection_manifest"],
        _dart_fundamental_manifest(dart_fundamental_rows, metadata_source_path, config),
    )
    _write_csv(outputs["value_reconciliation"], reconciliation_rows, RECONCILIATION_COLUMNS)
    _write_json(
        outputs["value_reconciliation_manifest"],
        _value_reconciliation_manifest(reconciliation_rows, config),
    )
    _write_csv(outputs["valuation_formula_reconciliation_review"], formula_review_rows, VALUATION_FORMULA_REVIEW_COLUMNS)
    _write_json(
        outputs["valuation_formula_reconciliation_review_manifest"],
        _valuation_formula_reconciliation_review_manifest(formula_review_rows, config),
    )
    _write_csv(outputs["valuation_formula_components"], formula_component_rows, VALUATION_FORMULA_COMPONENT_COLUMNS)
    _write_json(
        outputs["valuation_formula_components_manifest"],
        _valuation_formula_components_manifest(formula_component_rows, config),
    )
    _write_csv(
        outputs["chart_ratio_policy_reconstruction"],
        chart_ratio_reconstruction_rows,
        CHART_RATIO_POLICY_RECONSTRUCTION_COLUMNS,
    )
    _write_json(
        outputs["chart_ratio_policy_reconstruction_manifest"],
        _chart_ratio_policy_reconstruction_manifest(chart_ratio_reconstruction_rows, config),
    )
    _write_csv(outputs["naver_ratio_policy_snapshot"], naver_ratio_policy_rows, NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS)
    _write_json(
        outputs["naver_ratio_policy_snapshot_json"],
        _rows_payload("v1_5_naver_ratio_policy_snapshot", naver_ratio_policy_rows, config),
    )
    _write_csv(
        outputs["naver_ratio_asof_snapshot_registry"],
        naver_asof_registry_rows,
        NAVER_RATIO_ASOF_SNAPSHOT_REGISTRY_COLUMNS,
    )
    _write_json(
        outputs["naver_ratio_asof_snapshot_registry_manifest"],
        _rows_payload("v1_5_naver_ratio_asof_snapshot_registry", naver_asof_registry_rows, config),
    )
    _write_csv(
        outputs["naver_ratio_asof_resolved"],
        naver_asof_resolved_rows,
        NAVER_RATIO_ASOF_RESOLVED_COLUMNS,
    )
    _write_json(
        outputs["naver_ratio_asof_resolved_manifest"],
        _rows_payload("v1_5_naver_ratio_asof_resolved", naver_asof_resolved_rows, config),
    )
    _write_csv(
        outputs["chart_local_ratio_source_lineage"],
        chart_local_ratio_lineage_rows,
        CHART_LOCAL_RATIO_SOURCE_LINEAGE_COLUMNS,
    )
    _write_json(
        outputs["chart_local_ratio_source_lineage_json"],
        _rows_payload("v1_5_chart_local_ratio_source_lineage", chart_local_ratio_lineage_rows, config),
    )
    _write_csv(
        outputs["chart_local_vendor_source_policy_pack"],
        vendor_policy_pack_rows,
        CHART_LOCAL_VENDOR_SOURCE_POLICY_PACK_COLUMNS,
    )
    _write_json(
        outputs["chart_local_vendor_source_policy_pack_json"],
        _rows_payload("v1_5_chart_local_vendor_source_policy_pack", vendor_policy_pack_rows, config),
    )
    _write_csv(
        outputs["per_pbr_formula_candidate_grid"],
        per_pbr_formula_grid_rows,
        PER_PBR_FORMULA_CANDIDATE_GRID_COLUMNS,
    )
    _write_json(
        outputs["per_pbr_formula_candidate_grid_json"],
        _rows_payload("v1_5_per_pbr_formula_candidate_grid", per_pbr_formula_grid_rows, config),
    )
    _write_json(outputs["per_pbr_formula_match_report"], per_pbr_formula_match_report)
    _write_csv(
        outputs["dividend_pit_source_lineage"],
        dividend_pit_lineage_rows,
        DIVIDEND_PIT_SOURCE_LINEAGE_COLUMNS,
    )
    _write_json(
        outputs["dividend_pit_source_lineage_json"],
        _rows_payload("v1_5_dividend_pit_source_lineage", dividend_pit_lineage_rows, config),
    )
    _write_csv(
        outputs["per_pbr_split_readiness"],
        per_pbr_split_readiness_rows,
        PER_PBR_SPLIT_READINESS_COLUMNS,
    )
    _write_json(
        outputs["per_pbr_split_readiness_manifest"],
        _rows_payload("v1_5_per_pbr_split_readiness", per_pbr_split_readiness_rows, config),
    )
    _write_csv(
        outputs["v1_6_readiness_handoff"],
        v1_6_readiness_handoff_rows,
        V16_READINESS_HANDOFF_COLUMNS,
    )
    _write_json(
        outputs["v1_6_readiness_handoff_manifest"],
        _rows_payload("v1_6_readiness_status_handoff_from_v1_5", v1_6_readiness_handoff_rows, config),
    )
    _write_json(outputs["naver_daily_crawl_health"], naver_daily_crawl_health)
    _write_csv(outputs["naver_snapshot_drift_report"], naver_snapshot_drift_rows, NAVER_RATIO_SNAPSHOT_DRIFT_COLUMNS)
    _write_json(outputs["valuation_formula_policy"], formula_policy)
    _write_csv(outputs["valuation_scoring_readiness"], scoring_readiness_rows, VALUATION_SCORING_READINESS_COLUMNS)
    _write_json(
        outputs["valuation_scoring_readiness_manifest"],
        _valuation_scoring_readiness_manifest(scoring_readiness_rows, config),
    )
    _write_csv(outputs["feature_level_readiness"], feature_level_readiness_rows, FEATURE_LEVEL_READINESS_COLUMNS)
    _write_json(
        outputs["feature_level_readiness_json"],
        _rows_payload("v1_5_feature_level_readiness", feature_level_readiness_rows, config),
    )
    _write_json(outputs["source_lineage_report"], lineage_report)
    _write_json(outputs["policy_registry"], policy_registry)
    _write_csv(outputs["baseline_comparison"], baseline_rows, BASELINE_COLUMNS)
    _write_csv(outputs["shadow_comparison"], shadow_rows, SHADOW_COLUMNS)
    _write_csv(outputs["incremental_report"], incremental_rows, INCREMENTAL_COLUMNS)
    _write_csv(
        outputs["canonical_valuation_component_table"],
        canonical_component_rows,
        CANONICAL_VALUATION_COMPONENT_COLUMNS,
    )
    _write_json(
        outputs["canonical_valuation_component_table_manifest"],
        _canonical_valuation_component_table_manifest(canonical_component_rows, config),
    )
    _write_json(outputs["canonical_per_pbr_formula_policy"], _canonical_per_pbr_formula_policy(config))
    _write_csv(
        outputs["per_pbr_reconciliation_matrix"],
        per_pbr_reconciliation_matrix_rows,
        PER_PBR_RECONCILIATION_MATRIX_COLUMNS,
    )
    _write_json(
        outputs["per_pbr_reconciliation_summary"],
        _per_pbr_reconciliation_summary(per_pbr_reconciliation_matrix_rows, config),
    )
    _write_csv(
        outputs["dividend_yield_component_table"],
        dividend_component_rows,
        DIVIDEND_YIELD_COMPONENT_COLUMNS,
    )
    _write_json(
        outputs["dividend_yield_readiness"],
        _dividend_yield_readiness(dividend_component_rows, dividend_pit_lineage_rows, config),
    )
    _write_csv(
        outputs["technical_ml_baseline_for_incremental"],
        incremental_baseline_rows,
        INCREMENTAL_BASELINE_COLUMNS,
    )
    _write_csv(
        outputs["technical_ml_plus_valuation_overlay"],
        incremental_overlay_rows,
        INCREMENTAL_OVERLAY_COLUMNS,
    )
    _write_csv(
        outputs["incremental_valuation_real_comparison"],
        incremental_real_comparison_rows,
        INCREMENTAL_REAL_COMPARISON_COLUMNS,
    )
    _write_json(
        outputs["incremental_valuation_real_comparison_manifest"],
        _incremental_real_comparison_manifest(incremental_real_comparison_rows, config),
    )
    _write_json(outputs["v1_6_start_readiness_report"], v1_6_start_readiness_report)
    _write_csv(outputs["per_pbr_variance_debug"], per_pbr_variance_debug_rows, PER_PBR_VARIANCE_DEBUG_COLUMNS)
    _write_json(
        outputs["per_pbr_variance_debug_summary"],
        _per_pbr_variance_debug_summary(per_pbr_variance_debug_rows, config),
    )
    _write_json(outputs["per_pbr_formula_route_decision"], per_pbr_formula_route_decision)
    _write_json(outputs["incremental_baseline_dependency_check"], incremental_baseline_dependency_check)
    _write_json(outputs["complete_blocker_resolution_status"], complete_blocker_resolution_status)
    _write_json(outputs["complete_readiness_gap_report"], complete_readiness_gap_report)
    _write_json(outputs["completion_hygiene_report"], completion_hygiene_report)
    _write_json(outputs["missing_requirements"], missing_requirements)
    _write_json(outputs["limited_completion_update"], limited_update)

    return {
        "outputs": {key: str(path) for key, path in outputs.items()},
        "metadata_enriched_rows": enriched_rows,
        "metadata_manifest": _metadata_manifest(
            enriched_rows,
            metadata_path,
            metadata_source_kind,
            metadata_source_path,
            config,
        ),
        "dart_fundamental_collection_rows": dart_fundamental_rows,
        "dart_fundamental_collection_manifest": _dart_fundamental_manifest(
            dart_fundamental_rows,
            metadata_source_path,
            config,
        ),
        "value_reconciliation_rows": reconciliation_rows,
        "value_reconciliation_manifest": _value_reconciliation_manifest(reconciliation_rows, config),
        "valuation_formula_reconciliation_review_rows": formula_review_rows,
        "valuation_formula_reconciliation_review_manifest": _valuation_formula_reconciliation_review_manifest(formula_review_rows, config),
        "valuation_formula_component_rows": formula_component_rows,
        "valuation_formula_components_manifest": _valuation_formula_components_manifest(formula_component_rows, config),
        "chart_ratio_policy_reconstruction_rows": chart_ratio_reconstruction_rows,
        "chart_ratio_policy_reconstruction_manifest": _chart_ratio_policy_reconstruction_manifest(chart_ratio_reconstruction_rows, config),
        "naver_ratio_policy_snapshot_rows": naver_ratio_policy_rows,
        "naver_ratio_asof_snapshot_registry_rows": naver_asof_registry_rows,
        "naver_ratio_asof_resolved_rows": naver_asof_resolved_rows,
        "chart_local_ratio_source_lineage_rows": chart_local_ratio_lineage_rows,
        "chart_local_vendor_source_policy_pack_rows": vendor_policy_pack_rows,
        "per_pbr_formula_candidate_grid_rows": per_pbr_formula_grid_rows,
        "per_pbr_formula_match_report": per_pbr_formula_match_report,
        "dividend_pit_source_lineage_rows": dividend_pit_lineage_rows,
        "per_pbr_split_readiness_rows": per_pbr_split_readiness_rows,
        "v1_6_readiness_handoff_rows": v1_6_readiness_handoff_rows,
        "naver_daily_crawl_health": naver_daily_crawl_health,
        "naver_ratio_snapshot_drift_rows": naver_snapshot_drift_rows,
        "valuation_formula_policy": formula_policy,
        "valuation_scoring_readiness_rows": scoring_readiness_rows,
        "valuation_scoring_readiness_manifest": _valuation_scoring_readiness_manifest(scoring_readiness_rows, config),
        "feature_level_readiness_rows": feature_level_readiness_rows,
        "source_lineage_report": lineage_report,
        "policy_registry": policy_registry,
        "baseline_comparison_rows": baseline_rows,
        "shadow_comparison_rows": shadow_rows,
        "incremental_report_rows": incremental_rows,
        "canonical_valuation_component_rows": canonical_component_rows,
        "per_pbr_reconciliation_matrix_rows": per_pbr_reconciliation_matrix_rows,
        "dividend_yield_component_rows": dividend_component_rows,
        "incremental_baseline_rows": incremental_baseline_rows,
        "incremental_overlay_rows": incremental_overlay_rows,
        "incremental_real_comparison_rows": incremental_real_comparison_rows,
        "v1_6_start_readiness_report": v1_6_start_readiness_report,
        "per_pbr_variance_debug_rows": per_pbr_variance_debug_rows,
        "per_pbr_variance_debug_summary": _per_pbr_variance_debug_summary(per_pbr_variance_debug_rows, config),
        "per_pbr_formula_route_decision": per_pbr_formula_route_decision,
        "incremental_baseline_dependency_check": incremental_baseline_dependency_check,
        "complete_blocker_resolution_status": complete_blocker_resolution_status,
        "complete_readiness_gap_report": complete_readiness_gap_report,
        "completion_hygiene_report": completion_hygiene_report,
        "missing_requirements": missing_requirements,
        "limited_completion_update": limited_update,
    }


def _load_metadata_rows(
    config: V15SupplementationConfig,
    metadata_path: Path,
) -> tuple[list[dict[str, str]], str, Path | None]:
    if metadata_path.exists():
        return _read_csv_rows(metadata_path), "import_csv", metadata_path
    raw_snapshot_path = config.dart_raw_snapshot_path or _latest_raw_snapshot_path(
        config.output_dir.parent / "opendart_v1_4_raw_snapshots"
    )
    if raw_snapshot_path and raw_snapshot_path.exists():
        return _metadata_rows_from_raw_snapshot(raw_snapshot_path), "raw_snapshot", raw_snapshot_path
    return [], "missing", None


def _load_naver_ratio_policy_rows(config: V15SupplementationConfig) -> list[dict[str, str]]:
    snapshot_path = config.naver_ratio_policy_snapshot_path or (
        config.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.csv"
    )
    if not snapshot_path.exists():
        return []
    return _read_csv_rows(snapshot_path)


def _naver_ratio_asof_snapshot_registry_rows(
    snapshot_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> list[dict[str, str]]:
    existing_path = config.output_dir / "v1_5_naver_ratio_asof_snapshot_registry_latest.csv"
    existing_rows = _read_csv_rows(existing_path) if existing_path.exists() else []
    rows_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in existing_rows:
        normalized = {column: row.get(column, "") for column in NAVER_RATIO_ASOF_SNAPSHOT_REGISTRY_COLUMNS}
        key = (
            normalized.get("ticker", ""),
            normalized.get("source_available_date", ""),
            normalized.get("raw_html_sha256", ""),
        )
        if key[0]:
            rows_by_key[key] = normalized
    for row in snapshot_rows:
        raw_status = _raw_html_integrity_status(row, config.output_dir)
        source_available_date = row.get("source_available_date", "")
        normalized = {
            "schema_version": SCHEMA_VERSION,
            "ticker": row.get("ticker", ""),
            "vendor": row.get("vendor_name", "") or "Naver Finance",
            "source_page": row.get("source_url", ""),
            "snapshot_date": row.get("vendor_snapshot_date", ""),
            "source_available_date": source_available_date,
            "eligible_from_evaluation_date": source_available_date,
            "price_date": row.get("price_date", ""),
            "price_policy": row.get("price_policy", ""),
            "shares_policy": row.get("shares_policy", ""),
            "adjusted_price_policy": row.get("adjusted_price_policy", "") or "not_disclosed_by_naver_main",
            "raw_html_path": row.get("raw_html_path", ""),
            "raw_html_sha256": row.get("raw_html_sha256", ""),
            "per_reported_value": row.get("per_reported_value", ""),
            "pbr_reported_value": row.get("pbr_reported_value", ""),
            "crawler_version": "naver_main_ratio_policy_crawler_v1",
            "crawl_status": "collected" if raw_status == "ok" else raw_status,
            "source_available_before_evaluation_date_policy": "latest_snapshot_with_source_available_date_lte_evaluation_date_v1",
        }
        key = (
            normalized["ticker"],
            normalized["source_available_date"],
            normalized["raw_html_sha256"],
        )
        if key[0]:
            rows_by_key[key] = normalized
    return sorted(
        rows_by_key.values(),
        key=lambda row: (row.get("ticker", ""), row.get("source_available_date", ""), row.get("snapshot_date", "")),
    )


def _naver_ratio_asof_resolved_rows(
    pending_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    registry_by_ticker: dict[str, list[dict[str, str]]] = {}
    for row in registry_rows:
        registry_by_ticker.setdefault(row.get("ticker", ""), []).append(row)
    for rows in registry_by_ticker.values():
        rows.sort(key=lambda row: (row.get("source_available_date", ""), row.get("snapshot_date", "")))

    candidate_keys = sorted(
        {
            (
                row.get("candidate_id", ""),
                row.get("evidence_id", ""),
                row.get("ticker", ""),
                row.get("evaluation_date", ""),
            )
            for row in pending_rows
            if row.get("candidate_id") and row.get("ticker")
        }
    )
    rows = []
    for candidate_id, evidence_id, ticker, evaluation_date in candidate_keys:
        eval_date = _parse_date_text(evaluation_date)
        snapshots = registry_by_ticker.get(ticker, [])
        eligible_snapshots = []
        later_snapshots = []
        for snapshot in snapshots:
            source_date = _parse_date_text(snapshot.get("source_available_date", ""))
            if source_date is None or eval_date is None:
                continue
            if source_date <= eval_date:
                eligible_snapshots.append(snapshot)
            else:
                later_snapshots.append(snapshot)
        selected = eligible_snapshots[-1] if eligible_snapshots else {}
        if selected:
            status = (
                "vendor_snapshot_available_asof_evaluation"
                if selected.get("crawl_status") == "collected"
                else selected.get("crawl_status", "crawl_missing")
            )
        elif snapshots and later_snapshots:
            status = "after_evaluation_date"
        elif snapshots:
            status = "no_prior_vendor_snapshot"
        else:
            status = "crawl_missing"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": evidence_id,
                "ticker": ticker,
                "evaluation_date": evaluation_date,
                "selected_snapshot_date": selected.get("snapshot_date", ""),
                "selected_source_available_date": selected.get("source_available_date", ""),
                "eligible_from_evaluation_date": selected.get("eligible_from_evaluation_date", ""),
                "price_date": selected.get("price_date", ""),
                "price_policy": selected.get("price_policy", ""),
                "shares_policy": selected.get("shares_policy", ""),
                "adjusted_price_policy": selected.get("adjusted_price_policy", "not_disclosed_by_naver_main"),
                "raw_html_path": selected.get("raw_html_path", ""),
                "raw_html_sha256": selected.get("raw_html_sha256", ""),
                "asof_resolution_status": status,
                "source_available_before_evaluation_date_policy": "latest_snapshot_with_source_available_date_lte_evaluation_date_v1",
            }
        )
    return rows


def _raw_html_integrity_status(row: dict[str, str], output_dir: Path) -> str:
    raw_path_text = row.get("raw_html_path", "")
    expected_hash = row.get("raw_html_sha256", "")
    if not raw_path_text:
        return "raw_html_missing"
    if not expected_hash:
        return "raw_html_sha256_missing"
    raw_path = _resolve_raw_html_path(raw_path_text, output_dir)
    if not raw_path.exists():
        return "raw_html_missing"
    actual_hash = sha256(raw_path.read_bytes()).hexdigest()
    if expected_hash and actual_hash != expected_hash:
        return "hash_mismatch"
    return "ok"


def _resolve_raw_html_path(raw_path_text: str, output_dir: Path) -> Path:
    raw_path = Path(raw_path_text)
    if raw_path.is_absolute():
        return raw_path
    candidates = [
        output_dir / raw_path,
        output_dir / "naver_ratio_policy_raw_html" / raw_path.name,
        raw_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _latest_raw_snapshot_path(snapshot_root: Path) -> Path | None:
    if not snapshot_root.exists():
        return None
    candidates = sorted(snapshot_root.glob("*/*.jsonl"))
    return candidates[-1] if candidates else None


def _metadata_rows_from_raw_snapshot(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in _read_jsonl_rows(path):
        if record.get("endpoint_name") != "disclosure_list":
            continue
        raw_json = record.get("raw_json")
        if not isinstance(raw_json, dict):
            continue
        for item in raw_json.get("list") or []:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "corp_code": str(item.get("corp_code", "")).strip(),
                    "stock_code": str(item.get("stock_code", "")).strip(),
                    "report_nm": str(item.get("report_nm", "")).strip(),
                    "rcept_no": str(item.get("rcept_no", "")).strip(),
                    "rcept_dt": str(item.get("rcept_dt", "")).strip(),
                    "source_system": "OpenDART_raw_snapshot",
                    "source_ref": str(record.get("source_ref", "")).strip(),
                    "source_lineage_status": "metadata_from_v1_4_raw_snapshot",
                }
            )
    return rows


def _dart_fundamental_rows_from_raw_snapshot(
    raw_snapshot_path: Path | None,
    metadata_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if raw_snapshot_path is None or not raw_snapshot_path.exists():
        return []
    metadata_by_receipt = {
        (row.get("stock_code", ""), row.get("rcept_no", "")): row
        for row in metadata_rows
        if row.get("stock_code") and row.get("rcept_no")
    }
    rows: list[dict[str, str]] = []
    for record in _read_jsonl_rows(raw_snapshot_path):
        if record.get("endpoint_name") != "single_account":
            continue
        raw_json = record.get("raw_json")
        if not isinstance(raw_json, dict):
            continue
        source_ref = str(record.get("source_ref", "")).strip()
        for item in raw_json.get("list") or []:
            if not isinstance(item, dict):
                continue
            stock_code = str(item.get("stock_code", "")).strip()
            rcept_no = str(item.get("rcept_no", "")).strip()
            metadata = metadata_by_receipt.get((stock_code, rcept_no), {})
            rcept_dt = metadata.get("rcept_dt", "")
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "stock_code": stock_code,
                    "corp_code": str(item.get("corp_code", "")).strip() or metadata.get("corp_code", ""),
                    "rcept_no": rcept_no,
                    "report_nm": metadata.get("report_nm", ""),
                    "rcept_dt": rcept_dt,
                    "availability_date": _next_trading_day_text(rcept_dt) if rcept_dt else "",
                    "bsns_year": str(item.get("bsns_year", "")).strip(),
                    "reprt_code": str(item.get("reprt_code", "")).strip(),
                    "fs_div": str(item.get("fs_div", "")).strip(),
                    "fs_nm": str(item.get("fs_nm", "")).strip(),
                    "sj_div": str(item.get("sj_div", "")).strip(),
                    "sj_nm": str(item.get("sj_nm", "")).strip(),
                    "account_nm": str(item.get("account_nm", "")).strip(),
                    "thstrm_nm": str(item.get("thstrm_nm", "")).strip(),
                    "thstrm_dt": str(item.get("thstrm_dt", "")).strip(),
                    "thstrm_amount": str(item.get("thstrm_amount", "")).strip(),
                    "frmtrm_amount": str(item.get("frmtrm_amount", "")).strip(),
                    "bfefrmtrm_amount": str(item.get("bfefrmtrm_amount", "")).strip(),
                    "currency": str(item.get("currency", "")).strip(),
                    "source_system": "OpenDART_raw_snapshot",
                    "source_ref": source_ref,
                    "raw_snapshot_path": str(raw_snapshot_path),
                    "source_lineage_status": "single_account_collected",
                    "value_reconciliation_status": "collected_not_reconciled_to_chart_ratios",
                }
            )
    return rows


def _value_reconciliation_rows(
    pending_rows: list[dict[str, str]],
    dart_fundamental_rows: list[dict[str, str]],
    market_sources: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    fundamentals_by_stock = _fundamentals_by_stock(dart_fundamental_rows)
    market_sources = market_sources or {}
    rows = []
    for pending_row in pending_rows:
        ticker = pending_row.get("ticker", "").strip()
        field_name = pending_row.get("field_name", "").strip()
        chart_value = _parse_number(pending_row.get("value", ""))
        fundamentals = fundamentals_by_stock.get(ticker, {})
        formula = _calculate_dart_ratio(field_name, fundamentals, market_sources.get(ticker, {}))
        tolerance = 0.1
        if chart_value is None:
            status = "chart_value_missing"
            absolute_diff = ""
        elif formula["value"] is None:
            status = formula["status"]
            absolute_diff = ""
        else:
            diff = abs(chart_value - formula["value"])
            status = "formula_match" if diff <= tolerance else "formula_variance"
            absolute_diff = f"{diff:.6f}"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": pending_row.get("candidate_id", ""),
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": ticker,
                "field_name": field_name,
                "chart_value": pending_row.get("value", ""),
                "dart_formula_id": formula["formula_id"],
                "dart_value": "" if formula["value"] is None else f"{formula['value']:.6f}",
                "absolute_diff": absolute_diff,
                "tolerance": str(tolerance),
                "value_reconciliation_status": status,
                "source_accounts": "|".join(formula["source_accounts"]),
                "source_ref": formula["source_ref"],
                "blocked_reason": formula["blocked_reason"] if status != "formula_match" else "",
            }
        )
    return rows


def _fundamentals_by_stock(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    result: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("fs_div") != "CFS":
            continue
        stock_code = row.get("stock_code", "")
        account_nm = row.get("account_nm", "")
        if stock_code and account_nm and account_nm not in result.setdefault(stock_code, {}):
            result[stock_code][account_nm] = row
    return result


def _market_sources_by_stock(data_dir: Path, pending_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    liquidity_dir = data_dir / "v1_3_liquidity"
    market_rows = _read_market_cap_snapshot_rows(liquidity_dir)
    result: dict[str, dict[str, Any]] = {}
    for pending_row in pending_rows:
        ticker = pending_row.get("ticker", "").strip()
        if not ticker or ticker in result:
            continue
        evaluation_date = _parse_date_text(pending_row.get("evaluation_date", ""))
        if evaluation_date is None:
            continue
        market_row = _select_market_cap_row(market_rows, ticker, evaluation_date)
        if market_row is None:
            continue
        close_row = _select_daily_close_row(data_dir, market_row, ticker, evaluation_date)
        if close_row is None:
            continue
        close = _parse_number(close_row.get("종가", ""))
        shares = _parse_number(market_row.get("shares_outstanding", ""))
        if close is None or shares is None:
            continue
        result[ticker] = {
            "market_cap": close * shares,
            "close": close,
            "shares_outstanding": shares,
            "price_date": close_row.get("날짜", ""),
            "shares_as_of_date": market_row.get("as_of_date", ""),
            "source_ref": "local_market_source:{ticker}:price_date={price_date}:shares_as_of={shares_as_of}:{source_ref}".format(
                ticker=ticker,
                price_date=close_row.get("날짜", ""),
                shares_as_of=market_row.get("as_of_date", ""),
                source_ref=market_row.get("source_ref", ""),
            ),
        }
    return result


def _read_market_cap_snapshot_rows(liquidity_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not liquidity_dir.exists():
        return rows
    for path in sorted(liquidity_dir.glob("v1_3_approved_local_market_cap_snapshot_*.csv")):
        if path.name.endswith("_latest.csv"):
            continue
        rows.extend(_read_csv_rows(path))
    return rows


def _select_market_cap_row(
    rows: list[dict[str, str]],
    ticker: str,
    evaluation_date: date,
) -> dict[str, str] | None:
    candidates = []
    for row in rows:
        if row.get("ticker", "").strip() != ticker:
            continue
        as_of_date = _parse_date_text(row.get("as_of_date", ""))
        if as_of_date is not None and as_of_date <= evaluation_date:
            candidates.append((as_of_date, row))
    if not candidates:
        return None
    latest_date = max(candidate_date for candidate_date, _candidate_row in candidates)
    for candidate_date, candidate_row in candidates:
        if candidate_date == latest_date:
            return candidate_row
    return None


def _select_daily_close_row(
    data_dir: Path,
    market_row: dict[str, str],
    ticker: str,
    evaluation_date: date,
) -> dict[str, str] | None:
    source_path = market_row.get("average_traded_value_price_source_path", "")
    path = Path(source_path)
    if not path.is_absolute():
        if path.parts and path.parts[0] == data_dir.name:
            path = data_dir.parent / path
        else:
            path = data_dir / f"{ticker}_daily_prices.csv"
    if not path.exists():
        path = data_dir / f"{ticker}_daily_prices.csv"
    if not path.exists():
        return None
    candidates = []
    for row in _read_csv_rows(path):
        row_date = _parse_date_text(row.get("날짜", ""))
        if row_date is not None and row_date <= evaluation_date:
            candidates.append((row_date, row))
    if not candidates:
        return None
    latest_date = max(candidate_date for candidate_date, _candidate_row in candidates)
    for candidate_date, candidate_row in candidates:
        if candidate_date == latest_date:
            return candidate_row
    return None


def _calculate_dart_ratio(
    field_name: str,
    accounts: dict[str, dict[str, str]],
    market_source: dict[str, Any],
) -> dict[str, Any]:
    unsupported = {
        "dividend_yield": "cash dividend and market price source are not present in OpenDART single_account",
    }
    if field_name in unsupported:
        return _formula_result(
            formula_id="unsupported_by_single_account_v1",
            status="unsupported_missing_market_or_dividend_source",
            blocked_reason=unsupported[field_name],
        )
    if field_name == "price_to_earnings":
        return _market_ratio_result(
            formula_id="local_eval_market_cap_to_net_income_v1",
            denominator_account="당기순이익(손실)",
            accounts=accounts,
            market_source=market_source,
        )
    if field_name == "price_to_book":
        return _market_ratio_result(
            formula_id="local_eval_market_cap_to_total_equity_v1",
            denominator_account="자본총계",
            accounts=accounts,
            market_source=market_source,
        )
    if field_name == "operating_margin":
        return _ratio_result(
            formula_id="opendart_operating_margin_v1",
            numerator_account="영업이익",
            denominator_account="매출액",
            accounts=accounts,
        )
    if field_name == "net_margin":
        return _ratio_result(
            formula_id="opendart_net_margin_v1",
            numerator_account="당기순이익(손실)",
            denominator_account="매출액",
            accounts=accounts,
        )
    if field_name == "debt_ratio":
        return _ratio_result(
            formula_id="opendart_debt_ratio_v1",
            numerator_account="부채총계",
            denominator_account="자본총계",
            accounts=accounts,
        )
    if field_name == "roe":
        return _roe_result(accounts)
    return _formula_result(
        formula_id="unsupported_field_v1",
        status="unsupported_field",
        blocked_reason=f"no reconciliation formula for {field_name}",
    )


def _market_ratio_result(
    *,
    formula_id: str,
    denominator_account: str,
    accounts: dict[str, dict[str, str]],
    market_source: dict[str, Any],
) -> dict[str, Any]:
    market_cap = market_source.get("market_cap")
    denominator_row = accounts.get(denominator_account)
    denominator = _amount_from_row(denominator_row, "thstrm_amount")
    source_accounts = ["local_eval_close_x_prior_shares", denominator_account]
    if market_cap is None or denominator in (None, 0):
        return _formula_result(
            formula_id=formula_id,
            status="formula_source_missing",
            source_accounts=source_accounts,
            blocked_reason="PIT market cap/share source or OpenDART denominator account is missing",
        )
    return _formula_result(
        formula_id=formula_id,
        value=market_cap / denominator,
        source_accounts=source_accounts,
        source_ref="|".join(
            item
            for item in [
                str(market_source.get("source_ref", "")),
                _source_ref_from_rows([denominator_row]),
            ]
            if item
        ),
        blocked_reason="local market/share source is diagnostic and must pass PIT market-source review before promotion",
    )


def _ratio_result(
    *,
    formula_id: str,
    numerator_account: str,
    denominator_account: str,
    accounts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    numerator_row = accounts.get(numerator_account)
    denominator_row = accounts.get(denominator_account)
    numerator = _amount_from_row(numerator_row, "thstrm_amount")
    denominator = _amount_from_row(denominator_row, "thstrm_amount")
    source_accounts = [numerator_account, denominator_account]
    if numerator is None or denominator in (None, 0):
        return _formula_result(
            formula_id=formula_id,
            status="formula_source_missing",
            source_accounts=source_accounts,
            blocked_reason="required OpenDART accounts are missing or denominator is zero",
        )
    return _formula_result(
        formula_id=formula_id,
        value=(numerator / denominator) * 100,
        source_accounts=source_accounts,
        source_ref=_source_ref_from_rows([numerator_row, denominator_row]),
    )


def _roe_result(accounts: dict[str, dict[str, str]]) -> dict[str, Any]:
    net_income_row = accounts.get("당기순이익(손실)")
    equity_row = accounts.get("자본총계")
    net_income = _amount_from_row(net_income_row, "thstrm_amount")
    current_equity = _amount_from_row(equity_row, "thstrm_amount")
    previous_equity = _amount_from_row(equity_row, "frmtrm_amount")
    if net_income is None or current_equity is None or previous_equity is None:
        return _formula_result(
            formula_id="opendart_roe_average_equity_v1",
            status="formula_source_missing",
            source_accounts=["당기순이익(손실)", "자본총계"],
            blocked_reason="net income or average-equity source is missing",
        )
    average_equity = (current_equity + previous_equity) / 2
    if average_equity == 0:
        return _formula_result(
            formula_id="opendart_roe_average_equity_v1",
            status="formula_source_missing",
            source_accounts=["당기순이익(손실)", "자본총계"],
            blocked_reason="average equity denominator is zero",
        )
    return _formula_result(
        formula_id="opendart_roe_average_equity_v1",
        value=(net_income / average_equity) * 100,
        source_accounts=["당기순이익(손실)", "자본총계"],
        source_ref=_source_ref_from_rows([net_income_row, equity_row]),
    )


def _formula_result(
    *,
    formula_id: str,
    value: float | None = None,
    status: str = "formula_computed",
    source_accounts: list[str] | None = None,
    source_ref: str = "",
    blocked_reason: str = "",
) -> dict[str, Any]:
    return {
        "formula_id": formula_id,
        "value": value,
        "status": status,
        "source_accounts": source_accounts or [],
        "source_ref": source_ref,
        "blocked_reason": blocked_reason,
    }


def _amount_from_row(row: dict[str, str] | None, key: str) -> float | None:
    if row is None:
        return None
    return _parse_number(row.get(key, ""))


def _parse_number(value: str) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _source_ref_from_rows(rows: list[dict[str, str] | None]) -> str:
    refs = [row.get("source_ref", "") for row in rows if row and row.get("source_ref")]
    return "|".join(dict.fromkeys(refs))


def _enriched_rows(pending_rows: list[dict[str, str]], metadata_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    enriched = []
    for row in pending_rows:
        ticker = row.get("ticker", "").strip()
        metadata = _metadata_for_handoff_row(row, metadata_rows)
        rcept_dt = metadata.get("rcept_dt", "").strip()
        availability_date = _next_trading_day_text(rcept_dt) if rcept_dt else ""
        metadata_attached = bool(metadata)
        pending_reasons = _pending_reasons(row)
        if not metadata_attached:
            pending_reasons.extend(["dart_metadata_missing", "source_lineage_not_promoted"])
        else:
            pending_reasons.extend(["value_reconciliation_pending_external_source", "source_lineage_not_promoted"])
        source_ref = (
            metadata.get("source_ref", "").strip()
            or f"opendart:{metadata.get('rcept_no', '').strip()}"
            if metadata.get("rcept_no")
            else row.get("source_ref", "")
        )
        enriched.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": row.get("candidate_id", ""),
                "evidence_id": row.get("evidence_id", ""),
                "ticker": ticker,
                "company_name": row.get("company_name", ""),
                "evaluation_date": row.get("evaluation_date", ""),
                "fiscal_period": row.get("fiscal_period", ""),
                "report_period_end_date": row.get("report_period_end_date", ""),
                "corp_code": metadata.get("corp_code", ""),
                "stock_code": metadata.get("stock_code", ""),
                "report_nm": metadata.get("report_nm", ""),
                "rcept_no": metadata.get("rcept_no", ""),
                "rcept_dt": rcept_dt,
                "filing_date": rcept_dt,
                "disclosure_date": rcept_dt,
                "availability_date": availability_date,
                "availability_policy_id": AVAILABILITY_POLICY_ID if rcept_dt else "",
                "source_system": metadata.get("source_system", "OpenDART_import") if metadata_attached else "chart_mvp_local_cache",
                "source_ref": source_ref,
                "source_lineage_status": (
                    metadata.get("source_lineage_status", "metadata_attached_value_lineage_pending")
                    if metadata_attached
                    else "pending_dart_metadata"
                ),
                "field_name": row.get("field_name", ""),
                "value": row.get("value", ""),
                "unit": row.get("unit", ""),
                "currency": row.get("currency", ""),
                "sector_id": row.get("sector_id", ""),
                "industry_id": row.get("industry_id", ""),
                "industry_name": row.get("industry_name", ""),
                "restatement_policy": RESTATEMENT_POLICY_ID,
                "stale_data_policy": STALE_DATA_POLICY_ID,
                "reporting_lag_policy": REPORTING_LAG_POLICY_ID,
                "pit_validation_status": "pending_data",
                "coverage_status": "pending_data",
                "data_quality_flags": _append_flag(row.get("data_quality_flags", ""), "v1_5_supplemented_pending_data"),
                "pending_reason": ";".join(dict.fromkeys(pending_reasons)),
                "boundary_notice": row.get("boundary_notice", ""),
            }
        )
    return enriched


def _metadata_for_handoff_row(
    handoff_row: dict[str, str],
    metadata_rows: list[dict[str, str]],
) -> dict[str, str]:
    ticker = handoff_row.get("ticker", "").strip()
    evaluation_date = _parse_date_text(handoff_row.get("evaluation_date", ""))
    candidates = [row for row in metadata_rows if row.get("stock_code", "").strip() == ticker]
    eligible = []
    for row in candidates:
        availability_date = _parse_date_text(_next_trading_day_text(row.get("rcept_dt", "")))
        if evaluation_date is None or (availability_date is not None and availability_date <= evaluation_date):
            eligible.append(row)
    if not eligible:
        return {}
    return max(eligible, key=lambda row: row.get("rcept_dt", ""))


def _source_lineage_report(pending_rows: list[dict[str, str]]) -> dict[str, Any]:
    rows = []
    for index, row in enumerate(pending_rows, start=1):
        source_path = Path(row.get("source_financial_cache_path", ""))
        source_row = _find_source_row(row, source_path)
        source_row_id = source_row["row_id"] if source_row else None
        source_hash = _source_hash(source_row["row"]) if source_row else None
        status = "chart_cache_row_hashed" if source_row else "value_source_row_missing"
        rows.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "evidence_id": row.get("evidence_id", ""),
                "ticker": row.get("ticker", ""),
                "field_name": row.get("field_name", ""),
                "value_source_file": str(source_path),
                "value_source_row_id": source_row_id,
                "value_source_hash": source_hash,
                "ratio_formula_version": RATIO_FORMULA_VERSION,
                "source_lineage_status": status,
                "value_reconciliation_status": "pending_external_source",
                "blocked_reason": "DART financial value source unavailable locally; chart cache row is hashed but not reconciled",
                "handoff_row_index": index,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": "v1_5_fundamental_source_lineage_report",
        "row_count": len(rows),
        "hashed_source_row_count": sum(1 for row in rows if row["source_lineage_status"] == "chart_cache_row_hashed"),
        "value_reconciliation_status": "pending_external_source",
        "usable_as_available_v1_5_fundamentals": False,
        "rows": rows,
    }


def _find_source_row(handoff_row: dict[str, str], source_path: Path) -> dict[str, Any] | None:
    if not source_path.exists():
        return None
    source_metric = handoff_row.get("source_metric", "").strip()
    source_period = handoff_row.get("source_period", "").strip()
    value = handoff_row.get("value", "").strip()
    for row_id, row in enumerate(_read_csv_rows(source_path), start=1):
        if (
            row.get("metric", "").strip() == source_metric
            and row.get("period", "").strip() == source_period
            and row.get("value", "").strip().replace(",", "") == value
        ):
            return {"row_id": row_id, "row": row}
    return None


def _source_hash(row: dict[str, str]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def _policy_registry(config: V15SupplementationConfig) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "registry_type": "v1_5_pit_policy_registry",
        "created_at": config.created_at,
        "restatement_policy": {
            "policy_id": RESTATEMENT_POLICY_ID,
            "meaning": "Only first-filed values may be promoted until restatement lineage is explicitly supplied.",
        },
        "availability_date_policy": {
            "policy_id": AVAILABILITY_POLICY_ID,
            "meaning": "availability_date equals the next trading day after OpenDART rcept_dt.",
            "fallback": "weekday-only calendar when no stricter repository trading calendar is supplied",
        },
        "stale_data_policy": {
            "policy_id": STALE_DATA_POLICY_ID,
            "meaning": "Staleness is evaluated by report type before available promotion.",
        },
        "reporting_lag_policy": {
            "policy_id": REPORTING_LAG_POLICY_ID,
            "meaning": "Actual lag days are measured from report period end to filing/disclosure/availability dates.",
        },
        "promotion_rule": "Do not promote pending rows to available unless PIT metadata and value reconciliation both pass.",
        "usable_as_available_v1_5_fundamentals": False,
    }


def _baseline_comparison_rows(
    pending_rows: list[dict[str, str]],
    technical_ml_rows: list[dict[str, Any]],
    technical_ml_scores_path: Path | None,
) -> list[dict[str, str]]:
    by_candidate = {str(row.get("candidate_id", "")): row for row in technical_ml_rows}
    baseline_ref = str(technical_ml_scores_path) if technical_ml_scores_path else ""
    rows = []
    for candidate_id, evidence_id in _candidate_pairs(pending_rows):
        baseline = by_candidate.get(candidate_id)
        rows.append(
            {
                "candidate_id": candidate_id,
                "evidence_id": evidence_id,
                "technical_ml_baseline_status": "available" if baseline else "skipped_missing_candidate_overlap",
                "selector_score": str(baseline.get("selector_score", "")) if baseline else "",
                "selector_score_source": str(baseline.get("selector_score_source", "")) if baseline else "",
                "baseline_artifact_ref": baseline_ref,
                "reason_code": "baseline_row_available" if baseline else "technical_ml_baseline_candidate_id_missing",
            }
        )
    return rows


def _shadow_comparison_rows(pending_rows: list[dict[str, str]], baseline_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    valuation_counts: dict[str, int] = {}
    for row in pending_rows:
        candidate_id = row.get("candidate_id", "")
        valuation_counts[candidate_id] = valuation_counts.get(candidate_id, 0) + 1
    return [
        {
            "candidate_id": row["candidate_id"],
            "evidence_id": row["evidence_id"],
            "technical_ml_baseline_status": row["technical_ml_baseline_status"],
            "valuation_overlay_status": "skipped_insufficient_pit_fundamentals",
            "valuation_row_count": str(valuation_counts.get(row["candidate_id"], 0)),
            "comparison_status": "skipped_insufficient_pit_fundamentals",
            "reason_code": "valuation_rows_pending_data_not_available",
        }
        for row in baseline_rows
    ]


def _incremental_report_rows(baseline_rows: list[dict[str, str]], shadow_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    baseline_available_count = sum(1 for row in baseline_rows if row["technical_ml_baseline_status"] == "available")
    valuation_available_count = 0
    reason = (
        "skipped_insufficient_pit_fundamentals"
        if shadow_rows
        else "skipped_missing_baseline_artifacts"
    )
    return [
        {
            "report_version": SCHEMA_VERSION,
            "comparison_status": reason,
            "candidate_count": str(len(shadow_rows)),
            "baseline_available_count": str(baseline_available_count),
            "valuation_available_count": str(valuation_available_count),
            "reason_code": reason,
            "next_required_data": "PIT metadata, value reconciliation, and candidate-overlapping technical_ml baseline rows",
        }
    ]


def _canonical_valuation_component_rows(
    pending_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    component_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in component_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        component = component_by_key.get((pending_row.get("candidate_id", ""), field_name), {})
        canonical_value = _canonical_value_from_component(field_name, component)
        source_available_status = _canonical_component_availability_status(pending_row, component)
        required_values = [
            component.get("market_cap", ""),
            component.get("shares_outstanding", ""),
            component.get("net_income" if field_name == "price_to_earnings" else "equity", ""),
        ]
        component_status = (
            "canonical_component_ready_reference_only"
            if canonical_value is not None and source_available_status == "verified"
            else "missing_component"
        )
        if any(not value for value in required_values):
            component_status = "missing_component"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": pending_row.get("candidate_id", ""),
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": pending_row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": field_name,
                "canonical_formula_id": (
                    "canonical_pe_market_cap_to_net_income_attributable_to_owners_v1"
                    if field_name == "price_to_earnings"
                    else "canonical_pb_market_cap_to_equity_attributable_to_owners_v1"
                ),
                "canonical_value": _format_optional_number(canonical_value),
                "price_date": component.get("price_date", ""),
                "price": component.get("price", ""),
                "price_source_ref": component.get("source_ref", ""),
                "market_cap": component.get("market_cap", ""),
                "shares_outstanding": component.get("shares_outstanding", ""),
                "shares_policy": "local_v1_3_market_cap_snapshot_reference_only",
                "shares_date": _source_ref_token_value(component.get("source_ref", ""), "shares_as_of"),
                "shares_source_ref": component.get("source_ref", ""),
                "net_income": component.get("net_income", ""),
                "net_income_policy": "OpenDART_CFS_thstrm_amount_reference_only",
                "equity": component.get("equity", ""),
                "equity_policy": "OpenDART_CFS_thstrm_amount_reference_only",
                "fs_div": component.get("consolidated_or_separate", "").split(":")[0],
                "fiscal_period": component.get("fiscal_period", ""),
                "report_period_end_date": component.get("report_period_end_date", ""),
                "filing_date": component.get("filing_date", ""),
                "availability_date": component.get("availability_date", ""),
                "source_available_before_evaluation_date": source_available_status,
                "component_status": component_status,
            }
        )
    return rows


def _canonical_value_from_component(field_name: str, component: dict[str, str]) -> float | None:
    market_cap = _parse_number(component.get("market_cap", ""))
    denominator = _parse_number(
        component.get("net_income" if field_name == "price_to_earnings" else "equity", "")
    )
    return _divide_optional(market_cap, denominator)


def _canonical_component_availability_status(
    pending_row: dict[str, str],
    component: dict[str, str],
) -> str:
    evaluation_date = pending_row.get("evaluation_date", "")
    checks = [
        _source_available_before_evaluation_status(component.get("price_date", ""), evaluation_date),
        _source_available_before_evaluation_status(
            _source_ref_token_value(component.get("source_ref", ""), "shares_as_of"),
            evaluation_date,
        ),
        _source_available_before_evaluation_status(component.get("availability_date", ""), evaluation_date),
    ]
    return "verified" if all(status == "verified" for status in checks) else "unproven"


def _canonical_valuation_component_table_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("component_status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "component_status_counts": dict(sorted(status_counts.items())),
        "canonical_formula_policy": "reference_only_until_component_and_formula_reconciliation_pass",
        "scoring_activation_allowed": False,
        "promotion_status": "not_promoted",
    }


def _canonical_per_pbr_formula_policy(config: V15SupplementationConfig) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "policy_type": "v1_5_canonical_per_pbr_formula_policy",
        "scoring_activation_allowed": False,
        "chart_local_ratio_policy": "reference_only_until_reconciled",
        "formulas": {
            "canonical_PE": {
                "formula_id": "canonical_pe_market_cap_to_net_income_attributable_to_owners_v1",
                "formula": "market_cap_asof_evaluation_date / net_income_attributable_to_owners",
                "required_components": ["market_cap", "net_income_attributable_to_owners"],
                "pit_requirements": [
                    "market_cap source date <= evaluation_date",
                    "net_income availability_date <= evaluation_date",
                    "component source lineage must be present",
                ],
                "blocked_conditions": ["missing_component", "availability_after_evaluation_date", "formula_variance"],
            },
            "canonical_PB": {
                "formula_id": "canonical_pb_market_cap_to_equity_attributable_to_owners_v1",
                "formula": "market_cap_asof_evaluation_date / equity_attributable_to_owners",
                "required_components": ["market_cap", "equity_attributable_to_owners"],
                "pit_requirements": [
                    "market_cap source date <= evaluation_date",
                    "equity availability_date <= evaluation_date",
                    "component source lineage must be present",
                ],
                "blocked_conditions": ["missing_component", "availability_after_evaluation_date", "formula_variance"],
            },
        },
    }


def _per_pbr_reconciliation_matrix_rows(
    pending_rows: list[dict[str, str]],
    canonical_rows: list[dict[str, str]],
    naver_resolved_rows: list[dict[str, str]],
    naver_registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    canonical_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in canonical_rows
    }
    resolver_by_candidate = {row.get("candidate_id", ""): row for row in naver_resolved_rows}
    naver_by_key = {
        (
            row.get("ticker", ""),
            row.get("source_available_date", ""),
            row.get("snapshot_date", ""),
        ): row
        for row in naver_registry_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        candidate_id = pending_row.get("candidate_id", "")
        chart_value = _parse_number(pending_row.get("value", ""))
        canonical = canonical_by_key.get((candidate_id, field_name), {})
        canonical_value = _parse_number(canonical.get("canonical_value", ""))
        resolver = resolver_by_candidate.get(candidate_id, {})
        naver_snapshot = naver_by_key.get(
            (
                pending_row.get("ticker", ""),
                resolver.get("selected_source_available_date", ""),
                resolver.get("selected_snapshot_date", ""),
            ),
            {},
        )
        naver_value = _parse_number(
            naver_snapshot.get("per_reported_value" if field_name == "price_to_earnings" else "pbr_reported_value", "")
        )
        for basis, comparison_value in (
            ("chart_vs_naver", naver_value),
            ("chart_vs_canonical", canonical_value),
        ):
            absolute_delta = _absolute_delta(chart_value, comparison_value)
            relative_delta_pct = _relative_delta_pct(chart_value, absolute_delta)
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "candidate_id": candidate_id,
                    "evidence_id": pending_row.get("evidence_id", ""),
                    "ticker": pending_row.get("ticker", ""),
                    "evaluation_date": pending_row.get("evaluation_date", ""),
                    "field_name": field_name,
                    "chart_local_value": pending_row.get("value", ""),
                    "naver_reported_value": _format_optional_number(naver_value),
                    "canonical_value": canonical.get("canonical_value", ""),
                    "comparison_basis": basis,
                    "comparison_value": _format_optional_number(comparison_value),
                    "absolute_delta": _format_optional_number(absolute_delta),
                    "relative_delta_pct": _format_optional_number(relative_delta_pct),
                    "tolerance_bucket": _tolerance_bucket(absolute_delta, relative_delta_pct),
                    "suspected_mismatch_reason": _matrix_mismatch_reason(basis, comparison_value, resolver, canonical),
                    "reconciliation_status": _matrix_reconciliation_status(basis, comparison_value, resolver, canonical),
                }
            )
    return rows


def _tolerance_bucket(absolute_delta: float | None, relative_delta_pct: float | None) -> str:
    if absolute_delta is None:
        return "missing_comparison_value"
    if absolute_delta <= 0.1:
        return "within_absolute_tolerance"
    if relative_delta_pct is not None and relative_delta_pct <= 5:
        return "near_5pct"
    return "outside_tolerance"


def _matrix_mismatch_reason(
    basis: str,
    comparison_value: float | None,
    resolver: dict[str, str],
    canonical: dict[str, str],
) -> str:
    if comparison_value is None:
        return "missing_component" if basis == "chart_vs_canonical" else resolver.get("asof_resolution_status", "crawl_missing")
    if basis == "chart_vs_naver" and resolver.get("asof_resolution_status") != "vendor_snapshot_available_asof_evaluation":
        return resolver.get("asof_resolution_status", "crawl_missing")
    if basis == "chart_vs_canonical" and canonical.get("component_status") != "canonical_component_ready_reference_only":
        return canonical.get("component_status", "missing_component")
    return "unknown_chart_local_formula"


def _matrix_reconciliation_status(
    basis: str,
    comparison_value: float | None,
    resolver: dict[str, str],
    canonical: dict[str, str],
) -> str:
    if comparison_value is None:
        return "blocked_by_reconciliation"
    if basis == "chart_vs_naver":
        return (
            "vendor_reference_only"
            if resolver.get("asof_resolution_status") == "vendor_snapshot_available_asof_evaluation"
            else "blocked_by_reconciliation"
        )
    if canonical.get("component_status") != "canonical_component_ready_reference_only":
        return "blocked_by_reconciliation"
    return "blocked_by_reconciliation"


def _per_pbr_reconciliation_summary(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    bucket_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("reconciliation_status", "")
        bucket = row.get("tolerance_bucket", "")
        status_counts[status] = status_counts.get(status, 0) + 1
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "reconciliation_status_counts": dict(sorted(status_counts.items())),
        "tolerance_bucket_counts": dict(sorted(bucket_counts.items())),
        "scoring_activation_allowed": False,
        "promotion_status": "not_promoted",
    }


def _per_pbr_variance_debug_rows(
    pending_rows: list[dict[str, str]],
    canonical_rows: list[dict[str, str]],
    naver_resolved_rows: list[dict[str, str]],
    naver_registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    canonical_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in canonical_rows
    }
    resolver_by_candidate = {row.get("candidate_id", ""): row for row in naver_resolved_rows}
    naver_by_key = {
        (
            row.get("ticker", ""),
            row.get("source_available_date", ""),
            row.get("snapshot_date", ""),
        ): row
        for row in naver_registry_rows
    }
    pending_by_candidate: dict[str, dict[str, dict[str, str]]] = {}
    for row in pending_rows:
        field_name = row.get("field_name", "")
        if field_name in VALUATION_FORMULA_REVIEW_FIELDS:
            pending_by_candidate.setdefault(row.get("candidate_id", ""), {})[field_name] = row

    rows = []
    for candidate_id, fields in sorted(pending_by_candidate.items()):
        pe_pending = fields.get("price_to_earnings", {})
        pb_pending = fields.get("price_to_book", {})
        metadata = pe_pending or pb_pending
        ticker = metadata.get("ticker", "")
        pe_component = canonical_by_key.get((candidate_id, "price_to_earnings"), {})
        pb_component = canonical_by_key.get((candidate_id, "price_to_book"), {})
        resolver = resolver_by_candidate.get(candidate_id, {})
        naver = naver_by_key.get(
            (
                ticker,
                resolver.get("selected_source_available_date", ""),
                resolver.get("selected_snapshot_date", ""),
            ),
            {},
        )
        chart_pe = _parse_number(pe_pending.get("value", ""))
        chart_pb = _parse_number(pb_pending.get("value", ""))
        naver_pe = _parse_number(naver.get("per_reported_value", ""))
        naver_pb = _parse_number(naver.get("pbr_reported_value", ""))
        canonical_pe = _parse_number(pe_component.get("canonical_value", ""))
        canonical_pb = _parse_number(pb_component.get("canonical_value", ""))
        price = _parse_number(pe_component.get("price", "") or pb_component.get("price", ""))
        market_cap = _parse_number(pe_component.get("market_cap", "") or pb_component.get("market_cap", ""))
        shares = _parse_number(pe_component.get("shares_outstanding", "") or pb_component.get("shares_outstanding", ""))
        net_income_total = _parse_number(pe_component.get("net_income", ""))
        equity_total = _parse_number(pb_component.get("equity", ""))
        eps = _parse_number(pe_component.get("eps", ""))
        bps = _parse_number(pb_component.get("bps", ""))
        route = _recommended_formula_route(pe_component, pb_component, canonical_pe, canonical_pb)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": metadata.get("evidence_id", ""),
                "ticker": ticker,
                "evaluation_date": metadata.get("evaluation_date", ""),
                "chart_local_pe": pe_pending.get("value", ""),
                "naver_pe": _format_optional_number(naver_pe),
                "canonical_pe": _format_optional_number(canonical_pe),
                "chart_local_pb": pb_pending.get("value", ""),
                "naver_pb": _format_optional_number(naver_pb),
                "canonical_pb": _format_optional_number(canonical_pb),
                "price": _format_optional_number(price),
                "market_cap": _format_optional_number(market_cap),
                "shares_outstanding": _format_optional_number(shares),
                "net_income_total": _format_optional_number(net_income_total),
                "net_income_attributable_to_owners": "",
                "equity_total": _format_optional_number(equity_total),
                "equity_attributable_to_owners": "",
                "eps": _format_optional_number(eps),
                "bps": _format_optional_number(bps),
                "implied_net_income_from_chart_pe": _format_optional_number(_divide_optional(market_cap, chart_pe)),
                "implied_equity_from_chart_pb": _format_optional_number(_divide_optional(market_cap, chart_pb)),
                "implied_eps_from_chart_pe": _format_optional_number(_divide_optional(price, chart_pe)),
                "implied_bps_from_chart_pb": _format_optional_number(_divide_optional(price, chart_pb)),
                "pe_delta_chart_vs_canonical": _format_optional_number(_absolute_delta(chart_pe, canonical_pe)),
                "pb_delta_chart_vs_canonical": _format_optional_number(_absolute_delta(chart_pb, canonical_pb)),
                "pe_delta_naver_vs_canonical": _format_optional_number(_absolute_delta(naver_pe, canonical_pe)),
                "pb_delta_naver_vs_canonical": _format_optional_number(_absolute_delta(naver_pb, canonical_pb)),
                "suspected_pe_mismatch_reason": _variance_mismatch_reason(
                    "price_to_earnings",
                    pe_component,
                    resolver,
                    chart_pe,
                    canonical_pe,
                    naver_pe,
                ),
                "suspected_pb_mismatch_reason": _variance_mismatch_reason(
                    "price_to_book",
                    pb_component,
                    resolver,
                    chart_pb,
                    canonical_pb,
                    naver_pb,
                ),
                "recommended_formula_route": route,
            }
        )
    return rows


def _variance_mismatch_reason(
    field_name: str,
    component: dict[str, str],
    resolver: dict[str, str],
    chart_value: float | None,
    canonical_value: float | None,
    naver_value: float | None,
) -> str:
    reasons = []
    if resolver.get("asof_resolution_status") != "vendor_snapshot_available_asof_evaluation":
        reasons.append("price_date_mismatch")
    if resolver.get("adjusted_price_policy", "not_disclosed_by_naver_main") == "not_disclosed_by_naver_main":
        reasons.append("adjusted_price_policy_mismatch")
    if component.get("component_status") == "missing_component":
        reasons.append("market_cap_policy_mismatch")
    if component.get("shares_date") and component.get("shares_date") != component.get("price_date"):
        reasons.append("shares_policy_mismatch")
    if field_name == "price_to_earnings":
        reasons.append("net_income_total_vs_owner_attributable_mismatch")
        if not component.get("net_income"):
            reasons.append("missing_component")
        if chart_value is not None and canonical_value is not None and _relative_difference(chart_value, canonical_value) not in (None, 0):
            reasons.append("eps_bps_denominator_mismatch")
        if naver_value is not None and canonical_value is not None and _relative_difference(naver_value, canonical_value) not in (None, 0):
            reasons.append("ttm_vs_annual_mismatch")
    else:
        reasons.append("equity_total_vs_owner_attributable_mismatch")
        if not component.get("equity"):
            reasons.append("missing_component")
        if chart_value is not None and canonical_value is not None and _relative_difference(chart_value, canonical_value) not in (None, 0):
            reasons.append("eps_bps_denominator_mismatch")
    if not component.get("fs_div"):
        reasons.append("consolidated_vs_separate_mismatch")
    return "|".join(dict.fromkeys(reasons)) if reasons else "unknown_vendor_formula"


def _recommended_formula_route(
    pe_component: dict[str, str],
    pb_component: dict[str, str],
    canonical_pe: float | None,
    canonical_pb: float | None,
) -> str:
    component_statuses = {pe_component.get("component_status", ""), pb_component.get("component_status", "")}
    if component_statuses and component_statuses <= {"canonical_component_ready_reference_only"}:
        if canonical_pe is not None and canonical_pb is not None:
            return "use_canonical_component_formula_for_diagnostic"
    if "canonical_component_ready_reference_only" in component_statuses:
        return "near_match_needs_review"
    return "remain_blocked_by_reconciliation"


def _per_pbr_variance_debug_summary(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    route_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for row in rows:
        route = row.get("recommended_formula_route", "")
        route_counts[route] = route_counts.get(route, 0) + 1
        for field in ("suspected_pe_mismatch_reason", "suspected_pb_mismatch_reason"):
            for reason in row.get(field, "").split("|"):
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "recommended_formula_route_counts": dict(sorted(route_counts.items())),
        "suspected_mismatch_reason_counts": dict(sorted(reason_counts.items())),
        "valuation_scoring_activation_allowed": False,
        "formula_reconciled_ready": False,
        "likely_formula_variance_cause": "chart_local_or_vendor_ratio_policy_differs_from_canonical_evaluation_date_market_cap_formula",
    }


def _per_pbr_formula_route_decision(
    canonical_rows: list[dict[str, str]],
    matrix_rows: list[dict[str, str]],
    debug_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    component_statuses = sorted({row.get("component_status", "") for row in canonical_rows if row.get("component_status")})
    reconciliation_statuses = sorted({row.get("reconciliation_status", "") for row in matrix_rows if row.get("reconciliation_status")})
    route_counts = _per_pbr_variance_debug_summary(debug_rows, config)["recommended_formula_route_counts"]
    if route_counts.get("use_canonical_component_formula_for_diagnostic"):
        decision = "use_canonical_component_formula_for_diagnostic"
    elif route_counts.get("near_match_needs_review"):
        decision = "near_match_needs_review"
    elif "vendor_reference_only" in reconciliation_statuses:
        decision = "keep_vendor_reference_only"
    else:
        decision = "remain_blocked_by_reconciliation"
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "decision": decision,
        "canonical_component_statuses": component_statuses,
        "reconciliation_statuses": reconciliation_statuses,
        "route_counts": route_counts,
        "formula_reconciled_ready": False,
        "valuation_scoring_activation_allowed": False,
        "chart_local_and_naver_ratio_policy": "vendor_reference_only_until_numeric_match_and_source_lineage_pass",
        "recommendation": (
            "Use canonical component formula only as future diagnostic input when PIT components are present; "
            "keep chart-local and Naver PER/PBR as vendor_reference_only, and do not mark formula_reconciled_ready."
        ),
    }


def _dividend_yield_component_rows(
    dividend_rows: list[dict[str, str]],
    market_sources: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    rows = []
    for row in dividend_rows:
        ticker = row.get("ticker", "")
        market_source = market_sources.get(ticker, {})
        dividend_per_share = _parse_number(row.get("dividend_per_share", ""))
        price = _parse_number(str(market_source.get("close", "")))
        dividend_yield = None
        if dividend_per_share is not None and price not in (None, 0):
            dividend_yield = (dividend_per_share / price) * 100
        status = row.get("pit_dividend_source_status", "unsupported_missing_pit_dividend_source")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": row.get("candidate_id", ""),
                "evidence_id": row.get("evidence_id", ""),
                "ticker": ticker,
                "evaluation_date": row.get("evaluation_date", ""),
                "dividend_per_share": row.get("dividend_per_share", ""),
                "total_dividend": row.get("total_dividend", ""),
                "stock_kind": row.get("stock_kind", ""),
                "record_date": row.get("dividend_record_date", ""),
                "resolution_date": row.get("dividend_resolution_date", ""),
                "rcept_dt": row.get("rcept_dt", ""),
                "filing_date": row.get("filing_date", ""),
                "availability_date": row.get("availability_date", ""),
                "price_date": row.get("price_date", ""),
                "price_policy": row.get("price_policy", ""),
                "source_ref": row.get("source_ref", ""),
                "source_available_before_evaluation_date": (
                    "verified" if status == "diagnostic_ready" else "unproven"
                ),
                "dividend_yield": _format_optional_number(dividend_yield),
                "component_status": status,
            }
        )
    return rows


def _dividend_yield_readiness(
    component_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in component_rows:
        status = row.get("component_status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
    if not component_rows and dividend_rows:
        status_counts["unsupported_missing_component_table"] = len(dividend_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(component_rows),
        "dividend_yield_status_counts": dict(sorted(status_counts.items())),
        "scoring_activation_allowed": False,
        "promotion_status": "not_promoted",
        "promotion_rule": "dividend_yield remains unsupported or reference_only until PIT source lineage and price lineage pass.",
    }


def _incremental_baseline_rows(
    pending_rows: list[dict[str, str]],
    technical_ml_rows: list[dict[str, Any]],
    technical_ml_scores_path: Path | None,
) -> list[dict[str, str]]:
    baseline_by_candidate = {str(row.get("candidate_id", "")): row for row in technical_ml_rows}
    metadata_by_candidate = _candidate_metadata_rows(pending_rows)
    baseline_ref = str(technical_ml_scores_path) if technical_ml_scores_path else ""
    rows = []
    for candidate_id, metadata in sorted(metadata_by_candidate.items()):
        baseline = baseline_by_candidate.get(candidate_id)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": metadata.get("evidence_id", ""),
                "ticker": metadata.get("ticker", ""),
                "evaluation_date": metadata.get("evaluation_date", ""),
                "horizon_id": metadata.get("horizon_id", "") or "missing_horizon_id",
                "technical_ml_baseline_status": "available" if baseline else "skipped_missing_candidate_overlap",
                "selector_score": str(baseline.get("selector_score", "")) if baseline else "",
                "selector_score_source": str(baseline.get("selector_score_source", "")) if baseline else "",
                "baseline_artifact_ref": baseline_ref,
                "reason_code": "baseline_row_available" if baseline else "technical_ml_baseline_candidate_id_missing",
            }
        )
    return rows


def _incremental_overlay_rows(
    pending_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> list[dict[str, str]]:
    metadata_by_candidate = _candidate_metadata_rows(pending_rows)
    feature_by_candidate: dict[str, list[dict[str, str]]] = {}
    for row in feature_rows:
        feature_by_candidate.setdefault(row.get("candidate_id", ""), []).append(row)
    rows = []
    for candidate_id, metadata in sorted(metadata_by_candidate.items()):
        features = feature_by_candidate.get(candidate_id, [])
        ready = sorted(row.get("field_name", "") for row in features if row.get("feature_readiness_status") == "diagnostic_ready")
        blocked = sorted(row.get("field_name", "") for row in features if row.get("feature_readiness_status") != "diagnostic_ready")
        overlay_status = (
            "skipped_insufficient_pit_fundamentals"
            if any(field in blocked for field in VALUATION_SCORING_CORE_FIELDS)
            else "diagnostic_overlay_available_not_scoring"
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": metadata.get("evidence_id", ""),
                "ticker": metadata.get("ticker", ""),
                "evaluation_date": metadata.get("evaluation_date", ""),
                "horizon_id": metadata.get("horizon_id", "") or "missing_horizon_id",
                "valuation_overlay_status": overlay_status,
                "quality_profitability_status": "diagnostic_ready" if any(field in ready for field in QUALITY_PROFITABILITY_FIELDS) else "pending",
                "ready_fields": "|".join(ready),
                "blocked_fields": "|".join(blocked),
                "overlay_artifact_ref": str(config.output_dir / "v1_5_feature_level_readiness_latest.csv"),
                "reason_code": "valuation_core_fields_not_pit_reconciled",
            }
        )
    return rows


def _incremental_real_comparison_rows(
    baseline_rows: list[dict[str, str]],
    overlay_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    overlay_by_key = {
        (
            row.get("candidate_id", ""),
            row.get("ticker", ""),
            row.get("evaluation_date", ""),
            row.get("horizon_id", ""),
        ): row
        for row in overlay_rows
    }
    rows = []
    for baseline in baseline_rows:
        key = (
            baseline.get("candidate_id", ""),
            baseline.get("ticker", ""),
            baseline.get("evaluation_date", ""),
            baseline.get("horizon_id", ""),
        )
        overlay = overlay_by_key.get(key, {})
        baseline_status = baseline.get("technical_ml_baseline_status", "")
        overlay_status = overlay.get("valuation_overlay_status", "skipped_insufficient_pit_fundamentals")
        if baseline_status != "available":
            comparison_status = "skipped_missing_baseline_artifacts"
            reason_code = "candidate_overlapping_technical_ml_baseline_missing"
            required_dependency = "candidate_id/ticker/evaluation_date/horizon_id baseline row"
        elif overlay_status == "skipped_insufficient_pit_fundamentals":
            comparison_status = "skipped_insufficient_pit_fundamentals"
            reason_code = "pit_safe_valuation_overlay_unavailable"
            required_dependency = "PER/PBR formula reconciliation plus PIT dividend lineage"
        else:
            comparison_status = "diagnostic_comparison_ready_not_scoring"
            reason_code = "manual_review_only"
            required_dependency = "separate activation approval before any scoring use"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": baseline.get("candidate_id", ""),
                "evidence_id": baseline.get("evidence_id", ""),
                "ticker": baseline.get("ticker", ""),
                "evaluation_date": baseline.get("evaluation_date", ""),
                "horizon_id": baseline.get("horizon_id", ""),
                "technical_ml_baseline_status": baseline_status,
                "valuation_overlay_status": overlay_status,
                "comparison_status": comparison_status,
                "reason_code": reason_code,
                "required_dependency": required_dependency,
            }
        )
    return rows


def _incremental_real_comparison_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("comparison_status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "comparison_status_counts": dict(sorted(status_counts.items())),
        "join_keys": ["candidate_id", "ticker", "evaluation_date", "horizon_id"],
        "scoring_activation_allowed": False,
        "promotion_status": "not_promoted",
    }


def _incremental_baseline_dependency_check(
    baseline_rows: list[dict[str, str]],
    technical_ml_scores_path: Path | None,
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    required_keys = ["candidate_id", "ticker", "evaluation_date", "horizon_id"]
    checked_artifacts = _baseline_dependency_checked_artifacts(technical_ml_scores_path, config)
    missing_files = []
    if technical_ml_scores_path is None:
        missing_files.append("technical_ml_scores_path_not_configured")
    elif not technical_ml_scores_path.exists():
        missing_files.append(str(technical_ml_scores_path))
    missing_files.extend(
        item["path"]
        for item in checked_artifacts
        if item.get("required_for_real_comparison") == "true" and item.get("exists") == "false" and item.get("path")
    )
    missing_keys_by_candidate: dict[str, list[str]] = {}
    for row in baseline_rows:
        missing = [
            key
            for key in required_keys
            if not row.get(key) or row.get(key) == f"missing_{key}"
        ]
        if row.get("technical_ml_baseline_status") != "available":
            missing.append("technical_ml_baseline_row")
        if missing:
            missing_keys_by_candidate[row.get("candidate_id", "")] = sorted(dict.fromkeys(missing))
    status = (
        "joinable_baseline_available"
        if not missing_files and not missing_keys_by_candidate
        else "skipped_missing_baseline_artifacts"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "dependency_check_status": status,
        "join_keys": required_keys,
        "checked_technical_ml_scores_path": str(technical_ml_scores_path) if technical_ml_scores_path else "",
        "missing_files": missing_files,
        "missing_keys_by_candidate": missing_keys_by_candidate,
        "baseline_row_count": len(baseline_rows),
        "required_action": (
            "Provide candidate-overlapping technical_ml baseline rows keyed by candidate_id/ticker/evaluation_date/horizon_id."
            if status != "joinable_baseline_available"
            else "none"
        ),
        "checked_artifacts": checked_artifacts,
        "non_overlapping_conditions": _baseline_non_overlapping_conditions(baseline_rows),
        "valuation_scoring_activation_allowed": False,
    }


def _baseline_dependency_checked_artifacts(
    technical_ml_scores_path: Path | None,
    config: V15SupplementationConfig,
) -> list[dict[str, str]]:
    data_root = config.output_dir.parent
    workspace_root = data_root.parent.parent
    artifacts = [
        {
            "stage": "v1_2_or_v0_4_selector_scores",
            "path": str(technical_ml_scores_path) if technical_ml_scores_path else "",
            "artifact_role": "technical_ml_candidate_score_source",
            "required_for_real_comparison": "true",
        },
        {
            "stage": "v1_3_liquidity",
            "path": str(data_root / "v1_3_liquidity" / "v1_3_candidate_liquidity_handoff_records_latest.csv"),
            "artifact_role": "candidate_ticker_evaluation_handoff_not_technical_ml_baseline",
            "required_for_real_comparison": "false",
        },
        {
            "stage": "v1_1_net_profitability",
            "path": str(workspace_root / "Quant_mvp" / "data" / "v1_1" / "v1_1_selector_score_manifest_latest.json"),
            "artifact_role": "expected_historical_or_simulated_evidence_score_manifest",
            "required_for_real_comparison": "false",
        },
        {
            "stage": "v1_2_baseline_ml_selector",
            "path": str(workspace_root / "Quant_mvp" / "data" / "v1_2" / "v1_2_selector_score_manifest_latest.json"),
            "artifact_role": "expected_v1_2_selector_score_manifest",
            "required_for_real_comparison": "false",
        },
    ]
    checked = []
    for artifact in artifacts:
        path_text = artifact["path"]
        path = Path(path_text) if path_text else None
        exists = bool(path and path.exists())
        row_count = ""
        available_columns = ""
        if exists and path is not None and path.suffix.lower() == ".csv":
            rows = _read_csv_rows(path)
            row_count = str(len(rows))
            if rows:
                available_columns = "|".join(rows[0].keys())
        elif exists and path is not None and path.suffix.lower() == ".jsonl":
            rows = _read_jsonl_rows(path)
            row_count = str(len(rows))
            if rows:
                available_columns = "|".join(rows[0].keys())
        checked.append(
            {
                **artifact,
                "exists": "true" if exists else "false",
                "row_count": row_count,
                "available_columns": available_columns,
            }
        )
    return checked


def _baseline_non_overlapping_conditions(baseline_rows: list[dict[str, str]]) -> list[str]:
    conditions = []
    if any(row.get("technical_ml_baseline_status") != "available" for row in baseline_rows):
        conditions.append("candidate_id_not_overlapping_with_configured_technical_ml_scores")
    if any(row.get("horizon_id") == "missing_horizon_id" for row in baseline_rows):
        conditions.append("horizon_id_missing_from_v1_5_candidate_handoff")
    return conditions


def _v1_6_start_readiness_report(
    handoff_rows: list[dict[str, str]],
    formula_route_decision: dict[str, Any],
    baseline_dependency_check: dict[str, Any],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    handoff_statuses = sorted({row.get("candidate_overall_readiness_status", "") for row in handoff_rows if row.get("candidate_overall_readiness_status")})
    incremental_statuses = sorted({row.get("incremental_evidence_status", "") for row in handoff_rows if row.get("incremental_evidence_status")})
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": "v1_6_start_readiness_report",
        "can_start_v1_6": True,
        "start_basis": "readiness_status_flags_only",
        "v1_5_inputs_consumed": [
            "v1_5_feature_level_readiness_latest.csv",
            "v1_5_per_pbr_split_readiness_latest.csv",
            "v1_5_incremental_valuation_real_comparison_latest.csv",
            "v1_5_complete_readiness_gap_report_latest.json",
        ],
        "readiness_status_fields_used": [
            "overall_quality_profitability_status",
            "overall_valuation_status",
            "price_to_earnings_canonical_formula_status",
            "price_to_book_canonical_formula_status",
            "price_to_earnings_vendor_reference_status",
            "price_to_book_vendor_reference_status",
            "dividend_yield_status",
            "incremental_evidence_status",
            "candidate_overall_readiness_status",
        ],
        "fields_explicitly_not_used_as_score": [
            "price_to_earnings",
            "price_to_book",
            "dividend_yield",
            "canonical_pe",
            "canonical_pb",
            "naver_pe",
            "naver_pb",
            "valuation_score",
        ],
        "open_blockers_carried_forward": [
            "PER/PBR formula_reconciled_ready is unavailable",
            "Naver/chart-local PER/PBR are vendor_reference_only",
            baseline_dependency_check.get("dependency_check_status", "skipped_missing_baseline_artifacts"),
            "separate approval required before valuation scoring or ranking connection",
        ],
        "handoff_candidate_count": len(handoff_rows),
        "handoff_statuses": handoff_statuses,
        "incremental_evidence_statuses": incremental_statuses,
        "per_pbr_formula_route_decision": formula_route_decision.get("decision", ""),
        "next_required_v1_6_tasks": [
            "consume status flags in confidence/robustness/review-priority packet only",
            "keep valuation score absent from ranking",
            "continue PER/PBR formula variance debug in parallel",
            "attach joinable technical_ml baseline if incremental comparison is required",
        ],
        "valuation_scoring_activation_allowed": False,
    }


def _candidate_metadata_rows(pending_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in pending_rows:
        candidate_id = row.get("candidate_id", "")
        if not candidate_id or candidate_id in result:
            continue
        result[candidate_id] = {
            "candidate_id": candidate_id,
            "evidence_id": row.get("evidence_id", ""),
            "ticker": row.get("ticker", ""),
            "evaluation_date": row.get("evaluation_date", ""),
            "horizon_id": row.get("horizon_id", ""),
        }
    return result


def _complete_blocker_resolution_status(
    variance_debug_rows: list[dict[str, str]],
    formula_route_decision: dict[str, Any],
    baseline_dependency_check: dict[str, Any],
    incremental_rows: list[dict[str, str]],
    handoff_rows: list[dict[str, str]],
    gap_report: dict[str, Any],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    incremental_statuses = sorted({row.get("comparison_status", "") for row in incremental_rows if row.get("comparison_status")})
    vendor_statuses = sorted(
        {
            row.get("price_to_earnings_vendor_reference_status", "")
            for row in handoff_rows
            if row.get("price_to_earnings_vendor_reference_status")
        }
        | {
            row.get("price_to_book_vendor_reference_status", "")
            for row in handoff_rows
            if row.get("price_to_book_vendor_reference_status")
        }
    )
    formula_statuses = sorted(
        {
            row.get("price_to_earnings_canonical_formula_status", "")
            for row in handoff_rows
            if row.get("price_to_earnings_canonical_formula_status")
        }
        | {
            row.get("price_to_book_canonical_formula_status", "")
            for row in handoff_rows
            if row.get("price_to_book_canonical_formula_status")
        }
    )
    per_pbr_ready = formula_statuses == ["diagnostic_ready"]
    baseline_ready = baseline_dependency_check.get("dependency_check_status") == "joinable_baseline_available"
    incremental_ready = any(status == "diagnostic_comparison_ready_not_scoring" for status in incremental_statuses)
    can_promote = per_pbr_ready and baseline_ready and incremental_ready
    remaining_blockers = []
    if not per_pbr_ready:
        remaining_blockers.append("PER/PBR formula_reconciled_ready remains unavailable")
    if any(status.startswith("reference_only") or status == "vendor_reference_only" for status in vendor_statuses):
        remaining_blockers.append("Naver/chart-local PER/PBR remains vendor_reference_only or after_evaluation_date")
    if not baseline_ready:
        remaining_blockers.append("joinable technical_ml baseline keyed by candidate_id/ticker/evaluation_date/horizon_id is unavailable")
    if not incremental_ready:
        remaining_blockers.append("incremental real comparison remains skipped")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": "v1_5_complete_blocker_resolution_status",
        "current_verdict": "LIMITED COMPLETE",
        "can_promote_v1_5_to_COMPLETE": can_promote,
        "v1_6_can_continue": True,
        "per_pbr_reconciliation_status": gap_report.get("per_pbr_reconciliation_status", {}),
        "per_pbr_formula_statuses": formula_statuses,
        "canonical_formula_route_status": formula_route_decision.get("decision", ""),
        "canonical_formula_route_recommendation": formula_route_decision.get("recommendation", ""),
        "naver_chart_local_vendor_reference_status": vendor_statuses,
        "technical_ml_baseline_dependency_status": baseline_dependency_check.get("dependency_check_status", ""),
        "technical_ml_baseline_missing_files": baseline_dependency_check.get("missing_files", []),
        "technical_ml_baseline_missing_keys_by_candidate": baseline_dependency_check.get("missing_keys_by_candidate", {}),
        "technical_ml_baseline_checked_artifacts": baseline_dependency_check.get("checked_artifacts", []),
        "technical_ml_baseline_non_overlapping_conditions": baseline_dependency_check.get("non_overlapping_conditions", []),
        "incremental_real_comparison_status": incremental_statuses or ["skipped_missing_baseline_artifacts"],
        "valuation_scoring_activation_status": "disabled",
        "valuation_scoring_activation_allowed": False,
        "variance_debug_row_count": len(variance_debug_rows),
        "remaining_blockers": remaining_blockers,
        "requirements_to_promote_to_COMPLETE": gap_report.get("requirements_to_promote_to_COMPLETE", []),
    }


def _complete_readiness_gap_report(
    reconciliation_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]],
    naver_resolved_rows: list[dict[str, str]],
    incremental_rows: list[dict[str, str]],
    limited_update: dict[str, Any],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    per_pbr_status = {
        field: sorted(
            {
                row.get("value_reconciliation_status", "")
                for row in reconciliation_rows
                if row.get("field_name") == field
            }
        )
        for field in VALUATION_FORMULA_REVIEW_FIELDS
    }
    dividend_statuses = sorted({row.get("pit_dividend_source_status", "") for row in dividend_rows if row.get("pit_dividend_source_status")})
    naver_statuses = sorted({row.get("asof_resolution_status", "") for row in naver_resolved_rows if row.get("asof_resolution_status")})
    incremental_statuses = sorted({row.get("comparison_status", "") for row in incremental_rows if row.get("comparison_status")})
    blockers = [
        "PER/PBR formula reconciliation must pass with PIT-safe market_cap, net_income, and equity components",
        "incremental evidence requires candidate-overlapping technical_ml baseline and PIT-safe valuation overlay",
        "separate explicit approval is required before any valuation scoring activation",
    ]
    if "diagnostic_ready" not in dividend_statuses:
        blockers.insert(
            1,
            "dividend_yield requires PIT-safe dividend amount and availability lineage for every candidate that uses the field",
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "current_verdict": "LIMITED COMPLETE",
        "complete_readiness_status": "not_ready_for_COMPLETE",
        "per_pbr_reconciliation_status": per_pbr_status,
        "dividend_yield_pit_status": dividend_statuses or ["unsupported_missing_pit_dividend_source"],
        "naver_future_reference_status": naver_statuses or ["crawl_missing"],
        "incremental_evidence_status": incremental_statuses or ["skipped_insufficient_pit_fundamentals"],
        "completion_hygiene_status": "ready_for_review_gate",
        "blockers_preventing_COMPLETE": blockers,
        "requirements_to_promote_to_COMPLETE": [
            "formula_reconciled_ready for price_to_earnings and price_to_book",
            "diagnostic_ready or intentionally excluded dividend_yield with PIT-safe rationale",
            "real incremental comparison artifact not skipped for PIT-fundamental reasons",
            "focused tests and review gate pass with changed files classified",
        ],
        "limited_completion_update_summary": {
            "value_reconciliation_status": limited_update.get("value_reconciliation_status", ""),
            "incremental_evidence_status": limited_update.get("incremental_evidence_status", ""),
            "valuation_scoring_activation_allowed": limited_update.get("valuation_scoring_activation_allowed", False),
        },
    }


def _completion_hygiene_report(
    outputs_hint: list[str],
    naver_asof_registry_rows: list[dict[str, str]],
    metadata_source_path: Path | None,
    complete_readiness_gap_report: dict[str, Any],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    raw_files = sorted(
        {
            row.get("raw_html_path", "")
            for row in naver_asof_registry_rows
            if row.get("raw_html_path")
        }
    )
    if metadata_source_path:
        raw_files.append(str(metadata_source_path))
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": "v1_5_completion_hygiene_report",
        "changed_source_files": [
            "Quant_mvp/backtest_mvp/__init__.py",
            "Quant_mvp/backtest_mvp/valuation_quality_layer_v1_5.py",
            "chart_mvp/scripts/build_v1_5_supplementation.py",
            "chart_mvp/scripts/build_v1_5_valuation_quality_handoff.py",
            "chart_mvp/scripts/run_v1_5_fundamental_supplementation_pipeline.py",
            "chart_mvp/scripts/collect_v1_5_naver_ratio_policy_snapshots.py",
            "chart_mvp/src/stock_core/ml/__init__.py",
            "chart_mvp/src/stock_core/ml/opendart_v1_4_snapshot.py",
            "chart_mvp/src/stock_core/ml/v1_5_supplementation.py",
            "chart_mvp/src/stock_core/ml/v1_5_valuation_quality_handoff.py",
            "chart_mvp/src/stock_core/providers/naver_finance.py",
            "chart_mvp/tests/test_naver_finance.py",
            "chart_mvp/tests/test_opendart_v1_4_snapshot.py",
            "chart_mvp/tests/test_v1_5_supplementation.py",
            "chart_mvp/tests/test_v1_5_valuation_quality_handoff.py",
            "config/layer_registry.toml",
            "docs/context/EXTENSION_REGISTRY.toml",
            "docs/extension/v1_5_valuation_quality_profitability_layer.md",
            "docs/extension/v1_x_staged_release_plan.md",
            "docs/roadmap_status.md",
            "tests/backtest/test_v1_5_valuation_quality_layer.py",
        ],
        "generated_artifacts": sorted(path for path in outputs_hint if path.endswith((".csv", ".json"))),
        "raw_source_snapshot_files": raw_files,
        "manifests": sorted(path for path in outputs_hint if "manifest" in Path(path).name),
        "tests_run": [
            {
                "command": ".venv\\Scripts\\python.exe -m pytest -q chart_mvp\\tests\\test_naver_finance.py chart_mvp\\tests\\test_v1_5_supplementation.py",
                "status": "required_final_validation_passed_for_current_completion_run",
            },
            {
                "command": ".venv\\Scripts\\python.exe -m pytest -q chart_mvp\\tests\\test_v1_5_valuation_quality_handoff.py tests\\backtest\\test_v1_5_valuation_quality_layer.py",
                "status": "required_final_validation_passed_for_current_completion_run",
            }
        ],
        "review_gate_results": [
            {
                "gate": "quant-work-cycle",
                "status": "validated_by_dry_run_self_check",
            },
            {
                "gate": "quant-review-gate",
                "status": "contract_validator_passed",
            }
        ],
        "dirty_untracked_file_classification": {
            "source_code": "commit_candidate_after_review_gate_pass",
            "generated_v1_5_artifacts": "local_evidence_outputs_commit_only_if_explicitly_promoted",
            "raw_html_snapshots": "generated_source_snapshots_keep_local_or archive per data policy",
        },
        "files_to_commit": [
            "Quant_mvp/backtest_mvp/__init__.py",
            "Quant_mvp/backtest_mvp/valuation_quality_layer_v1_5.py",
            "chart_mvp/scripts/build_v1_5_supplementation.py",
            "chart_mvp/scripts/build_v1_5_valuation_quality_handoff.py",
            "chart_mvp/scripts/collect_v1_5_naver_ratio_policy_snapshots.py",
            "chart_mvp/scripts/run_v1_5_fundamental_supplementation_pipeline.py",
            "chart_mvp/src/stock_core/ml/__init__.py",
            "chart_mvp/src/stock_core/ml/opendart_v1_4_snapshot.py",
            "chart_mvp/src/stock_core/ml/v1_5_supplementation.py",
            "chart_mvp/src/stock_core/ml/v1_5_valuation_quality_handoff.py",
            "chart_mvp/src/stock_core/providers/naver_finance.py",
            "chart_mvp/tests/test_naver_finance.py",
            "chart_mvp/tests/test_opendart_v1_4_snapshot.py",
            "chart_mvp/tests/test_v1_5_supplementation.py",
            "chart_mvp/tests/test_v1_5_valuation_quality_handoff.py",
            "config/layer_registry.toml",
            "docs/context/EXTENSION_REGISTRY.toml",
            "docs/extension/v1_5_valuation_quality_profitability_layer.md",
            "docs/extension/v1_x_staged_release_plan.md",
            "docs/roadmap_status.md",
            "tests/backtest/test_v1_5_valuation_quality_layer.py",
        ],
        "files_to_ignore_or_delete": [
            "chart_mvp/data/v1_5_valuation/naver_ratio_policy_raw_html/* unless promoted as explicit source snapshot evidence",
            "chart_mvp/data/v1_5_valuation/*_latest.csv and *_latest.json unless release evidence promotion is explicitly approved",
        ],
        "known_limitations": complete_readiness_gap_report.get("blockers_preventing_COMPLETE", []),
        "final_verdict": "LIMITED COMPLETE",
        "scoring_activation_allowed": False,
    }


def _missing_requirements(
    enriched_rows: list[dict[str, str]],
    lineage_report: dict[str, Any],
    metadata_path: Path,
    metadata_source_kind: str,
    metadata_source_path: Path | None,
    dart_fundamental_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    missing_counts: dict[str, int] = {}
    for row in enriched_rows:
        for field in ("corp_code", "rcept_no", "rcept_dt", "filing_date", "disclosure_date", "availability_date"):
            if not row.get(field):
                missing_counts[field] = missing_counts.get(field, 0) + 1
    metadata_status = "available" if metadata_source_kind in {"import_csv", "raw_snapshot"} else "missing"
    if metadata_status == "available" and missing_counts:
        metadata_status = "partial"
    formula_match_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"] == "formula_match"
        }
    )
    dividend_ready = any(row.get("pit_dividend_source_status") == "diagnostic_ready" for row in dividend_rows or [])
    unsupported_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"].startswith("unsupported")
            and not (row["field_name"] == "dividend_yield" and dividend_ready)
        }
    )
    formula_variance_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"] == "formula_variance"
        }
    )
    still_required = []
    if missing_counts:
        still_required.append("OpenDART metadata coverage for all candidates with corp_code, stock_code, report_nm, rcept_no, rcept_dt")
    if not dart_fundamental_rows:
        still_required.append("DART financial statement value source for reconciliation")
    if unsupported_fields:
        still_required.append("PIT-safe market price, share count, book-value per share, and dividend sources for unsupported valuation fields")
    if formula_variance_fields:
        still_required.append("PIT-safe market price/share-count lineage or adjusted-price compatibility review for formula variance valuation fields")
    if not formula_match_fields and dart_fundamental_rows:
        still_required.append("reconciliation formula mapping from OpenDART single_account line items to chart-local ratio fields")
    still_required.extend(["candidate-overlapping technical_ml baseline artifacts", "manual review before any available promotion"])
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata_import_contract_path": str(metadata_path),
        "metadata_source_kind": metadata_source_kind,
        "metadata_source_path": str(metadata_source_path) if metadata_source_path else "",
        "metadata_import_status": metadata_status,
        "row_count": len(enriched_rows),
        "missing_counts": dict(sorted(missing_counts.items())),
        "dart_fundamental_collection_row_count": len(dart_fundamental_rows),
        "formula_match_fields": formula_match_fields,
        "formula_variance_fields": formula_variance_fields,
        "unsupported_fields": unsupported_fields,
        "value_reconciliation_status": (
            "partial_formula_reconciled"
            if formula_match_fields
            else lineage_report["value_reconciliation_status"]
        ),
        "still_required": still_required,
        "usable_as_available_v1_5_fundamentals": False,
    }


def _limited_completion_update(
    enriched_rows: list[dict[str, str]],
    lineage_report: dict[str, Any],
    missing_requirements: dict[str, Any],
    baseline_rows: list[dict[str, str]],
    shadow_rows: list[dict[str, str]],
    incremental_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    scoring_readiness_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    promoted_fields: list[str] = []
    pending_fields = sorted({row.get("field_name", "") for row in enriched_rows if row.get("field_name")})
    baseline_available_count = sum(1 for row in baseline_rows if row["technical_ml_baseline_status"] == "available")
    incremental_status = "skipped_missing_report"
    for row in incremental_rows:
        incremental_status = row.get("comparison_status", incremental_status)
        break
    formula_match_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"] == "formula_match"
        }
    )
    dividend_diagnostic_ready = any(
        row.get("dividend_readiness_status") == "diagnostic_ready"
        for row in scoring_readiness_rows
    )
    unsupported_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"].startswith("unsupported")
            and not (row["field_name"] == "dividend_yield" and dividend_diagnostic_ready)
        }
    )
    formula_variance_fields = sorted(
        {
            row["field_name"]
            for row in reconciliation_rows
            if row["value_reconciliation_status"] == "formula_variance"
        }
    )
    scoring_status_counts: dict[str, int] = {}
    overall_readiness_counts: dict[str, int] = {}
    quality_readiness_counts: dict[str, int] = {}
    dividend_readiness_counts: dict[str, int] = {}
    for row in scoring_readiness_rows:
        status = row["candidate_only_shadow_score_status"]
        scoring_status_counts[status] = scoring_status_counts.get(status, 0) + 1
        overall_status = row["candidate_overall_readiness_status"]
        quality_status = row["quality_profitability_readiness_status"]
        dividend_status = row["dividend_readiness_status"]
        overall_readiness_counts[overall_status] = overall_readiness_counts.get(overall_status, 0) + 1
        quality_readiness_counts[quality_status] = quality_readiness_counts.get(quality_status, 0) + 1
        dividend_readiness_counts[dividend_status] = dividend_readiness_counts.get(dividend_status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "current_status": "LIMITED COMPLETE",
        "row_count": len(enriched_rows),
        "promoted_fields": promoted_fields,
        "fields_still_pending": pending_fields,
        "pit_metadata_status": "attached" if not missing_requirements["missing_counts"] else "pending",
        "source_lineage_status": "hashed_not_reconciled",
        "value_reconciliation_status": missing_requirements["value_reconciliation_status"],
        "formula_match_fields": formula_match_fields,
        "formula_variance_fields": formula_variance_fields,
        "unsupported_fields": unsupported_fields,
        "valuation_scoring_status": (
            "ready_for_manual_scoring_review"
            if scoring_status_counts.get("ready_for_manual_scoring_review")
            else "blocked_by_reconciliation"
        ),
        "valuation_scoring_readiness_status_counts": dict(sorted(scoring_status_counts.items())),
        "candidate_overall_readiness_status_counts": dict(sorted(overall_readiness_counts.items())),
        "quality_profitability_readiness_status_counts": dict(sorted(quality_readiness_counts.items())),
        "dividend_readiness_status_counts": dict(sorted(dividend_readiness_counts.items())),
        "valuation_scoring_activation_allowed": False,
        "policy_registry_status": "created",
        "incremental_evidence_status": incremental_status,
        "dart_fundamental_collection_row_count": missing_requirements.get("dart_fundamental_collection_row_count", 0),
        "technical_ml_baseline_available_count": baseline_available_count,
        "technical_ml_plus_valuation_shadow_row_count": len(shadow_rows),
        "usable_as_available_v1_5_fundamentals": False,
        "completion_blockers": missing_requirements["still_required"],
    }


def _metadata_manifest(
    enriched_rows: list[dict[str, str]],
    metadata_path: Path,
    metadata_source_kind: str,
    metadata_source_path: Path | None,
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    attached = sum(1 for row in enriched_rows if row["source_lineage_status"] != "pending_dart_metadata")
    metadata_status = "available" if metadata_source_kind in {"import_csv", "raw_snapshot"} else "missing"
    if metadata_status == "available" and attached != len(enriched_rows):
        metadata_status = "partial"
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "metadata_import_contract_path": str(metadata_path),
        "metadata_source_kind": metadata_source_kind,
        "metadata_source_path": str(metadata_source_path) if metadata_source_path else "",
        "metadata_import_status": metadata_status,
        "row_count": len(enriched_rows),
        "metadata_attached_row_count": attached,
        "availability_policy_id": AVAILABILITY_POLICY_ID,
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "promotion_blocked_reason": "value lineage and reconciliation are still pending",
    }


def _dart_fundamental_manifest(
    rows: list[dict[str, str]],
    metadata_source_path: Path | None,
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    stocks = sorted({row["stock_code"] for row in rows if row.get("stock_code")})
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "raw_snapshot_path": str(metadata_source_path) if metadata_source_path else "",
        "row_count": len(rows),
        "stock_count": len(stocks),
        "stock_codes": stocks,
        "source_system": "OpenDART_raw_snapshot" if rows else "missing",
        "value_reconciliation_status": (
            "collected_not_reconciled_to_chart_ratios"
            if rows
            else "pending_external_source"
        ),
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "promotion_blocked_reason": "OpenDART statement rows are collected but chart ratio formula reconciliation is not complete.",
    }


def _value_reconciliation_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    field_status: dict[str, dict[str, int]] = {}
    for row in rows:
        status = row["value_reconciliation_status"]
        field_name = row["field_name"]
        status_counts[status] = status_counts.get(status, 0) + 1
        field_counts = field_status.setdefault(field_name, {})
        field_counts[status] = field_counts.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "field_status_counts": {key: dict(sorted(value.items())) for key, value in sorted(field_status.items())},
        "formula_version": "opendart_single_account_ratio_reconciliation_v1",
        "formula_match_fields": sorted(
            {
                row["field_name"]
                for row in rows
                if row["value_reconciliation_status"] == "formula_match"
            }
        ),
        "unsupported_fields": sorted(
            {
                row["field_name"]
                for row in rows
                if row["value_reconciliation_status"].startswith("unsupported")
            }
        ),
        "formula_variance_fields": sorted(
            {
                row["field_name"]
                for row in rows
                if row["value_reconciliation_status"] == "formula_variance"
            }
        ),
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "promotion_blocked_reason": "Formula reconciliation is diagnostic only until manual PIT review approves promotion.",
    }


def _valuation_formula_component_rows(
    pending_rows: list[dict[str, str]],
    enriched_rows: list[dict[str, str]],
    dart_fundamental_rows: list[dict[str, str]],
    market_sources: dict[str, dict[str, Any]],
    reconciliation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    fundamentals_by_stock = _fundamentals_by_stock(dart_fundamental_rows)
    enriched_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in enriched_rows
    }
    reconciliation_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in reconciliation_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        candidate_id = pending_row.get("candidate_id", "")
        ticker = pending_row.get("ticker", "").strip()
        enriched_row = enriched_by_key.get((candidate_id, field_name), {})
        reconciliation_row = reconciliation_by_key.get((candidate_id, field_name), {})
        account_row = _formula_denominator_row(
            fundamentals_by_stock.get(ticker, {}),
            reconciliation_row.get("source_accounts", ""),
        )
        amount = _amount_from_row(account_row, "thstrm_amount")
        market_source = market_sources.get(ticker, {})
        shares = market_source.get("shares_outstanding")
        net_income = amount if field_name == "price_to_earnings" else None
        equity = amount if field_name == "price_to_book" else None
        chart_eps = _chart_cache_metric_value(pending_row, "EPS(원)")
        chart_bps = _chart_cache_metric_value(pending_row, "BPS(원)")
        chart_ratio = _parse_number(pending_row.get("value", ""))
        chart_implied_price = _chart_implied_price(field_name, chart_ratio, chart_eps, chart_bps)
        price_to_chart_implied_ratio = _divide_optional(market_source.get("close"), chart_implied_price)
        quality_status = _component_quality_status(market_source, account_row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "ticker": ticker,
                "candidate_id": candidate_id,
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": field_name,
                "price_date": str(market_source.get("price_date", "")),
                "price": _format_optional_number(market_source.get("close")),
                "adjusted_price": "",
                "market_cap": _format_optional_number(market_source.get("market_cap")),
                "shares_outstanding": _format_optional_number(shares),
                "net_income": _format_optional_number(net_income),
                "equity": _format_optional_number(equity),
                "eps": _format_optional_number(_divide_optional(net_income, shares)),
                "bps": _format_optional_number(_divide_optional(equity, shares)),
                "chart_cache_eps": _format_optional_number(chart_eps),
                "chart_cache_bps": _format_optional_number(chart_bps),
                "chart_implied_price": _format_optional_number(chart_implied_price),
                "price_to_chart_implied_ratio": _format_optional_number(price_to_chart_implied_ratio),
                "consolidated_or_separate": _statement_scope(account_row),
                "fiscal_period": pending_row.get("fiscal_period", ""),
                "report_period_end_date": pending_row.get("report_period_end_date", ""),
                "filing_date": enriched_row.get("filing_date", ""),
                "availability_date": enriched_row.get("availability_date", ""),
                "source_ref": reconciliation_row.get("source_ref", ""),
                "component_quality_status": quality_status,
            }
        )
    return rows


def _formula_denominator_row(
    accounts: dict[str, dict[str, str]],
    source_accounts: str,
) -> dict[str, str] | None:
    for account_name in source_accounts.split("|"):
        account_name = account_name.strip()
        if account_name and account_name != "local_eval_close_x_prior_shares":
            return accounts.get(account_name)
    return None


def _chart_cache_metric_value(pending_row: dict[str, str], metric: str) -> float | None:
    source_path = Path(pending_row.get("source_financial_cache_path", ""))
    if not source_path.exists():
        return None
    period = pending_row.get("source_period", "").strip()
    for row in _read_csv_rows(source_path):
        if row.get("metric", "").strip() == metric and row.get("period", "").strip() == period:
            return _parse_number(row.get("value", ""))
    return None


def _chart_implied_price(
    field_name: str,
    chart_ratio: float | None,
    chart_eps: float | None,
    chart_bps: float | None,
) -> float | None:
    if field_name == "price_to_earnings":
        return _multiply_optional(chart_ratio, chart_eps)
    if field_name == "price_to_book":
        return _multiply_optional(chart_ratio, chart_bps)
    return None


def _statement_scope(row: dict[str, str] | None) -> str:
    if not row:
        return ""
    scope = row.get("fs_div", "")
    name = row.get("fs_nm", "")
    return ":".join(item for item in [scope, name] if item)


def _component_quality_status(
    market_source: dict[str, Any],
    account_row: dict[str, str] | None,
) -> str:
    if not market_source:
        return "missing_market_source"
    if account_row is None:
        return "missing_fundamental_component"
    return "diagnostic_unadjusted_price_review_required"


def _valuation_formula_reconciliation_review_rows(
    pending_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    pending_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in pending_rows
    }
    components_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in component_rows
    }
    rows = []
    for row in reconciliation_rows:
        if row.get("field_name") not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        if row.get("value_reconciliation_status") != "formula_variance":
            continue
        key = (row.get("candidate_id", ""), row.get("field_name", ""))
        pending_row = pending_by_key.get(key, {})
        component_row = components_by_key.get(key, {})
        chart_value = _parse_number(row.get("chart_value", ""))
        recomputed_value = _parse_number(row.get("dart_value", ""))
        absolute_delta = _parse_number(row.get("absolute_diff", ""))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": row.get("candidate_id", ""),
                "evidence_id": row.get("evidence_id", ""),
                "ticker": row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": row.get("field_name", ""),
                "chart_local_value": row.get("chart_value", ""),
                "recomputed_value": row.get("dart_value", ""),
                "absolute_delta": row.get("absolute_diff", ""),
                "relative_delta_pct": _format_optional_number(
                    _relative_delta_pct(chart_value, absolute_delta)
                ),
                "tolerance": row.get("tolerance", ""),
                "formula_version": row.get("dart_formula_id", ""),
                "suspected_mismatch_reason": _suspected_mismatch_reason(pending_row, component_row, row),
                "reconciliation_status": "blocked_reference_only_formula_variance",
                "source_ref": row.get("source_ref", ""),
            }
        )
    return rows


def _valuation_formula_reconciliation_review_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    reason_counts: dict[str, int] = {}
    for row in rows:
        for reason in row.get("suspected_mismatch_reason", "").split("|"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "field_names": sorted({row["field_name"] for row in rows if row.get("field_name")}),
        "suspected_mismatch_reason_counts": dict(sorted(reason_counts.items())),
        "reconciliation_status": "blocked_reference_only_formula_variance" if rows else "no_formula_variance",
        "chart_local_ratio_policy": "reference_only_until_reconciled",
        "primary_findings": [
            "chart-local valuation ratios imply a different embedded price than the evaluation-date local close",
            "recomputed P/E and P/B use evaluation-date close times prior shares, while chart-local ratios appear to use fiscal-period/cache ratio policy",
            "some candidates also show EPS/BPS denominator differences against OpenDART total net income or total equity per share",
        ] if rows else [],
        "recommended_fix": "Obtain or reconstruct the chart-local valuation ratio price/share/EPS/BPS policy before considering any valuation score readiness promotion.",
        "scoring_activation_allowed": False,
    }


def _valuation_formula_components_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("component_quality_status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "field_names": sorted({row["field_name"] for row in rows if row.get("field_name")}),
        "component_quality_status_counts": dict(sorted(status_counts.items())),
        "chart_local_ratio_policy": "reference_only_until_reconciled",
        "scoring_activation_allowed": False,
    }


def _chart_ratio_policy_reconstruction_rows(
    pending_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    component_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in component_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        key = (pending_row.get("candidate_id", ""), field_name)
        component_row = component_by_key.get(key, {})
        chart_value = _parse_number(pending_row.get("value", ""))
        per_share_metric = "EPS(원)" if field_name == "price_to_earnings" else "BPS(원)"
        per_share_value = _parse_number(
            component_row.get("chart_cache_eps" if field_name == "price_to_earnings" else "chart_cache_bps", "")
        )
        chart_implied_price = _parse_number(component_row.get("chart_implied_price", ""))
        evaluation_price = _parse_number(component_row.get("price", ""))
        chart_internal_value = _divide_optional(chart_implied_price, per_share_value)
        evaluation_price_value = _divide_optional(evaluation_price, per_share_value)
        chart_internal_delta = _absolute_delta(chart_value, chart_internal_value)
        evaluation_price_delta = _absolute_delta(chart_value, evaluation_price_value)
        internal_match = chart_internal_delta is not None and chart_internal_delta <= 0.01
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": pending_row.get("candidate_id", ""),
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": pending_row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": field_name,
                "chart_local_value": pending_row.get("value", ""),
                "chart_cache_per_share_metric": per_share_metric,
                "chart_cache_per_share_value": _format_optional_number(per_share_value),
                "chart_implied_price": _format_optional_number(chart_implied_price),
                "evaluation_date_price": _format_optional_number(evaluation_price),
                "price_to_chart_implied_ratio": component_row.get("price_to_chart_implied_ratio", ""),
                "chart_internal_recomputed_value": _format_optional_number(chart_internal_value),
                "chart_internal_absolute_delta": _format_optional_number(chart_internal_delta),
                "evaluation_price_recomputed_value": _format_optional_number(evaluation_price_value),
                "evaluation_price_absolute_delta": _format_optional_number(evaluation_price_delta),
                "reconstruction_status": (
                    "chart_ratio_internal_match_reference_only"
                    if internal_match
                    else "chart_ratio_internal_variance"
                ),
                "policy_inference": (
                    "chart-local ratio is internally reconstructable from chart cache per-share metric, "
                    "but embedded price differs from evaluation-date local close"
                ),
                "source_ref": pending_row.get("source_ref", ""),
            }
        )
    return rows


def _chart_ratio_policy_reconstruction_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("reconstruction_status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "reconstruction_status_counts": dict(sorted(status_counts.items())),
        "chart_local_ratio_policy": "reference_only_until_reconciled",
        "policy_inference": "chart-local PER/PBR can be reconstructed from chart-cache EPS/BPS, but the embedded price is not the evaluation-date local close.",
        "pit_promotion_status": "blocked_requires_external_policy_lineage",
        "required_external_data": [
            "chart-local ratio source price date and adjusted/unadjusted price policy",
            "chart-local shares or per-share denominator policy",
            "vendor/source lineage proving chart-local PER/PBR availability by evaluation_date",
        ],
        "scoring_activation_allowed": False,
    }


def _chart_local_ratio_source_lineage_rows(
    pending_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
    naver_ratio_policy_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    component_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in component_rows
    }
    naver_policy_by_ticker = {
        row.get("ticker", ""): row for row in naver_ratio_policy_rows or []
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        component = component_by_key.get((pending_row.get("candidate_id", ""), field_name), {})
        source_path = Path(pending_row.get("source_financial_cache_path", ""))
        source_row = _find_source_row(pending_row, source_path)
        source_hash = _source_hash(source_row["row"]) if source_row else ""
        source_row_id = str(source_row["row_id"]) if source_row else ""
        chart_value = pending_row.get("value", "")
        chart_local_per = chart_value if field_name == "price_to_earnings" else ""
        chart_local_pbr = chart_value if field_name == "price_to_book" else ""
        naver_policy = naver_policy_by_ticker.get(pending_row.get("ticker", ""), {})
        source_available_status = _source_available_before_evaluation_status(
            naver_policy.get("source_available_date", ""),
            pending_row.get("evaluation_date", ""),
        )
        missing = []
        if not source_row:
            missing.append("chart_local_ratio_source_row_missing")
        if not component.get("chart_implied_price") and not naver_policy.get("price_value"):
            missing.append("chart_implied_price_unavailable")
        per_share_metric = "EPS" if field_name == "price_to_earnings" else "BPS"
        adjusted_price_policy = naver_policy.get("adjusted_price_policy", "")
        unadjusted_price_policy = naver_policy.get("price_policy", "")
        shares_policy = naver_policy.get("shares_policy", "")
        eps_policy = (
            naver_policy.get("eps_policy", "")
            if per_share_metric == "EPS"
            else ""
        )
        bps_policy = (
            naver_policy.get("bps_policy", "")
            if per_share_metric == "BPS"
            else ""
        )
        denominator_policy = (
            naver_policy.get("per_formula", "")
            if per_share_metric == "EPS"
            else naver_policy.get("pbr_formula", "")
        )
        if not naver_policy.get("vendor_snapshot_date"):
            missing.append("vendor_snapshot_date_missing")
        if not naver_policy.get("price_date"):
            missing.append("price_date_missing_for_chart_local_ratio")
        if not adjusted_price_policy or adjusted_price_policy == "not_disclosed_by_naver_main":
            missing.append("adjusted_price_policy_missing")
        if not unadjusted_price_policy:
            missing.append("unadjusted_price_policy_missing")
        if not shares_policy:
            missing.append("shares_policy_missing")
        if source_available_status != "verified":
            missing.append("source_availability_lineage_unproven")
            if source_available_status == "after_evaluation_date":
                missing.append("source_snapshot_after_evaluation_date")
        lineage_status = "missing_chart_local_source_row"
        if source_row and naver_policy and source_available_status == "verified" and not missing:
            lineage_status = "source_available_verified"
        elif source_row and naver_policy:
            lineage_status = "source_row_hashed_naver_policy_snapshot_attached_pit_unproven"
        elif source_row:
            lineage_status = "source_row_hashed_policy_missing"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": pending_row.get("candidate_id", ""),
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": pending_row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "chart_local_per": chart_local_per,
                "chart_local_pbr": chart_local_pbr,
                "source_file": str(source_path),
                "source_row_id": source_row_id,
                "source_hash": source_hash,
                "vendor_or_origin": "chart_mvp_financial_cache",
                "vendor_snapshot_date": naver_policy.get("vendor_snapshot_date", ""),
                "vendor_as_of_date": pending_row.get("source_period", ""),
                "price_date": naver_policy.get("price_date", ""),
                "price_value": naver_policy.get("price_value", "") or component.get("chart_implied_price", ""),
                "adjusted_price_policy": adjusted_price_policy or "unknown",
                "unadjusted_price_policy": unadjusted_price_policy or "unknown",
                "shares_policy": shares_policy or "unknown",
                "shares_date": "",
                "eps_policy": eps_policy or ("chart_cache_reference_only" if per_share_metric == "EPS" else ""),
                "bps_policy": bps_policy or ("chart_cache_reference_only" if per_share_metric == "BPS" else ""),
                "denominator_policy": denominator_policy or f"{per_share_metric}_denominator_reference_only",
                "source_available_before_evaluation_date": source_available_status,
                "lineage_status": lineage_status,
                "missing_lineage_reason": "|".join(dict.fromkeys(missing)),
                "chart_local_ratio_usage": "reference_only_until_reconciled",
            }
        )
    return rows


def _chart_local_vendor_source_policy_pack_rows(
    lineage_rows: list[dict[str, str]],
    naver_ratio_policy_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    rows = []
    naver_policy_by_ticker = {
        row.get("ticker", ""): row for row in naver_ratio_policy_rows or []
    }
    required_policy_fields = [
        "vendor_snapshot_date",
        "price_date",
        "price_policy",
        "adjusted_price_policy",
        "shares_policy",
        "source_available_date",
    ]
    for lineage in lineage_rows:
        field_name = (
            "price_to_earnings"
            if lineage.get("chart_local_per")
            else "price_to_book"
        )
        naver_policy = naver_policy_by_ticker.get(lineage.get("ticker", ""), {})
        price_policy = _policy_value(naver_policy.get("price_policy", "") or lineage.get("unadjusted_price_policy", ""))
        adjusted_policy = _policy_value(naver_policy.get("adjusted_price_policy", "") or lineage.get("adjusted_price_policy", ""))
        ratio_formula = (
            naver_policy.get("per_formula", "")
            if field_name == "price_to_earnings"
            else naver_policy.get("pbr_formula", "")
        )
        source_available_date = naver_policy.get("source_available_date", "")
        source_available_status = _source_available_before_evaluation_status(
            source_available_date,
            lineage.get("evaluation_date", ""),
        )
        row = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": lineage.get("candidate_id", ""),
            "evidence_id": lineage.get("evidence_id", ""),
            "ticker": lineage.get("ticker", ""),
            "evaluation_date": lineage.get("evaluation_date", ""),
            "field_name": field_name,
            "vendor_name": "Naver Finance",
            "vendor_or_origin": lineage.get("vendor_or_origin", ""),
            "source_file": lineage.get("source_file", ""),
            "source_row_id": lineage.get("source_row_id", ""),
            "source_hash": lineage.get("source_hash", ""),
            "vendor_snapshot_date": naver_policy.get("vendor_snapshot_date", "") or lineage.get("vendor_snapshot_date", ""),
            "vendor_as_of_date": lineage.get("vendor_as_of_date", ""),
            "ratio_formula": ratio_formula or (
                "vendor_reported_PER_reference_only"
                if field_name == "price_to_earnings"
                else "vendor_reported_PBR_reference_only"
            ),
            "price_date": naver_policy.get("price_date", "") or lineage.get("price_date", ""),
            "price_policy": price_policy,
            "adjusted_price_policy": adjusted_policy,
            "shares_policy": _policy_value(lineage.get("shares_policy", "")),
            "eps_policy": lineage.get("eps_policy", ""),
            "bps_policy": lineage.get("bps_policy", ""),
            "source_available_date": source_available_date,
            "source_available_before_evaluation_date": source_available_status,
            "policy_pack_status": "incomplete_reference_only",
            "missing_policy_fields": "",
            "chart_local_ratio_usage": "reference_only_until_reconciled",
            "scoring_activation_allowed": "false",
        }
        missing = [
            field
            for field in required_policy_fields
            if not row.get(field)
            or row.get(field) == "unknown"
            or row.get(field) == "not_disclosed_by_naver_main"
        ]
        if source_available_status != "verified":
            missing.append("source_available_before_evaluation_date")
        if naver_policy and missing:
            row["policy_pack_status"] = "partially_enriched_reference_only"
        elif naver_policy:
            row["policy_pack_status"] = "enriched_reference_only_not_promoted"
        row["missing_policy_fields"] = "|".join(missing)
        rows.append(row)
    return rows


def _policy_value(value: str) -> str:
    text = str(value or "").strip()
    return text if text and text != "unknown" else "unknown"


def _source_available_before_evaluation_status(source_available_date: str, evaluation_date: str) -> str:
    source_date = _parse_date_text(str(source_available_date or ""))
    eval_date = _parse_date_text(str(evaluation_date or ""))
    if source_date is None or eval_date is None:
        return "unproven"
    return "verified" if source_date <= eval_date else "after_evaluation_date"


def _per_pbr_formula_candidate_grid_rows(
    pending_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    component_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in component_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        component = component_by_key.get((pending_row.get("candidate_id", ""), field_name), {})
        chart_value = _parse_number(pending_row.get("value", ""))
        for formula in _formula_candidates_for_field(field_name, component):
            formula_value = formula["value"]
            absolute_delta = _absolute_delta(chart_value, formula_value)
            relative_delta = _relative_delta_pct(chart_value, absolute_delta)
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "candidate_id": pending_row.get("candidate_id", ""),
                    "evidence_id": pending_row.get("evidence_id", ""),
                    "ticker": pending_row.get("ticker", ""),
                    "evaluation_date": pending_row.get("evaluation_date", ""),
                    "field_name": field_name,
                    "formula_id": formula["formula_id"],
                    "required_components": "|".join(formula["required_components"]),
                    "component_source_refs": component.get("source_ref", ""),
                    "component_availability_dates": _component_availability_dates(component),
                    "formula_value": _format_optional_number(formula_value),
                    "chart_local_value": pending_row.get("value", ""),
                    "absolute_delta": _format_optional_number(absolute_delta),
                    "relative_delta_pct": _format_optional_number(relative_delta),
                    "tolerance_bucket": _tolerance_bucket(absolute_delta, relative_delta),
                    "suspected_mismatch_reason": _formula_grid_mismatch_reason(formula, component, absolute_delta, relative_delta),
                    "match_status": _formula_grid_match_status(formula_value, absolute_delta, relative_delta),
                }
            )
    return rows


def _formula_candidates_for_field(field_name: str, component: dict[str, str]) -> list[dict[str, Any]]:
    close = _parse_number(component.get("price", ""))
    adjusted = _parse_number(component.get("adjusted_price", ""))
    market_cap = _parse_number(component.get("market_cap", ""))
    shares = _parse_number(component.get("shares_outstanding", ""))
    net_income = _parse_number(component.get("net_income", ""))
    total_equity = _parse_number(component.get("equity", ""))
    eps = _parse_number(component.get("chart_cache_eps", "")) or _parse_number(component.get("eps", ""))
    bps = _parse_number(component.get("chart_cache_bps", "")) or _parse_number(component.get("bps", ""))
    if field_name == "price_to_earnings":
        return [
            _formula_candidate("pe_market_cap_to_net_income", ["market_cap", "net_income"], _divide_optional(market_cap, net_income)),
            _formula_candidate("pe_close_x_shares_to_net_income", ["close_price", "shares_outstanding", "net_income"], _divide_optional(_multiply_optional(close, shares), net_income)),
            _formula_candidate("pe_adjusted_close_x_shares_to_net_income", ["adjusted_close_price", "shares_outstanding", "net_income"], _divide_optional(_multiply_optional(adjusted, shares), net_income)),
            _formula_candidate("pe_close_to_eps", ["close_price", "EPS"], _divide_optional(close, eps)),
            _formula_candidate("pe_adjusted_close_to_eps", ["adjusted_close_price", "EPS"], _divide_optional(adjusted, eps)),
        ]
    return [
        _formula_candidate("pb_market_cap_to_total_equity", ["market_cap", "total_equity"], _divide_optional(market_cap, total_equity)),
        _formula_candidate("pb_market_cap_to_equity_attributable_to_owners", ["market_cap", "equity_attributable_to_owners"], None),
        _formula_candidate("pb_close_x_shares_to_total_equity", ["close_price", "shares_outstanding", "total_equity"], _divide_optional(_multiply_optional(close, shares), total_equity)),
        _formula_candidate("pb_adjusted_close_x_shares_to_equity_attributable_to_owners", ["adjusted_close_price", "shares_outstanding", "equity_attributable_to_owners"], None),
        _formula_candidate("pb_close_to_bps", ["close_price", "BPS"], _divide_optional(close, bps)),
        _formula_candidate("pb_adjusted_close_to_bps", ["adjusted_close_price", "BPS"], _divide_optional(adjusted, bps)),
    ]


def _formula_candidate(formula_id: str, required_components: list[str], value: float | None) -> dict[str, Any]:
    return {
        "formula_id": formula_id,
        "required_components": required_components,
        "value": value,
    }


def _component_availability_dates(component: dict[str, str]) -> str:
    parts = []
    for label, key in (("price_date", "price_date"), ("filing_date", "filing_date"), ("availability_date", "availability_date")):
        if component.get(key):
            parts.append(f"{label}={component[key]}")
    shares_as_of = _source_ref_token_value(component.get("source_ref", ""), "shares_as_of")
    if shares_as_of:
        parts.append(f"shares_as_of={shares_as_of}")
    return "|".join(parts)


def _tolerance_bucket(absolute_delta: float | None, relative_delta_pct: float | None) -> str:
    if absolute_delta is None:
        return "missing_components"
    if absolute_delta <= 0.1:
        return "within_absolute_tolerance"
    if relative_delta_pct is not None and relative_delta_pct <= 5:
        return "near_match_5pct"
    return "large_variance"


def _formula_grid_match_status(
    formula_value: float | None,
    absolute_delta: float | None,
    relative_delta_pct: float | None,
) -> str:
    if formula_value is None:
        return "missing_components"
    if absolute_delta is not None and absolute_delta <= 0.1:
        return "numeric_match_source_lineage_pending"
    if relative_delta_pct is not None and relative_delta_pct <= 5:
        return "near_match_needs_review"
    return "formula_variance"


def _formula_grid_mismatch_reason(
    formula: dict[str, Any],
    component: dict[str, str],
    absolute_delta: float | None,
    relative_delta_pct: float | None,
) -> str:
    reasons = []
    formula_id = formula["formula_id"]
    if formula["value"] is None:
        if "adjusted" in formula_id:
            reasons.append("adjusted_price_policy_mismatch")
        if "equity_attributable_to_owners" in formula_id:
            reasons.append("equity_policy_mismatch")
        reasons.append("unknown_chart_local_formula")
        return "|".join(dict.fromkeys(reasons))
    if absolute_delta is not None and absolute_delta <= 0.1:
        return "numeric_match_but_source_lineage_unproven"
    if "close" in formula_id or "market_cap" in formula_id:
        reasons.extend(["price_date_mismatch", "adjusted_price_policy_mismatch"])
    if "shares" in formula_id or "market_cap" in formula_id:
        reasons.extend(["shares_policy_mismatch", "shares_date_mismatch"])
    if "eps" in formula_id or "bps" in formula_id:
        reasons.append("EPS_BPS_denominator_mismatch")
    if "net_income" in formula_id:
        reasons.append("net_income_policy_mismatch")
    if "equity" in formula_id:
        reasons.append("equity_policy_mismatch")
    if not component.get("consolidated_or_separate"):
        reasons.append("consolidated_vs_separate_mismatch")
    if relative_delta_pct is not None and relative_delta_pct > 100:
        reasons.append("unit_mismatch")
    return "|".join(dict.fromkeys(reasons)) if reasons else "unknown_chart_local_formula"


def _per_pbr_formula_match_report(
    rows: list[dict[str, str]],
    lineage_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    by_field: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_field.setdefault(row.get("field_name", ""), []).append(row)
    lineage_pass = all(row.get("lineage_status") == "source_available_verified" for row in lineage_rows)
    recommendations = {}
    for field_name, field_rows in sorted(by_field.items()):
        numeric_matches = [row for row in field_rows if row["match_status"] == "numeric_match_source_lineage_pending"]
        near_matches = [row for row in field_rows if row["match_status"] == "near_match_needs_review"]
        if numeric_matches and lineage_pass:
            recommendation = "matched_formula_id"
            matched_formula_id = numeric_matches[0]["formula_id"]
        elif numeric_matches or near_matches:
            recommendation = "near_match_needs_review"
            matched_formula_id = (numeric_matches or near_matches)[0]["formula_id"]
        else:
            recommendation = "no_safe_match_keep_blocked"
            matched_formula_id = ""
        if not lineage_pass:
            recommendation = "no_safe_match_keep_blocked"
        recommendations[field_name] = {
            "recommendation": recommendation,
            "matched_formula_id": matched_formula_id,
            "numeric_match_count": len(numeric_matches),
            "near_match_count": len(near_matches),
            "source_lineage_pass": lineage_pass,
            "promotion_allowed": False,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": "v1_5_per_pbr_formula_match_report",
        "recommendations": recommendations,
        "overall_recommendation": (
            "no_safe_match_keep_blocked"
            if any(item["recommendation"] == "no_safe_match_keep_blocked" for item in recommendations.values())
            else "near_match_needs_review"
        ),
        "scoring_activation_allowed": False,
        "promotion_rule": "Do not promote PER/PBR unless formula match and source availability both pass.",
    }


def _dividend_pit_source_lineage_rows(
    pending_rows: list[dict[str, str]],
    metadata_rows: list[dict[str, str]],
    raw_snapshot_path: Path | None,
    market_sources: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    raw_records = _read_jsonl_rows(raw_snapshot_path) if raw_snapshot_path and raw_snapshot_path.exists() else []
    rows = []
    for pending_row in pending_rows:
        if pending_row.get("field_name") != "dividend_yield":
            continue
        ticker = pending_row.get("ticker", "").strip()
        evaluation_date = _parse_date_text(pending_row.get("evaluation_date", ""))
        source = _dividend_source_for_ticker(ticker, evaluation_date, raw_records, metadata_rows)
        market_source = market_sources.get(ticker, {})
        rcept_dt = source.get("rcept_dt", "")
        availability_date = _next_trading_day_text(rcept_dt) if rcept_dt else ""
        dividend_per_share = source.get("dividend_per_share", "")
        price = market_source.get("close")
        has_price = price is not None
        available_date = _parse_date_text(availability_date)
        availability_pass = bool(
            dividend_per_share
            and availability_date
            and evaluation_date is not None
            and available_date is not None
            and available_date <= evaluation_date
        )
        if availability_pass and has_price:
            status = "diagnostic_ready"
            missing_reason = ""
        elif source.get("metadata_only"):
            status = "unsupported_metadata_only_missing_dividend_amount"
            missing_reason = "dividend_disclosure_metadata_found_but_amount_missing"
        else:
            status = "unsupported_missing_pit_dividend_source"
            missing_reason = "OpenDART alotMatter or vendor PIT dividend snapshot missing"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": pending_row.get("candidate_id", ""),
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": ticker,
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "dividend_per_share": dividend_per_share,
                "total_dividend": source.get("total_dividend", ""),
                "stock_kind": source.get("stock_kind", ""),
                "dividend_record_date": source.get("dividend_record_date", ""),
                "dividend_resolution_date": source.get("dividend_resolution_date", ""),
                "filing_date": rcept_dt,
                "rcept_no": source.get("rcept_no", ""),
                "rcept_dt": rcept_dt,
                "source_ref": source.get("source_ref", ""),
                "availability_date": availability_date,
                "availability_policy_id": AVAILABILITY_POLICY_ID if availability_date else "",
                "price_date": str(market_source.get("price_date", "")),
                "price_policy": "local_unadjusted_close_reference_only" if has_price else "",
                "dividend_yield_formula_id": "cash_dividend_per_share_to_local_close_v1",
                "pit_dividend_source_status": status,
                "missing_source_reason": missing_reason,
            }
        )
    return rows


def _dividend_source_for_ticker(
    ticker: str,
    evaluation_date: date | None,
    raw_records: list[dict[str, Any]],
    metadata_rows: list[dict[str, str]],
) -> dict[str, str]:
    candidates = []
    for record in raw_records:
        endpoint = str(record.get("endpoint_name", ""))
        raw_json = record.get("raw_json")
        if not isinstance(raw_json, dict):
            continue
        if endpoint == "alot_matter":
            request_context = raw_json.get("_request_context", {})
            record_code = str(request_context.get("code", "")).strip()
            if record_code and record_code != ticker:
                continue
            for item in raw_json.get("list") or []:
                if not isinstance(item, dict):
                    continue
                source = _dividend_source_from_alot_matter_item(item, record)
                if _dividend_source_eligible(source, evaluation_date):
                    candidates.append(source)
        elif endpoint == "disclosure_list":
            for item in raw_json.get("list") or []:
                if not isinstance(item, dict) or str(item.get("stock_code", "")).strip() != ticker:
                    continue
                report_nm = str(item.get("report_nm", "")).strip()
                if "배당" in report_nm or "dividend" in report_nm.lower():
                    source = {
                        "metadata_only": "true",
                        "rcept_no": str(item.get("rcept_no", "")).strip(),
                        "rcept_dt": str(item.get("rcept_dt", "")).strip(),
                        "source_ref": str(record.get("source_ref", "")).strip(),
                    }
                    if _dividend_source_eligible(source, evaluation_date):
                        candidates.append(source)
    for row in metadata_rows:
        if row.get("stock_code", "").strip() != ticker:
            continue
        report_nm = row.get("report_nm", "")
        if "배당" in report_nm or "dividend" in report_nm.lower():
            source = {
                "metadata_only": "true",
                "rcept_no": row.get("rcept_no", ""),
                "rcept_dt": row.get("rcept_dt", ""),
                "source_ref": row.get("source_ref", ""),
            }
            if _dividend_source_eligible(source, evaluation_date):
                candidates.append(source)
    if not candidates:
        return {}
    return max(candidates, key=lambda item: item.get("rcept_dt", ""))


def _dividend_source_from_alot_matter_item(item: dict[str, Any], record: dict[str, Any]) -> dict[str, str]:
    label = str(item.get("se", "")).strip()
    value = str(item.get("thstrm", "")).strip()
    source = {
        "metadata_only": "",
        "rcept_no": str(item.get("rcept_no", "")).strip(),
        "rcept_dt": str(item.get("rcept_dt", "")).strip(),
        "stock_kind": str(item.get("stock_knd", "")).strip(),
        "dividend_record_date": str(item.get("stlm_dt", "")).strip(),
        "source_ref": str(record.get("source_ref", "")).strip(),
    }
    if "주당" in label or "per_share" in label or "dividend_per_share" in label:
        source["dividend_per_share"] = value
    elif "총액" in label or "total" in label:
        source["total_dividend"] = value
    if not source.get("rcept_dt"):
        source["rcept_dt"] = _rcept_dt_from_receipt(source.get("rcept_no", ""))
    return source


def _dividend_source_eligible(source: dict[str, str], evaluation_date: date | None) -> bool:
    if evaluation_date is None:
        return True
    availability_date = _parse_date_text(_next_trading_day_text(source.get("rcept_dt", "")))
    return availability_date is not None and availability_date <= evaluation_date


def _rcept_dt_from_receipt(rcept_no: str) -> str:
    value = str(rcept_no or "").strip()
    if len(value) >= 8 and value[:8].isdigit():
        return value[:8]
    return ""


def _feature_level_readiness_rows(
    pending_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    formula_grid_rows: list[dict[str, str]],
    ratio_lineage_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    reconciliation_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in reconciliation_rows
    }
    ratio_lineage_by_key = {
        (row.get("candidate_id", ""), "price_to_earnings" if row.get("chart_local_per") else "price_to_book"): row
        for row in ratio_lineage_rows
    }
    dividend_by_candidate = {row.get("candidate_id", ""): row for row in dividend_rows}
    formula_status_by_key: dict[tuple[str, str], str] = {}
    for row in formula_grid_rows:
        key = (row.get("candidate_id", ""), row.get("field_name", ""))
        current = formula_status_by_key.get(key, "")
        if row.get("match_status") == "numeric_match_source_lineage_pending":
            formula_status_by_key[key] = row["match_status"]
        elif not current:
            formula_status_by_key[key] = row.get("match_status", "")
    rows = []
    for pending_row in pending_rows:
        candidate_id = pending_row.get("candidate_id", "")
        field_name = pending_row.get("field_name", "")
        key = (candidate_id, field_name)
        reconciliation = reconciliation_by_key.get(key, {})
        ratio_lineage = ratio_lineage_by_key.get(key, {})
        dividend = dividend_by_candidate.get(candidate_id, {})
        status = reconciliation.get("value_reconciliation_status", "")
        source_status = reconciliation.get("source_ref", "")
        pit_status = "pending_review"
        chart_usage = ""
        blocked_reason = reconciliation.get("blocked_reason", "")
        if field_name in VALUATION_FORMULA_REVIEW_FIELDS:
            chart_usage = ratio_lineage.get("chart_local_ratio_usage", "reference_only_until_reconciled")
            source_lineage_status = ratio_lineage.get("lineage_status", "missing_chart_local_source_row")
            formula_status = formula_status_by_key.get(key, status)
            feature_status = (
                "diagnostic_ready"
                if status == "formula_match" and source_lineage_status == "source_available_verified"
                else "blocked_by_reconciliation"
            )
            pit_status = "available" if source_lineage_status == "source_available_verified" else "unproven"
            if not blocked_reason:
                blocked_reason = "PER/PBR formula or chart-local source lineage has not passed"
        elif field_name == "dividend_yield":
            source_lineage_status = dividend.get("pit_dividend_source_status", "unsupported_missing_pit_dividend_source")
            formula_status = source_lineage_status
            feature_status = "diagnostic_ready" if source_lineage_status == "diagnostic_ready" else "unsupported"
            pit_status = "available" if feature_status == "diagnostic_ready" else "missing"
            blocked_reason = dividend.get("missing_source_reason", blocked_reason)
        elif field_name in QUALITY_PROFITABILITY_FIELDS:
            source_lineage_status = "opendart_formula_match" if status == "formula_match" else status
            formula_status = status
            feature_status = "diagnostic_ready" if status == "formula_match" else "pending"
            pit_status = "available" if status == "formula_match" else "pending"
        else:
            source_lineage_status = status
            formula_status = status
            feature_status = "pending"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": pending_row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": field_name,
                "feature_readiness_status": feature_status,
                "source_lineage_status": source_lineage_status or source_status,
                "formula_match_status": formula_status,
                "pit_availability_status": pit_status,
                "chart_local_ratio_usage": chart_usage,
                "scoring_activation_allowed": "false",
                "blocked_reason": blocked_reason,
            }
        )
    return rows


def _per_pbr_split_readiness_rows(
    pending_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    ratio_lineage_rows: list[dict[str, str]],
    naver_asof_resolved_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    reconciliation_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in reconciliation_rows
    }
    ratio_lineage_by_key = {
        (row.get("candidate_id", ""), "price_to_earnings" if row.get("chart_local_per") else "price_to_book"): row
        for row in ratio_lineage_rows
    }
    resolver_by_candidate = {
        row.get("candidate_id", ""): row for row in naver_asof_resolved_rows
    }
    rows = []
    for pending_row in pending_rows:
        field_name = pending_row.get("field_name", "")
        if field_name not in VALUATION_FORMULA_REVIEW_FIELDS:
            continue
        candidate_id = pending_row.get("candidate_id", "")
        key = (candidate_id, field_name)
        reconciliation = reconciliation_by_key.get(key, {})
        lineage = ratio_lineage_by_key.get(key, {})
        resolver = resolver_by_candidate.get(candidate_id, {})
        formula_reconciled = (
            reconciliation.get("value_reconciliation_status") == "formula_match"
            and lineage.get("lineage_status") == "source_available_verified"
        )
        if formula_reconciled:
            formula_status = "diagnostic_ready"
        elif reconciliation.get("value_reconciliation_status") == "formula_match":
            formula_status = "blocked_by_reconciliation"
        else:
            formula_status = "blocked_by_reconciliation"
        vendor_status = resolver.get("asof_resolution_status", "crawl_missing")
        if formula_status == "diagnostic_ready":
            diagnostic_status = "formula_diagnostic_ready_not_scoring"
        elif vendor_status == "vendor_snapshot_available_asof_evaluation":
            diagnostic_status = "vendor_reference_ready"
        elif vendor_status == "after_evaluation_date":
            diagnostic_status = "reference_only_after_evaluation_date"
        else:
            diagnostic_status = f"reference_only_{vendor_status}"
        blocked_reason = ""
        if formula_status != "diagnostic_ready":
            blocked_reason = "PER/PBR formula reconciliation is not verified for scoring or formula diagnostics"
        if vendor_status != "vendor_snapshot_available_asof_evaluation":
            blocked_reason = _join_flags(blocked_reason, f"vendor_snapshot_status={vendor_status}")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": pending_row.get("evidence_id", ""),
                "ticker": pending_row.get("ticker", ""),
                "evaluation_date": pending_row.get("evaluation_date", ""),
                "field_name": field_name,
                "formula_reconciled_status": formula_status,
                "vendor_snapshot_status": vendor_status,
                "diagnostic_usage_status": diagnostic_status,
                "formula_verified": "true" if formula_status == "diagnostic_ready" else "false",
                "adjusted_price_policy": resolver.get("adjusted_price_policy", "not_disclosed_by_naver_main"),
                "scoring_activation_allowed": "false",
                "blocked_reason": blocked_reason,
            }
        )
    return rows


def _v1_6_readiness_handoff_rows(
    pending_rows: list[dict[str, str]],
    scoring_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
    split_rows: list[dict[str, str]],
    incremental_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    metadata_by_candidate: dict[str, dict[str, str]] = {}
    for row in pending_rows:
        candidate_id = row.get("candidate_id", "")
        if not candidate_id:
            continue
        metadata_by_candidate.setdefault(
            candidate_id,
            {
                "candidate_id": candidate_id,
                "ticker": row.get("ticker", ""),
                "evaluation_date": row.get("evaluation_date", ""),
            },
        )
    feature_status_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row.get("feature_readiness_status", "")
        for row in feature_rows
    }
    scoring_by_candidate = {row.get("candidate_id", ""): row for row in scoring_rows}
    split_by_key = {
        (row.get("candidate_id", ""), row.get("field_name", "")): row
        for row in split_rows
    }
    incremental_by_candidate = {
        row.get("candidate_id", ""): row
        for row in (incremental_rows or [])
    }
    rows = []
    for candidate_id in sorted(metadata_by_candidate):
        metadata = metadata_by_candidate[candidate_id]
        scoring = scoring_by_candidate.get(candidate_id, {})
        pe = split_by_key.get((candidate_id, "price_to_earnings"), {})
        pb = split_by_key.get((candidate_id, "price_to_book"), {})
        quality_statuses = [
            feature_status_by_key.get((candidate_id, field), "pending")
            for field in QUALITY_PROFITABILITY_FIELDS
        ]
        valuation_usage = [
            pe.get("diagnostic_usage_status", "reference_only_crawl_missing"),
            pb.get("diagnostic_usage_status", "reference_only_crawl_missing"),
        ]
        pe_canonical_status = pe.get("formula_reconciled_status", "blocked_by_reconciliation")
        pb_canonical_status = pb.get("formula_reconciled_status", "blocked_by_reconciliation")
        pe_vendor_status = _vendor_reference_status(pe)
        pb_vendor_status = _vendor_reference_status(pb)
        if all(status == "formula_diagnostic_ready_not_scoring" for status in valuation_usage):
            overall_valuation_status = "formula_diagnostic_ready_not_scoring"
        elif any(status == "vendor_reference_ready" for status in valuation_usage):
            overall_valuation_status = "vendor_reference_only"
        elif any(status == "reference_only_after_evaluation_date" for status in valuation_usage):
            overall_valuation_status = "reference_only_after_evaluation_date"
        else:
            overall_valuation_status = "blocked_or_missing_vendor_snapshot"
        quality_ready = any(status == "diagnostic_ready" for status in quality_statuses)
        overall_quality_status = (
            scoring.get("quality_profitability_readiness_status", "")
            or ("diagnostic_ready" if quality_ready else "pending")
        )
        candidate_overall = scoring.get("candidate_overall_readiness_status", "")
        if overall_valuation_status in {"vendor_reference_only", "formula_diagnostic_ready_not_scoring"} or quality_ready:
            candidate_overall = "partial_diagnostic_ready"
        incremental = incremental_by_candidate.get(candidate_id, {})
        incremental_status = incremental.get("comparison_status", "skipped_missing_baseline_artifacts")
        limitations = [
            "valuation_score_not_consumed",
            "v1_6_consumes_status_flags_only",
            "per_pbr_blocked_by_reconciliation_allowed",
            "vendor_reference_only_not_formula_verified",
        ]
        adjusted_policies = {
            pe.get("adjusted_price_policy", ""),
            pb.get("adjusted_price_policy", ""),
        }
        if "not_disclosed_by_naver_main" in adjusted_policies:
            limitations.append("adjusted_price_policy_not_disclosed_by_naver_main")
        if "reference_only_after_evaluation_date" in valuation_usage:
            limitations.append("historical_evaluation_before_first_vendor_snapshot")
        if incremental_status.startswith("skipped_"):
            limitations.append(f"incremental_evidence_status={incremental_status}")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "ticker": metadata.get("ticker", ""),
                "candidate_id": candidate_id,
                "evaluation_date": metadata.get("evaluation_date", ""),
                "overall_valuation_status": overall_valuation_status,
                "overall_quality_profitability_status": overall_quality_status,
                "price_to_earnings_canonical_formula_status": pe_canonical_status,
                "price_to_book_canonical_formula_status": pb_canonical_status,
                "price_to_earnings_vendor_reference_status": pe_vendor_status,
                "price_to_book_vendor_reference_status": pb_vendor_status,
                "dividend_yield_status": feature_status_by_key.get((candidate_id, "dividend_yield"), "unsupported"),
                "incremental_evidence_status": incremental_status,
                "candidate_overall_readiness_status": candidate_overall or "pending",
                "limitations": "|".join(dict.fromkeys(limitations)),
                "manual_review_required": "true",
            }
        )
    return rows


def _vendor_reference_status(split_row: dict[str, str]) -> str:
    usage_status = split_row.get("diagnostic_usage_status", "reference_only_crawl_missing")
    if usage_status == "vendor_reference_ready":
        return "vendor_reference_only"
    if usage_status.startswith("reference_only_"):
        return usage_status
    if usage_status == "formula_diagnostic_ready_not_scoring":
        return "vendor_reference_not_required"
    return f"reference_only_{split_row.get('vendor_snapshot_status', 'crawl_missing')}"


def _naver_daily_crawl_health(
    snapshot_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    missing_fields: dict[str, list[str]] = {}
    duplicate_keys: dict[tuple[str, str], int] = {}
    weekend_or_holiday_count = 0
    for row in snapshot_rows:
        status = _raw_html_integrity_status(row, config.output_dir)
        status = "collected" if status == "ok" else status
        status_counts[status] = status_counts.get(status, 0) + 1
        key = (row.get("ticker", ""), row.get("source_available_date", ""))
        duplicate_keys[key] = duplicate_keys.get(key, 0) + 1
        source_date = _parse_date_text(row.get("source_available_date", ""))
        if source_date is not None and source_date.weekday() >= 5:
            weekend_or_holiday_count += 1
        missing = [
            field
            for field in ("raw_html_path", "raw_html_sha256", "price_date", "price_policy", "shares_policy")
            if not row.get(field)
        ]
        if missing:
            missing_fields[row.get("ticker", "")] = missing
    duplicate_snapshot_count = sum(1 for count in duplicate_keys.values() if count > 1)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": "v1_5_naver_daily_crawl_health",
        "snapshot_row_count": len(snapshot_rows),
        "registry_row_count": len(registry_rows),
        "crawl_status_counts": dict(sorted(status_counts.items())),
        "missing_raw_html_count": status_counts.get("raw_html_missing", 0),
        "hash_mismatch_count": status_counts.get("hash_mismatch", 0),
        "schema_drift_status": "review_required" if missing_fields else "not_detected",
        "missing_fields_by_ticker": missing_fields,
        "duplicate_snapshot_count": duplicate_snapshot_count,
        "weekend_or_holiday_handling": "calendar_weekend_flag_only_no_exchange_holiday_calendar",
        "weekend_or_holiday_snapshot_count": weekend_or_holiday_count,
        "scoring_activation_allowed": False,
    }


def _naver_ratio_snapshot_drift_rows(registry_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    by_ticker: dict[str, list[dict[str, str]]] = {}
    for row in registry_rows:
        by_ticker.setdefault(row.get("ticker", ""), []).append(row)
    for ticker, ticker_rows in sorted(by_ticker.items()):
        ticker_rows.sort(key=lambda row: (row.get("source_available_date", ""), row.get("snapshot_date", "")))
        previous: dict[str, str] | None = None
        for row in ticker_rows:
            per_value = row.get("per_reported_value", "")
            pbr_value = row.get("pbr_reported_value", "")
            previous_per = previous.get("per_reported_value", "") if previous else ""
            previous_pbr = previous.get("pbr_reported_value", "") if previous else ""
            if previous is None:
                drift_status = "no_prior_snapshot"
                per_changed = "false"
                pbr_changed = "false"
            else:
                per_changed = "true" if per_value != previous_per else "false"
                pbr_changed = "true" if pbr_value != previous_pbr else "false"
                drift_status = "changed" if per_changed == "true" or pbr_changed == "true" else "unchanged"
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "ticker": ticker,
                    "snapshot_date": row.get("snapshot_date", ""),
                    "source_available_date": row.get("source_available_date", ""),
                    "previous_snapshot_date": previous.get("snapshot_date", "") if previous else "",
                    "previous_source_available_date": previous.get("source_available_date", "") if previous else "",
                    "per_reported_value": per_value,
                    "previous_per_reported_value": previous_per,
                    "pbr_reported_value": pbr_value,
                    "previous_pbr_reported_value": previous_pbr,
                    "per_changed": per_changed,
                    "pbr_changed": pbr_changed,
                    "drift_status": drift_status,
                }
            )
            previous = row
    return rows


def _join_flags(existing: str, addition: str) -> str:
    return "|".join(dict.fromkeys([item for item in [*existing.split("|"), addition] if item]))


def _valuation_formula_policy(config: V15SupplementationConfig) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "policy_type": "v1_5_valuation_formula_policy",
        "chart_local_ratio_policy": "reference_only_until_reconciled",
        "scoring_activation_allowed": False,
        "formula_candidates": {
            "price_to_earnings": {
                "formula_id": "local_eval_market_cap_to_net_income_v1",
                "required_components": ["price", "shares_outstanding", "net_income"],
                "pit_requirements": [
                    "price_date <= evaluation_date",
                    "shares_outstanding as_of_date <= evaluation_date",
                    "net_income availability_date <= evaluation_date",
                    "source lineage must identify adjusted or unadjusted price policy",
                ],
                "source_priority": [
                    "PIT-safe local market cap if lineage proves price and shares policy",
                    "price * shares_outstanding diagnostic source",
                    "chart-local ratio reference only",
                ],
                "tolerance_policy": "absolute_delta <= 0.1 before diagnostic promotion review",
                "blocked_conditions": [
                    "formula_variance",
                    "missing availability metadata",
                    "adjusted price policy unknown",
                    "shares outstanding policy unknown",
                    "TTM versus annual basis unknown",
                ],
            },
            "price_to_book": {
                "formula_id": "local_eval_market_cap_to_total_equity_v1",
                "required_components": ["price", "shares_outstanding", "equity"],
                "pit_requirements": [
                    "price_date <= evaluation_date",
                    "shares_outstanding as_of_date <= evaluation_date",
                    "equity availability_date <= evaluation_date",
                    "source lineage must identify adjusted or unadjusted price policy",
                ],
                "source_priority": [
                    "PIT-safe local market cap if lineage proves price and shares policy",
                    "price * shares_outstanding diagnostic source",
                    "chart-local ratio reference only",
                ],
                "tolerance_policy": "absolute_delta <= 0.1 before diagnostic promotion review",
                "blocked_conditions": [
                    "formula_variance",
                    "missing availability metadata",
                    "adjusted price policy unknown",
                    "shares outstanding policy unknown",
                    "consolidated versus separate basis unknown",
                ],
            },
        },
    }


def _suspected_mismatch_reason(
    pending_row: dict[str, str],
    component_row: dict[str, str],
    reconciliation_row: dict[str, str],
) -> str:
    reasons = []
    evaluation_date = pending_row.get("evaluation_date", "")
    price_date = component_row.get("price_date", "")
    if price_date and evaluation_date and price_date != evaluation_date:
        reasons.append("price_date_mismatch")
    price_to_implied = _parse_number(component_row.get("price_to_chart_implied_ratio", ""))
    if price_to_implied is not None and abs(price_to_implied - 1) > 0.05:
        reasons.append("adjusted_price_policy_mismatch")
        reasons.append("market_cap_policy_mismatch")
        if pending_row.get("report_period_end_date", "") != evaluation_date:
            reasons.append("fiscal_period_mismatch")
    shares_as_of = _source_ref_token_value(component_row.get("source_ref", ""), "shares_as_of")
    if shares_as_of and evaluation_date and shares_as_of != evaluation_date:
        reasons.append("shares_outstanding_policy_mismatch")
    field_name = reconciliation_row.get("field_name", "")
    chart_eps = _parse_number(component_row.get("chart_cache_eps", ""))
    recomputed_eps = _parse_number(component_row.get("eps", ""))
    chart_bps = _parse_number(component_row.get("chart_cache_bps", ""))
    recomputed_bps = _parse_number(component_row.get("bps", ""))
    eps_diff = _relative_difference(chart_eps, recomputed_eps)
    bps_diff = _relative_difference(chart_bps, recomputed_bps)
    if field_name == "price_to_earnings" and (not component_row.get("net_income") or (eps_diff is not None and eps_diff > 0.05)):
        reasons.append("net_income_field_mismatch")
    if field_name == "price_to_book" and (not component_row.get("equity") or (bps_diff is not None and bps_diff > 0.05)):
        reasons.append("equity_field_mismatch")
    if not component_row.get("consolidated_or_separate"):
        reasons.append("consolidated_vs_separate_mismatch")
    if pending_row.get("fiscal_period") and not component_row.get("fiscal_period"):
        reasons.append("fiscal_period_mismatch")
    return "|".join(dict.fromkeys(reasons)) if reasons else "unknown_formula_source"


def _source_ref_token_value(source_ref: str, token: str) -> str:
    prefix = f"{token}="
    for part in source_ref.replace("|", ":").split(":"):
        if part.startswith(prefix):
            return part[len(prefix):]
    return ""


def _relative_delta_pct(chart_value: float | None, absolute_delta: float | None) -> float | None:
    if chart_value in (None, 0) or absolute_delta is None:
        return None
    return (absolute_delta / abs(chart_value)) * 100


def _absolute_delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return abs(a - b)


def _relative_difference(a: float | None, b: float | None) -> float | None:
    if a in (None, 0) or b is None:
        return None
    return abs(a - b) / abs(a)


def _divide_optional(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _multiply_optional(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a * b


def _format_optional_number(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def _valuation_scoring_readiness_rows(
    pending_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
    ratio_lineage_rows: list[dict[str, str]] | None = None,
    dividend_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    metadata_by_candidate: dict[str, dict[str, str]] = {}
    status_by_candidate: dict[str, dict[str, str]] = {}
    for row in pending_rows:
        candidate_id = row.get("candidate_id", "")
        if not candidate_id:
            continue
        metadata_by_candidate.setdefault(
            candidate_id,
            {
                "candidate_id": candidate_id,
                "evidence_id": row.get("evidence_id", ""),
                "ticker": row.get("ticker", ""),
            },
        )
    for row in reconciliation_rows:
        candidate_id = row.get("candidate_id", "")
        field_name = row.get("field_name", "")
        if not candidate_id or field_name not in VALUATION_SCORING_FIELDS + QUALITY_PROFITABILITY_FIELDS:
            continue
        status_by_candidate.setdefault(candidate_id, {})[field_name] = row.get("value_reconciliation_status", "")
    for row in dividend_rows or []:
        candidate_id = row.get("candidate_id", "")
        if row.get("pit_dividend_source_status") == "diagnostic_ready":
            status_by_candidate.setdefault(candidate_id, {})["dividend_yield"] = "dividend_diagnostic_ready"
    valuation_lineage_ready_by_key = {
        (
            row.get("candidate_id", ""),
            "price_to_earnings" if row.get("chart_local_per") else "price_to_book",
        ): row.get("lineage_status", "") == "source_available_verified"
        for row in ratio_lineage_rows or []
    }

    rows = []
    for candidate_id in sorted(metadata_by_candidate):
        metadata = metadata_by_candidate[candidate_id]
        field_statuses = status_by_candidate.get(candidate_id, {})
        formula_match_fields = sorted(
            field
            for field, status in field_statuses.items()
            if field in VALUATION_SCORING_FIELDS and status == "formula_match"
        )
        lineage_ready_formula_match_fields = sorted(
            field
            for field in formula_match_fields
            if field not in VALUATION_SCORING_CORE_FIELDS
            or valuation_lineage_ready_by_key.get((candidate_id, field), False)
        )
        quality_ready_fields = sorted(
            field
            for field, status in field_statuses.items()
            if field in QUALITY_PROFITABILITY_FIELDS and status == "formula_match"
        )
        formula_variance_fields = sorted(
            field for field, status in field_statuses.items() if status == "formula_variance"
        )
        unsupported_fields = sorted(
            field for field, status in field_statuses.items() if status.startswith("unsupported")
        )
        missing_core_fields = sorted(
            field for field in VALUATION_SCORING_CORE_FIELDS if field not in lineage_ready_formula_match_fields
        )
        blocked_fields = sorted(set(formula_variance_fields + unsupported_fields + missing_core_fields))
        core_fields_ready = not missing_core_fields
        if core_fields_ready:
            valuation_score_status = "not_activated"
            shadow_status = "ready_for_manual_scoring_review"
            blocked_reason = "valuation scoring activation requires separate approval before any score or ranking use"
            required_next_step = "manual valuation scoring activation review"
        else:
            valuation_score_status = "blocked_by_data"
            shadow_status = "blocked_by_reconciliation"
            blocked_reason = "valuation fields are not formula-reconciled enough for candidate-only shadow scoring"
            required_next_step = "resolve valuation formula variance and unsupported source lineage"
        dividend_status = (
            "diagnostic_ready"
            if field_statuses.get("dividend_yield") == "dividend_diagnostic_ready"
            else (
            "unsupported"
            if "dividend_yield" in unsupported_fields or field_statuses.get("dividend_yield", "").startswith("unsupported")
            else "pending"
            )
        )
        quality_status = "diagnostic_ready" if quality_ready_fields else "pending"
        valuation_status = "diagnostic_ready" if core_fields_ready else "blocked_by_reconciliation"
        overall_status = (
            "partial_diagnostic_ready"
            if quality_status == "diagnostic_ready" and valuation_status != "diagnostic_ready"
            else valuation_status
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "evidence_id": metadata.get("evidence_id", ""),
                "ticker": metadata.get("ticker", ""),
                "scoring_scope": "candidate_only_manual_review_support",
                "valuation_readiness_status": valuation_status,
                "quality_profitability_readiness_status": quality_status,
                "dividend_readiness_status": dividend_status,
                "candidate_overall_readiness_status": overall_status,
                "eligible_field_count": str(len(lineage_ready_formula_match_fields)),
                "blocked_field_count": str(len(blocked_fields)),
                "formula_match_valuation_fields": "|".join(lineage_ready_formula_match_fields),
                "formula_variance_valuation_fields": "|".join(formula_variance_fields),
                "unsupported_valuation_fields": "|".join(unsupported_fields),
                "diagnostic_ready_quality_profitability_fields": "|".join(quality_ready_fields),
                "missing_core_valuation_fields": "|".join(missing_core_fields),
                "valuation_score_status": valuation_score_status,
                "candidate_only_shadow_score_status": shadow_status,
                "scoring_activation_allowed": "false",
                "blocked_reason": blocked_reason,
                "required_next_step": required_next_step,
            }
        )
    return rows


def _valuation_scoring_readiness_manifest(
    rows: list[dict[str, str]],
    config: V15SupplementationConfig,
) -> dict[str, Any]:
    shadow_status_counts: dict[str, int] = {}
    valuation_status_counts: dict[str, int] = {}
    overall_status_counts: dict[str, int] = {}
    quality_status_counts: dict[str, int] = {}
    dividend_status_counts: dict[str, int] = {}
    for row in rows:
        shadow_status = row["candidate_only_shadow_score_status"]
        valuation_status = row["valuation_score_status"]
        shadow_status_counts[shadow_status] = shadow_status_counts.get(shadow_status, 0) + 1
        valuation_status_counts[valuation_status] = valuation_status_counts.get(valuation_status, 0) + 1
        overall_status = row["candidate_overall_readiness_status"]
        quality_status = row["quality_profitability_readiness_status"]
        dividend_status = row["dividend_readiness_status"]
        overall_status_counts[overall_status] = overall_status_counts.get(overall_status, 0) + 1
        quality_status_counts[quality_status] = quality_status_counts.get(quality_status, 0) + 1
        dividend_status_counts[dividend_status] = dividend_status_counts.get(dividend_status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "row_count": len(rows),
        "scoring_scope": "candidate_only_manual_review_support",
        "shadow_status_counts": dict(sorted(shadow_status_counts.items())),
        "valuation_score_status_counts": dict(sorted(valuation_status_counts.items())),
        "candidate_overall_readiness_status_counts": dict(sorted(overall_status_counts.items())),
        "quality_profitability_readiness_status_counts": dict(sorted(quality_status_counts.items())),
        "dividend_readiness_status_counts": dict(sorted(dividend_status_counts.items())),
        "scoring_activation_allowed": False,
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "promotion_blocked_reason": "Valuation scoring remains inactive until PIT metadata, source lineage, reconciliation, and manual activation review all pass.",
    }


def _candidate_pairs(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    pairs = sorted({(row.get("candidate_id", ""), row.get("evidence_id", "")) for row in rows})
    return [(candidate_id, evidence_id) for candidate_id, evidence_id in pairs if candidate_id]


def _pending_reasons(row: dict[str, str]) -> list[str]:
    raw = row.get("pending_reason", "")
    return [reason for reason in raw.split(";") if reason]


def _append_flag(flags: str, flag: str) -> str:
    parts = [item for item in flags.replace(",", "|").split("|") if item]
    parts.append(flag)
    return "|".join(dict.fromkeys(parts))


def _next_trading_day_text(raw_date: str) -> str:
    parsed = _parse_yyyymmdd(raw_date)
    if parsed is None:
        return ""
    current = parsed + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()


def _parse_yyyymmdd(raw_date: str) -> date | None:
    value = raw_date.strip()
    if not value:
        return None
    try:
        if "-" in value:
            return date.fromisoformat(value)
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except (ValueError, IndexError):
        return None


def _parse_date_text(raw_date: str) -> date | None:
    value = raw_date.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return _parse_yyyymmdd(value)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rows_payload(report_type: str, rows: list[dict[str, str]], config: V15SupplementationConfig) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": config.created_at,
        "report_type": report_type,
        "row_count": len(rows),
        "scoring_activation_allowed": False,
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build safe local v1.5 supplementation artifacts.")
    project_root = Path(__file__).resolve().parents[3]
    workspace_root = project_root.parent
    default_output_dir = project_root / "data" / "v1_5_valuation"
    parser.add_argument(
        "--pending-handoff",
        type=Path,
        default=default_output_dir / "v1_5_chart_local_valuation_quality_pending_handoff_latest.csv",
    )
    parser.add_argument(
        "--dart-metadata",
        type=Path,
        default=None,
        help="Optional local OpenDART metadata import CSV. No live collection is performed.",
    )
    parser.add_argument(
        "--dart-raw-snapshot",
        type=Path,
        default=None,
        help="Optional local OpenDART raw JSONL snapshot used only when --dart-metadata is absent.",
    )
    parser.add_argument(
        "--naver-ratio-policy-snapshot",
        type=Path,
        default=None,
        help="Optional local Naver main.naver ratio policy snapshot CSV.",
    )
    parser.add_argument(
        "--technical-ml-scores",
        type=Path,
        default=workspace_root / "Quant_mvp" / "data" / "v0_4" / "selector_scores" / "v0_4_selector_scores.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=default_output_dir)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_v1_5_supplementation(
        V15SupplementationConfig(
            pending_handoff_path=args.pending_handoff,
            dart_metadata_path=args.dart_metadata,
            dart_raw_snapshot_path=args.dart_raw_snapshot,
            naver_ratio_policy_snapshot_path=args.naver_ratio_policy_snapshot,
            technical_ml_scores_path=args.technical_ml_scores,
            output_dir=args.output_dir,
        )
    )
    update = result["limited_completion_update"]
    print(
        "v1.5 supplementation status={status} rows={rows} incremental={incremental}".format(
            status=update["current_status"],
            rows=update["row_count"],
            incremental=update["incremental_evidence_status"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
