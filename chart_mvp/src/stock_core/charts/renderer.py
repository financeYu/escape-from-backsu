"""Public chart-rendering interface."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


def render_stock_chart(df: pd.DataFrame, code: str, name: str, out_path: str) -> None:
    """Render the current stock chart and save it to a local image file."""

    output_path = Path(out_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plot_stock_data(df, stock_label=f"{name} ({code})", source_label="로컬 렌더링", show=False)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved chart for %s (%s) to %s", name, code, output_path)
