"""Build contract-only EvaluationEvidence packets for the v0.3 momentum cohort."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.evaluation_evidence import (
    build_contract_only_evaluation_evidence_packet,
    strategy_candidate_payload,
    validate_evaluation_evidence_output_path,
    write_evaluation_evidence_markdown,
)


DEFAULT_REGISTRY = Path(
    "Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl"
)
DEFAULT_OUTPUT_DIR = Path(
    "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/momentum_cohort_1"
)
DEFAULT_COHORT_ID = "momentum_evaluable_cohort_1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT_ID)
    parser.add_argument("--expected-count", type=int, help="Optional selected-candidate count guard.")
    parser.add_argument("--created-at", help="Optional YYYY-MM-DD packet creation date.")
    return parser.parse_args(argv)


def load_registry(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(payload)
    return rows


def select_momentum_evaluable_candidates(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        candidate = strategy_candidate_payload(row)
        scope = candidate.get("experiment_scope")
        strategy_type = scope.get("strategy_type") if isinstance(scope, dict) else None
        if candidate.get("status") == "evaluable" and strategy_type == "momentum":
            selected.append(row)
    return sorted(
        selected,
        key=lambda row: str(strategy_candidate_payload(row).get("candidate_id") or ""),
    )


def build_packets(
    rows: list[dict[str, Any]],
    *,
    cohort_id: str,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    return [
        build_contract_only_evaluation_evidence_packet(
            row,
            cohort_id=cohort_id,
            created_at=created_at,
        )
        for row in rows
    ]


def resolve_output_dir(output_dir: Path, *, project_root: Path) -> Path:
    boundary_probe = output_dir / "__boundary_probe__.md"
    return validate_evaluation_evidence_output_path(
        boundary_probe,
        project_root=project_root,
    ).parent


def remove_existing_packet_files(output_dir: Path, *, project_root: Path) -> list[Path]:
    resolved_dir = resolve_output_dir(output_dir, project_root=project_root)
    if not resolved_dir.exists():
        return []
    removed: list[Path] = []
    for path in sorted(resolved_dir.glob("ee_v0_3_*.md")):
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed


def write_packets(
    packets: list[dict[str, Any]],
    *,
    output_dir: Path,
    project_root: Path,
) -> list[Path]:
    written: list[Path] = []
    resolved_output_dir = resolve_output_dir(output_dir, project_root=project_root)
    for packet in packets:
        packet_path = resolved_output_dir / f"{packet['evaluation_id']}.md"
        written.append(
            write_evaluation_evidence_markdown(
                packet,
                packet_path,
                project_root=project_root,
            )
        )
    return written


def write_manifest(
    packets: list[dict[str, Any]],
    paths: list[Path],
    *,
    output_dir: Path,
    project_root: Path,
    cohort_id: str,
) -> Path:
    root = project_root.resolve()
    manifest_path = resolve_output_dir(output_dir, project_root=project_root)
    manifest_path.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_path / "manifest.json"
    manifest = {
        "schema_version": "v0_3_evaluation_evidence_cohort_manifest_0_1",
        "cohort_id": cohort_id,
        "status": "contract_only",
        "candidate_count": len(packets),
        "evaluation_ids": [str(packet["evaluation_id"]) for packet in packets],
        "candidate_ids": [str(packet["candidate_id"]) for packet in packets],
        "required_evaluation_check_ids": sorted(
            str(check_id)
            for packet in packets[:1]
            for check_id in packet.get("required_evaluation_checks", {})
        ),
        "packet_paths": [
            str(path.resolve().relative_to(root)).replace("\\", "/")
            for path in paths
        ],
        "generated_output_boundary": "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
    }
    manifest_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_file


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_registry(args.registry)
    selected = select_momentum_evaluable_candidates(rows)
    if args.expected_count is not None and len(selected) != args.expected_count:
        raise ValueError(
            f"expected {args.expected_count} momentum evaluable candidates, found {len(selected)}"
        )

    packets = build_packets(
        selected,
        cohort_id=args.cohort_id,
        created_at=args.created_at,
    )
    removed_paths = remove_existing_packet_files(
        args.output_dir,
        project_root=args.project_root,
    )
    paths = write_packets(
        packets,
        output_dir=args.output_dir,
        project_root=args.project_root,
    )
    manifest_path = write_manifest(
        packets,
        paths,
        output_dir=args.output_dir,
        project_root=args.project_root,
        cohort_id=args.cohort_id,
    )
    result = {
        "cohort_id": args.cohort_id,
        "candidate_count": len(packets),
        "manifest": str(manifest_path),
        "packet_paths": [str(path) for path in paths],
        "removed_packet_count": len(removed_paths),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
