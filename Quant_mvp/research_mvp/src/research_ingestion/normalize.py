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
    "nber_id",
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
_METADATA_FIELD_KEYS = [
    "publication_year",
    "publication_date",
    "updated_date",
    "venue",
    "publisher",
    "abstract",
    "language",
    "source_adapter",
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
]
_ACCESS_GUARDRAIL_KEYS = [
    "pdf_urls",
    "fulltext_available",
    "fulltext_used",
    "pdf_downloaded",
    "citation_count_metadata_only",
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


def normalize_nber_id(nber_id: str | None) -> str | None:
    if not nber_id:
        return None
    value = nber_id.strip().lower()
    value = re.sub(r"^nber:", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^https?://(?:www\.)?nber\.org/papers/", "", value, flags=re.IGNORECASE)
    if value.isdigit():
        value = f"w{value}"
    return value or None


def first_author(authors: list[str] | None) -> str | None:
    if not authors:
        return None
    return clean_text(next((author for author in authors if author), None))


def canonical_id(
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    nber_id: str | None = None,
    semantic_scholar_id: str | None = None,
    openalex_id: str | None = None,
    title: str | None = None,
    publication_year: int | None = None,
) -> str:
    if doi:
        return f"doi:{normalize_doi(doi)}"
    if arxiv_id:
        return f"arxiv:{normalize_arxiv_id(arxiv_id)}"
    if nber_id:
        return f"nber:{normalize_nber_id(nber_id)}"
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
    authors: list[str] | None = None, doi: str | None = None,
    arxiv_id: str | None = None, nber_id: str | None = None, openalex_id: str | None = None,
    semantic_scholar_id: str | None = None, crossref_id: str | None = None,
    publication_year: int | None = None, publication_date: str | None = None,
    updated_date: str | None = None, venue: str | None = None,
    publisher: str | None = None, abstract: str | None = None, language: str | None = None,
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
    return _make_normalized_paper_from_values(locals())


def _make_normalized_paper_from_values(values: dict[str, Any]) -> dict[str, Any]:
    values = dict(values)
    extra = values.pop("extra")
    values["doi"] = normalize_doi(values["doi"])
    values["arxiv_id"] = normalize_arxiv_id(values["arxiv_id"])
    values["nber_id"] = normalize_nber_id(values["nber_id"])
    if not clean_text(values["title"]):
        values["title"] = _fallback_title_from_metadata(values)
        values["manual_review_required"] = True
        values["conflict_notes"] = [
            *(values["conflict_notes"] or []),
            "source_title_missing_conservative_placeholder_used",
        ]
    values["now"] = utc_now_iso()
    paper = _normalized_paper_payload(values)
    paper.update(extra)
    validate_normalized_paper(paper)
    return paper


def _fallback_title_from_metadata(values: dict[str, Any]) -> str:
    primary_identifiers = [
        ("DOI", values.get("doi")),
        ("arXiv", values.get("arxiv_id")),
        ("NBER", values.get("nber_id")),
        ("OpenAlex", values.get("openalex_id")),
        ("Semantic Scholar", values.get("semantic_scholar_id")),
        ("Crossref", values.get("crossref_id")),
    ]
    context = [f"{label} {identifier}" for label, identifier in primary_identifiers if identifier]
    if not context:
        secondary_identifiers = [
            ("source record", values.get("source_record_id")),
            ("source URL", next(iter(values.get("source_urls") or []), None)),
            ("raw snapshot", next(iter(values.get("raw_snapshot_refs") or []), None)),
        ]
        context.extend(f"{label} {identifier}" for label, identifier in secondary_identifiers if identifier)
    if values.get("publication_year"):
        context.append(f"year {values['publication_year']}")
    venue = clean_text(values.get("venue"))
    if venue:
        context.append(f"venue {venue}")
    source = clean_text(values.get("source_adapter")) or "metadata source"
    detail = "; ".join(context) if context else "no reliable identifier"
    return f"Untitled paper metadata from {source} ({detail})"


def _normalized_paper_payload(values: dict[str, Any]) -> dict[str, Any]:
    source_ids = _source_ids(**_pick(values, ["doi", "arxiv_id", "openalex_id", "semantic_scholar_id", "crossref_id", "nber_id"]))
    paper_id = _paper_id_from_values(values)
    return {
        **_identity_fields(source_ids=source_ids, paper_id=paper_id, **_pick(values, ["title", "authors", "doi", "arxiv_id", "openalex_id", "semantic_scholar_id", "nber_id"])),
        **_metadata_fields(**_pick(values, _METADATA_FIELD_KEYS)),
        **_source_context_from_values(values, paper_id),
        **_access_guardrail_fields(**_pick(values, _ACCESS_GUARDRAIL_KEYS)),
        "collected_at_utc": values["collected_at_utc"] or values["now"],
        "created_at": values["created_at"] or values["now"],
        "updated_at": values["updated_at"] or values["now"],
    }


def _paper_id_from_values(values: dict[str, Any]) -> str:
    return canonical_id(
        doi=values["doi"],
        arxiv_id=values["arxiv_id"],
        nber_id=values["nber_id"],
        semantic_scholar_id=values["semantic_scholar_id"],
        openalex_id=values["openalex_id"],
        title=values["title"],
        publication_year=values["publication_year"],
    )


def _pick(values: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: values[key] for key in keys}


def _source_context_from_values(values: dict[str, Any], paper_id: str) -> dict[str, Any]:
    discovered_from_scholar_seed = values["discovered_from_scholar_seed"]
    return _source_context_fields(
        source_adapter=values["source_adapter"],
        source_record_id=values["source_record_id"] or _default_source_record_id(
            doi=values["doi"],
            arxiv_id=values["arxiv_id"],
            nber_id=values["nber_id"],
            openalex_id=values["openalex_id"],
            semantic_scholar_id=values["semantic_scholar_id"],
            crossref_id=values["crossref_id"],
        ),
        source_query_set=values["source_query_set"],
        query_run_id=values["query_run_id"],
        retrieved_at=values["retrieved_at"] or values["collected_at_utc"] or values["now"],
        seed_origin_type=values["seed_origin_type"] or ("scholar_local_seed" if discovered_from_scholar_seed else "metadata_api"),
        seed_origin_is_evidence=values["seed_origin_is_evidence"],
        canonical_resolution_status=values["canonical_resolution_status"] or ("resolved" if not discovered_from_scholar_seed else "unresolved"),
        resolution_confidence=values["resolution_confidence"] or _default_resolution_confidence(
            doi=values["doi"],
            arxiv_id=values["arxiv_id"],
            nber_id=values["nber_id"],
            openalex_id=values["openalex_id"],
            semantic_scholar_id=values["semantic_scholar_id"],
        ),
        paper_id=paper_id,
        duplicate_of=values["duplicate_of"],
        license=values["license"],
        same_as_sources=values["same_as_sources"],
        manual_review_required=values["manual_review_required"],
        conflict_notes=values["conflict_notes"],
        discovered_from_scholar_seed=discovered_from_scholar_seed,
    )


def _source_ids(
    *,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
    crossref_id: str | None,
    nber_id: str | None,
) -> dict[str, str | None]:
    return {
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "semantic_scholar_id": semantic_scholar_id,
        "crossref_id": crossref_id,
        "nber_id": nber_id,
    }


def _identity_fields(
    *,
    paper_id: str,
    source_ids: dict[str, str | None],
    title: str,
    authors: list[str] | None,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
    nber_id: str | None,
) -> dict[str, Any]:
    return {
        "canonical_paper_id": paper_id,
        "source_ids": source_ids,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": openalex_id,
        "semantic_scholar_id": semantic_scholar_id,
        "nber_id": nber_id,
        "title": clean_text(title) or "",
        "title_normalized": normalize_title(title),
        "authors": [clean_text(author) for author in (authors or []) if clean_text(author)],
        "first_author": first_author(authors or []),
    }


def _metadata_fields(
    *,
    publication_year: int | None,
    publication_date: str | None,
    updated_date: str | None,
    venue: str | None,
    publisher: str | None,
    abstract: str | None,
    language: str | None,
    source_adapter: str,
    source_urls: list[str] | None,
    pdf_urls: list[str] | None,
    oa_status: str | None,
    open_access_status: str | None,
    license: str | None,
    is_retracted: bool | None,
    citation_count: int | None,
    influential_citation_count: int | None,
    topics: list[str] | None,
    fields_of_study: list[str] | None,
    categories: list[str] | None,
    raw_snapshot_refs: list[str] | None,
) -> dict[str, Any]:
    cleaned_abstract = clean_text(abstract)
    return {
        "publication_year": publication_year,
        "publication_date": publication_date,
        "updated_date": updated_date,
        "venue": clean_text(venue),
        "publisher": clean_text(publisher),
        "abstract": cleaned_abstract,
        "abstract_available": bool(cleaned_abstract),
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
    }


def _source_context_fields(
    *,
    source_adapter: str,
    source_record_id: str | None,
    source_query_set: str | None,
    query_run_id: str | None,
    retrieved_at: str,
    seed_origin_type: str,
    seed_origin_is_evidence: bool,
    canonical_resolution_status: str,
    resolution_confidence: str,
    paper_id: str,
    duplicate_of: str | None,
    license: str | None,
    same_as_sources: list[str] | None,
    manual_review_required: bool,
    conflict_notes: list[str] | None,
    discovered_from_scholar_seed: bool,
) -> dict[str, Any]:
    return {
        "discovered_from_scholar_seed": discovered_from_scholar_seed,
        "source_adapter": source_adapter,
        "source_record_id": source_record_id,
        "source_query_set": source_query_set,
        "query_run_id": query_run_id,
        "retrieved_at": retrieved_at,
        "seed_origin_type": seed_origin_type,
        "seed_origin_is_evidence": seed_origin_is_evidence,
        "canonical_resolution_status": canonical_resolution_status,
        "resolution_confidence": resolution_confidence,
        "dedup_key": paper_id,
        "duplicate_of": duplicate_of,
        "metadata_license": license,
        "same_as_sources": same_as_sources or [],
        "manual_review_required": manual_review_required,
        "conflict_notes": conflict_notes or [],
    }


def _access_guardrail_fields(
    *,
    pdf_urls: list[str] | None,
    fulltext_available: bool | None,
    fulltext_used: bool,
    pdf_downloaded: bool,
    citation_count_metadata_only: bool,
) -> dict[str, Any]:
    return {
        "fulltext_available": bool(pdf_urls) if fulltext_available is None else fulltext_available,
        "fulltext_used": fulltext_used,
        "pdf_downloaded": pdf_downloaded,
        "citation_count_metadata_only": citation_count_metadata_only,
    }


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
        or paper.get("nber_id")
        or paper.get("openalex_id")
        or paper.get("semantic_scholar_id")
        or source_ids.get("doi")
        or source_ids.get("arxiv_id")
        or source_ids.get("nber_id")
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
    paper.setdefault("nber_id", paper.get("nber_id") or source_ids.get("nber_id"))
    paper.setdefault("resolution_confidence", "high" if paper.get("doi") or paper.get("arxiv_id") or paper.get("nber_id") or paper.get("openalex_id") or paper.get("semantic_scholar_id") else "medium")
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
    nber_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
    crossref_id: str | None,
) -> str | None:
    return doi or arxiv_id or nber_id or openalex_id or semantic_scholar_id or crossref_id


def _default_resolution_confidence(
    *,
    doi: str | None,
    arxiv_id: str | None,
    nber_id: str | None,
    openalex_id: str | None,
    semantic_scholar_id: str | None,
) -> str:
    return "high" if any([doi, arxiv_id, nber_id, openalex_id, semantic_scholar_id]) else "medium"
