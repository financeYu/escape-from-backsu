from __future__ import annotations

from datetime import datetime
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from ..normalize import clean_text, make_normalized_paper, normalize_arxiv_id
from ..redaction import assert_no_scholar_request


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivAdapter:
    source_name = "arxiv"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "https://export.arxiv.org/api/query")
        self.min_interval_seconds = float(config.get("min_interval_seconds", 3.2))
        self.max_concurrency = int(config.get("max_concurrency", 1))
        self.default_max_results = int(config.get("default_max_results", 25))
        self.pdf_download_enabled = bool(config.get("pdf_download_enabled", False))
        self._last_request_ts = 0.0
        self.validate_rate_limit_settings()

    def validate_rate_limit_settings(self) -> None:
        if self.min_interval_seconds < 3.0:
            raise ValueError("arXiv min_interval_seconds must be >= 3.0.")
        if self.max_concurrency != 1:
            raise ValueError("arXiv max_concurrency must be 1.")

    def build_search_url(self, query: str, start: int = 0, max_results: int | None = None) -> str:
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": max_results or self.default_max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        return f"{self.base_url}?{urlencode(params)}"

    def fetch_search(self, query: str, start: int = 0, max_results: int | None = None) -> str:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        url = self.build_search_url(query, start=start, max_results=max_results)
        assert_no_scholar_request(url)
        request = Request(url, headers={"User-Agent": "QuantMVPResearchIngestion/0.1"})
        with urlopen(request, timeout=float(self.config.get("timeout_seconds", 20))) as response:
            body = response.read().decode("utf-8")
        self._last_request_ts = time.monotonic()
        return body

    def parse_atom(self, xml_text: str, raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        papers = []
        for entry in root.findall("atom:entry", ATOM_NS):
            title = clean_text(_find_text(entry, "atom:title"))
            abstract = clean_text(_find_text(entry, "atom:summary"))
            published = clean_text(_find_text(entry, "atom:published"))
            updated = clean_text(_find_text(entry, "atom:updated"))
            entry_url = clean_text(_find_text(entry, "atom:id"))
            arxiv_id = _arxiv_id_from_url(entry_url)
            doi = clean_text(_find_text(entry, "arxiv:doi"))
            authors = [
                clean_text(author.findtext("atom:name", namespaces=ATOM_NS))
                for author in entry.findall("atom:author", ATOM_NS)
            ]
            authors = [author for author in authors if author]
            categories = [
                category.attrib.get("term")
                for category in entry.findall("atom:category", ATOM_NS)
                if category.attrib.get("term")
            ]
            source_urls: list[str] = []
            pdf_urls: list[str] = []
            if entry_url:
                source_urls.append(entry_url)
            for link in entry.findall("atom:link", ATOM_NS):
                href = link.attrib.get("href")
                if not href:
                    continue
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_urls.append(href)
                elif href not in source_urls:
                    source_urls.append(href)
            papers.append(
                make_normalized_paper(
                    title=title or "",
                    source_adapter=self.source_name,
                    authors=authors,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    publication_year=_year_from_date(published),
                    publication_date=_date_only(published),
                    venue="arXiv",
                    abstract=abstract,
                    source_urls=source_urls,
                    oa_status="open",
                    license=None,
                    is_retracted=False,
                    citation_count=None,
                    topics=categories,
                    fields_of_study=[],
                    raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
                    updated_date=_date_only(updated),
                    categories=categories,
                    pdf_urls=pdf_urls,
                    pdf_downloaded=False,
                )
            )
        return papers


def _find_text(entry: ET.Element, path: str) -> str | None:
    node = entry.find(path, ATOM_NS)
    return node.text if node is not None else None


def _arxiv_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.rstrip("/").split("/")[-1]
    return normalize_arxiv_id(value)


def _date_only(value: str | None) -> str | None:
    if not value:
        return None
    return value[:10]


def _year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        try:
            return int(value[:4])
        except ValueError:
            return None
