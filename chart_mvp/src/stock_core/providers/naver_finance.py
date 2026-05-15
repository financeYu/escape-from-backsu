"""Naver Finance fetching helpers."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from hashlib import sha256
from html import unescape
from io import StringIO
from typing import Optional
from zoneinfo import ZoneInfo

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
KST = ZoneInfo("Asia/Seoul")
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
NAVER_RATIO_POLICY_SNAPSHOT_SCHEMA_VERSION = "v1_5_naver_ratio_policy_snapshot_v1_0"
NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS = [
    "schema_version",
    "ticker",
    "vendor_name",
    "vendor_or_origin",
    "source_system",
    "source_url",
    "vendor_snapshot_date",
    "vendor_as_of_date",
    "source_available_date",
    "source_available_policy",
    "price_basis_datetime",
    "price_date",
    "price_value",
    "price_policy",
    "adjusted_price_policy",
    "shares_outstanding",
    "shares_policy",
    "eps_policy",
    "bps_policy",
    "per_formula",
    "pbr_formula",
    "dividend_yield_formula",
    "per_reported_value",
    "eps_reported_value",
    "pbr_reported_value",
    "bps_reported_value",
    "raw_html_sha256",
    "raw_html_path",
    "source_lineage_status",
    "missing_policy_fields",
]


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


def extract_ratio_policy_snapshot_from_html(
    html: str,
    code: str,
    *,
    fetched_at: str | None = None,
    raw_html_path: str = "",
) -> dict[str, str]:
    """Extract reference-only PER/PBR policy metadata from a Naver main page.

    The returned row is a crawl-time snapshot. It can document what the page
    disclosed at fetch time, but it does not prove historical availability for
    an earlier evaluation date by itself.
    """

    fetched_at_text = fetched_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    text = _html_to_text(html)
    price_date = _extract_price_date(text)
    price_value = _first_match(text, r"\ud604\uc7ac\uac00\s*([\d,]+)")
    shares_outstanding = _first_match(text, r"\uc0c1\uc7a5\uc8fc\uc2dd\uc218\s*([\d,]+)")
    per_value, eps_value = _extract_pair_after_label(text, "PER/EPS")
    pbr_value, bps_value = _extract_pair_after_label(text, "PBR")
    per_formula = (
        "current_price_divided_by_eps_vendor_reported"
        if re.search(r"PER\s*=\s*\ud604\uc7ac\uac00\s*(?:\u00f7|/)\s*EPS", text)
        else ""
    )
    pbr_formula = (
        "current_price_divided_by_bps_vendor_reported"
        if re.search(r"PBR\s*=\s*\ud604\uc7ac\uac00\s*(?:\u00f7|/)\s*BPS", text)
        else ""
    )
    dividend_formula = (
        "dividend_per_share_divided_by_current_price_vendor_reported"
        if re.search(r"\ubc30\ub2f9\uc218\uc775\ub960\s*=\s*\(\s*\ubc30\ub2f9\uae08\s*/\s*\ud604\uc7ac\uac00\s*\)\s*x\s*100", text)
        else ""
    )
    eps_policy = (
        "controlling_owner_recent_4q_net_income_divided_by_modified_average_issued_shares_common_plus_preferred"
        if "\ucd5c\uadfc 4\ubd84\uae30 \ud569\uc0b0 \uc21c\uc774\uc775" in text and "\uc218\uc815\ud3c9\uade0\ubc1c\ud589\uc8fc\uc2dd\uc218" in text
        else ""
    )
    bps_policy = (
        "recent_quarter_equity_divided_by_modified_period_end_floating_shares_common_plus_preferred"
        if "\ucd5c\uadfc \ubd84\uae30 \uc790\ubcf8\ucd1d\uacc4" in text and "\uc218\uc815\uae30\ub9d0\uc720\ud1b5\uc8fc\uc2dd\uc218" in text
        else ""
    )
    shares_policy = "|".join(part for part in [eps_policy, bps_policy] if part)
    price_policy = "naver_main_current_price" if per_formula or pbr_formula else ""
    source_date = _source_available_date_from_fetched_at(fetched_at_text)
    row = {
        "schema_version": NAVER_RATIO_POLICY_SNAPSHOT_SCHEMA_VERSION,
        "ticker": code,
        "vendor_name": "Naver Finance",
        "vendor_or_origin": "Naver Finance main.naver",
        "source_system": "NaverFinance_main_page",
        "source_url": f"{MAIN_URL}?code={code}",
        "vendor_snapshot_date": fetched_at_text,
        "vendor_as_of_date": price_date,
        "source_available_date": source_date,
        "source_available_policy": "crawl_fetch_date_only_not_historical_vendor_publication_date",
        "price_basis_datetime": _extract_price_basis_datetime(text),
        "price_date": price_date,
        "price_value": price_value,
        "price_policy": price_policy,
        "adjusted_price_policy": "not_disclosed_by_naver_main",
        "shares_outstanding": shares_outstanding,
        "shares_policy": shares_policy,
        "eps_policy": eps_policy,
        "bps_policy": bps_policy,
        "per_formula": per_formula,
        "pbr_formula": pbr_formula,
        "dividend_yield_formula": dividend_formula,
        "per_reported_value": per_value,
        "eps_reported_value": eps_value,
        "pbr_reported_value": pbr_value,
        "bps_reported_value": bps_value,
        "raw_html_sha256": sha256(html.encode("utf-8")).hexdigest(),
        "raw_html_path": raw_html_path,
        "source_lineage_status": "policy_extracted_reference_snapshot",
        "missing_policy_fields": "",
    }
    row["missing_policy_fields"] = "|".join(_missing_ratio_policy_fields(row))
    if row["missing_policy_fields"]:
        row["source_lineage_status"] = "policy_extracted_partial_reference_snapshot"
    return row


def crawl_ratio_policy_snapshot(code: str, timeout: int = 10) -> dict[str, str]:
    """Fetch Naver main page and extract reference-only ratio policy metadata."""

    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    with build_session() as session:
        html = fetch_main_page_html(code=code, session=session, timeout=timeout)
    return extract_ratio_policy_snapshot_from_html(html, code, fetched_at=fetched_at)


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _source_available_date_from_fetched_at(fetched_at: str) -> str:
    value = str(fetched_at or "").strip()
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:10] if len(value) >= 10 else ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST).date().isoformat()


def _extract_price_basis_datetime(text: str) -> str:
    match = re.search(
        r"(\d{4})\ub144\s*(\d{2})\uc6d4\s*(\d{2})\uc77c\s*(\d{2})\uc2dc\s*(\d{2})\ubd84\s*\uae30\uc900\s*([^\s]+)",
        text,
    )
    if not match:
        return ""
    year, month, day, hour, minute, suffix = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:00[{suffix}]"


def _extract_price_date(text: str) -> str:
    match = re.search(r"\ub0a0\uc9dc\s*(\d{4})\.(\d{2})\.(\d{2})\s*\uae30\uc900", text)
    if match:
        return "-".join(match.groups())
    basis = _extract_price_basis_datetime(text)
    return basis[:10] if basis else ""


def _extract_pair_after_label(text: str, label: str) -> tuple[str, str]:
    if label == "PER/EPS":
        match = re.search(r"PER/EPS\s+PER\s*l\s*EPS.*?([\d,.]+)\s*\ubc30\s*l\s*([\d,.]+)\s*\uc6d0", text)
        if match:
            return match.group(1), match.group(2)
    if label == "PBR":
        match = re.search(r"PBR\s*l\s*BPS.*?([\d,.]+)\s*\ubc30\s*l\s*([\d,.]+)\s*\uc6d0", text)
        if match:
            return match.group(1), match.group(2)
    index = text.find(label)
    if index < 0:
        return "", ""
    match = re.search(r"([\d,.]+)\s*\ubc30\s*l\s*([\d,.]+)\s*\uc6d0", text[index:])
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _missing_ratio_policy_fields(row: dict[str, str]) -> list[str]:
    missing = []
    for field in ("vendor_snapshot_date", "price_date", "price_policy", "shares_policy", "source_available_date"):
        if not row.get(field):
            missing.append(field)
    if row.get("adjusted_price_policy") == "not_disclosed_by_naver_main":
        missing.append("adjusted_price_policy")
    return missing


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
