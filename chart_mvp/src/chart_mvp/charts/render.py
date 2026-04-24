"""Backward-compatible accessors for matplotlib chart rendering."""

from stock_core.charts.matplotlib_renderer import BG_COLOR, BB_COLOR, DOWN_COLOR, GRID_COLOR, MA20_COLOR, MA5_COLOR, RSI_COLOR, RSI_SIGNAL_COLOR, UP_COLOR, add_price_summary, draw_candlesticks, format_number, format_volume_tick, plot_stock_data, style_axis

__all__ = [
    "UP_COLOR",
    "DOWN_COLOR",
    "MA5_COLOR",
    "MA20_COLOR",
    "BB_COLOR",
    "RSI_COLOR",
    "RSI_SIGNAL_COLOR",
    "GRID_COLOR",
    "BG_COLOR",
    "format_number",
    "format_volume_tick",
    "draw_candlesticks",
    "style_axis",
    "add_price_summary",
    "plot_stock_data",
]
