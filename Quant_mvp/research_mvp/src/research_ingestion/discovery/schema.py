from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib

from ..normalize import clean_text, utc_now_iso
from ..redaction import redact_url


ALLOWED_SOURCE_CHANNELS = {
    "google_scholar_alert_email",
    "google_scholar_manual_bibtex",
    "google_scholar_manual_endnote",
    "google_scholar_manual_refman",
    "google_scholar_manual_refworks",
    "google_scholar_manual_title_list",
    "google_scholar_manual_citation_seed",
    "user_provided_doi_list",
}

ALLOWED_LOOKUP_STATUSES = {
    "unresolved",
    "matched_openalex",
    "matched_crossref",
    "matched_arxiv",
    "matched_semantic_scholar",
    "matched_nber",
    "ambiguous",
    "rejected",
}

DISCOVERY_SEED_REQUIRED_FIELDS = [
    "discovery_seed_id",
    "source_channel",
    "discovered_at",
    "raw_title",
    "raw_authors",
    "raw_venue",
    "raw_year",
    "raw_snippet",
    "raw_link",
    "alert_query",
    "local_input_path",
    "canonical_lookup_status",
    "lifecycle_status",
    "canonical_resolution_status",
    "matched_source",
    "canonical_paper_id",
    "resolution_confidence",
    "manual_review_required",
    "notes_ko",
]


def make_discovery_seed(
    *,
    source_channel: str,
    raw_title: str,
    local_input_path: str | Path,
    raw_authors: list[str] | None = None,
    raw_venue: str | None = None,
    raw_year: int | None = None,
    raw_snippet: str | None = None,
    raw_link: str | None = None,
    alert_query: str | None = None,
    notes_ko: str | None = None,
    candidate_doi: str | None = None,
    candidate_arxiv_id: str | None = None,
    candidate_nber_id: str | None = None,
) -> dict[str, Any]:
    if source_channel not in ALLOWED_SOURCE_CHANNELS:
        raise ValueError(f"Unsupported DiscoverySeed source_channel: {source_channel}")
    basis = f"{source_channel}|{clean_text(raw_title) or ''}|{Path(local_input_path)}|{raw_year or ''}"
    seed = {
        "discovery_seed_id": "seed:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20],
        "source_channel": source_channel,
        "discovered_at": utc_now_iso(),
        "raw_title": clean_text(raw_title) or "",
        "raw_authors": [clean_text(author) for author in (raw_authors or []) if clean_text(author)],
        "raw_venue": clean_text(raw_venue),
        "raw_year": raw_year,
        "raw_snippet": clean_text(raw_snippet),
        "raw_link": redact_url(raw_link),
        "alert_query": clean_text(alert_query),
        "local_input_path": str(local_input_path),
        "canonical_lookup_status": "unresolved",
        "lifecycle_status": "local_seed_ingested",
        "canonical_resolution_status": "unresolved",
        "matched_source": None,
        "canonical_paper_id": None,
        "resolution_confidence": "unresolved",
        "manual_review_required": True,
        "notes_ko": notes_ko or "Google Scholar 기반 로컬 discovery seed입니다. 정식 EvidenceCard가 아니며 canonical metadata resolution이 필요합니다.",
        "candidate_doi": clean_text(candidate_doi),
        "candidate_arxiv_id": clean_text(candidate_arxiv_id),
        "candidate_nber_id": clean_text(candidate_nber_id),
        "seed_origin_type": source_channel,
        "seed_origin_is_evidence": False,
        "guardrails": {
            "scholar_seed_only": True,
            "not_evidence": True,
            "no_score_adopted": True,
        },
    }
    validate_discovery_seed(seed)
    return seed


def validate_discovery_seed(seed: dict[str, Any]) -> None:
    missing = [field for field in DISCOVERY_SEED_REQUIRED_FIELDS if field not in seed]
    if missing:
        raise ValueError(f"DiscoverySeed is missing required fields: {', '.join(missing)}")
    if seed["source_channel"] not in ALLOWED_SOURCE_CHANNELS:
        raise ValueError(f"Invalid source_channel: {seed['source_channel']}")
    if seed["canonical_lookup_status"] not in ALLOWED_LOOKUP_STATUSES:
        raise ValueError(f"Invalid canonical_lookup_status: {seed['canonical_lookup_status']}")
    if seed["canonical_resolution_status"] not in ALLOWED_LOOKUP_STATUSES:
        raise ValueError(f"Invalid canonical_resolution_status: {seed['canonical_resolution_status']}")
    if seed.get("seed_origin_is_evidence") is not False:
        raise ValueError("DiscoverySeed must not be treated as evidence.")
    guardrails = seed.get("guardrails", {})
    if guardrails.get("scholar_seed_only") is not True or guardrails.get("not_evidence") is not True:
        raise ValueError("Scholar DiscoverySeed guardrails must remain true.")
