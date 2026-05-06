"""CLI wrapper for adjusted-close corporate-action event inputs."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.corporate_action_events import main


if __name__ == "__main__":
    raise SystemExit(main())
