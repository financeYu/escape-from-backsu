from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable
import json
from time import perf_counter
from typing import Any

from .classify import classify_paper
from .config import ProjectPaths, get_query_set
from .dedupe import deduplicate_papers
from .evidence import generate_evidence_cards
from .persistence import read_json, read_jsonl, validate_storage_segment, write_json, write_jsonl
from .refresh import build_refresh_summary, select_unseen_papers
from .reporting import generate_reports
from .cli_collect import cmd_collect
from .cli_collect import estimate_collection_request_budget
from .cli_common import (
    _dedup_ratio,
    _elapsed_ms,
    _refresh_policy,
    _source_adapter_registry,
    _split_csv,
    _validate_query_allowed_sources,
    _validate_sources,
)
from .cli_outputs import (
    _dedupe_index_row,
    _seeds_path,
    _write_evidence_outputs,
    _write_lane_paper_outputs,
    _write_new_only_outputs,
)


_REFRESH_SOURCE_INT_FIELDS = [
    "request_count",
    "rate_limit_wait_count",
    "success_count",
    "failure_count",
    "http_429_count",
    "parse_error_count",
    "schema_error_count",
    "new_item_count",
    "manual_review_required_count",
    "request_cache_hit_count",
    "request_cache_miss_count",
    "request_cache_stale_count",
    "unresolved_seed_count",
    "pdf_download_attempt_count",
]

_REFRESH_SOURCE_FLOAT_FIELDS = [
    "rate_limit_wait_seconds",
    "request_latency_ms",
    "parse_ms",
    "dedupe_ms",
    "classification_ms",
]


def cmd_refresh(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    *,
    collect_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]] | None = None,
    current_policy_versions_func: Callable[[dict[str, Any]], dict[str, str]] | None = None,
) -> None:
    collect_command, classify_func, generate_cards_func, current_policy_versions_func = _refresh_dependencies(
        collect_command, classify_func, generate_cards_func, current_policy_versions_func
    )
    sources, query_sets, selected_profile, plan = _prepare_refresh_run(args, config, paths)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    existing_papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    if args.offline:
        _write_offline_refresh(args, paths, sources, query_sets, existing_papers, plan, selected_profile)
        return

    collection = _collect_refresh_candidates(args, config, paths, sources, query_sets, collect_command)
    papers = _dedupe_refresh_papers(existing_papers, collection["candidate_papers"])
    new_outputs = _generate_new_refresh_cards(args, config, papers["new_papers"], classify_func, generate_cards_func)
    card_outputs = _build_refresh_card_outputs(
        args, config, paths, papers, new_outputs,
        classify_func, generate_cards_func, current_policy_versions_func,
    )
    source_health, pipeline_telemetry = _refresh_source_health(paths, collection, card_outputs, papers)
    current_versions = current_policy_versions_func(config)
    incremental_pipeline = _incremental_pipeline(card_outputs, new_outputs, current_versions)
    summary = _refresh_summary(
        args, sources, query_sets, selected_profile, existing_papers,
        collection, papers, plan, pipeline_telemetry, incremental_pipeline,
    )

    _write_refresh_outputs(args, paths, papers, new_outputs, card_outputs, current_versions, source_health, summary)
    print(
        f"periodic refresh complete: new_papers={len(papers['new_papers'])}, "
        f"refreshed_papers={len(papers['refreshed_papers'])}"
    )


def _refresh_dependencies(
    collect_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None,
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] | None,
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]] | None,
    current_policy_versions_func: Callable[[dict[str, Any]], dict[str, str]] | None,
) -> tuple[
    Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None],
    Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]],
    Callable[[dict[str, Any]], dict[str, str]],
]:
    return (
        collect_command or cmd_collect,
        classify_func or classify_paper,
        generate_cards_func or generate_evidence_cards,
        current_policy_versions_func or _current_policy_versions,
    )


def _prepare_refresh_run(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
) -> tuple[list[str], list[str], str, dict[str, Any]]:
    sources = _refresh_sources(args, config)
    _validate_sources(sources, config)
    query_sets = _refresh_query_sets(args, config)
    _validate_refresh_query_allowed_sources(sources, query_sets, config)
    selected_profile = _refresh_profile_name(args, config)
    setattr(args, "request_cache_ttl_days", _refresh_profile_config(args, config).get("request_cache_ttl_days"))
    return sources, query_sets, selected_profile, _refresh_plan(args, config, paths, sources, query_sets)


def _write_offline_refresh(
    args: argparse.Namespace,
    paths: ProjectPaths,
    sources: list[str],
    query_sets: list[str],
    existing_papers: list[dict[str, Any]],
    plan: dict[str, Any],
    selected_profile: str,
) -> None:
    summary = build_refresh_summary(
        run_id=args.run_id,
        selected_sources=sources,
        selected_query_sets=query_sets,
        existing_count=len(existing_papers),
        candidate_count=0,
        new_count=0,
        refreshed_count=len(existing_papers),
        child_runs=[],
        plan=plan,
        selected_profile=selected_profile,
    )
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_refresh_new_papers.jsonl", [])
    _write_new_only_outputs(paths, [], [], [])
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_refresh_summary.json", summary)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_collection_summary.json", summary)
    offline_health = _offline_refresh_health()
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health.json", offline_health)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health_report.json", offline_health)
    write_json(paths.data_dir / "indexes" / "source_health_report.json", offline_health)
    print("offline mode: refresh network call 없이 metadata artifact를 생성했습니다.")


def _collect_refresh_candidates(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_sets: list[str],
    collect_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None],
) -> dict[str, Any]:
    collection = _empty_refresh_collection()
    adapter_registry = _source_adapter_registry(config, sources)
    for index, query_set in enumerate(query_sets):
        child_run_id = _refresh_child_run_id(args.run_id, query_set, index)
        child_args = _refresh_collect_args(args, child_run_id, query_set, sources, adapter_registry)
        collect_command(child_args, config, paths)
        _add_refresh_child_run(collection, paths, child_run_id)
    return collection


def _empty_refresh_collection() -> dict[str, Any]:
    return {
        "child_runs": [],
        "candidate_papers": [],
        "raw_counts": Counter(),
        "relevance_rejected_count": 0,
        "relevance_manual_review_count": 0,
    }


def _add_refresh_child_run(collection: dict[str, Any], paths: ProjectPaths, child_run_id: str) -> None:
    collection["child_runs"].append(child_run_id)
    collection["candidate_papers"].extend(
        read_jsonl(paths.data_dir / "normalized" / f"{child_run_id}_collected_papers.jsonl")
    )
    child_summary = read_json(paths.data_dir / "indexes" / f"{child_run_id}_collection_summary.json", default={}) or {}
    collection["raw_counts"].update(child_summary.get("raw_records_collected_by_source", {}))
    collection["relevance_rejected_count"] += int(child_summary.get("records_rejected_by_relevance", 0) or 0)
    collection["relevance_manual_review_count"] += int(
        child_summary.get("records_manual_review_by_relevance", 0) or 0
    )


def _dedupe_refresh_papers(
    existing_papers: list[dict[str, Any]],
    candidate_papers: list[dict[str, Any]],
) -> dict[str, Any]:
    dedupe_started = perf_counter()
    deduped_candidates = deduplicate_papers(candidate_papers)
    new_papers = select_unseen_papers(existing_papers, deduped_candidates)
    refreshed_papers = deduplicate_papers([*existing_papers, *new_papers])
    return {
        "deduped_candidates": deduped_candidates,
        "new_papers": new_papers,
        "refreshed_papers": refreshed_papers,
        "dedupe_ms": _elapsed_ms(dedupe_started),
    }


def _generate_new_refresh_cards(
    args: argparse.Namespace,
    config: dict[str, Any],
    new_papers: list[dict[str, Any]],
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]],
) -> dict[str, Any]:
    classification_started = perf_counter()
    new_classifications = [classify_func(paper, config["classification"], config["policy"]) for paper in new_papers]
    classification_ms = _elapsed_ms(classification_started)
    return {
        "new_classifications": new_classifications,
        "new_cards": generate_cards_func(new_papers, new_classifications, args.run_id),
        "classification_ms": classification_ms,
    }


def _build_refresh_card_outputs(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    papers: dict[str, Any],
    new_outputs: dict[str, Any],
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]],
    current_policy_versions_func: Callable[[dict[str, Any]], dict[str, str]],
) -> dict[str, Any]:
    existing_cards = read_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl")
    version_state = _existing_evidence_version_state(
        paths, config, current_policy_versions_func=current_policy_versions_func
    )
    if version_state["regenerate_existing_cards"]:
        return _regenerated_refresh_card_outputs(
            args, config, papers, new_outputs, classify_func, generate_cards_func, existing_cards, version_state
        )
    cards = _merge_existing_and_new_cards(existing_cards, new_outputs["new_cards"])
    classified = _classified_paper_rows(papers["new_papers"], new_outputs["new_classifications"])
    return {
        "cards": cards,
        "classifications_output": new_outputs["new_classifications"],
        "classified_papers_output": classified,
        "existing_cards": existing_cards,
        "existing_version_state": version_state,
        "classification_ms": new_outputs["classification_ms"],
    }


def _regenerated_refresh_card_outputs(
    args: argparse.Namespace,
    config: dict[str, Any],
    papers: dict[str, Any],
    new_outputs: dict[str, Any],
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]],
    existing_cards: list[dict[str, Any]],
    version_state: dict[str, Any],
) -> dict[str, Any]:
    classification_started = perf_counter()
    classifications = [
        classify_func(paper, config["classification"], config["policy"])
        for paper in papers["refreshed_papers"]
    ]
    classification_ms = new_outputs["classification_ms"] + _elapsed_ms(classification_started)
    return {
        "cards": generate_cards_func(papers["refreshed_papers"], classifications, args.run_id),
        "classifications_output": classifications,
        "classified_papers_output": _classified_paper_rows(papers["refreshed_papers"], classifications),
        "existing_cards": existing_cards,
        "existing_version_state": version_state,
        "classification_ms": classification_ms,
    }


def _classified_paper_rows(
    papers: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"paper": paper, "classification": classification}
        for paper, classification in zip(papers, classifications, strict=True)
    ]


def _refresh_source_health(
    paths: ProjectPaths,
    collection: dict[str, Any],
    card_outputs: dict[str, Any],
    papers: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_health = _aggregate_refresh_source_health(paths, collection["child_runs"])
    _update_source_health_from_cards(source_health, card_outputs["cards"], replace_new_item_count=True)
    pipeline_telemetry = _pipeline_telemetry(
        source_health=source_health,
        dedupe_ms=papers["dedupe_ms"],
        classification_ms=card_outputs["classification_ms"],
        relevance_rejected_count=collection["relevance_rejected_count"],
    )
    _attach_pipeline_telemetry(source_health, pipeline_telemetry)
    return source_health, pipeline_telemetry


def _incremental_pipeline(
    card_outputs: dict[str, Any],
    new_outputs: dict[str, Any],
    current_versions: dict[str, str],
) -> dict[str, Any]:
    version_state = card_outputs["existing_version_state"]
    if version_state["missing_existing_cards"]:
        classification_scope = "full_corpus_due_to_missing_existing_cards"
    elif version_state["regenerate_existing_cards"]:
        classification_scope = "full_corpus_due_to_policy_or_schema_version_change"
    else:
        classification_scope = "new_papers_only"
    return {
        "classification_scope": classification_scope,
        "new_papers_classified": len(new_outputs["new_classifications"]),
        "new_evidence_cards_generated": len(new_outputs["new_cards"]),
        "existing_evidence_cards_reused": 0 if version_state["regenerate_existing_cards"] else len(card_outputs["existing_cards"]),
        "existing_evidence_cards_regenerated": bool(version_state["regenerate_existing_cards"]),
        "missing_existing_cards": bool(version_state["missing_existing_cards"]),
        "policy_version": current_versions["policy_version"],
        "evidence_schema_version": current_versions["evidence_schema_version"],
        "previous_policy_version": version_state["previous_versions"].get("policy_version"),
        "previous_evidence_schema_version": version_state["previous_versions"].get("evidence_schema_version"),
    }


def _refresh_summary(
    args: argparse.Namespace,
    sources: list[str],
    query_sets: list[str],
    selected_profile: str,
    existing_papers: list[dict[str, Any]],
    collection: dict[str, Any],
    papers: dict[str, Any],
    plan: dict[str, Any],
    pipeline_telemetry: dict[str, Any],
    incremental_pipeline: dict[str, Any],
) -> dict[str, Any]:
    return build_refresh_summary(
        run_id=args.run_id,
        selected_sources=sources,
        selected_query_sets=query_sets,
        existing_count=len(existing_papers),
        candidate_count=len(papers["deduped_candidates"]),
        new_count=len(papers["new_papers"]),
        refreshed_count=len(papers["refreshed_papers"]),
        child_runs=collection["child_runs"],
        raw_counts=collection["raw_counts"],
        relevance_rejected_count=collection["relevance_rejected_count"],
        relevance_manual_review_count=collection["relevance_manual_review_count"],
        plan=plan,
        selected_profile=selected_profile,
        pipeline_telemetry=pipeline_telemetry,
        incremental_pipeline=incremental_pipeline,
    )


def _write_refresh_outputs(
    args: argparse.Namespace,
    paths: ProjectPaths,
    papers: dict[str, Any],
    new_outputs: dict[str, Any],
    card_outputs: dict[str, Any],
    current_versions: dict[str, str],
    source_health: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_refresh_new_papers.jsonl", papers["new_papers"])
    _write_new_only_outputs(paths, papers["new_papers"], new_outputs["new_cards"], read_jsonl(_seeds_path(paths, args.run_id)))
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", papers["refreshed_papers"])
    _write_lane_paper_outputs(paths, papers["refreshed_papers"])
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_dedupe_index.jsonl", [_dedupe_index_row(paper) for paper in papers["refreshed_papers"]])
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl", card_outputs["classifications_output"])
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_new_classifications.jsonl", new_outputs["new_classifications"])
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classified_papers.jsonl", card_outputs["classified_papers_output"])
    _write_evidence_outputs(paths, card_outputs["cards"], run_id=args.run_id)
    write_jsonl(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl", card_outputs["cards"])
    write_json(paths.data_dir / "indexes" / "evidence_policy_version.json", current_versions)
    _write_refresh_metadata(args, paths, source_health, summary)
    generate_reports(
        output_dir=paths.reports_dir,
        run_id=args.run_id,
        papers=papers["refreshed_papers"],
        evidence_cards=card_outputs["cards"],
        scholar_seeds=read_jsonl(_seeds_path(paths, args.run_id)),
        source_health=source_health,
        collection_summary=summary,
    )


def _write_refresh_metadata(
    args: argparse.Namespace,
    paths: ProjectPaths,
    source_health: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_refresh_summary.json", summary)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_collection_summary.json", summary)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health.json", source_health)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health_report.json", source_health)
    write_json(paths.data_dir / "indexes" / "source_health_report.json", source_health)


def _refresh_profile_name(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(getattr(args, "profile", None) or _refresh_policy(config).get("default_profile") or "default")


def _refresh_profile_config(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    profiles = config.get("policy", {}).get("refresh_profiles", {})
    name = _refresh_profile_name(args, config)
    if name == "default":
        return {}
    if name not in profiles:
        available = ", ".join(sorted(profiles))
        raise ValueError(f"알 수 없는 refresh profile입니다: {name}. 사용 가능: {available}")
    return dict(profiles[name])


def _refresh_sources(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    if getattr(args, "sources", None):
        return _split_csv(args.sources)
    profile = _refresh_profile_config(args, config)
    sources = [str(source) for source in profile.get("sources", []) if str(source).strip()]
    if not sources:
        sources = [str(source) for source in _refresh_policy(config).get("default_sources", []) if str(source).strip()]
    if not sources:
        raise ValueError("refresh source가 비어 있습니다. --sources, refresh profile, 또는 research_policy.toml refresh_policy.default_sources를 지정하세요.")
    return sources


def _refresh_query_sets(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    if getattr(args, "query_sets", None):
        query_sets = _split_csv(args.query_sets)
    else:
        profile = _refresh_profile_config(args, config)
        query_sets = [str(query_set) for query_set in profile.get("query_sets", []) if str(query_set).strip()]
        if not query_sets:
            query_sets = [str(query_set) for query_set in _refresh_policy(config).get("default_query_sets", []) if str(query_set).strip()]
    if not query_sets:
        raise ValueError("refresh query-set이 비어 있습니다. --query-sets, refresh profile, 또는 research_policy.toml refresh_policy.default_query_sets를 지정하세요.")
    for query_set in query_sets:
        _validate_refresh_query_set_allowed(args, query_set, get_query_set(config, query_set))
    return query_sets


def _validate_refresh_query_set_allowed(args: argparse.Namespace, query_set_name: str, query_set: dict[str, Any]) -> None:
    branch = str(query_set.get("branch_hint") or "")
    required_policy = str(query_set.get("required_input_policy") or "")
    if branch == "valuation" or "fundamental" in query_set_name or "fundamental" in required_policy:
        if not getattr(args, "include_valuation", False):
            raise ValueError(
                f"{query_set_name}은 valuation/fundamental query-set이라 --include-valuation 명시 opt-in이 필요합니다."
            )


def _refresh_plan(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_sets: list[str],
) -> dict[str, Any]:
    policy = _refresh_policy(config)
    profile_name = _refresh_profile_name(args, config)
    profile = _refresh_profile_config(args, config)
    existing_papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    child_run_ids = [_refresh_child_run_id(args.run_id, query_set, index) for index, query_set in enumerate(query_sets)]
    child_budgets = _refresh_child_request_budgets(args, config, sources, query_sets, child_run_ids)
    return {
        "run_id": args.run_id,
        "mode": "periodic_refresh",
        "selected_profile": profile_name,
        "profile": profile,
        "refresh_policy": policy,
        "selected_sources": sources,
        "selected_query_sets": query_sets,
        "include_valuation": bool(getattr(args, "include_valuation", False)),
        "child_run_ids": child_run_ids,
        "existing_paper_count": len(existing_papers),
        "offline": bool(getattr(args, "offline", False)),
        "dry_run": bool(args.dry_run),
        "request_budget": _aggregate_refresh_request_budget(child_budgets),
        "outputs": _refresh_output_paths(args, paths),
        "guardrails_ko": _refresh_guardrails(),
    }


def _refresh_child_request_budgets(
    args: argparse.Namespace,
    config: dict[str, Any],
    sources: list[str],
    query_sets: list[str],
    child_run_ids: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "query_set": query_set,
            **estimate_collection_request_budget(
                args=_refresh_collect_args(args, child_run_ids[index], query_set, sources),
                config=config,
                sources=sources,
                query_set=get_query_set(config, query_set),
            ),
        }
        for index, query_set in enumerate(query_sets)
    ]


def _refresh_output_paths(args: argparse.Namespace, paths: ProjectPaths) -> dict[str, str]:
    return {
        "new_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_refresh_new_papers.jsonl"),
        "normalized_papers_new_jsonl": str(paths.data_dir / "normalized" / "normalized_papers_new.jsonl"),
        "normalized_papers_jsonl": str(paths.data_dir / "normalized" / "papers.jsonl"),
        "refresh_summary_json": str(paths.data_dir / "indexes" / f"{args.run_id}_refresh_summary.json"),
        "evidence_cards_jsonl": str(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl"),
        "evidence_cards_new_jsonl": str(paths.data_dir / "evidence" / "evidence_cards_new.jsonl"),
        "technical_candidates_new_jsonl": str(paths.data_dir / "evidence" / "technical_candidates_new.jsonl"),
        "diagnostic_items_new_jsonl": str(paths.data_dir / "evidence" / "diagnostic_items_new.jsonl"),
        "hybrid_review_required_new_jsonl": str(paths.data_dir / "evidence" / "hybrid_review_required_new.jsonl"),
        "unresolved_seeds_new_jsonl": str(paths.data_dir / "discovery" / "google_scholar" / "unresolved_seeds_new.jsonl"),
        "reject_log_new_jsonl": str(paths.data_dir / "evidence" / "reject_log_new.jsonl"),
        "source_health_report_json": str(paths.data_dir / "indexes" / "source_health_report.json"),
        "reports_dir": str(paths.reports_dir),
    }


def _refresh_guardrails() -> list[str]:
    return [
        "refresh는 기존 papers.jsonl을 보존하고 새로 발견된 논문만 병합합니다.",
        "PDF fulltext 수집은 기본 비활성화입니다.",
        "Google Scholar live request는 수행하지 않습니다.",
        "EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.",
        "backtest, adoption decision, valuation scoring은 수행하지 않습니다.",
    ]


def _aggregate_refresh_request_budget(child_budgets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query_set_count": len(child_budgets),
        "full_page_request_count": sum(int(item.get("full_page_request_count", 0) or 0) for item in child_budgets),
        "worst_case_request_count": sum(int(item.get("worst_case_request_count", 0) or 0) for item in child_budgets),
        "estimated_min_rate_limit_wait_seconds": round(
            sum(float(item.get("estimated_min_rate_limit_wait_seconds", 0.0) or 0.0) for item in child_budgets),
            3,
        ),
        "request_cache_enabled": any(bool(item.get("request_cache_enabled", False)) for item in child_budgets),
        "child_query_set_budgets": child_budgets,
        "notes_ko": [
            "refresh dry-run 예산은 각 child query-set collect plan의 보수적 상한을 합산합니다.",
            "cache hit, early stop, API page underfill이 있으면 실제 live request 수는 더 작을 수 있습니다.",
            "이 예산은 root/master가 동일한 request 계산을 반복하지 않도록 handoff에 포함됩니다.",
        ],
    }


def _validate_refresh_query_allowed_sources(sources: list[str], query_sets: list[str], config: dict[str, Any]) -> None:
    for query_set_name in query_sets:
        _validate_query_allowed_sources(sources, get_query_set(config, query_set_name))


def _current_policy_versions(config: dict[str, Any]) -> dict[str, str]:
    policy = config.get("policy", {})
    metadata = policy.get("policy_metadata", {})
    return {
        "policy_version": str(metadata.get("policy_version") or "research_policy.v1"),
        "evidence_schema_version": str(metadata.get("evidence_schema_version") or "evidence_card.v1"),
    }


def _existing_evidence_version_state(
    paths: ProjectPaths,
    config: dict[str, Any],
    *,
    current_policy_versions_func: Callable[[dict[str, Any]], dict[str, str]] | None = None,
) -> dict[str, Any]:
    if current_policy_versions_func is None:
        current_policy_versions_func = _current_policy_versions
    previous_versions = read_json(paths.data_dir / "indexes" / "evidence_policy_version.json", default={}) or {}
    current_versions = current_policy_versions_func(config)
    existing_papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    existing_cards = read_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl")
    missing_existing_cards = bool(existing_papers and not existing_cards)
    return {
        "previous_versions": previous_versions,
        "current_versions": current_versions,
        "missing_existing_cards": missing_existing_cards,
        "regenerate_existing_cards": bool(missing_existing_cards or (previous_versions and previous_versions != current_versions)),
    }


def _merge_existing_and_new_cards(existing_cards: list[dict[str, Any]], new_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for card in existing_cards:
        key = _card_canonical_paper_id(card)
        if key:
            merged[key] = card
    for card in new_cards:
        key = _card_canonical_paper_id(card)
        if key:
            merged[key] = card
        else:
            merged[f"new:{len(merged)}"] = card
    return list(merged.values())


def _card_canonical_paper_id(card: dict[str, Any]) -> str | None:
    paper = card.get("paper", {})
    value = paper.get("canonical_paper_id")
    return str(value) if value else None


def _pipeline_telemetry(
    *,
    source_health: dict[str, Any],
    dedupe_ms: float,
    classification_ms: float,
    relevance_rejected_count: int,
) -> dict[str, Any]:
    reject_counts: Counter[str] = Counter()
    for payload in source_health.values():
        reject_counts.update(payload.get("relevance_reject_reason_counts", {}))
    return {
        "request_latency_ms": round(sum(float(payload.get("request_latency_ms", 0.0) or 0.0) for payload in source_health.values()), 3),
        "rate_limit_wait_seconds": round(sum(float(payload.get("rate_limit_wait_seconds", 0.0) or 0.0) for payload in source_health.values()), 3),
        "parse_ms": round(sum(float(payload.get("parse_ms", 0.0) or 0.0) for payload in source_health.values()), 3),
        "dedupe_ms": round(dedupe_ms, 3),
        "classification_ms": round(classification_ms, 3),
        "relevance_rejected_count": int(relevance_rejected_count),
        "relevance_reject_reason_counts": dict(reject_counts),
    }


def _attach_pipeline_telemetry(source_health: dict[str, Any], pipeline_telemetry: dict[str, Any]) -> None:
    source_health["periodic_refresh_pipeline"] = {
        "source": "periodic_refresh_pipeline",
        "adapter_version": "research_ingestion.v1",
        "query_set": None,
        "status": "ok",
        "request_count": 0,
        "rate_limit_wait_count": 0,
        "rate_limit_wait_seconds": pipeline_telemetry.get("rate_limit_wait_seconds", 0.0),
        "request_latency_ms": pipeline_telemetry.get("request_latency_ms", 0.0),
        "parse_ms": pipeline_telemetry.get("parse_ms", 0.0),
        "dedupe_ms": pipeline_telemetry.get("dedupe_ms", 0.0),
        "classification_ms": pipeline_telemetry.get("classification_ms", 0.0),
        "success_count": 0,
        "failure_count": 0,
        "http_status_summary": {},
        "http_429_count": 0,
        "parse_error_count": 0,
        "schema_error_count": 0,
        "dedup_ratio": None,
        "new_item_count": 0,
        "candidate_route_counts": {},
        "reject_reason_counts": {},
        "relevance_reject_reason_counts": pipeline_telemetry.get("relevance_reject_reason_counts", {}),
        "manual_review_required_count": 0,
        "request_cache_hit_count": 0,
        "request_cache_miss_count": 0,
        "request_cache_stale_count": 0,
        "unresolved_seed_count": 0,
        "pdf_download_attempt_count": 0,
        "rate_limit_observations": [],
        "missing_api_key_note_ko": None,
        "skipped_source_reason": None,
    }


def _refresh_child_run_id(run_id: str, query_set: str, index: int) -> str:
    safe_query_set = "".join(char if char.isalnum() or char in {"_", ".", "-"} else "_" for char in query_set)
    candidate = f"{run_id}_{safe_query_set}"
    if len(candidate) <= 128:
        return validate_storage_segment(candidate, "run_id")
    suffix = f"q{index + 1}"
    prefix = run_id[: max(1, 127 - len(suffix))]
    return validate_storage_segment(f"{prefix}_{suffix}", "run_id")


def _refresh_collect_args(
    args: argparse.Namespace,
    child_run_id: str,
    query_set: str,
    sources: list[str],
    adapter_registry: dict[str, Any] | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        run_id=child_run_id,
        dry_run=False,
        adapter_registry=adapter_registry,
        request_cache_ttl_days=getattr(args, "request_cache_ttl_days", None),
        sources=",".join(sources),
        query_set=query_set,
        max_results=getattr(args, "max_results", None),
        page_size=getattr(args, "page_size", None),
        offline=False,
    )


def _offline_refresh_health() -> dict[str, Any]:
    return {
        "periodic_refresh": {
            "source": "periodic_refresh",
            "adapter_version": "research_ingestion.v1",
            "query_set": None,
            "status": "skipped",
            "request_count": 0,
            "rate_limit_wait_count": 0,
            "rate_limit_wait_seconds": 0.0,
            "request_latency_ms": 0.0,
            "parse_ms": 0.0,
            "dedupe_ms": 0.0,
            "classification_ms": 0.0,
            "success_count": 0,
            "failure_count": 0,
            "http_status_summary": {},
            "http_429_count": 0,
            "parse_error_count": 0,
            "schema_error_count": 0,
            "dedup_ratio": None,
            "new_item_count": 0,
            "candidate_route_counts": {},
            "reject_reason_counts": {},
            "relevance_reject_reason_counts": {},
            "manual_review_required_count": 0,
            "request_cache_hit_count": 0,
            "request_cache_miss_count": 0,
            "request_cache_stale_count": 0,
            "unresolved_seed_count": 0,
            "pdf_download_attempt_count": 0,
            "rate_limit_observations": [],
            "skipped_source_reason": "--offline 지정으로 refresh network call을 수행하지 않았습니다.",
        }
    }


def _aggregate_refresh_source_health(paths: ProjectPaths, child_runs: list[str]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for child_run in child_runs:
        child_health = read_json(paths.data_dir / "indexes" / f"{child_run}_source_health.json", default={}) or {}
        for source, payload in child_health.items():
            target = aggregate.setdefault(source, _empty_aggregate_source_health(source))
            _merge_refresh_source_payload(target, payload, child_run)
    for payload in aggregate.values():
        _finalize_refresh_source_health(payload)
    return aggregate


def _empty_aggregate_source_health(source: str) -> dict[str, Any]:
    return {
        "source": source,
        "adapter_version": "research_ingestion.v1",
        "query_set": None,
        "status": "planned",
        "request_count": 0,
        "rate_limit_wait_count": 0,
        "rate_limit_wait_seconds": 0.0,
        "request_latency_ms": 0.0,
        "parse_ms": 0.0,
        "dedupe_ms": 0.0,
        "classification_ms": 0.0,
        "success_count": 0,
        "failure_count": 0,
        "http_status_summary": Counter(),
        "http_429_count": 0,
        "parse_error_count": 0,
        "schema_error_count": 0,
        "dedup_ratio": None,
        "new_item_count": 0,
        "candidate_route_counts": {},
        "reject_reason_counts": {},
        "relevance_reject_reason_counts": {},
        "manual_review_required_count": 0,
        "request_cache_hit_count": 0,
        "request_cache_miss_count": 0,
        "request_cache_stale_count": 0,
        "unresolved_seed_count": 0,
        "pdf_download_attempt_count": 0,
        "rate_limit_observations": [],
        "missing_api_key_note_ko": None,
        "skipped_source_reason": None,
        "child_runs": [],
    }


def _merge_refresh_source_payload(target: dict[str, Any], payload: dict[str, Any], child_run: str) -> None:
    target["child_runs"].append(child_run)
    for field in _REFRESH_SOURCE_INT_FIELDS:
        target[field] += int(payload.get(field, 0) or 0)
    for field in _REFRESH_SOURCE_FLOAT_FIELDS:
        target[field] += float(payload.get(field, 0.0) or 0.0)
    target["http_status_summary"].update(payload.get("http_status_summary", {}))
    target["relevance_reject_reason_counts"] = dict(
        Counter(target.get("relevance_reject_reason_counts", {}))
        + Counter(payload.get("relevance_reject_reason_counts", {}))
    )
    target["rate_limit_observations"].extend(payload.get("rate_limit_observations", []))
    target["missing_api_key_note_ko"] = target["missing_api_key_note_ko"] or payload.get("missing_api_key_note_ko")
    target["skipped_source_reason"] = target["skipped_source_reason"] or payload.get("skipped_source_reason")
    if payload.get("last_error_ko"):
        target["last_error_ko"] = payload["last_error_ko"]
    if payload.get("last_raw_snapshot_ref"):
        target["last_raw_snapshot_ref"] = payload["last_raw_snapshot_ref"]


def _finalize_refresh_source_health(payload: dict[str, Any]) -> None:
    payload["http_status_summary"] = dict(payload["http_status_summary"])
    payload["child_runs"] = sorted(set(payload["child_runs"]))
    for field in _REFRESH_SOURCE_FLOAT_FIELDS:
        payload[field] = round(float(payload.get(field, 0.0) or 0.0), 3)
    if payload["failure_count"] and not payload["success_count"]:
        payload["status"] = "failed"
    elif payload["failure_count"]:
        payload["status"] = "partial"
    elif payload["success_count"]:
        payload["status"] = "ok"
    elif payload["request_count"] == 0:
        payload["status"] = "skipped"


def _update_source_health_from_collection(
    health: dict[str, Any],
    accepted_papers: list[dict[str, Any]],
    rejected_papers: list[dict[str, Any]],
) -> None:
    accepted_counts: Counter[str] = Counter()
    manual_review_counts: Counter[str] = Counter()
    reject_reason_counts: dict[str, Counter[str]] = {}

    for paper in accepted_papers:
        for source in _paper_sources(paper):
            accepted_counts[source] += 1
            if paper.get("manual_review_required") or paper.get("collection_relevance", {}).get("manual_review_required"):
                manual_review_counts[source] += 1

    for paper in rejected_papers:
        reason = _collection_reject_reason(paper)
        for source in _paper_sources(paper):
            reject_reason_counts.setdefault(source, Counter())[reason] += 1

    for source, payload in health.items():
        payload["new_item_count"] = int(payload.get("new_item_count", 0) or 0) + accepted_counts[source]
        payload["manual_review_required_count"] = (
            int(payload.get("manual_review_required_count", 0) or 0) + manual_review_counts[source]
        )
        relevance_reject_reason_counts = dict(
            Counter(payload.get("reject_reason_counts", {})) + reject_reason_counts.get(source, Counter())
        )
        payload["reject_reason_counts"] = relevance_reject_reason_counts
        payload["relevance_reject_reason_counts"] = dict(
            Counter(payload.get("relevance_reject_reason_counts", {}))
            + Counter(relevance_reject_reason_counts)
        )


def _update_source_health_from_cards(
    health: dict[str, Any],
    cards: list[dict[str, Any]],
    *,
    replace_new_item_count: bool = False,
) -> None:
    route_counts: dict[str, Counter[str]] = {}
    manual_review_counts: Counter[str] = Counter()
    reject_reason_counts: dict[str, Counter[str]] = {}

    for card in cards:
        classification = card.get("classification", {})
        route = str(classification.get("downstream_route") or "unknown")
        reject_reason = _card_reject_reason(card)
        for source in _card_sources(card):
            route_counts.setdefault(source, Counter())[route] += 1
            if classification.get("manual_review_required"):
                manual_review_counts[source] += 1
            if route == "reject_log":
                reject_reason_counts.setdefault(source, Counter())[reject_reason] += 1

    for source, payload in health.items():
        previous_new_item_count = int(payload.get("new_item_count", 0) or 0)
        observed_route_counts = route_counts.get(source, Counter())
        observed_new_item_count = sum(observed_route_counts.values())
        if replace_new_item_count:
            if previous_new_item_count:
                payload["dedup_ratio"] = _dedup_ratio(previous_new_item_count, observed_new_item_count)
            payload["new_item_count"] = observed_new_item_count
            payload["manual_review_required_count"] = manual_review_counts[source]
            payload["candidate_route_counts"] = dict(observed_route_counts)
            payload["reject_reason_counts"] = dict(reject_reason_counts.get(source, Counter()))
            continue
        payload["new_item_count"] = previous_new_item_count + observed_new_item_count
        payload["manual_review_required_count"] = (
            int(payload.get("manual_review_required_count", 0) or 0) + manual_review_counts[source]
        )
        payload["candidate_route_counts"] = dict(
            Counter(payload.get("candidate_route_counts", {})) + observed_route_counts
        )
        payload["reject_reason_counts"] = dict(
            Counter(payload.get("reject_reason_counts", {})) + reject_reason_counts.get(source, Counter())
        )


def _paper_sources(paper: dict[str, Any]) -> tuple[str, ...]:
    sources: list[str] = []
    source_adapter = paper.get("source_adapter")
    if source_adapter:
        sources.append(str(source_adapter))
    source_adapters = paper.get("source_adapters") or []
    if isinstance(source_adapters, str):
        source_adapters = [source_adapters]
    for source in source_adapters:
        if source:
            sources.append(str(source))
    return tuple(dict.fromkeys(sources))


def _card_sources(card: dict[str, Any]) -> tuple[str, ...]:
    source_paper = {
        "source_adapter": card.get("source", {}).get("source_adapter"),
        "source_adapters": card.get("paper", {}).get("source_adapters", []),
    }
    return _paper_sources(source_paper)


def _collection_reject_reason(paper: dict[str, Any]) -> str:
    assessment = paper.get("collection_relevance", {})
    if assessment.get("exclude_keyword_hits"):
        return "collection_exclude_keyword"
    missing_groups = [
        name
        for name, hits in (assessment.get("required_keyword_group_hits") or {}).items()
        if not hits
    ]
    if missing_groups:
        return "collection_required_keyword_group_missing"
    return str(assessment.get("status") or "collection_relevance_rejected")


def _card_reject_reason(card: dict[str, Any]) -> str:
    classification = card.get("classification", {})
    violations = classification.get("guardrail_violations") or []
    if violations:
        return ";".join(str(value) for value in violations)
    return str(classification.get("classification_reason_ko") or "reject_log")
