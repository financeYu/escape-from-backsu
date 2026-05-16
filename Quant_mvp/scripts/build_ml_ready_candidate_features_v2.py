"""Build ml_ready_candidate_features_v2 rows and trainability report.

This script connects existing audit, label, lineage, and leakage-review inputs
without training a model or changing selector output behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.ml_ready_candidate_features_v2 import (
    build_baseline_selector_trainability_check_v2,
    build_ml_ready_candidate_features_v2,
)
from Quant_mvp.scripts.artifact_io import read_json, read_jsonl

DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_4/ml_ready_candidate_features_v2")
DEFAULT_ROWS_NAME = "ml_ready_candidate_features_v2.jsonl"
DEFAULT_MANIFEST_NAME = "ml_ready_candidate_features_v2_manifest.json"
DEFAULT_TRAINABILITY_NAME = "baseline_selector_trainability_v2_report.json"

MANIFEST_ID_KEYS = (
    "label_manifest_id",
    "audit_manifest_id",
    "feature_lineage_manifest_id",
    "manifest_id",
    "id",
)


def build_ml_ready_candidate_features_v2_outputs(
    *,
    candidate_rows_path: Path,
    audit_manifest_path: Path,
    feature_lineage_manifest_path: Path,
    output_dir: Path,
    label_manifest_path: Path | None = None,
    leakage_findings_path: Path | None = None,
    label_manifest_id: str | None = None,
    audit_manifest_id: str | None = None,
    feature_lineage_manifest_id: str | None = None,
    source_artifacts: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build and write v2 rows, manifest, and trainability report."""

    result = dry_run_ml_ready_candidate_features_v2(
        candidate_rows_path=candidate_rows_path,
        audit_manifest_path=audit_manifest_path,
        feature_lineage_manifest_path=feature_lineage_manifest_path,
        label_manifest_path=label_manifest_path,
        leakage_findings_path=leakage_findings_path,
        label_manifest_id=label_manifest_id,
        audit_manifest_id=audit_manifest_id,
        feature_lineage_manifest_id=feature_lineage_manifest_id,
        source_artifacts=source_artifacts,
        created_at=created_at,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / DEFAULT_ROWS_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    trainability_path = output_dir / DEFAULT_TRAINABILITY_NAME
    _write_jsonl_preserve_order(rows_path, result["artifact"]["rows"])
    _write_json(manifest_path, result["artifact"]["manifest"])
    _write_json(trainability_path, result["baseline_trainability_report"])
    return {
        "mode": "write",
        "output_written": True,
        "rows": str(rows_path),
        "manifest": str(manifest_path),
        "baseline_trainability_report": str(trainability_path),
        "source_summary": result["source_summary"],
    }


def dry_run_ml_ready_candidate_features_v2(
    *,
    candidate_rows_path: Path,
    audit_manifest_path: Path,
    feature_lineage_manifest_path: Path,
    label_manifest_path: Path | None = None,
    leakage_findings_path: Path | None = None,
    label_manifest_id: str | None = None,
    audit_manifest_id: str | None = None,
    feature_lineage_manifest_id: str | None = None,
    source_artifacts: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build v2 artifacts in memory and return a deterministic summary."""

    timestamp = created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candidate_rows = read_jsonl(candidate_rows_path)
    audit_manifest = read_json(audit_manifest_path)
    label_manifest = read_json(label_manifest_path) if label_manifest_path else {}
    lineage_manifest = read_json(feature_lineage_manifest_path)
    leakage_findings = _read_leakage_findings(leakage_findings_path)

    resolved_label_manifest_id = label_manifest_id or _manifest_id(label_manifest, "label_manifest_id")
    resolved_audit_manifest_id = audit_manifest_id or _manifest_id(audit_manifest, "audit_manifest_id")
    resolved_feature_lineage_manifest_id = (
        feature_lineage_manifest_id
        or _manifest_id(lineage_manifest, "feature_lineage_manifest_id")
    )
    feature_lineage = _feature_lineage(lineage_manifest)
    resolved_source_artifacts = _source_artifacts(
        candidate_rows_path=candidate_rows_path,
        audit_manifest_path=audit_manifest_path,
        feature_lineage_manifest_path=feature_lineage_manifest_path,
        label_manifest_path=label_manifest_path,
        leakage_findings_path=leakage_findings_path,
        explicit=source_artifacts,
    )
    artifact = build_ml_ready_candidate_features_v2(
        candidate_rows,
        audit_manifest,
        source_artifacts=resolved_source_artifacts,
        label_manifest_id=resolved_label_manifest_id,
        audit_manifest_id=resolved_audit_manifest_id or audit_manifest_path.stem,
        feature_lineage=feature_lineage,
        created_at=timestamp,
    )
    baseline_report = build_baseline_selector_trainability_check_v2(
        artifact,
        label_manifest_id=resolved_label_manifest_id,
        feature_lineage_manifest_id=resolved_feature_lineage_manifest_id,
        leakage_findings=leakage_findings,
        created_at=timestamp,
    )
    return {
        "mode": "dry_run",
        "output_written": False,
        "artifact": artifact,
        "baseline_trainability_report": baseline_report,
        "source_summary": {
            "candidate_rows_path": str(candidate_rows_path),
            "audit_manifest_path": str(audit_manifest_path),
            "label_manifest_path": str(label_manifest_path) if label_manifest_path else None,
            "feature_lineage_manifest_path": str(feature_lineage_manifest_path),
            "leakage_findings_path": str(leakage_findings_path) if leakage_findings_path else None,
            "label_manifest_id": resolved_label_manifest_id,
            "audit_manifest_id": resolved_audit_manifest_id or audit_manifest_path.stem,
            "feature_lineage_manifest_id": resolved_feature_lineage_manifest_id,
            "leakage_finding_count": len(leakage_findings),
        },
    }


def _feature_lineage(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if isinstance(manifest.get("feature_lineage"), Mapping):
        return {
            str(feature_name): dict(lineage)
            for feature_name, lineage in manifest["feature_lineage"].items()
            if isinstance(lineage, Mapping)
        }
    rows = manifest.get("rows") or manifest.get("features") or []
    if isinstance(rows, list):
        lineage: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            feature_name = row.get("feature_name") or row.get("name")
            if feature_name:
                lineage[str(feature_name)] = dict(row)
        return lineage
    return {}


def _manifest_id(manifest: Mapping[str, Any], preferred_key: str) -> str | None:
    for key in (preferred_key, *MANIFEST_ID_KEYS):
        value = manifest.get(key)
        if value:
            return str(value)
    return None


def _read_leakage_findings(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        findings = payload
    elif isinstance(payload, Mapping):
        findings = payload.get("leakage_findings") or payload.get("findings") or payload.get("rows") or []
    else:
        raise ValueError(f"{path} must contain a leakage findings object or list")
    if not isinstance(findings, list):
        raise ValueError(f"{path} leakage findings must be a list")
    return [dict(item) for item in findings if isinstance(item, Mapping)]


def _source_artifacts(
    *,
    candidate_rows_path: Path,
    audit_manifest_path: Path,
    feature_lineage_manifest_path: Path,
    label_manifest_path: Path | None,
    leakage_findings_path: Path | None,
    explicit: list[str] | None,
) -> list[str]:
    sources = list(explicit or [])
    sources.extend(
        [
            str(candidate_rows_path),
            str(audit_manifest_path),
            str(feature_lineage_manifest_path),
        ]
    )
    if label_manifest_path:
        sources.append(str(label_manifest_path))
    if leakage_findings_path:
        sources.append(str(leakage_findings_path))
    return sorted(set(sources))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl_preserve_order(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-rows", type=Path, required=True)
    parser.add_argument("--audit-manifest", type=Path, required=True)
    parser.add_argument("--feature-lineage-manifest", type=Path, required=True)
    parser.add_argument("--label-manifest", type=Path)
    parser.add_argument("--leakage-findings", type=Path)
    parser.add_argument("--label-manifest-id")
    parser.add_argument("--audit-manifest-id")
    parser.add_argument("--feature-lineage-manifest-id")
    parser.add_argument("--source-artifact", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--created-at")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    kwargs = {
        "candidate_rows_path": args.candidate_rows,
        "audit_manifest_path": args.audit_manifest,
        "feature_lineage_manifest_path": args.feature_lineage_manifest,
        "label_manifest_path": args.label_manifest,
        "leakage_findings_path": args.leakage_findings,
        "label_manifest_id": args.label_manifest_id,
        "audit_manifest_id": args.audit_manifest_id,
        "feature_lineage_manifest_id": args.feature_lineage_manifest_id,
        "source_artifacts": args.source_artifact,
        "created_at": args.created_at,
    }
    if args.dry_run:
        result = dry_run_ml_ready_candidate_features_v2(**kwargs)
    else:
        result = build_ml_ready_candidate_features_v2_outputs(
            output_dir=args.output_dir,
            **kwargs,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
