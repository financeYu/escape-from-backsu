from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..normalize import make_normalized_paper, normalize_arxiv_id, normalize_doi
from ..redaction import assert_no_scholar_request, redact_mapping


class SemanticScholarAdapter:
    source_name = "semantic_scholar"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "https://api.semanticscholar.org/graph/v1/paper/search")
        self.batch_base_url = config.get("batch_base_url", "https://api.semanticscholar.org/graph/v1/paper/batch")
        self.default_limit = int(config.get("default_limit", 25))
        self.api_key_env_var = config.get("api_key_env_var")
        self.fields = config.get("fields", [])

    def build_search_url(self, query: str, limit: int | None = None, offset: int = 0) -> str:
        params = {
            "query": query,
            "limit": limit or self.default_limit,
            "offset": offset,
            "fields": ",".join(self.fields),
        }
        return f"{self.base_url}?{urlencode(params)}"

    def build_batch_payload(self, ids: list[str]) -> dict[str, Any]:
        return {"ids": ids, "fields": ",".join(self.fields)}

    def request_headers(self, env: dict[str, str] | None = None) -> dict[str, str]:
        import os

        env = env or os.environ
        headers = {"User-Agent": "QuantMVPResearchIngestion/0.1"}
        api_key = env.get(self.api_key_env_var or "")
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    def request_metadata(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        return redact_mapping({"request_url": url, "headers": headers}, env_var_names=[self.api_key_env_var] if self.api_key_env_var else [])

    def fetch_search(self, query: str, limit: int | None = None, offset: int = 0) -> str:
        url = self.build_search_url(query, limit=limit, offset=offset)
        assert_no_scholar_request(url)
        request = Request(url, headers=self.request_headers())
        with urlopen(request, timeout=float(self.config.get("timeout_seconds", 20))) as response:
            return response.read().decode("utf-8")

    def parse_search_json(self, payload: dict[str, Any], raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        papers = payload if isinstance(payload, list) else payload.get("data", [])
        return [parse_semantic_scholar_paper(item, raw_snapshot_ref=raw_snapshot_ref) for item in papers]


def parse_semantic_scholar_paper(item: dict[str, Any], raw_snapshot_ref: str | None = None) -> dict[str, Any]:
    external = item.get("externalIds") or {}
    authors = [author.get("name") for author in item.get("authors", []) if author.get("name")]
    open_pdf = item.get("openAccessPdf") or {}
    doi = normalize_doi(external.get("DOI"))
    arxiv_id = normalize_arxiv_id(external.get("ArXiv"))
    return make_normalized_paper(
        title=item.get("title") or "",
        source_adapter="semantic_scholar",
        authors=authors,
        doi=doi,
        arxiv_id=arxiv_id,
        semantic_scholar_id=item.get("paperId"),
        publication_year=item.get("year"),
        publication_date=item.get("publicationDate"),
        venue=item.get("venue"),
        abstract=item.get("abstract"),
        source_urls=[url for url in [item.get("url"), f"https://doi.org/{doi}" if doi else None] if url],
        oa_status="open" if item.get("isOpenAccess") else None,
        license=None,
        is_retracted=item.get("isRetracted"),
        citation_count=item.get("citationCount"),
        topics=[],
        fields_of_study=item.get("fieldsOfStudy") or [],
        raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
        influential_citation_count=item.get("influentialCitationCount"),
        pdf_urls=[open_pdf.get("url")] if open_pdf.get("url") else [],
        pdf_downloaded=False,
    )
