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
    "source_adapter",
    "source_record_id",
    "source_query_set",
    "query_run_id",
    "retrieved_at",
    "seed_origin_type",
    "seed_origin_is_evidence",
    "canonical_resolution_status",
    "resolution_confidence",
    "dedup_key",
    "duplicate_of",
    "metadata_license",
    "fulltext_available",
    "fulltext_used",
    "pdf_downloaded",
    "citation_count_metadata_only",
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
    source_record_id: str | None = None,
    source_query_set: str | None = None,
    query_run_id: str | None = None,
    retrieved_at: str | None = None,
    seed_origin_type: str | None = None,
    seed_origin_is_evidence: bool = False,
    canonical_resolution_status: str | None = None,
    resolution_confidence: str | None = None,
    duplicate_of: str | None = None,
    fulltext_available: bool | None = None,
    fulltext_used: bool = False,
    pdf_downloaded: bool = False,
    citation_count_metadata_only: bool = True,
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
        "source_adapter": source_adapter,
        "source_record_id": source_record_id
        or _default_source_record_id(
            doi=doi,
            arxiv_id=arxiv_id,
            openalex_id=openalex_id,
            semantic_scholar_id=semantic_scholar_id,
            crossref_id=crossref_id,
        ),
        "source_query_set": source_query_set,
        "query_run_id": query_run_id,
        "retrieved_at": retrieved_at or collected_at_utc or now,
        "seed_origin_type": seed_origin_type or ("scholar_local_seed" if discovered_from_scholar_seed else "metadata_api"),
        "seed_origin_is_evidence": seed_origin_is_evidence,
        "canonical_resolution_status": canonical_resolution_status or ("resolved" if not discovered_from_scholar_seed else "unresolved"),
        "resolution_confidence": resolution_confidence or _default_resolution_confidence(
            doi=doi,
            arxiv_id=arxiv_id,
            openalex_id=openalex_id,
            semantic_scholar_id=semantic_scholar_id,
        ),
        "dedup_key": canonical_id(
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=semantic_scholar_id,
            openalex_id=openalex_id,
            title=title,
            publication_year=publication_year,
        ),
        "duplicate_of": duplicate_of,
        "metadata_license": license,
        "fulltext_available": bool(pdf_urls) if fulltext_available is None else fulltext_available,
        "fulltext_used": fulltext_used,
        "pdf_downloaded": pdf_downloaded,
        "citation_count_metadata_only": citation_count_metadata_only,
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
    _apply_backward_compatible_defaults(paper)
    missing = [field for field in NORMALIZED_REQUIRED_FIELDS if field not in paper]
    if missing:
        raise ValueError(f"NormalizedPaper is missing required fields: {', '.join(missing)}")
    if not paper["canonical_paper_id"]:
        raise ValueError("NormalizedPaper canonical_paper_id is required.")
    if not paper["title"]:
        raise ValueError("NormalizedPaper title is required.")
    if paper.get("seed_origin_is_evidence") is not False:
        raise ValueError("Discovery seeds and source hints must not be treated as evidence.")
    if paper.get("fulltext_used") or paper.get("pdf_downloaded"):
        raise ValueError("NormalizedPaper must keep PDF/fulltext use disabled by default.")
    if paper.get("citation_count_metadata_only") is not True:
        raise ValueError("Citation counts must remain metadata only.")


def _apply_backward_compatible_defaults(paper: dict[str, Any]) -> None:
    source_adapters = paper.get("source_adapters") or []
    source_ids = paper.get("source_ids") or {}
    paper.setdefault("source_adapter", next(iter(source_adapters), None))
    paper.setdefault(
        "source_record_id",
        paper.get("doi")
        or paper.get("arxiv_id")
        or paper.get("openalex_id")
        or paper.get("semantic_scholar_id")
        or source_ids.get("doi")
        or source_ids.get("arxiv_id")
        or source_ids.get("openalex_id")
        or source_ids.get("semantic_scholar_id")
        or source_ids.get("crossref_id"),
    )
    paper.setdefault("source_query_set", paper.get("research_query_set"))
    paper.setdefault("query_run_id", None)
    paper.setdefault("retrieved_at", paper.get("collected_at_utc") or paper.get("created_at"))
    paper.setdefault("seed_origin_type", "scholar_local_seed" if paper.get("discovered_from_scholar_seed") else "metadata_api")
    paper.setdefault("seed_origin_is_evidence", False)
    paper.setdefault("canonical_resolution_status", "resolved" if not paper.get("discovered_from_scholar_seed") else "unresolved")
    paper.setdefault("resolution_confidence", "high" if paper.get("doi") or paper.get("arxiv_id") or paper.get("openalex_id") or paper.get("semantic_scholar_id") else "medium")
    paper.setdefault("dedup_key", paper.get("canonical_paper_id"))
    paper.setdefault("duplicate_of", None)
    paper.setdefault("metadata_license", paper.get("license"))
    paper.setdefault("fulltext_available", bool(paper.get("pdf_urls")))
    paper.setdefault("fulltext_used", False)
    paper.setdefault("pdf_downloaded", False)
    paper.setdefault("citation_count_metadata_only", True)


def _default_source_record_id(
    *,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
    crossref_id: str | None,
) -> str | None:
    return doi or arxiv_id or openalex_id or semantic_scholar_id or crossref_id


def _default_resolution_confidence(
    *,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
) -> str:
    return "high" if any([doi, arxiv_id, openalex_id, semantic_scholar_id]) else "medium"
