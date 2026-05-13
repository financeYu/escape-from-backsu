from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CHART_LIQUIDITY_HANDOFF_PATH = (
    PROJECT_ROOT
    / "chart_mvp"
    / "data"
    / "v1_3_liquidity"
    / "v1_3_candidate_liquidity_handoff_records_latest.csv"
)

from Quant_mvp.backtest_mvp.cost_liquidity_reliability_v1_3 import (  # noqa: E402
    CostLiquidityReliabilityConfig,
    build_v1_3_candidate_liquidity_handoff,
    run_v1_3_cost_turnover_liquidity_reliability,
    validate_v1_3_candidate_liquidity_handoff,
    validate_v1_3_reliability_artifacts,
)
from Quant_mvp.backtest_mvp.net_profitability_runner_v1 import (  # noqa: E402
    NetProfitabilityRunnerConfig,
    run_net_profitability_evidence_v1_1,
)


def _records() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "sc_v1_3_low_drag",
            "selector_score": 88.0,
            "gross_return": 0.12,
            "benchmark_return": 0.04,
            "turnover": 0.35,
            "volatility": 0.11,
            "max_drawdown": -0.05,
            "coverage_ratio": 0.96,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
            "rebalance_frequency": "monthly",
            "rebalancing_role": "material_effect_on_candidate_evidence",
            "rebalance_disclosure": "historical simulated monthly rebalancing materially affects candidate evidence context only",
        },
        {
            "candidate_id": "sc_v1_3_high_turnover",
            "selector_score": 77.0,
            "gross_return": 0.10,
            "benchmark_return": 0.04,
            "turnover": 1.60,
            "volatility": 0.13,
            "max_drawdown": -0.08,
            "coverage_ratio": 0.91,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
        {
            "candidate_id": "sc_v1_3_missing_liquidity",
            "selector_score": 61.0,
            "gross_return": 0.07,
            "benchmark_return": 0.04,
            "turnover": 0.70,
            "volatility": 0.09,
            "max_drawdown": -0.04,
            "coverage_ratio": 0.88,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
    ]


def _evidences() -> list[dict[str, object]]:
    artifacts = run_net_profitability_evidence_v1_1(
        _records(),
        config=NetProfitabilityRunnerConfig(
            top_k=3,
            cost_rate=0.003,
            slippage_rate=0.001,
            random_seed=13,
        ),
    )
    return artifacts["evaluation_evidence_v1"]


def _liquidity_records() -> list[dict[str, object]]:
    with CHART_LIQUIDITY_HANDOFF_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _artifacts() -> dict[str, object]:
    return run_v1_3_cost_turnover_liquidity_reliability(
        _evidences(),
        liquidity_records=_liquidity_records(),
        config=CostLiquidityReliabilityConfig(capacity_reference_amount=100_000_000.0),
    )


def test_v1_3_reliability_layer_builds_required_artifacts() -> None:
    artifacts = _artifacts()

    validate_v1_3_reliability_artifacts(artifacts)
    assert artifacts["v1_3_candidate_liquidity_handoff"]["candidate_count"] == 3
    assert artifacts["v1_3_cost_profile_registry"]["active_cost_profile_ref"]
    assert artifacts["v1_3_turnover_penalty_report"]["candidate_count"] == 3
    assert artifacts["v1_3_liquidity_guard_report"]["candidate_count"] == 3
    assert artifacts["v1_3_manual_review_cost_risk_section"]["manual_review_required"] is True


def test_v1_3_candidate_liquidity_handoff_normalizes_candidate_rows() -> None:
    handoff = build_v1_3_candidate_liquidity_handoff(
        _evidences(),
        liquidity_records=_liquidity_records(),
        config=CostLiquidityReliabilityConfig(capacity_reference_amount=100_000_000.0),
    )

    validate_v1_3_candidate_liquidity_handoff(handoff)
    rows = {row["candidate_id"]: row for row in handoff["candidate_liquidity_rows"]}
    assert rows["sc_v1_3_low_drag"]["liquidity_handoff_status"] == "complete"
    assert rows["sc_v1_3_low_drag"]["liquidity_handoff_fields_complete"] is True
    assert rows["sc_v1_3_low_drag"]["liquidity_sufficiently_checked"] is True
    assert rows["sc_v1_3_low_drag"]["average_traded_value"] == 921_622_170_800.0
    assert rows["sc_v1_3_high_turnover"]["liquidity_handoff_status"] == "complete"
    assert rows["sc_v1_3_high_turnover"]["liquidity_handoff_fields_complete"] is True
    assert rows["sc_v1_3_high_turnover"]["liquidity_sufficiently_checked"] is True
    assert rows["sc_v1_3_missing_liquidity"]["liquidity_handoff_status"] == "complete"
    assert rows["sc_v1_3_missing_liquidity"]["liquidity_handoff_fields_complete"] is True
    assert rows["sc_v1_3_missing_liquidity"]["liquidity_sufficiently_checked"] is True
    assert rows["sc_v1_3_missing_liquidity"]["capacity_reference_amount"] == 100_000_000.0
    assert handoff["data_gap_summary"] == []
    assert handoff["unmatched_liquidity_record_candidate_ids"] == []
    assert "liquidity_proxy_source_ref" in handoff["liquidity_proxy_fields"]


def test_v1_3_runner_accepts_candidate_liquidity_handoff() -> None:
    handoff = build_v1_3_candidate_liquidity_handoff(
        _evidences(),
        liquidity_records=_liquidity_records(),
        config=CostLiquidityReliabilityConfig(capacity_reference_amount=100_000_000.0),
    )

    artifacts = run_v1_3_cost_turnover_liquidity_reliability(
        _evidences(),
        liquidity_handoff=handoff,
        config=CostLiquidityReliabilityConfig(capacity_reference_amount=100_000_000.0),
    )

    assert artifacts["v1_3_candidate_liquidity_handoff"]["handoff_id"] == handoff["handoff_id"]
    assert artifacts["v1_3_liquidity_guard_report"]["liquidity_status_counts"] == {
        "pass": 3,
        "warn": 0,
        "block": 0,
    }


def test_v1_3_candidate_liquidity_handoff_reports_unknown_candidate_as_mismatch() -> None:
    records = _liquidity_records()
    records.append({"candidate_id": "sc_v1_3_unknown", "average_traded_value": 1.0})

    handoff = build_v1_3_candidate_liquidity_handoff(_evidences(), liquidity_records=records)

    assert handoff["unmatched_liquidity_record_candidate_ids"] == ["sc_v1_3_unknown"]
    assert handoff["unmatched_liquidity_record_count"] == 1
    assert "candidate_id_mismatch" in handoff["data_gap_summary"]


def test_v1_3_candidate_liquidity_handoff_rejects_duplicate_candidate_rows() -> None:
    records = _liquidity_records()
    records.append(dict(records[0]))

    with pytest.raises(ValueError, match="duplicate candidate_id"):
        build_v1_3_candidate_liquidity_handoff(_evidences(), liquidity_records=records)


def test_v1_3_cost_profile_ref_is_attached_to_every_evidence_row() -> None:
    artifacts = _artifacts()
    refs = artifacts["v1_3_cost_profile_registry"]["evidence_cost_profile_refs"]

    assert len(refs) == 3
    assert all(ref["cost_profile_ref"] == "kr_equity_simulated_cost_profile_v1_3_base" for ref in refs)
    rows = artifacts["v1_3_gross_vs_net_evidence_summary"]["candidate_rows"]
    assert all(row["cost_profile_ref"] == "kr_equity_simulated_cost_profile_v1_3_base" for row in rows)


def test_v1_3_turnover_and_cost_drag_can_warn_or_block_candidates() -> None:
    artifacts = _artifacts()
    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_turnover_penalty_report"]["candidate_turnover_rows"]
    }

    assert rows["sc_v1_3_low_drag"]["turnover_status"] == "pass"
    assert rows["sc_v1_3_high_turnover"]["turnover_status"] == "block"
    assert "turnover_above_block_threshold" in rows["sc_v1_3_high_turnover"]["reason_codes"]


def test_v1_3_liquidity_guard_resolves_chart_handoff_data_as_pass() -> None:
    artifacts = _artifacts()
    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_liquidity_guard_report"]["liquidity_rows"]
    }

    assert rows["sc_v1_3_low_drag"]["liquidity_status"] == "pass"
    assert rows["sc_v1_3_low_drag"]["liquidity_sufficiently_checked"] is True
    assert rows["sc_v1_3_low_drag"]["average_traded_value"] == 921_622_170_800.0
    assert rows["sc_v1_3_high_turnover"]["liquidity_status"] == "pass"
    assert rows["sc_v1_3_missing_liquidity"]["liquidity_status"] == "pass"
    assert rows["sc_v1_3_high_turnover"]["average_traded_value"] == 6_361_836_727_250.0
    assert rows["sc_v1_3_missing_liquidity"]["average_traded_value"] == 6_297_164_325_150.0


def test_v1_3_handoff_sufficient_flag_matches_guard_assessment() -> None:
    artifacts = _artifacts()
    handoff_rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_candidate_liquidity_handoff"]["candidate_liquidity_rows"]
    }
    guard_rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_liquidity_guard_report"]["liquidity_rows"]
    }

    for candidate_id, handoff_row in handoff_rows.items():
        assert handoff_row["liquidity_sufficiently_checked"] is guard_rows[candidate_id]["liquidity_sufficiently_checked"]


@pytest.mark.parametrize(
    ("record_update", "expected_status", "expected_reason", "sufficiently_checked"),
    [
        (
            {
                "average_traded_value": 12_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 100_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "pass",
            "liquidity_proxy_sufficiently_checked",
            True,
        ),
        (
            {
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 100_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "warn",
            "average_traded_value_missing",
            False,
        ),
        (
            {
                "average_traded_value": 1_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 10_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "block",
            "average_traded_value_below_block_threshold",
            False,
        ),
        (
            {
                "average_traded_value": 3_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 100_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "warn",
            "average_traded_value_below_warn_threshold",
            False,
        ),
        (
            {
                "average_traded_value": 12_000_000_000.0,
                "capacity_reference_amount": 100_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "warn",
            "market_cap_proxy_missing",
            False,
        ),
        (
            {
                "average_traded_value": 12_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "warn",
            "capacity_reference_missing",
            False,
        ),
        (
            {
                "average_traded_value": 12_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 700_000_000.0,
                "liquidity_proxy_source_ref": "approved_local_liquidity_snapshot_20260514_20d",
            },
            "warn",
            "capacity_reference_exceeds_liquidity_proxy",
            False,
        ),
        (
            {
                "average_traded_value": 12_000_000_000.0,
                "market_cap_proxy": 900_000_000_000.0,
                "capacity_reference_amount": 100_000_000.0,
            },
            "warn",
            "liquidity_proxy_source_ref_missing",
            False,
        ),
    ],
)
def test_v1_3_liquidity_guard_applies_handoff_field_thresholds(
    record_update: dict[str, object],
    expected_status: str,
    expected_reason: str,
    sufficiently_checked: bool,
) -> None:
    record = {"candidate_id": "sc_v1_3_low_drag", **record_update}
    artifacts = run_v1_3_cost_turnover_liquidity_reliability(
        _evidences(),
        liquidity_records=[record],
        config=CostLiquidityReliabilityConfig(),
    )
    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_liquidity_guard_report"]["liquidity_rows"]
    }

    low_drag_row = rows["sc_v1_3_low_drag"]
    assert low_drag_row["liquidity_status"] == expected_status
    assert expected_reason in low_drag_row["reason_codes"]
    assert low_drag_row["liquidity_sufficiently_checked"] is sufficiently_checked


def test_v1_3_liquidity_block_takes_priority_over_warn_reasons() -> None:
    artifacts = run_v1_3_cost_turnover_liquidity_reliability(
        _evidences(),
        liquidity_records=[
            {
                "candidate_id": "sc_v1_3_low_drag",
                "average_traded_value": 1_000_000_000.0,
            }
        ],
        config=CostLiquidityReliabilityConfig(),
    )
    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_3_liquidity_guard_report"]["liquidity_rows"]
    }

    low_drag_row = rows["sc_v1_3_low_drag"]
    assert low_drag_row["liquidity_status"] == "block"
    assert "average_traded_value_below_block_threshold" in low_drag_row["reason_codes"]
    assert "market_cap_proxy_missing" in low_drag_row["reason_codes"]
    assert "capacity_reference_missing" in low_drag_row["reason_codes"]


def test_v1_3_gross_vs_net_and_rebalance_sensitivity_are_separated() -> None:
    artifacts = _artifacts()
    summary = artifacts["v1_3_gross_vs_net_evidence_summary"]
    sensitivity = artifacts["v1_3_rebalance_sensitivity_report"]

    assert summary["separation_policy"].startswith("gross evidence")
    first = summary["candidate_rows"][0]
    assert "gross_evidence_return" in first
    assert "source_net_return" in first
    assert "v1_3_adjusted_net_return" in first
    frequencies = {
        row["frequency_label"]
        for candidate in sensitivity["candidate_sensitivity_rows"]
        for row in candidate["sensitivity_rows"]
    }
    assert frequencies == {"daily", "weekly", "monthly"}


def test_v1_3_manual_review_section_summarizes_cost_and_liquidity_limits() -> None:
    artifacts = _artifacts()
    section = artifacts["v1_3_manual_review_cost_risk_section"]
    rows = {row["candidate_id"]: row for row in section["candidate_sections"]}

    assert rows["sc_v1_3_high_turnover"]["turnover_status"] == "block"
    assert rows["sc_v1_3_high_turnover"]["liquidity_status"] == "pass"
    assert rows["sc_v1_3_low_drag"]["liquidity_status"] == "pass"
    assert "confirm_liquidity_status_before_interpreting_candidate_evidence" in section["manual_review_checklist"]
    assert section["data_gap_summary"] == []


def test_v1_3_artifacts_reject_prohibited_language() -> None:
    artifacts = _artifacts()
    artifacts["v1_3_manual_review_cost_risk_section"]["bad_text"] = "future return"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_v1_3_reliability_artifacts(artifacts)


def test_v1_3_artifacts_are_json_serializable() -> None:
    artifacts = _artifacts()

    text = json.dumps(artifacts, sort_keys=True)
    assert "v1_3_cost_profile_registry" in text
    assert "production_ranking_update_enabled" in text
