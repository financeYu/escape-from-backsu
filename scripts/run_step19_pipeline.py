"""CLI for the Step 19 automatic execution pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.step19_pipeline import (  # noqa: E402
    DEFAULT_STEP19_PIPELINE_CONFIG,
    run_step19_pipeline,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the Step 19 CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run the Step 19 automatic execution pipeline summary.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_STEP19_PIPELINE_CONFIG),
        help="Path to Step 19 pipeline TOML config.",
    )
    parser.add_argument(
        "--mode",
        choices=("dry_run", "validate_only", "run_allowed_stages"),
        default=None,
        help="Pipeline run mode. Defaults to config default, which must be dry_run.",
    )
    parser.add_argument(
        "--stage",
        dest="stages",
        action="append",
        default=None,
        help="Stage or alias to include. Can be repeated.",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Optional generated summary JSON path under reports/*/generated/.",
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Write a generated summary JSON. Default dry-run prints only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    summary = run_step19_pipeline(
        config_path=args.config,
        run_mode=args.mode,
        selected_stages=args.stages,
        summary_output_path=args.summary_output,
        write_summary=args.write_summary,
        project_root=PROJECT_ROOT,
    )
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.overall_status.value == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
