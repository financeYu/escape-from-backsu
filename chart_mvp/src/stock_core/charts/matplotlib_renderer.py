"""Matplotlib chart rendering for local stock analysis."""

from __future__ import annotations

from stock_core.utils import paths as _paths  # Ensure MPLCONFIGDIR is configured before matplotlib import.

import matplotlib.dates as mdates
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN, HIGH_COLUMN, LOW_COLUMN, OPEN_COLUMN, VOLUME_COLUMN


UP_COLOR = "#ff4d5a"
DOWN_COLOR = "#3b82f6"
MA5_COLOR = "#14b86a"
MA20_COLOR = "#ff9d00"
BB_COLOR = "#f59e0b"
RSI_COLOR = "#b04ef7"
RSI_SIGNAL_COLOR = "#2f80ff"
GRID_COLOR = "#e6eaf2"
BG_COLOR = "#ffffff"
LEGEND_MARGIN_X = -0.12

PREFERRED_FONT_FAMILIES = [
    "Malgun Gothic",
    "Noto Sans KR",
    "AppleGothic",
    "NanumGothic",
    "DejaVu Sans",
]


def resolve_font_family(available_names: set[str] | None = None) -> str:
    """Choose the best installed font family for local Korean chart labels."""

    names = available_names
    if names is None:
        names = {font.name for font in font_manager.fontManager.ttflist}

    for family in PREFERRED_FONT_FAMILIES:
        if family in names:
            return family
    return "DejaVu Sans"


plt.rcParams["font.family"] = resolve_font_family()
plt.rcParams["axes.unicode_minus"] = False


def format_number(value: float) -> str:
    """Format a numeric value with comma separators."""

    return f"{value:,.0f}"


def format_volume_tick(value: float, _: float) -> str:
    """Format volume axis values with K/M/B suffixes."""

    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def draw_candlesticks(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Draw candlesticks using open, high, low, and close prices."""

    dates = mdates.date2num(df[DATE_COLUMN].dt.to_pydatetime())
    candle_width = 0.62

    for x, open_price, high_price, low_price, close_price in zip(
        dates,
        df[OPEN_COLUMN],
        df[HIGH_COLUMN],
        df[LOW_COLUMN],
        df[CLOSE_COLUMN],
    ):
        color = UP_COLOR if close_price >= open_price else DOWN_COLOR
        lower = min(open_price, close_price)
        height = abs(close_price - open_price)

        ax.vlines(x, low_price, high_price, color=color, linewidth=1.2, zorder=3)

        if height == 0:
            ax.hlines(close_price, x - candle_width / 2, x + candle_width / 2, color=color, linewidth=2.0, zorder=4)
            continue

        candle = Rectangle(
            (x - candle_width / 2, lower),
            candle_width,
            height,
            facecolor=color,
            edgecolor=color,
            linewidth=0,
            alpha=0.95,
            zorder=4,
        )
        ax.add_patch(candle)


def style_axis(ax: plt.Axes, y_right: bool = True) -> None:
    """Apply a clean trading-chart style to an axis."""

    ax.set_facecolor(BG_COLOR)
    ax.grid(color=GRID_COLOR, linestyle="-", linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#d7dde8")
    ax.tick_params(colors="#6b7280")
    if y_right:
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")


def add_price_summary(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Render a compact summary line similar to trading UIs."""

    latest = df.iloc[-1]
    previous_close = df.iloc[-2][CLOSE_COLUMN] if len(df) > 1 else latest[CLOSE_COLUMN]
    change_value = latest[CLOSE_COLUMN] - previous_close
    change_pct = (change_value / previous_close * 100) if previous_close else 0.0
    change_color = UP_COLOR if change_value >= 0 else DOWN_COLOR

    summary = (
        f"시가 {format_number(latest[OPEN_COLUMN])}  "
        f"고가 {format_number(latest[HIGH_COLUMN])}  "
        f"저가 {format_number(latest[LOW_COLUMN])}  "
        f"종가 {format_number(latest[CLOSE_COLUMN])}"
    )
    ax.text(0.01, 1.01, summary, transform=ax.transAxes, fontsize=9.2, color="#374151", va="bottom")
    ax.text(
        0.99,
        1.01,
        f"{change_value:+,.0f} ({change_pct:+.2f}%)",
        transform=ax.transAxes,
        fontsize=9.2,
        color=change_color,
        va="bottom",
        ha="right",
    )

    indicator_text = (
        f"이동평균선 5 {format_number(latest['MA5'])}  "
        f"20 {format_number(latest['MA20'])}  "
        f"볼린저 밴드 중단선 {format_number(latest['BB_MID'])} "
        f"상한선 {format_number(latest['BB_UPPER'])}  하한선 {format_number(latest['BB_LOWER'])}"
    )
    ax.text(0.01, 0.955, indicator_text, transform=ax.transAxes, fontsize=8.8, color="#6b7280", va="bottom")


def plot_stock_data(df: pd.DataFrame, stock_label: str, source_label: str, show: bool = True) -> plt.Figure:
    """Display a trading-style three-panel chart."""

    if df.empty:
        raise ValueError("Cannot plot an empty DataFrame.")

    fig, (ax_price, ax_volume, ax_rsi) = plt.subplots(
        3,
        1,
        figsize=(14, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [4.2, 1.6, 1.9]},
    )
    fig.patch.set_facecolor(BG_COLOR)

    style_axis(ax_price, y_right=True)
    style_axis(ax_volume, y_right=True)
    style_axis(ax_rsi, y_right=True)

    draw_candlesticks(ax_price, df)
    ax_price.plot(df[DATE_COLUMN], df["MA5"], color=MA5_COLOR, linewidth=1.1, zorder=5)
    ax_price.plot(df[DATE_COLUMN], df["MA20"], color=MA20_COLOR, linewidth=1.0, zorder=5)
    ax_price.plot(df[DATE_COLUMN], df["BB_MID"], color="#9d4edd", linewidth=0.9, zorder=4)
    ax_price.plot(df[DATE_COLUMN], df["BB_UPPER"], color=BB_COLOR, linewidth=0.9, zorder=4)
    ax_price.plot(df[DATE_COLUMN], df["BB_LOWER"], color=BB_COLOR, linewidth=0.9, zorder=4)

    latest_close = df.iloc[-1][CLOSE_COLUMN]
    ax_price.axhline(latest_close, color=UP_COLOR, linestyle=":", linewidth=1.0, alpha=0.9)
    ax_price.annotate(
        f"{format_number(latest_close)}",
        xy=(df[DATE_COLUMN].iloc[-1], latest_close),
        xytext=(10, 0),
        textcoords="offset points",
        va="center",
        fontsize=10,
        color="white",
        bbox={"boxstyle": "round,pad=0.25", "fc": UP_COLOR, "ec": UP_COLOR},
    )

    latest_date = df[DATE_COLUMN].max().strftime("%Y-%m-%d")
    ax_price.text(
        0.01,
        1.08,
        f"{stock_label} 일봉 차트",
        transform=ax_price.transAxes,
        fontsize=14,
        fontweight="bold",
        color="#1f2937",
        va="bottom",
    )
    ax_price.text(
        0.99,
        1.08,
        f"{source_label} · 최신일 {latest_date}",
        transform=ax_price.transAxes,
        fontsize=9.5,
        color="#6b7280",
        va="bottom",
        ha="right",
    )
    add_price_summary(ax_price, df)
    ax_price.set_ylabel("가격")

    price_legend = [
        Line2D([0], [0], color=MA5_COLOR, linewidth=1.3, label="이동평균선 5"),
        Line2D([0], [0], color=MA20_COLOR, linewidth=1.3, label="이동평균선 20"),
        Line2D([0], [0], color=BB_COLOR, linewidth=1.1, label="볼린저 밴드"),
    ]

    up_day = df[CLOSE_COLUMN] >= df[OPEN_COLUMN]
    volume_colors = up_day.map({True: UP_COLOR, False: DOWN_COLOR})
    ax_volume.bar(df[DATE_COLUMN], df[VOLUME_COLUMN], width=0.8, color=volume_colors, alpha=0.95, zorder=2)
    ax_volume.plot(df[DATE_COLUMN], df["VOLUME_MA20"], color="#14b8a6", linewidth=1.2, zorder=3)
    ax_volume.set_ylabel("거래량")
    ax_volume.yaxis.set_major_formatter(mticker.FuncFormatter(format_volume_tick))
    ax_volume.legend(
        handles=[
            Rectangle((0, 0), 1, 1, facecolor=UP_COLOR, edgecolor=UP_COLOR, alpha=0.9, label="거래량"),
            Line2D([0], [0], color="#14b8a6", linewidth=1.5, label="거래량 20일선"),
        ],
        loc="upper left",
        bbox_to_anchor=(LEGEND_MARGIN_X, 1.0),
        borderaxespad=0.0,
        frameon=False,
        fontsize=9,
    )

    ax_rsi.axhspan(30, 70, facecolor="#ede9fe", alpha=0.7, zorder=0)
    ax_rsi.axhline(70, color="#94a3b8", linestyle="--", linewidth=0.9)
    ax_rsi.axhline(50, color="#cbd5e1", linestyle="--", linewidth=0.8)
    ax_rsi.axhline(30, color="#94a3b8", linestyle="--", linewidth=0.9)
    ax_rsi.plot(df[DATE_COLUMN], df["RSI14"], color=RSI_COLOR, linewidth=1.1, zorder=3)
    ax_rsi.plot(df[DATE_COLUMN], df["RSI_SIGNAL"], color=RSI_SIGNAL_COLOR, linewidth=1.0, zorder=3)
    ax_rsi.set_ylim(20, 100)
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_yticks([20, 40, 60, 80])
    ax_rsi.legend(
        handles=[
            Line2D([0], [0], color=RSI_COLOR, linewidth=1.3, label=f"RSI(14) {df['RSI14'].iloc[-1]:.2f}"),
            Line2D([0], [0], color=RSI_SIGNAL_COLOR, linewidth=1.3, label=f"시그널 {df['RSI_SIGNAL'].iloc[-1]:.2f}"),
        ],
        loc="upper left",
        bbox_to_anchor=(LEGEND_MARGIN_X, 1.0),
        borderaxespad=0.0,
        frameon=False,
        fontsize=9,
    )

    for axis in (ax_price, ax_volume, ax_rsi):
        axis.xaxis.set_major_locator(mdates.AutoDateLocator())
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    ax_price.tick_params(axis="x", labelbottom=False)
    ax_volume.tick_params(axis="x", labelbottom=False)
    ax_rsi.set_xlabel("날짜")
    plt.setp(ax_rsi.get_xticklabels(), rotation=35, ha="right")

    ax_price.legend(
        handles=price_legend,
        loc="upper left",
        bbox_to_anchor=(LEGEND_MARGIN_X, 0.92),
        borderaxespad=0.0,
        frameon=False,
        fontsize=9,
    )

    fig.subplots_adjust(hspace=0.0, top=0.88, bottom=0.1, left=0.16, right=0.92)

    if show:
        plt.show()

    return fig
