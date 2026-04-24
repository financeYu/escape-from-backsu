from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import re
from typing import Any


NORMALIZED_REQUIRED_FIELDS = [
    "canonical_paper_id",
    "source_ids",
    "doi",
    "arxiv_id",
    "openalex_id",
    "semantic_scholar_id",
    "title",
    "title_normalized",
    "authors",
    "first_author",
    "publication_year",
    "publication_date",
    "updated_date",
    "venue",
    "publisher",
    "abstract",
    "abstract_available",
    "language",
    "source_adapters",
    "source_urls",
    "pdf_urls",
    "oa_status",
    "open_access_status",
    "license",
    "is_retracted",
    "citation_count",
    "influential_citation_count",
    "topics",
    "fields_of_study",
    "categories",
    "raw_snapshot_refs",
    "discovered_from_scholar_seed",
    "same_as_sources",
    "manual_review_required",
    "conflict_notes",
    "collected_at_utc",
    "created_at",
    "updated_at",
]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip() or None


def normalize_title(title: str | None) -> str:
    cleaned = clean_text(title) or ""
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9가-힣 ]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    value = doi.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value.lower() or None


def normalize_arxiv_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    value = arxiv_id.strip()
    value = re.sub(r"^arxiv:", "", value, flags=re.IGNORECASE)
    value = re.sub(r"v\d+$", "", value, flags=re.IGNORECASE)
    return value or None


def first_author(authors: list[str] | None) -> str | None:
    if not authors:
        return None
    return clean_text(next((author for author in authors if author), None))


def canonical_id(
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    semantic_scholar_id: str | None = None,
    openalex_id: str | None = None,
    title: str | None = None,
    publication_year: int | None = None,
) -> str:
    if doi:
        return f"doi:{normalize_doi(doi)}"
    if arxiv_id:
        return f"arxiv:{normalize_arxiv_id(arxiv_id)}"
    if semantic_scholar_id:
        return f"semantic_scholar:{semantic_scholar_id}"
    if openalex_id:
        return f"openalex:{openalex_id}"
    basis = f"{normalize_title(title)}|{publication_year or ''}"
    return "titlehash:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def make_normalized_paper(
    *,
    title: str,
    source_adapter: str,
    authors: list[str] | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
    openalex_id: str | None = None,
    semantic_scholar_id: str | None = None,
    crossref_id: str | None = None,
    publication_year: int | None = None,
    publication_date: str | None = None,
    updated_date: str | None = None,
    venue: str | None = None,
    publisher: str | None = None,
    abstract: str | None = None,
    language: str | None = None,
    source_urls: list[str] | None = None,
    pdf_urls: list[str] | None = None,
    oa_status: str | None = None,
    open_access_status: str | None = None,
    license: str | None = None,
    is_retracted: bool | None = None,
    citation_count: int | None = None,
    influential_citation_count: int | None = None,
    topics: list[str] | None = None,
    fields_of_study: list[str] | None = None,
    categories: list[str] | None = None,
    raw_snapshot_refs: list[str] | None = None,
    discovered_from_scholar_seed: bool = False,
    same_as_sources: list[str] | None = None,
    manual_review_required: bool = False,
    conflict_notes: list[str] | None = None,
    collected_at_utc: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    doi = normalize_doi(doi)
    arxiv_id = normalize_arxiv_id(arxiv_id)
    now = utc_now_iso()
    paper = {
        "canonical_paper_id": canonical_id(
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=semantic_scholar_id,
            openalex_id=openalex_id,
            title=title,
            publication_year=publication_year,
        ),
        "source_ids": {
            "doi": doi,
            "arxiv_id": arxiv_id,
            "openalex_id": openalex_id,
            "semantic_scholar_id": semantic_scholar_id,
            "crossref_id": crossref_id,
        },
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "semantic_scholar_id": semantic_scholar_id,
        "title": clean_text(title) or "",
        "title_normalized": normalize_title(title),
        "authors": [clean_text(author) for author in (authors or []) if clean_text(author)],
        "first_author": first_author(authors or []),
        "publication_year": publication_year,
        "publication_date": publication_date,
        "updated_date": updated_date,
        "venue": clean_text(venue),
        "publisher": clean_text(publisher),
        "abstract": clean_text(abstract),
        "abstract_available": bool(clean_text(abstract)),
        "language": clean_text(language),
        "source_adapters": [source_adapter],
        "source_urls": source_urls or [],
        "pdf_urls": pdf_urls or [],
        "oa_status": oa_status,
        "open_access_status": open_access_status or oa_status,
        "license": license,
        "is_retracted": is_retracted,
        "citation_count": citation_count,
        "influential_citation_count": influential_citation_count,
        "topics": topics or [],
        "categories": categories or [],
        "fields_of_study": fields_of_study or [],
        "raw_snapshot_refs": raw_snapshot_refs or [],
        "discovered_from_scholar_seed": discovered_from_scholar_seed,
        "same_as_sources": same_as_sources or [],
        "manual_review_required": manual_review_required,
        "conflict_notes": conflict_notes or [],
        "collected_at_utc": collected_at_utc or now,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }
    paper.update(extra)
    validate_normalized_paper(paper)
    return paper


def validate_normalized_paper(paper: dict[str, Any]) -> None:
    missing = [field for field in NORMALIZED_REQUIRED_FIELDS if field not in paper]
    if missing:
        raise ValueError(f"NormalizedPaper is missing required fields: {', '.join(missing)}")
    if not paper["canonical_paper_id"]:
        raise ValueError("NormalizedPaper canonical_paper_id is required.")
    if not paper["title"]:
        raise ValueError("NormalizedPaper title is required.")
