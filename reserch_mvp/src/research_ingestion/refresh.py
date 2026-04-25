from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from .dedupe import PaperDedupeIndex, deduplicate_papers


def refresh_timestamp_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def select_unseen_papers(existing_papers: list[dict[str, Any]], candidate_papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidate papers that are not already represented in the corpus."""
    unseen: list[dict[str, Any]] = []
    comparison_pool = list(existing_papers)
    dedupe_index = PaperDedupeIndex(comparison_pool)
    for paper in candidate_papers:
        if dedupe_index.find_duplicate_index(comparison_pool, paper) is not None:
            continue
        unseen.append(paper)
        comparison_pool.append(paper)
        dedupe_index.add(len(comparison_pool) - 1, paper)
    return deduplicate_papers(unseen)


def build_refresh_summary(
    *,
    run_id: str,
    selected_sources: list[str],
    selected_query_sets: list[str],
    existing_count: int,
    candidate_count: int,
    new_count: int,
    refreshed_count: int,
    child_runs: list[str],
    raw_counts: dict[str, int] | Counter[str] | None = None,
    relevance_rejected_count: int = 0,
    relevance_manual_review_count: int = 0,
    plan: dict[str, Any] | None = None,
    selected_profile: str | None = None,
    pipeline_telemetry: dict[str, Any] | None = None,
    incremental_pipeline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "timestamp_utc": refresh_timestamp_utc(),
        "mode": "periodic_refresh",
        "selected_profile": selected_profile,
        "selected_sources": selected_sources,
        "selected_query_set": ",".join(selected_query_sets),
        "selected_query_sets": selected_query_sets,
        "raw_records_collected_by_source": dict(raw_counts or {}),
        "normalized_records_written": refreshed_count,
        "records_rejected_by_relevance": relevance_rejected_count,
        "records_manual_review_by_relevance": relevance_manual_review_count,
        "refresh_existing_paper_count": existing_count,
        "refresh_candidate_paper_count": candidate_count,
        "refresh_new_paper_count": new_count,
        "refresh_refreshed_paper_count": refreshed_count,
        "refresh_child_runs": child_runs,
        "pdf_fulltext_used": False,
        "pipeline_telemetry": pipeline_telemetry or {},
        "incremental_pipeline": incremental_pipeline or {},
        "plan": plan or {},
    }
