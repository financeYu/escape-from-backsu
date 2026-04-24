"""CSV cache helpers for processed stock data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from stock_core.indicators.technical import add_indicators
from stock_core.providers.naver_finance import crawl_financial_statements, crawl_stock_data
from stock_core.utils.constants import DATE_COLUMN, INDICATOR_COLUMNS
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.normalization import clean_stock_data
from stock_core.utils.paths import DATA_DIR
from stock_core.utils.trading_calendar import is_trading_day


logger = get_logger(__name__)
ROWS_PER_NAVER_PAGE = 10


def get_cache_path(code: str) -> Path:
    """Return the CSV cache path for a stock code."""

    return DATA_DIR / f"{code}_daily_prices.csv"


def get_financial_statement_cache_path(code: str) -> Path:
    """Return the statement cache path for a stock code."""

    return DATA_DIR / f"{code}_financial_statements.csv"


def save_stock_data(df: pd.DataFrame, code: str) -> Path:
    """Save the prepared DataFrame as CSV."""

    cache_path = get_cache_path(code)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return cache_path


def save_financial_statements(df: pd.DataFrame, code: str) -> Path:
    """Save extracted financial statements as CSV."""

    cache_path = get_financial_statement_cache_path(code)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return cache_path


def load_cached_data(code: str) -> pd.DataFrame:
    """Load cached CSV data if present."""

    cache_path = get_cache_path(code)
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    cached_df = pd.read_csv(cache_path)
    cached_df[DATE_COLUMN] = pd.to_datetime(cached_df[DATE_COLUMN], errors="coerce")
    cached_df = cached_df.dropna(subset=[DATE_COLUMN]).sort_values(DATE_COLUMN).reset_index(drop=True)
    return cached_df


def load_financial_statements(code: str) -> pd.DataFrame:
    """Load cached financial statements if present."""

    cache_path = get_financial_statement_cache_path(code)
    if not cache_path.exists():
        raise FileNotFoundError(f"Financial statement cache file not found: {cache_path}")

    return pd.read_csv(cache_path, dtype=str).fillna("")


def is_weekday(target: Optional[datetime] = None) -> bool:
    """Backward-compatible weekday helper."""

    return is_trading_day(target)


def get_cache_timestamp(code: str) -> Optional[datetime]:
    """Return the last-modified timestamp for a cache file if present."""

    cache_path = get_cache_path(code)
    if not cache_path.exists():
        return None
    return datetime.fromtimestamp(cache_path.stat().st_mtime)


def is_same_day_cache_available(code: str, target: Optional[datetime] = None) -> bool:
    """Return True when the cache file exists and was written on the same local day."""

    timestamp = get_cache_timestamp(code)
    if timestamp is None:
        return False

    current = target or datetime.now()
    return timestamp.date() == current.date()


def is_cache_coverage_sufficient(df: pd.DataFrame, pages: int) -> bool:
    """Return True when cached rows roughly cover the requested Naver pages."""

    if pages <= 1:
        return not df.empty

    required_rows = pages * ROWS_PER_NAVER_PAGE
    return len(df) >= required_rows


def refresh_stock_data(code: str, pages: int) -> tuple[pd.DataFrame, str]:
    """Refresh on weekdays, otherwise reuse the latest cached data if available."""

    cache_path = get_cache_path(code)

    should_fetch = False
    cached_df: Optional[pd.DataFrame] = None

    if not cache_path.exists():
        should_fetch = True
    else:
        cached_df = load_cached_data(code)
        if not is_cache_coverage_sufficient(cached_df, pages):
            logger.info("Refreshing stock data for %s because cache coverage is shorter than requested pages=%s", code, pages)
            should_fetch = True
        elif is_weekday() and not is_same_day_cache_available(code):
            should_fetch = True

    # Preserve weekend cache reuse, and avoid repeated weekday refetches after a successful same-day refresh.
    if should_fetch:
        logger.info("Refreshing stock data for %s from source", code)
        raw_df = crawl_stock_data(code=code, pages=pages, sleep_seconds=0.3)
        clean_df = clean_stock_data(raw_df)
        final_df = add_indicators(clean_df)
        save_stock_data(final_df, code)
        try:
            financial_statements_df = crawl_financial_statements(code=code)
            save_financial_statements(financial_statements_df, code)
        except Exception as exc:
            logger.warning("Failed to refresh financial statements for %s: %s", code, exc)
        return final_df, "fetched"

    logger.info("Loading cached stock data for %s", code)
    if cached_df is None:
        cached_df = load_cached_data(code)
    if not set(INDICATOR_COLUMNS).issubset(set(cached_df.columns)):
        logger.info("Cached data for %s is missing indicators; recalculating", code)
        cached_df = add_indicators(cached_df)
        save_stock_data(cached_df, code)
    return cached_df, "cached"
