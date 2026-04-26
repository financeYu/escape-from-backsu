"""CLI wrapper for the MVP v0.1 canonical latest-ranking builder."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import sys

from importlib import metadata

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner.latest_ranking import build_latest_ranking_output  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the MVP latest-ranking CLI parser."""

    parser = argparse.ArgumentParser(
        description="Build the KOSPI200 technical MVP v0.1 latest ranking from local CSV inputs.",
    )
    parser.add_argument(
        "--normalized-scores",
        required=True,
        help="CSV path containing normalized technical score rows.",
    )
    parser.add_argument(
        "--adoption-synthesis",
        required=True,
        help="CSV path containing the Step 14 technical-only adoption synthesis table.",
    )
    parser.add_argument(
        "--as-of-date",
        required=True,
        help="Required same-date ranking snapshot date.",
    )
    parser.add_argument(
        "--max-allowed-date",
        required=True,
        help="Required maximum allowed input date for future-date rejection.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Optional row limit for display/export after canonical ranking is built.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional CSV output path. If omitted, CSV is printed to stdout.",
    )
    parser.add_argument(
        "--manifest-output",
        default=None,
        help="Optional JSON manifest path with input hashes, parameters, and runtime versions.",
    )
    return parser


def _read_csv(path: str | Path, *, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV input not found: {csv_path}")
    return pd.read_csv(csv_path, dtype=dtype)


def main(argv: list[str] | None = None) -> int:
    """Run the canonical latest-ranking builder from local CSV inputs."""

    args = build_parser().parse_args(argv)
    normalized_scores = _read_csv(args.normalized_scores, dtype={"ticker": str})
    adoption_synthesis = _read_csv(args.adoption_synthesis)
    ranking = build_latest_ranking_output(
        normalized_scores,
        adoption_synthesis,
        as_of_date=args.as_of_date,
        max_allowed_date=args.max_allowed_date,
        top_n=args.top_n,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ranking.to_csv(output_path, index=False, encoding="utf-8")
    else:
        print(ranking.to_csv(index=False), end="")
    if args.manifest_output:
        _write_manifest(
            Path(args.manifest_output),
            normalized_scores_path=Path(args.normalized_scores),
            adoption_synthesis_path=Path(args.adoption_synthesis),
            output_path=Path(args.output) if args.output else None,
            as_of_date=args.as_of_date,
            max_allowed_date=args.max_allowed_date,
            top_n=args.top_n,
        )
    return 0


def _write_manifest(
    path: Path,
    *,
    normalized_scores_path: Path,
    adoption_synthesis_path: Path,
    output_path: Path | None,
    as_of_date: str,
    max_allowed_date: str,
    top_n: int | None,
) -> None:
    manifest = {
        "schema_version": 1,
        "scope": "kospi200_technical_mvp_v0_1_latest_ranking",
        "parameters": {
            "as_of_date": as_of_date,
            "max_allowed_date": max_allowed_date,
            "top_n": top_n,
        },
        "inputs": {
            "normalized_scores": _file_ref(normalized_scores_path),
            "adoption_synthesis": _file_ref(adoption_synthesis_path),
        },
        "output": _file_ref(output_path) if output_path else {"path": "stdout"},
        "runtime": {
            "python": platform.python_version(),
            "pandas": _package_version("pandas"),
            "numpy": _package_version("numpy"),
        },
        "contract": {
            "universe": "KOSPI200",
            "technical_composite_score": "technical_only",
            "final_composite_score": "equals_technical_composite_score",
            "valuation_fundamental_scoring": "inactive",
            "backtest_feedback": "not_allowed",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_ref(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"path": None}
    return {
        "path": str(path),
        "sha256": _sha256(path) if path.exists() and path.is_file() else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not_installed"


if __name__ == "__main__":
    raise SystemExit(main())
