"""Build the v0.3 KOSPI200 ML price feature table from price CSV inputs."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.price_feature_table import main


if __name__ == "__main__":
    raise SystemExit(main())
