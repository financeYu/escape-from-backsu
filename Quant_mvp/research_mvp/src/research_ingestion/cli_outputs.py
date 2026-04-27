from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ProjectPaths
from .persistence import read_json, read_jsonl, validate_storage_segment, write_json, write_jsonl


def _write_run_metadata(paths: ProjectPaths, run_id: str, source_health: dict[str, Any], collection_summary: dict[str, Any]) -> None:
    indexes_dir = paths.data_dir / "indexes"
    write_json(indexes_dir / f"{run_id}_source_health.json", source_health)
    write_json(indexes_dir / f"{run_id}_source_health_report.json", source_health)
    write_json(indexes_dir / "source_health_report.json", source_health)
    write_json(indexes_dir / f"{run_id}_collection_summary.json", collection_summary)


def _annotate_collection_lane(paper: dict[str, Any], query_set_name: str, query_set: dict[str, Any], run_id: str) -> dict[str, Any]:
    annotated = dict(paper)
    branch_hint = query_set.get("branch_hint")
    management_lane = query_set.get("management_lane")
    downstream_route = query_set.get("downstream_route")
    annotated["research_query_set"] = query_set_name
    annotated["research_query_sets"] = _append_unique(annotated.get("research_query_sets", []), query_set_name)
    annotated["source_query_set"] = query_set_name
    annotated["query_run_id"] = run_id
    annotated["region_scope"] = query_set.get("region_scope")
    annotated["required_input_policy"] = query_set.get("required_input_policy")
    if branch_hint:
        annotated["research_branch_hint"] = branch_hint
        annotated["research_branch_hints"] = _append_unique(annotated.get("research_branch_hints", []), branch_hint)
    if downstream_route:
        annotated["research_downstream_route"] = downstream_route
    if management_lane:
        annotated["research_management_lane"] = management_lane
        annotated["research_management_lanes"] = _append_unique(annotated.get("research_management_lanes", []), management_lane)
    return annotated


def _append_unique(values: list[Any], value: Any) -> list[Any]:
    result = list(values or [])
    if value not in result and value not in {None, ""}:
        result.append(value)
    return result


def _run_collection_summary(paths: ProjectPaths, run_id: str) -> dict[str, Any]:
    return read_json(paths.data_dir / "indexes" / f"{run_id}_collection_summary.json", default={}) or {}


def _run_management_lane(paths: ProjectPaths, run_id: str) -> str | None:
    summary = _run_collection_summary(paths, run_id)
    lane = summary.get("selected_management_lane") or summary.get("plan", {}).get("management_lane")
    return str(lane) if lane else None


def _normalized_papers_path_for_run(paths: ProjectPaths, run_id: str) -> Path:
    run_path = paths.data_dir / "normalized" / f"{run_id}_papers.jsonl"
    if run_path.exists():
        return run_path
    lane = _run_management_lane(paths, run_id)
    if lane:
        lane_path = paths.data_dir / "normalized" / f"{validate_storage_segment(lane, 'management_lane')}_papers.jsonl"
        if lane_path.exists():
            return lane_path
    return paths.data_dir / "normalized" / "papers.jsonl"


def _read_normalized_papers_for_run(paths: ProjectPaths, run_id: str) -> list[dict[str, Any]]:
    return read_jsonl(_normalized_papers_path_for_run(paths, run_id))


def _write_normalized_papers(paths: ProjectPaths, run_id: str, papers: list[dict[str, Any]]) -> None:
    write_jsonl(paths.data_dir / "normalized" / f"{run_id}_papers.jsonl", papers)
    lane = _run_management_lane(paths, run_id)
    _write_lane_paper_outputs(paths, papers)
    if lane and not any(lane in _paper_management_lanes(paper) for paper in papers):
        safe_lane = validate_storage_segment(lane, "management_lane")
        write_jsonl(paths.data_dir / "normalized" / f"{safe_lane}_papers.jsonl", [])
    if lane != "backtest_methodology":
        write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", papers)


def _write_lane_paper_outputs(paths: ProjectPaths, papers: list[dict[str, Any]]) -> None:
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for paper in papers:
        for lane in _paper_management_lanes(paper):
            by_lane.setdefault(lane, []).append(paper)
    for lane, lane_papers in by_lane.items():
        safe_lane = validate_storage_segment(lane, "management_lane")
        write_jsonl(paths.data_dir / "normalized" / f"{safe_lane}_papers.jsonl", lane_papers)


def _paper_management_lanes(paper: dict[str, Any]) -> list[str]:
    lanes = []
    for lane in paper.get("research_management_lanes", []) or []:
        if lane not in lanes:
            lanes.append(str(lane))
    lane = paper.get("research_management_lane")
    if lane and lane not in lanes:
        lanes.append(str(lane))
    return lanes


def _write_enrichment_metadata(paths: ProjectPaths, run_id: str, source_health: dict[str, Any], enrichment_summary: dict[str, Any]) -> None:
    indexes_dir = paths.data_dir / "indexes"
    existing_health = read_json(indexes_dir / f"{run_id}_source_health.json", default={}) or {}
    existing_health.update(source_health)
    write_json(indexes_dir / f"{run_id}_source_health.json", existing_health)
    write_json(indexes_dir / f"{run_id}_source_health_report.json", existing_health)
    write_json(indexes_dir / "source_health_report.json", existing_health)
    write_json(indexes_dir / f"{run_id}_enrichment_summary.json", enrichment_summary)
    collection_summary = read_json(indexes_dir / f"{run_id}_collection_summary.json", default={}) or {}
    collection_summary["enrichment"] = enrichment_summary
    write_json(indexes_dir / f"{run_id}_collection_summary.json", collection_summary)


def _dedupe_index_row(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_paper_id": paper.get("canonical_paper_id"),
        "source_ids": paper.get("source_ids", {}),
        "source_adapters": paper.get("source_adapters", []),
        "raw_snapshot_refs": paper.get("raw_snapshot_refs", []),
        "research_query_sets": paper.get("research_query_sets", []),
        "research_management_lanes": paper.get("research_management_lanes", []),
        "manual_review_required": paper.get("manual_review_required", False),
        "conflict_notes": paper.get("conflict_notes", []),
    }


def _seeds_path(paths: ProjectPaths, run_id: str) -> Path:
    return paths.data_dir / "discovery" / "google_scholar" / f"{run_id}_seeds.jsonl"


def _write_evidence_outputs(
    paths: ProjectPaths,
    cards: list[dict[str, Any]],
    *,
    run_id: str | None = None,
    management_lane: str | None = None,
) -> None:
    evidence_dir = paths.data_dir / "evidence"
    backtest_cards = [card for card in cards if _card_management_lane(card) == "backtest_methodology"]
    if management_lane == "backtest_methodology":
        write_jsonl(evidence_dir / "backtest_methodology_items.jsonl", backtest_cards)
        if run_id:
            write_jsonl(evidence_dir / f"{run_id}_backtest_methodology_items.jsonl", backtest_cards)
        return

    non_backtest_cards = [card for card in cards if _card_management_lane(card) != "backtest_methodology"]
    write_jsonl(evidence_dir / "evidence_cards.jsonl", non_backtest_cards)
    write_jsonl(evidence_dir / "technical_candidates.jsonl", [card for card in non_backtest_cards if card["classification"]["downstream_route"] == "technical_score_architect"])
    write_jsonl(evidence_dir / "valuation_candidates.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "valuation_agent_handoff"])
    write_jsonl(evidence_dir / "hybrid_review_required.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "hybrid_split_required"])
    write_jsonl(evidence_dir / "diagnostic_items.jsonl", [card for card in non_backtest_cards if card["classification"]["downstream_route"] == "diagnostic_backlog"])
    write_jsonl(evidence_dir / "backtest_methodology_items.jsonl", backtest_cards)
    if run_id:
        write_jsonl(evidence_dir / f"{run_id}_backtest_methodology_items.jsonl", backtest_cards)
    write_jsonl(evidence_dir / "reject_log.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "reject_log"])


def _write_new_only_outputs(
    paths: ProjectPaths,
    new_papers: list[dict[str, Any]],
    new_cards: list[dict[str, Any]],
    scholar_seeds: list[dict[str, Any]],
) -> None:
    normalized_dir = paths.data_dir / "normalized"
    evidence_dir = paths.data_dir / "evidence"
    discovery_dir = paths.data_dir / "discovery" / "google_scholar"
    unresolved = [
        seed
        for seed in scholar_seeds
        if seed.get("canonical_lookup_status") in {"unresolved", "ambiguous", "rejected"}
    ]
    backtest_cards = [card for card in new_cards if _card_management_lane(card) == "backtest_methodology"]
    non_backtest_cards = [card for card in new_cards if _card_management_lane(card) != "backtest_methodology"]
    write_jsonl(normalized_dir / "normalized_papers_new.jsonl", new_papers)
    write_jsonl(evidence_dir / "evidence_cards_new.jsonl", non_backtest_cards)
    write_jsonl(
        evidence_dir / "technical_candidates_new.jsonl",
        [card for card in non_backtest_cards if card["classification"]["downstream_route"] == "technical_score_architect"],
    )
    write_jsonl(
        evidence_dir / "valuation_candidates_new.jsonl",
        [card for card in new_cards if card["classification"]["downstream_route"] == "valuation_agent_handoff"],
    )
    write_jsonl(
        evidence_dir / "diagnostic_items_new.jsonl",
        [card for card in non_backtest_cards if card["classification"]["downstream_route"] == "diagnostic_backlog"],
    )
    write_jsonl(
        evidence_dir / "hybrid_review_required_new.jsonl",
        [card for card in new_cards if card["classification"]["downstream_route"] == "hybrid_split_required"],
    )
    write_jsonl(
        evidence_dir / "reject_log_new.jsonl",
        [card for card in new_cards if card["classification"]["downstream_route"] == "reject_log"],
    )
    write_jsonl(evidence_dir / "backtest_methodology_items_new.jsonl", backtest_cards)
    write_jsonl(discovery_dir / "unresolved_seeds_new.jsonl", unresolved)


def _card_management_lane(card: dict[str, Any]) -> str | None:
    lane = card.get("classification", {}).get("management_lane")
    return str(lane) if lane else None
