"""Public price-provider wrappers for Naver Finance daily prices."""

from __future__ import annotations

import pandas as pd

from stock_core.cache.csv_cache import DEFAULT_PRICE_CACHE_POLICY, PriceCachePolicy, load_cached_data, refresh_stock_data, save_financial_statements
from stock_core.providers.naver_finance import crawl_financial_statements, crawl_stock_data, fetch_stock_name
from stock_core.utils.constants import DATE_COLUMN, PRICE_COLUMNS
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.market_specs import NAVER_PRICE_PROVIDER_SPEC, PriceProviderSpec
from stock_core.utils.normalization import clean_stock_data


logger = get_logger(__name__)
BASE_PRICE_COLUMNS = [DATE_COLUMN, *PRICE_COLUMNS]


def get_stock_name(code: str) -> str:
    """Return the stock name for a code using the current Naver lookup."""

    return fetch_stock_name(code)


def get_price_df(
    code: str,
    pages: int = 20,
    use_cache: bool = True,
    *,
    provider_spec: PriceProviderSpec = NAVER_PRICE_PROVIDER_SPEC,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> pd.DataFrame:
    """Return normalized daily price data for a stock code.

    When ``use_cache`` is True, the existing weekday/weekend cache policy is
    preserved via the current cache-refresh flow. The returned DataFrame is
    normalized to the base Korean price columns only.
    """

    logger.info("Loading price data for %s (pages=%s, use_cache=%s)", code, pages, use_cache)

    if use_cache:
        df, source = refresh_stock_data(
            code=code,
            pages=pages,
            provider_spec=provider_spec,
            cache_policy=cache_policy,
        )
        logger.info("Loaded %s from %s path", code, source)
    else:
        raw_df = crawl_stock_data(code=code, pages=pages, sleep_seconds=provider_spec.request_sleep_seconds)
        df = clean_stock_data(raw_df)
        try:
            financial_statements_df = crawl_financial_statements(code=code)
            save_financial_statements(financial_statements_df, code, cache_policy=cache_policy)
        except Exception as exc:
            logger.warning("Failed to save financial statements for %s during direct fetch: %s", code, exc)
        logger.info("Loaded %s without cache", code)

    existing_columns = [column for column in BASE_PRICE_COLUMNS if column in df.columns]
    return df.loc[:, existing_columns].copy()


def get_cached_price_df(
    code: str,
    *,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> pd.DataFrame:
    """Return normalized base columns from cached data only."""

    df = load_cached_data(code, cache_policy=cache_policy)
    existing_columns = [column for column in BASE_PRICE_COLUMNS if column in df.columns]
    return df.loc[:, existing_columns].copy()
