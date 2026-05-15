from __future__ import annotations

import sys
import json
import csv
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.confidence_review_priority_v1_6 import (  # noqa: E402
    ALLOWED_INPUT_STATUS_VALUES,
    ALLOWED_REASON_CODES,
    COMMON_REQUIRED_FIELDS,
    CONFIG_DIAGNOSTIC_VALUES,
    FORBIDDEN_COLUMN_NAMES,
    GENERATED_OUTPUT_PATHS,
    OUTPUT_SCHEMAS,
    READINESS_VERDICTS,
    REQUIRED_INPUT_COLUMNS,
    THRESHOLD_CONFIG_CANDIDATES,
    THRESHOLD_POLICY,
    find_forbidden_column_names,
    validate_v1_6_output_schemas,
    validate_v1_6_readiness_verdict,
    validate_v1_6_reason_codes,
    validate_v1_6_status_values,
)
from src.review_priority.v1_6_confidence_review_priority import (  # noqa: E402
    V16InputError,
    run_v1_6_confidence_review_priority,
)
from src.review_priority.v1_6_real_artifact_adapter import build_real_available_v1_6_input  # noqa: E402


def test_v1_6_contract_defines_required_status_and_reason_vocabularies() -> None:
    required_statuses = {
        "diagnostic_ready",
        "partial_diagnostic_ready",
        "blocked_by_reconciliation",
        "vendor_reference_only",
        "after_evaluation_date",
        "skipped_missing_baseline_artifacts",
        "insufficient_data",
        "missing_artifact",
    }
    required_reason_codes = {
        "strong_multi_layer_coverage",
        "stable_across_horizons",
        "stable_across_splits",
        "blocked_by_upstream_reconciliation",
        "insufficient_baseline_artifact",
        "redundant_layer_warning",
        "limited_quality_evidence",
        "manual_review_only",
    }

    assert required_statuses <= ALLOWED_INPUT_STATUS_VALUES
    assert required_reason_codes <= ALLOWED_REASON_CODES
    validate_v1_6_status_values(required_statuses)
    validate_v1_6_reason_codes(required_reason_codes)


def test_v1_6_contract_blocks_forbidden_input_and_output_columns() -> None:
    required_forbidden = {
        "valuation_score",
        "fundamental_score",
        "technical_composite_score",
        "final_composite_score",
        "trade_signal",
        "signal",
        "order_instruction",
        "rebalance_instruction",
        "forward_return",
        "future_return",
        "expected_return",
        "alpha",
        "proven_alpha",
    }

    assert required_forbidden <= FORBIDDEN_COLUMN_NAMES
    assert find_forbidden_column_names(["candidate_id", "valuation_score", "final_composite_score"]) == (
        "final_composite_score",
        "valuation_score",
    )


def test_v1_6_contract_defines_all_required_output_schemas() -> None:
    expected_artifacts = {
        "v1_6_confidence_score_manifest",
        "v1_6_horizon_stability_report",
        "v1_6_split_stability_report",
        "v1_6_layer_redundancy_report",
        "v1_6_composite_review_priority_manifest",
        "v1_6_v2_0_readiness_packet",
    }

    assert expected_artifacts == set(OUTPUT_SCHEMAS)
    validate_v1_6_output_schemas()
    for artifact_key, columns in OUTPUT_SCHEMAS.items():
        assert all(field in columns for field in COMMON_REQUIRED_FIELDS), artifact_key
        assert not set(columns).intersection(FORBIDDEN_COLUMN_NAMES), artifact_key
        assert GENERATED_OUTPUT_PATHS[artifact_key].startswith("Quant_mvp/data/v1_6/review_priority/")


def test_v1_6_contract_defines_readiness_verdicts_and_input_columns() -> None:
    assert {
        "V2_0_READY_FOR_LIMITED_REVIEW",
        "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY",
        "V2_0_NOT_READY",
    } == READINESS_VERDICTS
    validate_v1_6_readiness_verdict("V2_0_NOT_READY")
    with pytest.raises(ValueError, match="unknown v1.6 readiness verdict"):
        validate_v1_6_readiness_verdict("READY_FOR_PRODUCTION")

    assert {
        "candidate_id",
        "ticker",
        "evaluation_date",
    } == REQUIRED_INPUT_COLUMNS


def test_v1_6_contract_exposes_config_missing_instead_of_fallback_thresholds() -> None:
    assert "config_missing" in CONFIG_DIAGNOSTIC_VALUES
    assert "config/thresholds.toml" in THRESHOLD_CONFIG_CANDIDATES
    assert "Quant_mvp/config/thresholds.toml" in THRESHOLD_CONFIG_CANDIDATES
    assert "no fallback numeric thresholds" in THRESHOLD_POLICY


def test_v1_6_runner_emits_manual_review_only_fixture_outputs(tmp_path: Path) -> None:
    input_path = PROJECT_ROOT / "tests" / "fixtures" / "v1_6_merged_evidence_fixture.csv"
    output_dir = tmp_path / "v1_6_outputs"

    result = run_v1_6_confidence_review_priority(
        input_path=input_path,
        output_dir=output_dir,
        input_mode="fixture",
    )

    expected_files = {
        "v1_6_confidence_score_manifest_latest.csv",
        "v1_6_horizon_stability_report_latest.csv",
        "v1_6_split_stability_report_latest.csv",
        "v1_6_layer_redundancy_report_latest.csv",
        "v1_6_composite_review_priority_manifest_latest.csv",
        "v1_6_v2_0_readiness_packet_latest.json",
        "v1_6_v2_0_readiness_packet_latest.md",
        "v1_6_integration_guardrail_lineage_packet_test_report_latest.json",
    }
    assert expected_files == {path.name for path in output_dir.iterdir()}
    assert result["readiness_verdict"] == "V2_0_NOT_READY"

    composite_rows = _read_csv(output_dir / "v1_6_composite_review_priority_manifest_latest.csv")
    assert {row["manual_review_priority"] for row in composite_rows} == {
        "review_preferred",
        "blocked_manual_review",
    }
    for row in composite_rows:
        assert row["manual_review_only_notice"]
        assert "manual_review_only" in row["reason_codes"]


def test_v1_6_runner_blocks_forbidden_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "forbidden.csv"
    input_path.write_text(
        "candidate_id,ticker,evaluation_date,valuation_score\n"
        "A,005930,2026-05-14,1.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden column"):
        run_v1_6_confidence_review_priority(input_path=input_path, output_dir=tmp_path / "out")


def test_v1_6_runner_blocks_forbidden_language(tmp_path: Path) -> None:
    input_path = tmp_path / "forbidden_language.csv"
    input_path.write_text(
        "candidate_id,ticker,evaluation_date,evidence_status,coverage,data_quality,stability,source_artifact\n"
        "A,005930,2026-05-14,diagnostic_ready,0.9,0.9,0.9,production ranking note\n",
        encoding="utf-8",
    )

    with pytest.raises(V16InputError, match="forbidden v1.6 language"):
        run_v1_6_confidence_review_priority(input_path=input_path, output_dir=tmp_path / "out")


def test_v1_6_runner_readiness_packet_fields_and_lineage(tmp_path: Path) -> None:
    input_path = PROJECT_ROOT / "tests" / "fixtures" / "v1_6_merged_evidence_fixture.csv"
    output_dir = tmp_path / "v1_6_outputs"
    run_v1_6_confidence_review_priority(input_path=input_path, output_dir=output_dir, input_mode="fixture")

    packet = json.loads((output_dir / "v1_6_v2_0_readiness_packet_latest.json").read_text(encoding="utf-8"))
    guardrail = json.loads(
        (
            output_dir / "v1_6_integration_guardrail_lineage_packet_test_report_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert packet["manual_review_only"] is True
    assert packet["valuation_scoring_activation_allowed"] is False
    assert packet["automatic_action_allowed"] is False
    assert packet["source_artifact_refs"] == (
        "v1_1_profitability_fixture;v1_2_ml_fixture;v1_3_cost_fixture;v1_5_handoff_fixture"
    )
    assert "valuation:002" in packet["lineage_refs"]
    assert "baseline artifact missing" in packet["carry_forward_limitations"]
    assert guardrail["manual_review_only_confirmed"] is True
    assert guardrail["forbidden_columns_absent"] is True
    assert guardrail["lineage_or_source_refs_present"] is True
    assert packet["guardrail_summary"]["manual_review_only"] is True
    assert packet["guardrail_summary"]["valuation_scoring_activation_allowed"] is False
    assert len(packet["output_file_names"]) == 8


def test_v1_6_runner_emits_config_missing_without_threshold_fallback(tmp_path: Path) -> None:
    input_path = PROJECT_ROOT / "tests" / "fixtures" / "v1_6_merged_evidence_fixture.csv"
    output_dir = tmp_path / "v1_6_outputs"

    result = run_v1_6_confidence_review_priority(
        input_path=input_path,
        output_dir=output_dir,
        config_path=tmp_path / "missing_thresholds.toml",
        input_mode="fixture",
    )

    confidence_rows = _read_csv(output_dir / "v1_6_confidence_score_manifest_latest.csv")
    assert {row["confidence_support_status"] for row in confidence_rows} == {"config_missing"}
    assert "missing_threshold_config" in result["missing_dependencies"]


def test_v1_6_runner_marks_missing_lineage_explicitly(tmp_path: Path) -> None:
    input_path = tmp_path / "missing_lineage.csv"
    input_path.write_text(
        "candidate_id,ticker,evaluation_date,evidence_status,coverage,data_quality,stability\n"
        "A,005930,2026-05-14,diagnostic_ready,0.9,0.9,0.9\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    result = run_v1_6_confidence_review_priority(input_path=input_path, output_dir=output_dir)
    packet = json.loads((output_dir / "v1_6_v2_0_readiness_packet_latest.json").read_text(encoding="utf-8"))

    assert "missing_source_artifact_refs" in result["missing_dependencies"]
    assert "missing_lineage_refs" in result["missing_dependencies"]
    assert packet["source_artifact_refs"] == "missing_source_artifact"
    assert packet["lineage_refs"] == "missing_lineage_ref"


def test_v1_6_stability_statuses_are_deterministic(tmp_path: Path) -> None:
    input_path = tmp_path / "stability.csv"
    input_path.write_text(
        "candidate_id,ticker,evaluation_date,horizon_id,split_id,seed,evidence_status,"
        "coverage,data_quality,stability,source_artifact,lineage_ref\n"
        "A,005930,2026-05-14,1d,s1,1,diagnostic_ready,0.9,0.9,0.8,src,line\n"
        "A,005930,2026-05-14,1w,s2,2,diagnostic_ready,0.9,0.9,0.7,src,line\n"
        "B,000660,2026-05-14,1d,s1,1,diagnostic_ready,0.9,0.9,0.8,src,line\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    run_v1_6_confidence_review_priority(input_path=input_path, output_dir=output_dir)
    first_horizon = _read_csv(output_dir / "v1_6_horizon_stability_report_latest.csv")
    first_split = _read_csv(output_dir / "v1_6_split_stability_report_latest.csv")
    run_v1_6_confidence_review_priority(input_path=input_path, output_dir=output_dir)
    second_horizon = _read_csv(output_dir / "v1_6_horizon_stability_report_latest.csv")
    second_split = _read_csv(output_dir / "v1_6_split_stability_report_latest.csv")

    assert first_horizon == second_horizon
    assert first_split == second_split
    horizon_by_candidate = {row["candidate_id"]: row["horizon_stability_status"] for row in first_horizon}
    split_by_candidate = {row["candidate_id"]: row["split_stability_status"] for row in first_split}
    assert horizon_by_candidate == {"A": "stable_across_horizons", "B": "insufficient_horizon_coverage"}
    assert split_by_candidate == {"A": "stable_across_splits", "B": "insufficient_split_or_seed_coverage"}


def test_v1_6_layer_redundancy_uses_config_warn_and_block_thresholds(tmp_path: Path) -> None:
    config_path = tmp_path / "thresholds.toml"
    config_path.write_text(
        "[coverage]\n"
        "warn_score_coverage = 0.80\n"
        "min_score_coverage = 0.60\n"
        "[stability]\n"
        "rank_stability_warn_floor = 0.50\n"
        "[redundancy]\n"
        "spearman_warn = 0.80\n"
        "spearman_block = 0.95\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "redundancy.csv"
    rows = [
        "candidate_id,ticker,evaluation_date,layer_id,evidence_status,coverage,data_quality,"
        "stability,evidence_value,source_artifact,lineage_ref",
    ]
    for index, block_value, warn_value in [
        (1, 1, 1),
        (2, 2, 2),
        (3, 3, 3),
        (4, 4, 5),
        (5, 5, 4),
    ]:
        candidate_id = f"C{index}"
        ticker = f"00066{index}"
        common = f"{candidate_id},{ticker},2026-05-14"
        rows.append(f"{common},block_a,diagnostic_ready,0.9,0.9,0.9,{block_value},src,line")
        rows.append(f"{common},block_b,diagnostic_ready,0.9,0.9,0.9,{block_value},src,line")
        rows.append(f"{common},warn_c,diagnostic_ready,0.9,0.9,0.9,{warn_value},src,line")
    input_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    run_v1_6_confidence_review_priority(
        input_path=input_path,
        output_dir=output_dir,
        config_path=config_path,
    )

    layer_rows = _read_csv(output_dir / "v1_6_layer_redundancy_report_latest.csv")
    statuses = {
        (row["layer_id_a"], row["layer_id_b"]): row["redundancy_status"]
        for row in layer_rows
    }
    assert statuses[("block_a", "block_b")] == "redundant_layer_block"
    assert statuses[("block_a", "warn_c")] == "redundant_layer_warning"
    assert statuses[("block_b", "warn_c")] == "redundant_layer_warning"


def test_v1_6_real_adapter_merges_clear_join_keys_and_marks_missing_upstream(tmp_path: Path) -> None:
    v1_3 = tmp_path / "v1_3.csv"
    v1_4 = tmp_path / "v1_4.csv"
    v1_5_features = tmp_path / "v1_5_features.csv"
    v1_5_handoff = tmp_path / "v1_5_handoff.csv"
    v1_5_incremental = tmp_path / "v1_5_incremental.csv"
    v1_3.write_text(
        "candidate_id,candidate_ticker,as_of_date,liquidity_proxy_source_ref\n"
        "C1,005930,2026-05-14,liquidity-ref\n",
        encoding="utf-8",
    )
    v1_4.write_text(
        "candidate_id,source_ticker,selection_reference_date,diagnostic_status,"
        "diagnostic_reason_codes,revision_source_ref\n"
        "C1,005930,2026-05-14,diagnostic_missing_pit_revision_fields,available_at_missing,revision-ref\n",
        encoding="utf-8",
    )
    v1_5_features.write_text(
        "candidate_id,ticker,evaluation_date,field_name,feature_readiness_status\n"
        "C1,005930,2026-05-14,price_to_earnings,blocked_by_reconciliation\n",
        encoding="utf-8",
    )
    v1_5_handoff.write_text(
        "schema_version,ticker,candidate_id,evaluation_date,overall_valuation_status,"
        "overall_quality_profitability_status,price_to_earnings_canonical_formula_status,"
        "price_to_book_canonical_formula_status,price_to_earnings_vendor_reference_status,"
        "price_to_book_vendor_reference_status,dividend_yield_status,incremental_evidence_status,"
        "candidate_overall_readiness_status,limitations,manual_review_required\n"
        "v1,005930,C1,2026-05-14,reference_only_after_evaluation_date,diagnostic_ready,"
        "blocked_by_reconciliation,blocked_by_reconciliation,reference_only_after_evaluation_date,"
        "reference_only_after_evaluation_date,diagnostic_ready,skipped_missing_baseline_artifacts,"
        "partial_diagnostic_ready,formula_variance,true\n",
        encoding="utf-8",
    )
    v1_5_incremental.write_text(
        "candidate_id,evidence_id,ticker,evaluation_date,horizon_id,technical_ml_baseline_status,"
        "valuation_overlay_status,comparison_status,reason_code,required_dependency\n"
        "C1,E1,005930,2026-05-14,missing_horizon_id,skipped_missing_candidate_overlap,"
        "skipped_insufficient_pit_fundamentals,skipped_missing_baseline_artifacts,"
        "candidate_overlapping_technical_ml_baseline_missing,baseline row\n",
        encoding="utf-8",
    )

    output_csv = tmp_path / "merged.csv"
    report_path = tmp_path / "report.json"
    report = build_real_available_v1_6_input(
        output_csv=output_csv,
        dependency_report=report_path,
        artifacts={
            "v1_3_liquidity": v1_3,
            "v1_4_revision": v1_4,
            "v1_5_feature_readiness": v1_5_features,
            "v1_5_to_v1_6_handoff": v1_5_handoff,
            "v1_5_incremental_comparison": v1_5_incremental,
        },
    )

    rows = _read_csv(output_csv)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["merged_row_count"] == 1
    assert report_payload["join_keys"] == ["candidate_id", "ticker", "evaluation_date"]
    assert "v1_1_net_profitability" in report["missing_or_limited_artifacts"]
    assert "v1_2_baseline_ml_selector" in report["missing_or_limited_artifacts"]
    assert rows[0]["candidate_id"] == "C1"
    assert "liquidity-ref" in rows[0]["lineage_ref"]
    assert "formula_variance" in rows[0]["limitations"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
