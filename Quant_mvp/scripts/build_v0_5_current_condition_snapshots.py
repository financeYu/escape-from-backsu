"""Build v0.5 fail-closed CurrentConditionSnapshot rows.

The builder does not read raw price files and does not ingest market data. It
uses the v0.5 PersonalDecisionSupportPacket candidate set as a read-only source
and emits blocked snapshot rows until an approved current-condition input route
is supplied in a later task.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_PACKET_INPUT = Path(
    "Quant_mvp/data/v0_5/personal_decision_support/v0_5_personal_decision_support_packets.jsonl"
)
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_5/current_condition_snapshots")
DEFAULT_JSONL_NAME = "v0_5_current_condition_snapshots.jsonl"
DEFAULT_CSV_NAME = "v0_5_current_condition_snapshots.csv"
DEFAULT_MANIFEST_NAME = "v0_5_current_condition_snapshot_manifest.json"
SCHEMA_VERSION = "v0_5_current_condition_snapshot_v1_0"
MANIFEST_SCHEMA_VERSION = "v0_5_current_condition_snapshot_manifest_v1_0"
CONTRACT_REF = "docs/extension/v0_5_current_condition_snapshot_contract.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-input", type=Path, default=DEFAULT_PACKET_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--jsonl-name", default=DEFAULT_JSONL_NAME)
    parser.add_argument("--csv-name", default=DEFAULT_CSV_NAME)
    parser.add_argument("--manifest-name", default=DEFAULT_MANIFEST_NAME)
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_snapshot(packet: dict[str, Any], *, as_of_date: str, generated_at: str) -> dict[str, Any]:
    candidate_id = str(packet["candidate_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": "ccs_v0_5_" + candidate_id.replace(":", "_"),
        "candidate_id": candidate_id,
        "candidate_version": packet.get("candidate_version"),
        "as_of_date": as_of_date,
        "generated_at_utc": generated_at,
        "contract_ref": CONTRACT_REF,
        "universe_boundary": "KOSPI_or_KOSPI200_only",
        "data_source_ref": None,
        "price_recency_status": "not_checked_missing_approved_snapshot",
        "liquidity_check": "not_checked_missing_approved_snapshot",
        "cost_profile_ref": _first_cost_profile(packet),
        "condition_check_status": "blocked_missing_approved_current_condition_snapshot",
        "current_condition_status": "blocked_missing_current_condition",
        "no_new_ingestion_check": "pass_no_new_market_data_ingestion_attempted",
        "no_universe_expansion_check": "pass_no_universe_expansion",
        "no_order_generation_check": "pass_no_order_generation",
        "manual_review_required": True,
        "blocked_reason": "approved_current_condition_snapshot_not_supplied",
    }


def _first_cost_profile(packet: dict[str, Any]) -> str | None:
    for flag in packet.get("cost_sensitivity_flags") or []:
        text = str(flag)
        if text.startswith("cost_profile_"):
            return text.removeprefix("cost_profile_")
    return None


def _assert_snapshot_guardrails(snapshot: dict[str, Any]) -> None:
    if snapshot["current_condition_status"] == "snapshot_available":
        required = {
            "universe_boundary": "KOSPI_or_KOSPI200_only",
            "condition_check_status": "current_condition_passed",
            "no_new_ingestion_check": "pass_no_new_market_data_ingestion",
            "no_universe_expansion_check": "pass_no_universe_expansion",
            "no_order_generation_check": "pass_no_order_generation",
        }
        for key, expected in required.items():
            if snapshot.get(key) != expected:
                raise ValueError(f"snapshot_available requires {key}={expected}")
        if not snapshot.get("data_source_ref"):
            raise ValueError("snapshot_available requires approved data_source_ref")
        if not snapshot.get("price_recency_status") or not snapshot.get("liquidity_check"):
            raise ValueError("snapshot_available requires recency and liquidity checks")
    if snapshot["no_order_generation_check"] != "pass_no_order_generation":
        raise ValueError("snapshot failed no_order_generation_check")


def build_snapshots(
    *,
    packet_input: Path,
    output_dir: Path,
    jsonl_name: str,
    csv_name: str,
    manifest_name: str,
    as_of_date: str,
    dry_run: bool,
) -> dict[str, Any]:
    packets = read_jsonl(packet_input)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshots = [
        build_snapshot(packet, as_of_date=as_of_date, generated_at=generated_at)
        for packet in packets
        if packet.get("candidate_id")
    ]
    for snapshot in snapshots:
        _assert_snapshot_guardrails(snapshot)

    jsonl_path = output_dir / jsonl_name
    csv_path = output_dir / csv_name
    manifest_path = output_dir / manifest_name
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "contract_ref": CONTRACT_REF,
        "generated_at_utc": generated_at,
        "mode": "dry_run" if dry_run else "write",
        "snapshot_count": len(snapshots),
        "as_of_date": as_of_date,
        "current_condition_status_counts": dict(
            sorted(Counter(row["current_condition_status"] for row in snapshots).items())
        ),
        "condition_check_status_counts": dict(
            sorted(Counter(row["condition_check_status"] for row in snapshots).items())
        ),
        "input_refs": {"packet_input": _relative(packet_input)},
        "output_refs": {
            "jsonl": _relative(jsonl_path),
            "csv": _relative(csv_path),
            "manifest": _relative(manifest_path),
        },
        "guardrails": {
            "raw_price_files_read": False,
            "new_market_data_ingestion_allowed": False,
            "universe_expansion_allowed": False,
            "order_generation_allowed": False,
            "position_sizing_allowed": False,
            "production_activation_allowed": False,
        },
    }
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in snapshots) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "snapshot_id",
                "candidate_id",
                "candidate_version",
                "as_of_date",
                "current_condition_status",
                "condition_check_status",
                "price_recency_status",
                "liquidity_check",
                "manual_review_required",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in snapshots:
                writer.writerow({key: row[key] for key in fieldnames})
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_snapshots(
        packet_input=args.packet_input,
        output_dir=args.output_dir,
        jsonl_name=args.jsonl_name,
        csv_name=args.csv_name,
        manifest_name=args.manifest_name,
        as_of_date=args.as_of_date,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
