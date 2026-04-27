from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .normalize import canonical_id, first_author, normalize_arxiv_id, normalize_doi, normalize_nber_id, normalize_title, utc_now_iso, validate_normalized_paper


IDENTIFIER_FIELDS = ["doi", "arxiv_id", "nber_id", "openalex_id", "semantic_scholar_id"]
MERGED_LIST_FIELDS = [
    "authors",
    "source_adapters",
    "source_urls",
    "pdf_urls",
    "topics",
    "categories",
    "fields_of_study",
    "raw_snapshot_refs",
    "same_as_sources",
    "research_query_sets",
    "research_branch_hints",
    "research_management_lanes",
]
PRIMARY_OR_SECONDARY_FIELDS = [
    "research_query_set",
    "research_branch_hint",
    "research_management_lane",
    "source_query_set",
    "query_run_id",
    "source_record_id",
    "retrieved_at",
]
SECONDARY_FILL_FIELDS = [
    "title",
    "title_normalized",
    "publication_year",
    "publication_date",
    "updated_date",
    "venue",
    "publisher",
    "language",
    "oa_status",
    "open_access_status",
    "license",
    "metadata_license",
    "is_retracted",
    "citation_count",
    "influential_citation_count",
]


class PaperDedupeIndex:
    """Identifier-first duplicate lookup with narrow fuzzy title buckets."""

    def __init__(self, papers: list[dict[str, Any]] | None = None):
        self.doi: dict[str, int] = {}
        self.arxiv_id: dict[str, int] = {}
        self.nber_id: dict[str, int] = {}
        self.openalex_id: dict[str, int] = {}
        self.semantic_scholar_id: dict[str, int] = {}
        self.title_buckets: dict[tuple[int | None, str], list[int]] = {}
        for index, paper in enumerate(papers or []):
            self.add(index, paper)

    def add(self, index: int, paper: dict[str, Any]) -> None:
        for key, value in _identifier_keys(paper):
            getattr(self, key)[value] = index
        bucket = _fuzzy_bucket(paper)
        if bucket is not None:
            indexes = self.title_buckets.setdefault(bucket, [])
            if index not in indexes:
                indexes.append(index)

    def rebuild(self, papers: list[dict[str, Any]]) -> None:
        self.doi.clear()
        self.arxiv_id.clear()
        self.nber_id.clear()
        self.openalex_id.clear()
        self.semantic_scholar_id.clear()
        self.title_buckets.clear()
        for index, paper in enumerate(papers):
            self.add(index, paper)

    def find_duplicate_index(self, papers: list[dict[str, Any]], paper: dict[str, Any]) -> int | None:
        for key, value in _identifier_keys(paper):
            match = getattr(self, key).get(value)
            if match is not None:
                return match
        bucket = _fuzzy_bucket(paper)
        if bucket is None:
            return None
        for index in self.title_buckets.get(bucket, []):
            if _fuzzy_title_year_author(papers[index], paper):
                return index
        return None


def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = PaperDedupeIndex()
    for paper in papers:
        match_index = index.find_duplicate_index(merged, paper)
        if match_index is None:
            merged.append(dict(paper))
            index.add(len(merged) - 1, merged[-1])
        else:
            merged[match_index] = merge_papers(merged[match_index], paper)
            index.add(match_index, merged[match_index])
    for paper in merged:
        validate_normalized_paper(paper)
    return merged


def merge_papers(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    merged["source_ids"] = _merge_source_ids(primary.get("source_ids", {}), secondary.get("source_ids", {}))
    for field in IDENTIFIER_FIELDS:
        merged[field] = primary.get(field) or secondary.get(field) or merged["source_ids"].get(field)
    merged["crossref_id"] = merged["source_ids"].get("crossref_id")
    _merge_list_fields(merged, primary, secondary)
    _merge_primary_or_secondary_fields(merged, primary, secondary)
    merged["seed_origin_type"] = _merge_seed_origin_type(primary, secondary)
    merged["seed_origin_is_evidence"] = False
    merged["canonical_resolution_status"] = _merge_resolution_status(primary, secondary)
    merged["resolution_confidence"] = _merge_resolution_confidence(primary, secondary)
    merged["duplicate_of"] = primary.get("duplicate_of") or secondary.get("duplicate_of")
    merged["fulltext_available"] = bool(primary.get("fulltext_available") or secondary.get("fulltext_available"))
    merged["fulltext_used"] = False
    merged["pdf_downloaded"] = False
    merged["citation_count_metadata_only"] = True
    merged["abstract"] = _prefer_longer(primary.get("abstract"), secondary.get("abstract"))
    merged["abstract_available"] = bool(merged.get("abstract"))
    _fill_empty_fields_from_secondary(merged, secondary)
    conflict_notes = _merge_unique(primary.get("conflict_notes", []), secondary.get("conflict_notes", []))
    conflict_notes.extend(_conflict_notes(primary, secondary))
    if secondary.get("is_retracted") is True:
        merged["is_retracted"] = True
        merged["manual_review_required"] = True
    merged["discovered_from_scholar_seed"] = bool(primary.get("discovered_from_scholar_seed") or secondary.get("discovered_from_scholar_seed"))
    merged["manual_review_required"] = bool(merged.get("manual_review_required") or secondary.get("manual_review_required") or conflict_notes)
    merged["conflict_notes"] = _merge_unique([], conflict_notes)
    merged["first_author"] = first_author(merged.get("authors", []))
    merged["title_normalized"] = normalize_title(merged.get("title"))
    merged["canonical_paper_id"] = canonical_id(
        doi=merged.get("doi"),
        arxiv_id=merged.get("arxiv_id"),
        nber_id=merged.get("nber_id"),
        semantic_scholar_id=merged.get("semantic_scholar_id"),
        openalex_id=merged.get("openalex_id"),
        title=merged.get("title"),
        publication_year=merged.get("publication_year"),
    )
    merged["dedup_key"] = merged["canonical_paper_id"]
    merged["updated_at"] = utc_now_iso()
    return merged


def _merge_list_fields(merged: dict[str, Any], primary: dict[str, Any], secondary: dict[str, Any]) -> None:
    for field in MERGED_LIST_FIELDS:
        merged[field] = _merge_unique(primary.get(field, []), secondary.get(field, []))


def _merge_primary_or_secondary_fields(
    merged: dict[str, Any],
    primary: dict[str, Any],
    secondary: dict[str, Any],
) -> None:
    for field in PRIMARY_OR_SECONDARY_FIELDS:
        merged[field] = primary.get(field) or secondary.get(field)


def _fill_empty_fields_from_secondary(merged: dict[str, Any], secondary: dict[str, Any]) -> None:
    for field in SECONDARY_FILL_FIELDS:
        if _is_empty_value(merged.get(field)) and not _is_empty_value(secondary.get(field)):
            merged[field] = secondary[field]


def is_duplicate_paper(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _is_duplicate(left, right)


def _find_duplicate_index(existing: list[dict[str, Any]], paper: dict[str, Any]) -> int | None:
    return PaperDedupeIndex(existing).find_duplicate_index(existing, paper)


def _is_duplicate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_ids = left.get("source_ids", {}) or {}
    right_ids = right.get("source_ids", {}) or {}
    if _same_nonempty(normalize_doi(left.get("doi")), normalize_doi(right.get("doi"))):
        return True
    if _same_nonempty(normalize_arxiv_id(left.get("arxiv_id")), normalize_arxiv_id(right.get("arxiv_id"))):
        return True
    if _same_nonempty(
        normalize_nber_id(left.get("nber_id") or left_ids.get("nber_id")),
        normalize_nber_id(right.get("nber_id") or right_ids.get("nber_id")),
    ):
        return True
    if _same_nonempty(left.get("semantic_scholar_id"), right.get("semantic_scholar_id")):
        return True
    if _same_nonempty(left.get("openalex_id"), right.get("openalex_id")):
        return True
    return _fuzzy_title_year_author(left, right)


def _same_nonempty(left: str | None, right: str | None) -> bool:
    return bool(left and right and left == right)


def _fuzzy_title_year_author(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("publication_year") != right.get("publication_year"):
        return False
    left_author = normalize_title(left.get("first_author"))
    right_author = normalize_title(right.get("first_author"))
    if not left_author or not right_author:
        return False
    if left_author != right_author and SequenceMatcher(None, left_author, right_author).ratio() < 0.80:
        return False
    left_title = normalize_title(left.get("title"))
    right_title = normalize_title(right.get("title"))
    if not left_title or not right_title:
        return False
    return SequenceMatcher(None, left_title, right_title).ratio() >= 0.93


def _identifier_keys(paper: dict[str, Any]) -> list[tuple[str, str]]:
    source_ids = paper.get("source_ids", {}) or {}
    keys: list[tuple[str, str]] = []
    doi = normalize_doi(paper.get("doi") or source_ids.get("doi"))
    arxiv_id = normalize_arxiv_id(paper.get("arxiv_id") or source_ids.get("arxiv_id"))
    nber_id = normalize_nber_id(paper.get("nber_id") or source_ids.get("nber_id"))
    openalex_id = paper.get("openalex_id") or source_ids.get("openalex_id")
    semantic_scholar_id = paper.get("semantic_scholar_id") or source_ids.get("semantic_scholar_id")
    if doi:
        keys.append(("doi", doi))
    if arxiv_id:
        keys.append(("arxiv_id", arxiv_id))
    if nber_id:
        keys.append(("nber_id", nber_id))
    if openalex_id:
        keys.append(("openalex_id", str(openalex_id)))
    if semantic_scholar_id:
        keys.append(("semantic_scholar_id", str(semantic_scholar_id)))
    return keys


def _fuzzy_bucket(paper: dict[str, Any]) -> tuple[int | None, str] | None:
    year = paper.get("publication_year")
    author = normalize_title(paper.get("first_author"))
    if year is None or not author:
        return None
    return (year, author)


def _merge_unique(left: list[Any], right: list[Any]) -> list[Any]:
    result = []
    for item in [*left, *right]:
        if item not in result and item not in {None, ""}:
            result.append(item)
    return result


def _merge_source_ids(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    keys = set(left) | set(right)
    return {key: left.get(key) or right.get(key) for key in keys}


def _is_empty_value(value: Any) -> bool:
    return value is None or value == "" or value == []


def _prefer_longer(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right:
        return left
    return right if len(right) > len(left) else left


def _conflict_notes(primary: dict[str, Any], secondary: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for field in ["title", "publication_year", "publication_date"]:
        left = primary.get(field)
        right = secondary.get(field)
        if left and right and left != right:
            if field == "title":
                similarity = SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()
                if similarity >= 0.93:
                    continue
            notes.append(f"{field} conflict between sources")
    return notes


def _merge_seed_origin_type(primary: dict[str, Any], secondary: dict[str, Any]) -> str:
    values = {primary.get("seed_origin_type"), secondary.get("seed_origin_type")}
    if "scholar_local_seed" in values:
        return "scholar_local_seed"
    return str(primary.get("seed_origin_type") or secondary.get("seed_origin_type") or "metadata_api")


def _merge_resolution_status(primary: dict[str, Any], secondary: dict[str, Any]) -> str:
    statuses = {primary.get("canonical_resolution_status"), secondary.get("canonical_resolution_status")}
    if "resolved" in statuses:
        return "resolved"
    if "ambiguous" in statuses:
        return "ambiguous"
    return str(primary.get("canonical_resolution_status") or secondary.get("canonical_resolution_status") or "unresolved")


def _merge_resolution_confidence(primary: dict[str, Any], secondary: dict[str, Any]) -> str:
    priority = {"high": 0, "medium": 1, "low": 2, "unresolved": 3}
    values = [
        str(value)
        for value in [primary.get("resolution_confidence"), secondary.get("resolution_confidence")]
        if value
    ]
    if not values:
        return "unresolved"
    return min(values, key=lambda value: priority.get(value, 9))
