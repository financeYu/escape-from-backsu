"""CSV cache helpers for processed stock data."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from stock_core.indicators.technical import add_indicators
from stock_core.providers.naver_finance import crawl_financial_statements, crawl_stock_data
from stock_core.utils.constants import DATE_COLUMN, INDICATOR_COLUMNS
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.market_specs import KOSPI200_UNIVERSE_SPEC, NAVER_PRICE_PROVIDER_SPEC, PriceProviderSpec
from stock_core.utils.normalization import clean_stock_data
from stock_core.utils.paths import DATA_DIR
from stock_core.utils.trading_calendar import is_trading_day


logger = get_logger(__name__)
ROWS_PER_NAVER_PAGE = NAVER_PRICE_PROVIDER_SPEC.rows_per_page


@dataclass(frozen=True)
class PriceCachePolicy:
    """Filesystem layout policy for cached price and statement data."""

    provider_id: str = NAVER_PRICE_PROVIDER_SPEC.provider_id
    universe_id: str = KOSPI200_UNIVERSE_SPEC.universe_id
    legacy_layout: bool = True
    price_suffix: str = "daily_prices"
    financial_suffix: str = "financial_statements"


DEFAULT_PRICE_CACHE_POLICY = PriceCachePolicy()
DEFAULT_REFRESH_FINANCIALS_WITH_PRICE = False


def _safe_cache_part(value: str) -> str:
    return "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in value.strip())


def _normalize_code_for_cache(code: str, cache_policy: PriceCachePolicy) -> str:
    text = str(code).strip()
    if cache_policy.universe_id == KOSPI200_UNIVERSE_SPEC.universe_id:
        return KOSPI200_UNIVERSE_SPEC.symbol_policy.normalize(text)
    return text


def _resolve_cache_dir(cache_policy: PriceCachePolicy) -> Path:
    if cache_policy.legacy_layout:
        return DATA_DIR
    return DATA_DIR / "market_cache" / _safe_cache_part(cache_policy.provider_id) / _safe_cache_part(cache_policy.universe_id)


def get_cache_path(code: str, *, cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY) -> Path:
    """Return the CSV cache path for a stock code."""

    normalized_code = _normalize_code_for_cache(code, cache_policy)
    return _resolve_cache_dir(cache_policy) / f"{_safe_cache_part(normalized_code)}_{cache_policy.price_suffix}.csv"


def get_financial_statement_cache_path(
    code: str,
    *,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> Path:
    """Return the statement cache path for a stock code."""

    normalized_code = _normalize_code_for_cache(code, cache_policy)
    return _resolve_cache_dir(cache_policy) / f"{_safe_cache_part(normalized_code)}_{cache_policy.financial_suffix}.csv"


def save_stock_data(df: pd.DataFrame, code: str, *, cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY) -> Path:
    """Save the prepared DataFrame as CSV."""

    cache_path = get_cache_path(code, cache_policy=cache_policy)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return cache_path


def save_financial_statements(
    df: pd.DataFrame,
    code: str,
    *,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> Path:
    """Save extracted financial statements as CSV."""

    cache_path = get_financial_statement_cache_path(code, cache_policy=cache_policy)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return cache_path


def load_cached_data(code: str, *, cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY) -> pd.DataFrame:
    """Load cached CSV data if present."""

    cache_path = get_cache_path(code, cache_policy=cache_policy)
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    cached_df = pd.read_csv(cache_path)
    cached_df[DATE_COLUMN] = pd.to_datetime(cached_df[DATE_COLUMN], errors="coerce")
    cached_df = cached_df.dropna(subset=[DATE_COLUMN]).sort_values(DATE_COLUMN).reset_index(drop=True)
    return cached_df


def load_financial_statements(code: str, *, cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY) -> pd.DataFrame:
    """Load cached financial statements if present."""

    cache_path = get_financial_statement_cache_path(code, cache_policy=cache_policy)
    if not cache_path.exists():
        raise FileNotFoundError(f"Financial statement cache file not found: {cache_path}")

    return pd.read_csv(cache_path, dtype=str).fillna("")


def is_weekday(target: Optional[datetime] = None) -> bool:
    """Backward-compatible weekday helper."""

    return is_trading_day(target)


def get_cache_timestamp(
    code: str,
    *,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> Optional[datetime]:
    """Return the last-modified timestamp for a cache file if present."""

    cache_path = get_cache_path(code, cache_policy=cache_policy)
    if not cache_path.exists():
        return None
    return datetime.fromtimestamp(cache_path.stat().st_mtime)


def is_same_day_cache_available(
    code: str,
    target: Optional[datetime] = None,
    *,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> bool:
    """Return True when the cache file exists and was written on the same local day."""

    timestamp = get_cache_timestamp(code, cache_policy=cache_policy)
    if timestamp is None:
        return False

    current = target or datetime.now()
    return timestamp.date() == current.date()


def is_cache_coverage_sufficient(
    df: pd.DataFrame,
    pages: int,
    *,
    provider_spec: PriceProviderSpec = NAVER_PRICE_PROVIDER_SPEC,
) -> bool:
    """Return True when cached rows roughly cover the requested provider pages."""

    if pages <= 1:
        return not df.empty

    required_rows = pages * provider_spec.rows_per_page
    return len(df) >= required_rows


def refresh_stock_data(
    code: str,
    pages: int,
    *,
    provider_spec: PriceProviderSpec = NAVER_PRICE_PROVIDER_SPEC,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
    price_fetcher=None,
    financial_fetcher=None,
    refresh_financials: bool = DEFAULT_REFRESH_FINANCIALS_WITH_PRICE,
) -> tuple[pd.DataFrame, str]:
    """Refresh price data when needed and optionally refresh statement cache.

    Financial-statement crawling is intentionally opt-in here. The daily price
    cache path should stay lightweight; dedicated financial refresh scripts own
    bulk statement-cache updates.
    """

    if price_fetcher is None:
        price_fetcher = crawl_stock_data
    if financial_fetcher is None:
        financial_fetcher = crawl_financial_statements

    normalized_code = _normalize_code_for_cache(code, cache_policy)
    cache_path = get_cache_path(normalized_code, cache_policy=cache_policy)

    should_fetch = False
    cached_df: Optional[pd.DataFrame] = None

    if not cache_path.exists():
        should_fetch = True
    else:
        cached_df = load_cached_data(code, cache_policy=cache_policy)
        if not is_cache_coverage_sufficient(cached_df, pages, provider_spec=provider_spec):
            logger.info("Refreshing stock data for %s because cache coverage is shorter than requested pages=%s", normalized_code, pages)
            should_fetch = True
        elif is_weekday() and not is_same_day_cache_available(code, cache_policy=cache_policy):
            should_fetch = True

    # Preserve weekend cache reuse, and avoid repeated weekday refetches after a successful same-day refresh.
    if should_fetch:
        logger.info("Refreshing stock data for %s from source", normalized_code)
        raw_df = price_fetcher(code=normalized_code, pages=pages, sleep_seconds=provider_spec.request_sleep_seconds)
        clean_df = clean_stock_data(raw_df)
        final_df = add_indicators(clean_df)
        if cache_policy == DEFAULT_PRICE_CACHE_POLICY:
            save_stock_data(final_df, normalized_code)
        else:
            save_stock_data(final_df, normalized_code, cache_policy=cache_policy)
        if refresh_financials:
            try:
                financial_statements_df = financial_fetcher(code=normalized_code)
                if cache_policy == DEFAULT_PRICE_CACHE_POLICY:
                    save_financial_statements(financial_statements_df, normalized_code)
                else:
                    save_financial_statements(financial_statements_df, normalized_code, cache_policy=cache_policy)
            except Exception as exc:
                logger.warning("Failed to refresh financial statements for %s: %s", normalized_code, exc)
        return final_df, "fetched"

    logger.info("Loading cached stock data for %s", normalized_code)
    if cached_df is None:
        cached_df = load_cached_data(code, cache_policy=cache_policy)
    if not set(INDICATOR_COLUMNS).issubset(set(cached_df.columns)):
        logger.info("Cached data for %s is missing indicators; recalculating", code)
        cached_df = add_indicators(cached_df)
        if cache_policy == DEFAULT_PRICE_CACHE_POLICY:
            save_stock_data(cached_df, code)
        else:
            save_stock_data(cached_df, code, cache_policy=cache_policy)
    return cached_df, "cached"
