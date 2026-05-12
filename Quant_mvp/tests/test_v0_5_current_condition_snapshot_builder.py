from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_5_current_condition_snapshots.py"
SPEC = importlib.util.spec_from_file_location("build_v0_5_current_condition_snapshots", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_current_condition_snapshot_builder_fails_closed_without_price_ingestion(tmp_path: Path) -> None:
    packet_input = tmp_path / "packets.jsonl"
    write_jsonl(
        packet_input,
        [
            {
                "candidate_id": "sc:recorded",
                "candidate_version": "v0.3.0",
                "cost_sensitivity_flags": ["cost_profile_kospi_product_purchase_cost_v1"],
            }
        ],
    )

    manifest = builder.build_snapshots(
        packet_input=packet_input,
        output_dir=tmp_path / "out",
        jsonl_name="snapshots.jsonl",
        csv_name="snapshots.csv",
        manifest_name="manifest.json",
        as_of_date="2026-05-10",
        dry_run=False,
    )

    snapshots = [
        json.loads(line)
        for line in (tmp_path / "out" / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert manifest["snapshot_count"] == 1
    assert manifest["guardrails"]["raw_price_files_read"] is False
    assert manifest["guardrails"]["new_market_data_ingestion_allowed"] is False
    assert snapshots[0]["current_condition_status"] == "blocked_missing_current_condition"
    assert snapshots[0]["no_order_generation_check"] == "pass_no_order_generation"
    assert snapshots[0]["cost_profile_ref"] == "kospi_product_purchase_cost_v1"


def test_snapshot_available_requires_approved_guards() -> None:
    bad_snapshot = {
        "current_condition_status": "snapshot_available",
        "universe_boundary": "KOSPI_or_KOSPI200_only",
        "condition_check_status": "current_condition_not_checked",
        "no_new_ingestion_check": "pass_no_new_market_data_ingestion_attempted",
        "no_universe_expansion_check": "pass_no_universe_expansion",
        "no_order_generation_check": "pass_no_order_generation",
        "data_source_ref": "approved-local-snapshot.jsonl",
        "price_recency_status": "approved_snapshot_current",
        "liquidity_check": "approved_snapshot_liquidity_reviewed",
    }

    try:
        builder._assert_snapshot_guardrails(bad_snapshot)
    except ValueError as exc:
        assert "snapshot_available requires condition_check_status" in str(exc)
    else:
        raise AssertionError("expected snapshot_available guardrail failure")
