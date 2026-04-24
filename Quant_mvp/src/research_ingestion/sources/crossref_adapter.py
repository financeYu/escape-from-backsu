from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from ..normalize import clean_text, make_normalized_paper, normalize_doi
from ..redaction import redact_mapping
from .http import SourceRateLimiter, SourceResponse, fetch_text_with_retries


class CrossrefAdapter:
    source_name = "crossref"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "https://api.crossref.org/works")
        self.default_rows = int(config.get("default_rows", 25))
        self.polite_email_env_var = config.get("polite_email_env_var")
        self.plus_api_token_env_var = config.get("plus_api_token_env_var")
        self._rate_limiter = SourceRateLimiter(
            min_interval_seconds=float(config.get("min_interval_seconds", 0.0)),
            max_concurrency=int(config.get("max_concurrency", 1)),
            source_name=self.source_name,
        )

    def build_search_url(self, query: str, rows: int | None = None, offset: int = 0) -> str:
        params = {"query.bibliographic": query, "rows": rows or self.default_rows, "offset": offset}
        return f"{self.base_url}?{urlencode(params)}"

    def build_doi_url(self, doi: str) -> str:
        return f"{self.base_url}/{quote(doi, safe='')}"

    def request_headers(self, env: dict[str, str] | None = None) -> dict[str, str]:
        import os

        env = env or os.environ
        headers = {"User-Agent": "QuantMVPResearchIngestion/0.1"}
        email = env.get(self.polite_email_env_var or "")
        token = env.get(self.plus_api_token_env_var or "")
        if email:
            headers["User-Agent"] += f" (mailto:{email})"
        if token:
            headers["Crossref-Plus-API-Token"] = f"Bearer {token}"
        return headers

    def request_metadata(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        return redact_mapping(
            {"request_url": url, "headers": headers},
            env_var_names=[name for name in [self.polite_email_env_var, self.plus_api_token_env_var] if name],
        )

    def fetch_search_response(self, query: str, rows: int | None = None, offset: int = 0) -> SourceResponse:
        url = self.build_search_url(query, rows=rows, offset=offset)
        self._rate_limiter.wait_before_request()
        try:
            return fetch_text_with_retries(
                url=url,
                headers=self.request_headers(),
                timeout_seconds=float(self.config.get("timeout_seconds", 20)),
                max_retries=int(self.config.get("max_retries", 0)),
                retry_backoff_seconds=float(self.config.get("retry_backoff_seconds", 1.0)),
            )
        finally:
            self._rate_limiter.mark_request_complete()

    def fetch_search(self, query: str, rows: int | None = None, offset: int = 0) -> str:
        return self.fetch_search_response(query, rows=rows, offset=offset).body

    def fetch_doi_response(self, doi: str) -> SourceResponse:
        url = self.build_doi_url(doi)
        self._rate_limiter.wait_before_request()
        try:
            return fetch_text_with_retries(
                url=url,
                headers=self.request_headers(),
                timeout_seconds=float(self.config.get("timeout_seconds", 20)),
                max_retries=int(self.config.get("max_retries", 0)),
                retry_backoff_seconds=float(self.config.get("retry_backoff_seconds", 1.0)),
            )
        finally:
            self._rate_limiter.mark_request_complete()

    def fetch_doi(self, doi: str) -> str:
        return self.fetch_doi_response(doi).body

    def parse_works_json(self, payload: dict[str, Any], raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        message = payload.get("message", {})
        items = _message_items(message)
        return [parse_crossref_work(item, raw_snapshot_ref=raw_snapshot_ref) for item in items]

    def parse_rate_limit_headers(self, headers: dict[str, str]) -> dict[str, str | None]:
        lowered = {key.lower(): value for key, value in headers.items()}
        return {
            "limit": lowered.get("x-rate-limit-limit"),
            "interval": lowered.get("x-rate-limit-interval"),
            "retry_after": lowered.get("retry-after"),
        }


def parse_crossref_work(item: dict[str, Any], raw_snapshot_ref: str | None = None) -> dict[str, Any]:
    title = _first(item.get("title")) or ""
    authors = []
    for author in item.get("author", []):
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part).strip()
        if name:
            authors.append(name)
    date = _date_from_parts(item.get("published-print") or item.get("published-online") or item.get("created"))
    doi = normalize_doi(item.get("DOI"))
    return make_normalized_paper(
        title=title,
        source_adapter="crossref",
        authors=authors,
        doi=doi,
        crossref_id=doi,
        publication_year=int(date[:4]) if date else None,
        publication_date=date,
        venue=_first(item.get("container-title")),
        abstract=item.get("abstract"),
        source_urls=[url for url in [item.get("URL"), f"https://doi.org/{doi}" if doi else None] if url],
        oa_status=None,
        license=_license_from_item(item),
        is_retracted=None,
        citation_count=item.get("is-referenced-by-count"),
        topics=item.get("subject", []) or [],
        fields_of_study=[],
        raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
    )


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        return next((clean_text(item) for item in value if clean_text(item)), None)
    if isinstance(value, str):
        return clean_text(value)
    return None


def _date_from_parts(date_obj: dict[str, Any] | None) -> str | None:
    if not isinstance(date_obj, dict):
        return None
    date_parts = date_obj.get("date-parts")
    if not isinstance(date_parts, list):
        return None
    parts = next((part for part in date_parts if isinstance(part, list) and part), None)
    if not parts:
        return None
    year = _safe_int(next(iter(parts), None))
    month = _safe_int(parts[1]) if len(parts) > 1 else 1
    day = _safe_int(parts[2]) if len(parts) > 2 else 1
    if year is None or month is None or day is None:
        return None
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _license_from_item(item: dict[str, Any]) -> str | None:
    licenses = item.get("license") or []
    if not isinstance(licenses, list):
        return None
    for license_item in licenses:
        if not isinstance(license_item, dict):
            continue
        value = clean_text(license_item.get("URL")) or clean_text(license_item.get("content-version"))
        if value:
            return value
    return None


def _message_items(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    items = message.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if message.get("DOI"):
        return [message]
    return []


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
