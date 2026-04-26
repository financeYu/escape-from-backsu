"""Filesystem paths used by the local analysis component."""

from __future__ import annotations

import os
from pathlib import Path

from stock_core.utils.market_specs import KOSPI200_UNIVERSE_SPEC, UniverseSpec


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = DATA_DIR / "scan_results"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_CHARTS_DIR = OUTPUTS_DIR / "charts"
UNIVERSE_DIR = PROJECT_ROOT / "universe"
MPL_CONFIG_DIR = PROJECT_ROOT / ".mplconfig"


def get_universe_snapshot_path(universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC) -> Path:
    """Return the local snapshot path for a universe spec."""

    return UNIVERSE_DIR / universe_spec.snapshot_filename


def get_packaged_universe_file(universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC) -> Path:
    """Return the packaged fallback CSV path for a universe spec."""

    return PACKAGE_ROOT / "providers" / universe_spec.packaged_filename


UNIVERSE_SNAPSHOT_PATH = get_universe_snapshot_path(KOSPI200_UNIVERSE_SPEC)
UNIVERSE_FILE = get_packaged_universe_file(KOSPI200_UNIVERSE_SPEC)

DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_CHARTS_DIR.mkdir(exist_ok=True)
UNIVERSE_DIR.mkdir(exist_ok=True)
MPL_CONFIG_DIR.mkdir(exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))
