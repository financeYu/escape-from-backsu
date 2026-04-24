"""Naver Finance fetching helpers."""

from __future__ import annotations

import re
import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests

from stock_core.utils.constants import DATE_COLUMN


BASE_URL = "https://finance.naver.com/item/sise_day.naver"
MAIN_URL = "https://finance.naver.com/item/main.naver"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}
FINANCIAL_STATEMENT_ROW_KEYWORDS = (
    "\ub9e4\ucd9c\uc561",
    "\uc601\uc5c5\uc774\uc775",
    "\ub2f9\uae30\uc21c\uc774\uc775",
    "\uc790\uc0b0\ucd1d\uacc4",
    "\ubd80\ucc44\ucd1d\uacc4",
    "\uc790\ubcf8\ucd1d\uacc4",
    "EPS",
    "PER",
    "BPS",
    "PBR",
    "\ubc30\ub2f9\uc218\uc775\ub960",
)
FISCAL_PERIOD_LABEL_PATTERN = re.compile(r"\d{4}[/.-](?:\d{2}|Q[1-4])(?:\(E\))?")


def build_session() -> requests.Session:
    """Build a requests session configured for local crawling."""

    session = requests.Session()
    session.trust_env = False
    return session


def fetch_page_table(
    code: str,
    page: int,
    session: requests.Session,
    timeout: int = 10,
) -> Optional[pd.DataFrame]:
    """Fetch and parse one Naver Finance daily-price table."""

    response = session.get(
        BASE_URL,
        params={"code": code, "page": page},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    for table in tables:
        if DATE_COLUMN in table.columns:
            return table
    return None


def fetch_stock_name(code: str, timeout: int = 10) -> str:
    """Fetch a stock name from the Naver Finance main page title."""

    with build_session() as session:
        response = session.get(
            MAIN_URL,
            params={"code": code},
            headers=HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()

    match = re.search(r"<title>\s*(.*?)\s*:\s*Npay 증권\s*</title>", response.text)
    if match:
        stock_name = match.group(1).strip()
        if stock_name:
            return stock_name

    return code


def fetch_main_page_html(
    code: str,
    session: requests.Session,
    timeout: int = 10,
) -> str:
    """Fetch the Naver Finance main page HTML for a stock code."""

    response = session.get(
        MAIN_URL,
        params={"code": code},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def _flatten_column_name(column: object) -> str:
    """Convert a possibly nested table column into a stable string."""

    if isinstance(column, tuple):
        parts = [str(part).strip() for part in column if str(part).strip() and "Unnamed" not in str(part)]
        return " ".join(parts)
    return str(column).strip()


def _make_unique_column_names(columns: list[str]) -> list[str]:
    """Make flattened table columns unique while preserving readable labels."""

    seen: dict[str, int] = {}
    unique_columns: list[str] = []
    for index, column in enumerate(columns):
        base_name = column or f"column_{index}"
        count = seen.get(base_name, 0)
        seen[base_name] = count + 1
        unique_columns.append(base_name if count == 0 else f"{base_name}__{count + 1}")
    return unique_columns


def _looks_like_financial_statement(table: pd.DataFrame) -> bool:
    """Heuristically detect Naver Finance statement tables."""

    flattened_columns = [_flatten_column_name(column) for column in table.columns]
    if any(keyword in " ".join(flattened_columns) for keyword in FINANCIAL_STATEMENT_ROW_KEYWORDS):
        return True

    for column in table.columns[:2]:
        series = table[column].astype(str)
        if any(series.str.contains(keyword, na=False).any() for keyword in FINANCIAL_STATEMENT_ROW_KEYWORDS):
            return True

    return False


def extract_financial_statements_from_html(html: str, code: str) -> pd.DataFrame:
    """Extract statement-like tables from the Naver Finance main page."""

    tables = pd.read_html(StringIO(html))
    records: list[dict[str, str]] = []

    for table_index, table in enumerate(tables):
        if table.empty or not _looks_like_financial_statement(table):
            continue

        normalized = table.copy()
        period_labels = [_flatten_column_name(column) or f"column_{index}" for index, column in enumerate(normalized.columns)]
        normalized.columns = _make_unique_column_names(period_labels)
        metric_column = normalized.columns[0]
        period_label_by_column = dict(zip(normalized.columns[1:], period_labels[1:]))
        fiscal_period_columns = [
            column for column in normalized.columns[1:] if FISCAL_PERIOD_LABEL_PATTERN.search(period_label_by_column[column])
        ]
        if not fiscal_period_columns:
            continue

        for _, row in normalized.iterrows():
            metric = str(row.get(metric_column, "")).strip()
            if not metric or metric == "nan":
                continue

            for period_column in fiscal_period_columns:
                value = row.get(period_column)
                if pd.isna(value):
                    continue
                value_text = str(value).strip()
                if not value_text or value_text == "-" or value_text == "nan":
                    continue

                records.append(
                    {
                        "code": code,
                        "table_index": str(table_index),
                        "metric": metric,
                        "period": period_label_by_column[period_column],
                        "value": value_text,
                    }
                )

    if not records:
        return pd.DataFrame(columns=["code", "table_index", "metric", "period", "value"])

    return pd.DataFrame.from_records(records)


def crawl_financial_statements(code: str, timeout: int = 10) -> pd.DataFrame:
    """Fetch and extract financial statement rows from Naver Finance."""

    with build_session() as session:
        html = fetch_main_page_html(code=code, session=session, timeout=timeout)
    return extract_financial_statements_from_html(html=html, code=code)


def crawl_stock_data(code: str, pages: int, sleep_seconds: float = 0.3) -> pd.DataFrame:
    """Collect daily-price tables from multiple pages and merge them."""

    if pages < 1:
        raise ValueError("pages must be greater than or equal to 1.")

    frames: list[pd.DataFrame] = []

    with build_session() as session:
        for page in range(1, pages + 1):
            try:
                table = fetch_page_table(code=code, page=page, session=session)
            except requests.RequestException as exc:
                print(f"[Warning] Failed to fetch page {page}: {exc}")
                continue
            except ValueError as exc:
                print(f"[Warning] Failed to parse page {page}: {exc}")
                continue

            if table is not None and not table.empty:
                frames.append(table)
            else:
                print(f"[Info] No valid table found on page {page}.")

            time.sleep(sleep_seconds)

    if not frames:
        raise ValueError("No stock data was collected. Check the stock code or network.")

    return pd.concat(frames, ignore_index=True)
