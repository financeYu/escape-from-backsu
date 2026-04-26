from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .schema import validate_discovery_seed
from ..normalize import normalize_arxiv_id, normalize_doi, normalize_title
from ..persistence import write_jsonl
from ..redaction import assert_no_scholar_request


APPROVED_RESOLUTION_SOURCES = {"openalex", "crossref", "arxiv", "semantic_scholar"}


def assert_approved_resolution_url(url: str) -> None:
    assert_no_scholar_request(url)


def resolve_seed(seed: dict[str, Any], candidates_by_source: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    validate_discovery_seed(seed)
    _validate_resolution_sources(candidates_by_source)

    matches = _find_matches(seed, candidates_by_source)
    resolved = dict(seed)
    if not matches:
        resolved.update(
            {
                "canonical_lookup_status": "unresolved",
                "lifecycle_status": "unresolved",
                "canonical_resolution_status": "unresolved",
                "matched_source": None,
                "canonical_paper_id": None,
                "resolution_confidence": "unresolved",
                "manual_review_required": True,
                "notes_ko": "승인된 metadata source에서 canonical match를 찾지 못했습니다. EvidenceCard로 승격할 수 없습니다.",
            }
        )
        return resolved

    if _has_ambiguous_matches(matches):
        resolved.update(
            {
                "canonical_lookup_status": "ambiguous",
                "lifecycle_status": "resolved_ambiguous",
                "canonical_resolution_status": "ambiguous",
                "matched_source": ",".join(sorted({source for source, _, _ in matches})),
                "canonical_paper_id": None,
                "resolution_confidence": "low",
                "manual_review_required": True,
                "notes_ko": "여러 canonical 후보가 충돌했습니다. 수동 검토가 필요합니다.",
            }
        )
        return resolved

    source, paper, confidence = _best_match(matches)
    resolved.update(
        {
            "canonical_lookup_status": f"matched_{source}",
            "lifecycle_status": "resolved_unique",
            "canonical_resolution_status": f"matched_{source}",
            "matched_source": source,
            "canonical_paper_id": paper["canonical_paper_id"],
            "resolution_confidence": confidence,
            "manual_review_required": confidence != "high",
            "notes_ko": "승인된 metadata source를 통해 canonical paper로 해소되었습니다.",
        }
    )
    return resolved


def _validate_resolution_sources(candidates_by_source: dict[str, list[dict[str, Any]]]) -> None:
    for source in candidates_by_source:
        if source not in APPROVED_RESOLUTION_SOURCES:
            raise ValueError(f"Unapproved resolution source: {source}")


def _has_ambiguous_matches(matches: list[tuple[str, dict[str, Any], str]]) -> bool:
    return len({paper["canonical_paper_id"] for _, paper, _ in matches}) > 1


def resolve_seeds(
    seeds: list[dict[str, Any]],
    candidates_by_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [resolve_seed(seed, candidates_by_source) for seed in seeds]


def unresolved_seeds(resolved_seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        seed
        for seed in resolved_seeds
        if seed["canonical_lookup_status"] in {"unresolved", "ambiguous", "rejected"}
    ]


def write_unresolved_scholar_seeds(path: str | Path, resolved_seeds: list[dict[str, Any]]) -> None:
    write_jsonl(Path(path), unresolved_seeds(resolved_seeds))


def _find_matches(
    seed: dict[str, Any],
    candidates_by_source: dict[str, list[dict[str, Any]]],
) -> list[tuple[str, dict[str, Any], str]]:
    seed_doi = normalize_doi(seed.get("candidate_doi"))
    seed_arxiv = normalize_arxiv_id(seed.get("candidate_arxiv_id"))
    raw_title = normalize_title(seed.get("raw_title"))
    raw_year = seed.get("raw_year")
    first_author = normalize_title(_first_raw_author(seed.get("raw_authors")))
    matches: list[tuple[str, dict[str, Any], str]] = []

    for source, papers in candidates_by_source.items():
        for paper in papers:
            if seed_doi and seed_doi == normalize_doi(paper.get("doi")):
                matches.append((source, paper, "high"))
            elif seed_arxiv and seed_arxiv == normalize_arxiv_id(paper.get("arxiv_id")):
                matches.append((source, paper, "high"))
            elif paper.get("source_ids", {}).get("openalex_id") and seed.get("candidate_openalex_id") == paper["source_ids"]["openalex_id"]:
                matches.append((source, paper, "high"))
            elif paper.get("source_ids", {}).get("semantic_scholar_id") and seed.get("candidate_semantic_scholar_id") == paper["source_ids"]["semantic_scholar_id"]:
                matches.append((source, paper, "high"))
            elif raw_title and _title_year_author_match(raw_title, raw_year, first_author, paper):
                matches.append((source, paper, "medium"))
    return matches


def _title_year_author_match(title: str, year: int | None, first_author_value: str, paper: dict[str, Any]) -> bool:
    paper_title = normalize_title(paper.get("title"))
    similarity = SequenceMatcher(None, title, paper_title).ratio()
    if similarity < 0.90:
        return False
    if year and paper.get("publication_year") and year != paper.get("publication_year"):
        return False
    if first_author_value and paper.get("first_author"):
        return SequenceMatcher(None, first_author_value, normalize_title(paper.get("first_author"))).ratio() >= 0.80
    return True


def _best_match(matches: list[tuple[str, dict[str, Any], str]]) -> tuple[str, dict[str, Any], str]:
    priority = {"high": 0, "medium": 1, "low": 2}
    source_priority = {"crossref": 0, "arxiv": 1, "openalex": 2, "semantic_scholar": 3}
    best = min(matches, key=lambda match: _match_sort_key(match, priority, source_priority), default=None)
    if best is None:
        raise ValueError("_best_match requires at least one match.")
    return best


def _match_sort_key(
    match: tuple[str, dict[str, Any], str],
    priority: dict[str, int],
    source_priority: dict[str, int],
) -> tuple[int, int]:
    source, _paper, confidence = match
    return (priority.get(confidence, 9), source_priority.get(source, 9))


def _first_raw_author(raw_authors: Any) -> str | None:
    if isinstance(raw_authors, list):
        return next((str(author) for author in raw_authors if author), None)
    return None
