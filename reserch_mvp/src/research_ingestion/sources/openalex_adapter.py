from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from ..normalize import make_normalized_paper, normalize_doi
from ..redaction import redact_mapping
from .http import SourceRateLimiter, SourceResponse, fetch_text_with_retries


class OpenAlexAdapter:
    source_name = "openalex"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "https://api.openalex.org/works")
        self.default_per_page = int(config.get("default_per_page", 25))
        self.api_key_env_var = config.get("api_key_env_var")
        self.mailto_env_var = config.get("mailto_env_var")
        self.pdf_download_enabled = bool(config.get("pdf_download_enabled", False))
        self._rate_limiter = SourceRateLimiter(
            min_interval_seconds=float(config.get("min_interval_seconds", 0.0)),
            max_concurrency=int(config.get("max_concurrency", 1)),
            source_name=self.source_name,
        )

    def build_search_url(self, query: str, page: int = 1, per_page: int | None = None) -> str:
        params: dict[str, str | int] = {
            "search": query,
            "page": page,
            "per-page": per_page or self.default_per_page,
        }
        mailto = os.environ.get(self.mailto_env_var or "")
        if mailto:
            params["mailto"] = mailto
        api_key = os.environ.get(self.api_key_env_var or "")
        if api_key:
            params["api_key"] = api_key
        return f"{self.base_url}?{urlencode(params)}"

    def request_headers(self) -> dict[str, str]:
        return {"User-Agent": "QuantMVPResearchIngestion/0.1"}

    def request_metadata(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return redact_mapping(
            {"request_url": url, "headers": headers or {}},
            env_var_names=[name for name in [self.api_key_env_var, self.mailto_env_var] if name],
        )

    def fetch_search_response(self, query: str, page: int = 1, per_page: int | None = None) -> SourceResponse:
        url = self.build_search_url(query, page=page, per_page=per_page)
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

    def fetch_search(self, query: str, page: int = 1, per_page: int | None = None) -> str:
        return self.fetch_search_response(query, page=page, per_page=per_page).body

    def parse_works_json(self, payload: dict[str, Any], raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        results = payload if isinstance(payload, list) else payload.get("results", [])
        papers = []
        for work in results:
            papers.append(parse_openalex_work(work, raw_snapshot_ref=raw_snapshot_ref))
        return papers


def reconstruct_abstract(abstract_inverted_index: dict[str, list[int]] | None) -> str | None:
    if not abstract_inverted_index:
        return None
    max_position = max(position for positions in abstract_inverted_index.values() for position in positions)
    words = [""] * (max_position + 1)
    for word, positions in abstract_inverted_index.items():
        for position in positions:
            words[position] = word
    return " ".join(word for word in words if word).strip() or None


def parse_openalex_work(work: dict[str, Any], raw_snapshot_ref: str | None = None) -> dict[str, Any]:
    authors = [
        authorship.get("author", {}).get("display_name")
        for authorship in work.get("authorships", [])
        if authorship.get("author", {}).get("display_name")
    ]
    primary_location = work.get("primary_location") or {}
    best_oa = work.get("best_oa_location") or {}
    source = primary_location.get("source") or {}
    open_access = work.get("open_access") or {}
    topics = [topic.get("display_name") for topic in work.get("topics", []) if topic.get("display_name")]
    primary_topic = (work.get("primary_topic") or {}).get("display_name")
    if primary_topic and primary_topic not in topics:
        topics.insert(0, primary_topic)
    source_urls = [url for url in [work.get("id"), work.get("doi"), primary_location.get("landing_page_url")] if url]
    pdf_urls = [url for url in [best_oa.get("pdf_url"), primary_location.get("pdf_url")] if url]
    doi = normalize_doi(work.get("doi"))
    return make_normalized_paper(
        title=work.get("title") or work.get("display_name") or "",
        source_adapter="openalex",
        authors=authors,
        doi=doi,
        openalex_id=work.get("id"),
        publication_year=work.get("publication_year"),
        publication_date=work.get("publication_date"),
        venue=source.get("display_name"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        source_urls=source_urls,
        oa_status=open_access.get("oa_status") or ("open" if open_access.get("is_oa") else None),
        license=best_oa.get("license") or primary_location.get("license"),
        is_retracted=work.get("is_retracted"),
        citation_count=work.get("cited_by_count"),
        topics=topics,
        fields_of_study=[],
        raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
        pdf_urls=pdf_urls,
        pdf_downloaded=False,
    )
