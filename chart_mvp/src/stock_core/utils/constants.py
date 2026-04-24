"""Shared constants for Korean stock price analysis."""

DATE_COLUMN = "날짜"
CLOSE_COLUMN = "종가"
PREV_DIFF_COLUMN = "전일비"
OPEN_COLUMN = "시가"
HIGH_COLUMN = "고가"
LOW_COLUMN = "저가"
VOLUME_COLUMN = "거래량"
PRICE_COLUMNS = ["종가", "전일비", "시가", "고가", "저가", "거래량"]

INDICATOR_COLUMNS = [
    "MA5",
    "MA20",
    "BB_MID",
    "BB_UPPER",
    "BB_LOWER",
    "RSI14",
    "RSI_SIGNAL",
    "VOLUME_MA20",
]
