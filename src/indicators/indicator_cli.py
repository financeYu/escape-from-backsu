"""Step 7 indicator command-line entrypoint."""

from __future__ import annotations

import argparse
from typing import Iterable

from .indicator_io import run_indicator_pipeline_from_config


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Step 7 technical indicator calculation.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--data-config", default="config/data.toml")
    parser.add_argument("--windows-config", default="config/windows.toml")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run_indicator_pipeline_from_config(
        project_root=args.project_root,
        data_config_path=args.data_config,
        windows_config_path=args.windows_config,
    )
    print(
        "Step 7 indicators complete: "
        f"rows={result.summary['row_count']}, "
        f"indicator_columns={result.summary['indicator_column_count']}, "
        f"output={result.output_path}"
    )
    return 0


__all__ = ["main"]
