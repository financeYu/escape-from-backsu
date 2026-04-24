from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .normalize import canonical_id, first_author, normalize_arxiv_id, normalize_doi, normalize_title, utc_now_iso, validate_normalized_paper


def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for paper in papers:
        match_index = _find_duplicate_index(merged, paper)
        if match_index is None:
            merged.append(dict(paper))
        else:
            merged[match_index] = merge_papers(merged[match_index], paper)
    for paper in merged:
        validate_normalized_paper(paper)
    return merged


def merge_papers(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    merged["source_ids"] = _merge_source_ids(primary.get("source_ids", {}), secondary.get("source_ids", {}))
    for field in ["doi", "arxiv_id", "openalex_id", "semantic_scholar_id"]:
        merged[field] = primary.get(field) or secondary.get(field) or merged["source_ids"].get(field)
    merged["crossref_id"] = merged["source_ids"].get("crossref_id")
    merged["authors"] = _merge_unique(primary.get("authors", []), secondary.get("authors", []))
    merged["source_adapters"] = _merge_unique(primary.get("source_adapters", []), secondary.get("source_adapters", []))
    merged["source_urls"] = _merge_unique(primary.get("source_urls", []), secondary.get("source_urls", []))
    merged["pdf_urls"] = _merge_unique(primary.get("pdf_urls", []), secondary.get("pdf_urls", []))
    merged["topics"] = _merge_unique(primary.get("topics", []), secondary.get("topics", []))
    merged["categories"] = _merge_unique(primary.get("categories", []), secondary.get("categories", []))
    merged["fields_of_study"] = _merge_unique(primary.get("fields_of_study", []), secondary.get("fields_of_study", []))
    merged["raw_snapshot_refs"] = _merge_unique(primary.get("raw_snapshot_refs", []), secondary.get("raw_snapshot_refs", []))
    merged["same_as_sources"] = _merge_unique(primary.get("same_as_sources", []), secondary.get("same_as_sources", []))
    merged["research_query_sets"] = _merge_unique(primary.get("research_query_sets", []), secondary.get("research_query_sets", []))
    merged["research_branch_hints"] = _merge_unique(primary.get("research_branch_hints", []), secondary.get("research_branch_hints", []))
    merged["research_management_lanes"] = _merge_unique(primary.get("research_management_lanes", []), secondary.get("research_management_lanes", []))
    merged["research_query_set"] = primary.get("research_query_set") or secondary.get("research_query_set")
    merged["research_branch_hint"] = primary.get("research_branch_hint") or secondary.get("research_branch_hint")
    merged["research_management_lane"] = primary.get("research_management_lane") or secondary.get("research_management_lane")
    merged["abstract"] = _prefer_longer(primary.get("abstract"), secondary.get("abstract"))
    merged["abstract_available"] = bool(merged.get("abstract"))
    for field in [
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
        "is_retracted",
        "citation_count",
        "influential_citation_count",
    ]:
        if _is_empty_value(merged.get(field)) and not _is_empty_value(secondary.get(field)):
            merged[field] = secondary[field]
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
        semantic_scholar_id=merged.get("semantic_scholar_id"),
        openalex_id=merged.get("openalex_id"),
        title=merged.get("title"),
        publication_year=merged.get("publication_year"),
    )
    merged["updated_at"] = utc_now_iso()
    return merged


def is_duplicate_paper(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _is_duplicate(left, right)


def _find_duplicate_index(existing: list[dict[str, Any]], paper: dict[str, Any]) -> int | None:
    for index, candidate in enumerate(existing):
        if _is_duplicate(candidate, paper):
            return index
    return None


def _is_duplicate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if _same_nonempty(normalize_doi(left.get("doi")), normalize_doi(right.get("doi"))):
        return True
    if _same_nonempty(normalize_arxiv_id(left.get("arxiv_id")), normalize_arxiv_id(right.get("arxiv_id"))):
        return True
    if _same_nonempty(left.get("semantic_scholar_id"), right.get("semantic_scholar_id")):
        return True
    if _same_nonempty(left.get("openalex_id"), right.get("openalex_id")):
        return True
    return _fuzzy_title_year_author(left, right)


def _same_nonempty(left: str | None, right: str | None) -> bool:
    return bool(left and right and left == right)


def _fuzzy_title_year_author(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("publication_year") and right.get("publication_year") and left["publication_year"] != right["publication_year"]:
        return False
    left_title = normalize_title(left.get("title"))
    right_title = normalize_title(right.get("title"))
    if not left_title or not right_title:
        return False
    if SequenceMatcher(None, left_title, right_title).ratio() < 0.93:
        return False
    left_author = normalize_title(left.get("first_author"))
    right_author = normalize_title(right.get("first_author"))
    if left_author and right_author:
        return SequenceMatcher(None, left_author, right_author).ratio() >= 0.80
    return True


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
