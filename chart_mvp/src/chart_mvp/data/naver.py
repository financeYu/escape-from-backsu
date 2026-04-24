"""Backward-compatible accessors for Naver Finance helpers."""

from stock_core.providers.naver_finance import BASE_URL, HEADERS, MAIN_URL, build_session, crawl_stock_data, fetch_page_table, fetch_stock_name
from stock_core.utils.normalization import clean_stock_data

__all__ = [
    "BASE_URL",
    "MAIN_URL",
    "HEADERS",
    "build_session",
    "fetch_page_table",
    "fetch_stock_name",
    "crawl_stock_data",
    "clean_stock_data",
]
