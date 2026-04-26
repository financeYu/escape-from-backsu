"""Backward-compatible accessors for filesystem paths."""

from stock_core.utils.paths import (
    DATA_DIR,
    MPL_CONFIG_DIR,
    PACKAGE_ROOT,
    PROJECT_ROOT,
    RESULTS_DIR,
    UNIVERSE_FILE,
    get_packaged_universe_file,
    get_universe_snapshot_path,
)

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "DATA_DIR",
    "RESULTS_DIR",
    "MPL_CONFIG_DIR",
    "UNIVERSE_FILE",
    "get_packaged_universe_file",
    "get_universe_snapshot_path",
]
