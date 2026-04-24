"""Filesystem paths used by the local analysis component."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = DATA_DIR / "scan_results"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_CHARTS_DIR = OUTPUTS_DIR / "charts"
UNIVERSE_DIR = PROJECT_ROOT / "universe"
UNIVERSE_SNAPSHOT_PATH = UNIVERSE_DIR / "kospi200_snapshot.csv"
MPL_CONFIG_DIR = PROJECT_ROOT / ".mplconfig"
UNIVERSE_FILE = PACKAGE_ROOT / "providers" / "kospi200.csv"

DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_CHARTS_DIR.mkdir(exist_ok=True)
UNIVERSE_DIR.mkdir(exist_ok=True)
MPL_CONFIG_DIR.mkdir(exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))
