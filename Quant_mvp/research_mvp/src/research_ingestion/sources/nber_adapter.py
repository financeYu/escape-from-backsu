from __future__ import annotations

import csv
from datetime import datetime
import io
import json
import re
from typing import Any

from ..normalize import clean_text, make_normalized_paper, normalize_doi
from ..redaction import redact_mapping
from .http import SourceRateLimiter, SourceResponse, fetch_text_with_retries


DEFAULT_FILES = ["ref", "abs", "auth", "auths", "title", "jel", "prog", "published"]


class NberAdapter:
    source_name = "nber"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.base_url = str(config.get("base_url", "https://data.nber.org/nber_paper_chapter_metadata/tsv")).rstrip("/")
        self.paper_url_template = str(config.get("paper_url_template", "https://www.nber.org/papers/{paper}"))
        self.default_max_results = int(config.get("default_max_results", 25))
        self.files = [str(name) for name in config.get("files", DEFAULT_FILES)]
        self.metadata_license = config.get("metadata_license", "nber_public_metadata")
        self.metadata_license_note = config.get(
            "metadata_license_note",
            "NBER public metadata dump; fulltext copyright/license is not inferred.",
        )
        self.pdf_download_enabled = bool(config.get("pdf_download_enabled", False))
        self._rate_limiter = SourceRateLimiter(
            min_interval_seconds=float(config.get("min_interval_seconds", 0.0)),
            max_concurrency=int(config.get("max_concurrency", 1)),
            source_name=self.source_name,
        )

    def build_file_url(self, file_name: str) -> str:
        if file_name not in self.files:
            raise ValueError(f"Configured NBER metadata file is not enabled: {file_name}")
        return f"{self.base_url}/{file_name}.tsv"

    def request_headers(self) -> dict[str, str]:
        return {"User-Agent": "QuantMVPResearchIngestion/0.1"}

    def request_metadata(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return redact_mapping({"request_url": url, "headers": headers or self.request_headers()})

    def fetch_search_response(self, query: str, limit: int | None = None, offset: int = 0) -> SourceResponse:
        files: dict[str, dict[str, Any]] = {}
        combined_status = 200
        retry_count = 0
        headers: dict[str, str] = {}
        for file_name in self.files:
            response = self._fetch_file_response(file_name)
            files[file_name] = {
                "url": response.url,
                "status": response.status,
                "body": response.body,
            }
            retry_count = max(retry_count, int(response.retry_count or 0))
            headers.update({f"{file_name}-{key}": value for key, value in response.headers.items()})
            if not response.ok and combined_status == 200:
                combined_status = int(response.status or 0) or 500
        body = json.dumps(
            {
                "query": query,
                "limit": limit or self.default_max_results,
                "offset": offset,
                "files": files,
                "metadata_license": self.metadata_license,
                "metadata_license_note": self.metadata_license_note,
            },
            ensure_ascii=False,
        )
        return SourceResponse(
            url=f"{self.base_url}?files={','.join(self.files)}",
            body=body,
            status=combined_status,
            headers=headers,
            retry_count=retry_count,
        )

    def fetch_search(self, query: str, limit: int | None = None, offset: int = 0) -> str:
        return self.fetch_search_response(query, limit=limit, offset=offset).body

    def parse_dump_json(self, payload: dict[str, Any], raw_snapshot_ref: str | None = None) -> list[dict[str, Any]]:
        files = payload.get("files", {})
        refs = _tsv_rows(_file_body(files, "ref"))
        abstracts = _single_value_by_paper(_tsv_rows(_file_body(files, "abs")), ["abstract"])
        titles = _single_value_by_paper(_tsv_rows(_file_body(files, "title")), ["title"])
        authors = _merge_list_maps(
            _list_by_paper(_tsv_rows(_file_body(files, "auth")), ["author", "name"]),
            _list_by_paper(_tsv_rows(_file_body(files, "auths")), ["author", "name"]),
        )
        jels = _list_by_paper(_tsv_rows(_file_body(files, "jel")), ["jel"])
        programs = _list_by_paper(_tsv_rows(_file_body(files, "prog")), ["program"])
        published = _single_value_by_paper(_tsv_rows(_file_body(files, "published")), ["published_text", "published"])
        query = str(payload.get("query") or "")
        offset = max(0, int(payload.get("offset") or 0))
        limit = max(0, int(payload.get("limit") or self.default_max_results))
        papers = [
            self._paper_from_ref(
                row,
                abstract=abstracts.get(_paper_id(row)),
                title_override=titles.get(_paper_id(row)),
                authors=authors.get(_paper_id(row), []),
                jels=jels.get(_paper_id(row), []),
                programs=programs.get(_paper_id(row), []),
                published_note=published.get(_paper_id(row)),
                raw_snapshot_ref=raw_snapshot_ref,
            )
            for row in refs
            if _paper_id(row)
        ]
        matched = [paper for paper in papers if _matches_query(paper, query)]
        return matched[offset : offset + limit] if limit else []

    def _fetch_file_response(self, file_name: str) -> SourceResponse:
        url = self.build_file_url(file_name)
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

    def _paper_from_ref(
        self,
        row: dict[str, str],
        *,
        abstract: str | None,
        title_override: str | None,
        authors: list[str],
        jels: list[str],
        programs: list[str],
        published_note: str | None,
        raw_snapshot_ref: str | None,
    ) -> dict[str, Any]:
        paper_id = _paper_id(row) or ""
        title = clean_text(row.get("title")) or title_override or ""
        issue_date = _date_only(row.get("issue_date") or row.get("date"))
        doi = normalize_doi(row.get("doi"))
        source_urls = [self.paper_url_template.format(paper=paper_id)]
        if doi:
            source_urls.append(f"https://doi.org/{doi}")
        categories = [*jels, *programs]
        return make_normalized_paper(
            title=title,
            source_adapter=self.source_name,
            authors=authors or _split_ref_authors(row.get("author")),
            doi=doi,
            nber_id=paper_id,
            publication_year=_year_from_date(issue_date),
            publication_date=issue_date,
            venue="NBER Working Paper" if paper_id.startswith("w") else "NBER Paper/Chapter",
            publisher="National Bureau of Economic Research",
            abstract=abstract,
            source_urls=source_urls,
            oa_status=None,
            license=None,
            is_retracted=False,
            citation_count=None,
            topics=categories,
            fields_of_study=["Economics", "Finance"] if categories else [],
            raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
            categories=categories,
            pdf_urls=[],
            pdf_downloaded=False,
            metadata_license=self.metadata_license,
            metadata_license_note=self.metadata_license_note,
            published_note=published_note,
            license_collection_allowed=True,
            license_noncommercial_allowed=True,
            license_use_basis="nber_public_metadata_metadata_only",
            license_policy_notes_ko="NBER public metadata dump 기반 metadata-only 수집이며 PDF/fulltext license는 추론하지 않습니다.",
        )


def _file_body(files: dict[str, Any], name: str) -> str:
    payload = files.get(name) or {}
    return str(payload.get("body") or "")


def _tsv_rows(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [
        {str(key): clean_text(value) or "" for key, value in row.items() if key}
        for row in reader
    ]


def _paper_id(row: dict[str, str]) -> str | None:
    value = clean_text(row.get("paper") or row.get("paper_id") or row.get("id"))
    if not value:
        return None
    value = value.lower()
    if re.fullmatch(r"\d{4,5}", value):
        return f"w{value}"
    return value


def _single_value_by_paper(rows: list[dict[str, str]], value_fields: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        paper = _paper_id(row)
        value = next((clean_text(row.get(field)) for field in value_fields if clean_text(row.get(field))), None)
        if paper and value and paper not in result:
            result[paper] = value
    return result


def _list_by_paper(rows: list[dict[str, str]], value_fields: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in rows:
        paper = _paper_id(row)
        value = next((clean_text(row.get(field)) for field in value_fields if clean_text(row.get(field))), None)
        if paper and value:
            bucket = result.setdefault(paper, [])
            if value not in bucket:
                bucket.append(value)
    return result


def _merge_list_maps(left: dict[str, list[str]], right: dict[str, list[str]]) -> dict[str, list[str]]:
    result = {key: list(values) for key, values in left.items()}
    for key, values in right.items():
        bucket = result.setdefault(key, [])
        for value in values:
            if value not in bucket:
                bucket.append(value)
    return result


def _split_ref_authors(value: str | None) -> list[str]:
    cleaned = clean_text(value)
    if not cleaned:
        return []
    return [author for author in (clean_text(part) for part in re.split(r"\s*(?:;|\band\b)\s*", cleaned)) if author]


def _matches_query(paper: dict[str, Any], query: str) -> bool:
    tokens = _query_tokens(query)
    if not tokens:
        return True
    text = " ".join(
        str(value)
        for value in [
            paper.get("title"),
            paper.get("abstract"),
            paper.get("venue"),
            paper.get("publisher"),
            " ".join(paper.get("topics", [])),
            " ".join(paper.get("categories", [])),
        ]
        if value
    ).lower()
    return any(token in text for token in tokens)


def _query_tokens(query: str) -> list[str]:
    stopwords = {"and", "or", "the", "with", "for", "from", "daily", "stock", "equity"}
    return [
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) >= 4 and token not in stopwords
    ]


def _date_only(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m", "%Y"]:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if fmt == "%Y":
                return f"{parsed.year:04d}-01-01"
            if fmt == "%Y-%m":
                return f"{parsed.year:04d}-{parsed.month:02d}-01"
            return parsed.date().isoformat()
        except ValueError:
            continue
    match = re.search(r"\b(19|20)\d{2}\b", cleaned)
    return f"{match.group(0)}-01-01" if match else None


def _year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
