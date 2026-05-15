"""CLI wrapper for the v1.6 walk-forward backtest input builder."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.walk_forward_dataset_v1_6 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
