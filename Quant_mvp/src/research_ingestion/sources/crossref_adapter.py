from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ..normalize import make_normalized_paper, normalize_doi
from ..redaction import assert_no_scholar_request, redact_mapping


class CrossrefAdapter:
    source_name = "crossref"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "https://api.crossref.org/works")
        self.default_rows = int(config.get("default_rows", 25))
        self.polite_email_env_var = config.get("polite_email_env_var")
        self.plus_api_token_env_var = config.get("plus_api_token_env_var")

    def build_search_url(self, query: str, rows: int | None = None) -> str:
        params = {"query.bibliographic": query, "rows": rows or self.default_rows}
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

    def fetch_search(self, query: str, rows: int | None = None) -> str:
        url = self.build_search_url(query, rows=rows)
        assert_no_scholar_request(url)
        request = Request(url, headers=self.request_headers())
        with urlopen(request, timeout=float(self.config.get("timeout_seconds", 20))) as response:
            return response.read().decode("utf-8")

    def parse_works_json(self, payload: dict[str, Any], raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        message = payload.get("message", {})
        items = message.get("items", [message] if message.get("DOI") else [])
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
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, str):
        return value
    return None


def _date_from_parts(date_obj: dict[str, Any] | None) -> str | None:
    if not date_obj:
        return None
    parts = (date_obj.get("date-parts") or [[]])[0]
    if not parts:
        return None
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _license_from_item(item: dict[str, Any]) -> str | None:
    licenses = item.get("license") or []
    if not licenses:
        return None
    return licenses[0].get("URL") or licenses[0].get("content-version")
