from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
import json
from time import perf_counter
from typing import Any

from .config import ProjectPaths, get_query_set
from .license_policy import annotate_license_policy
from .persistence import write_jsonl
from .relevance import apply_collection_relevance_gate
from .request_cache import RequestCache, request_cache_from_config
from .cli_common import (
    SourcePageFetch,
    _adapter_for_source,
    _adapter_total_wait_seconds,
    _elapsed_ms,
    _empty_source_health,
    _missing_key_note,
    _missing_key_skip_reason,
    _new_source_health,
    _redaction_env_vars,
    _refresh_policy,
    _safe_error_message,
    _split_csv,
    _store_source_response_snapshot,
    _validate_query_allowed_sources,
    _validate_sources,
)
from .cli_outputs import _write_run_metadata


def cmd_collect(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    sources = _split_csv(args.sources)
    _validate_sources(sources, config)
    query_set = get_query_set(config, args.query_set)
    _validate_query_allowed_sources(sources, query_set)
    plan = _collection_plan(args, config, paths, sources, query_set)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if args.offline:
        _write_offline_collection(args, paths, sources, query_set, plan)
        return

    papers: list[dict[str, Any]] = []
    raw_counts: Counter[str] = Counter()
    adapter_registry = getattr(args, "adapter_registry", None)
    health = _new_source_health(sources, config, adapter_registry=adapter_registry)
    for source_health in health.values():
        source_health["query_set"] = args.query_set
    source_results = _collect_sources(args, config, paths, sources, query_set, adapter_registry=adapter_registry)
    for result in source_results:
        source = result["source"]
        health[source] = result["health"]
        raw_counts[source] += int(result["raw_count"])
        papers.extend(result["papers"])
    license_policy = config.get("policy", {}).get("license_policy", {})
    papers = [
        annotate_license_policy(
            _annotate_collection_lane(paper, args.query_set, query_set, args.run_id),
            license_policy,
        )
        for paper in papers
    ]
    accepted_papers, rejected_papers = apply_collection_relevance_gate(
        papers,
        query_set,
        config.get("queries", {}).get("relevance_defaults", {}),
    )
    _write_collection_result(
        args,
        paths,
        sources,
        query_set,
        plan=plan,
        health=health,
        raw_counts=dict(raw_counts),
        accepted_papers=accepted_papers,
        rejected_papers=rejected_papers,
    )


def _write_offline_collection(
    args: argparse.Namespace,
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    health = _empty_source_health(sources, skipped_reason="--offline 지정으로 network call을 수행하지 않았습니다.")
    for source_health in health.values():
        source_health["query_set"] = args.query_set
    summary = _collection_summary(args, sources, query_set, raw_counts={}, normalized_count=0, plan=plan)
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl", [])
    _write_run_metadata(paths, args.run_id, health, summary)
    print("offline mode: network call 없이 빈 collection artifact를 생성했습니다.")


def _write_collection_result(
    args: argparse.Namespace,
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
    *,
    plan: dict[str, Any],
    health: dict[str, Any],
    raw_counts: dict[str, int],
    accepted_papers: list[dict[str, Any]],
    rejected_papers: list[dict[str, Any]],
) -> None:
    _update_source_health_from_collection(health, accepted_papers, rejected_papers)
    for source_health in health.values():
        source_health["http_status_summary"] = dict(source_health["http_status_summary"])
    summary = _collection_summary(
        args,
        sources,
        query_set,
        raw_counts=raw_counts,
        normalized_count=len(accepted_papers),
        plan=plan,
        relevance_rejected_count=len(rejected_papers),
        relevance_manual_review_count=sum(1 for paper in accepted_papers if paper.get("manual_review_required")),
    )
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl", accepted_papers)
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_rejected_collected_papers.jsonl", rejected_papers)
    write_jsonl(
        paths.data_dir / "indexes" / f"{args.run_id}_collection_relevance.jsonl",
        _collection_relevance_rows(accepted_papers, rejected_papers),
    )
    _write_run_metadata(paths, args.run_id, health, summary)


def _collect_sources(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
    *,
    adapter_registry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if _parallel_source_collection_enabled(config, sources):
        max_workers = min(len(sources), max(1, int(_refresh_policy(config).get("source_parallelism", len(sources)))))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_collect_source, args, config, paths, source, query_set, adapter_registry)
                for source in sources
            ]
            return [future.result() for future in as_completed(futures)]
    return [
        _collect_source(args, config, paths, source, query_set, adapter_registry)
        for source in sources
    ]


def _collect_source(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    source: str,
    query_set: dict[str, Any],
    adapter_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapter = _adapter_for_source(source, config, adapter_registry=adapter_registry)
    health = _new_source_health([source], config, adapter_registry=adapter_registry)[source]
    health["query_set"] = args.query_set
    papers: list[dict[str, Any]] = []
    raw_count = 0
    source_limit = _source_max_results(args, query_set, source, adapter)
    page_size = _source_page_size(args, query_set, source, adapter)
    source_queries = _queries_for_source(query_set, source)
    cache = request_cache_from_config(
        root=paths.root,
        config=config,
        query_set=_query_set_with_runtime_cache_ttl(args, query_set),
        redaction_env_vars=_redaction_env_vars(config, adapter),
    )
    source_total = 0
    skipped = _missing_key_skip_reason(source, adapter)
    if skipped:
        health["status"] = "skipped"
        health["skipped_source_reason"] = skipped
        return {"source": source, "papers": papers, "raw_count": raw_count, "health": health}
    papers, raw_count = _collect_source_pages(
        args=args,
        config=config,
        paths=paths,
        adapter=adapter,
        source=source,
        source_queries=source_queries,
        source_limit=source_limit,
        page_size=page_size,
        cache=cache,
        health=health,
    )
    health["http_status_summary"] = dict(health["http_status_summary"])
    return {"source": source, "papers": papers, "raw_count": raw_count, "health": health}


def _collect_source_pages(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    adapter: Any,
    source: str,
    source_queries: list[str],
    source_limit: int,
    page_size: int,
    cache: RequestCache | None,
    health: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    papers: list[dict[str, Any]] = []
    raw_count = 0
    source_total = 0
    for query_index, query in enumerate(source_queries):
        source_offset = 0
        page_number = 1
        while source_total < source_limit:
            current_page_size = min(page_size, source_limit - source_total)
            parsed, should_continue = _collect_source_page(
                args=args,
                config=config,
                paths=paths,
                adapter=adapter,
                source=source,
                query=query,
                query_index=query_index,
                page_number=page_number,
                page_size=current_page_size,
                offset=source_offset,
                cache=cache,
                health=health,
            )
            raw_count += len(parsed)
            papers.extend(parsed)
            source_total += len(parsed)
            if not should_continue:
                break
            source_offset += current_page_size
            page_number += 1
        if source_total >= source_limit:
            break
    return papers, raw_count


def _collect_source_page(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    adapter: Any,
    source: str,
    query: str,
    query_index: int,
    page_number: int,
    page_size: int,
    offset: int,
    cache: RequestCache | None,
    health: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    query_id = f"{args.query_set}:{source}:{query_index}:page{page_number}"
    try:
        page_fetch = _fetch_source_page(adapter, source, query, page_size, offset, page_number, cache=cache)
    except Exception as exc:
        _record_collect_request_exception(health, config, adapter, exc)
        return [], False
    response = page_fetch.response
    _record_fetch_health(health, page_fetch, response)
    if not response.ok:
        _record_collect_http_failure(
            args, config, paths, adapter, source, query, query_id,
            page_size, offset, page_number, page_fetch, health,
        )
        return [], False
    parsed = _parse_collect_success(
        args, config, paths, adapter, source, query, query_id,
        page_size, offset, page_number, page_fetch, health,
    )
    return parsed, bool(page_size > 0 and len(parsed) >= page_size)


def _record_collect_request_exception(
    health: dict[str, Any],
    config: dict[str, Any],
    adapter: Any,
    exc: Exception,
) -> None:
    health["request_count"] += 1
    health["failure_count"] += 1
    health["status"] = "failed"
    health["last_error_ko"] = (
        f"요청 실패: {type(exc).__name__}: {_safe_error_message(exc, _redaction_env_vars(config, adapter))}"
    )


def _record_collect_http_failure(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    adapter: Any,
    source: str,
    query: str,
    query_id: str,
    page_size: int,
    offset: int,
    page_number: int,
    page_fetch: SourcePageFetch,
    health: dict[str, Any],
) -> None:
    snapshot = _store_collection_snapshot(
        args=args,
        config=config,
        paths=paths,
        adapter=adapter,
        source=source,
        query=query,
        query_id=query_id,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
        page_fetch=page_fetch,
    )
    response = page_fetch.response
    health["failure_count"] += 1
    health["status"] = "failed"
    health["last_raw_snapshot_ref"] = snapshot["body_path"]
    if response.status in {403, 429}:
        health["rate_limit_observations"].append(f"HTTP {response.status} observed for {query_id}")
    if response.status == 429:
        health["http_429_count"] += 1


def _parse_collect_success(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    adapter: Any,
    source: str,
    query: str,
    query_id: str,
    page_size: int,
    offset: int,
    page_number: int,
    page_fetch: SourcePageFetch,
    health: dict[str, Any],
) -> list[dict[str, Any]]:
    health["success_count"] += 1
    health["status"] = "ok"
    snapshot = _store_collection_snapshot(
        args=args,
        config=config,
        paths=paths,
        adapter=adapter,
        source=source,
        query=query,
        query_id=query_id,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
        page_fetch=page_fetch,
    )
    parse_started = perf_counter()
    parsed = _parse_source_response(adapter, source, page_fetch.response.body, snapshot["body_path"])
    health["parse_ms"] += _elapsed_ms(parse_started)
    return parsed


def _store_collection_snapshot(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    adapter: Any,
    source: str,
    query: str,
    query_id: str,
    page_size: int,
    offset: int,
    page_number: int,
    page_fetch: SourcePageFetch,
) -> dict[str, str]:
    return _store_source_response_snapshot(
        paths=paths,
        config=config,
        adapter=adapter,
        source=source,
        run_id=args.run_id,
        response=page_fetch.response,
        query_id=query_id,
        query_set=args.query_set,
        query=query,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
        cache_status=page_fetch.cache_status,
        cache_key=page_fetch.cache_key,
    )


def _query_set_with_runtime_cache_ttl(args: argparse.Namespace, query_set: dict[str, Any]) -> dict[str, Any]:
    ttl_days = getattr(args, "request_cache_ttl_days", None)
    if ttl_days is None:
        return query_set
    patched = dict(query_set)
    patched["refresh_cadence_days"] = int(ttl_days)
    return patched


def _fetch_source_page(
    adapter: Any,
    source: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
    *,
    cache: RequestCache | None = None,
) -> SourcePageFetch:
    cache_lookup = _request_cache_lookup(cache, source, query, page_size, offset, page_number)
    if cache_lookup and cache_lookup.response is not None:
        return _cached_source_page_fetch(cache_lookup)
    wait_before = _adapter_total_wait_seconds(adapter)
    started = perf_counter()
    response = _fetch_source_response(adapter, source, query, page_size, offset, page_number)
    cache_status = cache_lookup.status if cache_lookup else "disabled"
    cache_key = cache_lookup.cache_key if cache_lookup else None
    cache_key = _store_request_cache_response(cache, source, query, page_size, offset, page_number, response, cache_key)
    return SourcePageFetch(
        response=response,
        cache_status=cache_status,
        cache_key=cache_key,
        request_latency_ms=_elapsed_ms(started),
        rate_limit_wait_seconds=max(0.0, _adapter_total_wait_seconds(adapter) - wait_before),
    )


def _request_cache_lookup(
    cache: RequestCache | None,
    source: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
) -> Any:
    if cache is None:
        return None
    return cache.get(
        source=source,
        query=query,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
    )


def _cached_source_page_fetch(cache_lookup: Any) -> SourcePageFetch:
    return SourcePageFetch(
        response=cache_lookup.response,
        cache_status=cache_lookup.status,
        cache_key=cache_lookup.cache_key,
        request_latency_ms=0.0,
        rate_limit_wait_seconds=0.0,
    )


def _fetch_source_response(
    adapter: Any,
    source: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
) -> Any:
    if source == "arxiv":
        return adapter.fetch_search_response(query, start=offset, max_results=page_size)
    if source == "openalex":
        return adapter.fetch_search_response(query, page=page_number, per_page=page_size)
    if source == "crossref":
        return adapter.fetch_search_response(query, rows=page_size, offset=offset)
    if source == "semantic_scholar":
        return adapter.fetch_search_response(query, limit=page_size, offset=offset)
    if source == "nber":
        return adapter.fetch_search_response(query, limit=page_size, offset=offset)
    raise ValueError(f"지원하지 않는 source입니다: {source}")


def _store_request_cache_response(
    cache: RequestCache | None,
    source: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
    response: Any,
    cache_key: str | None,
) -> str | None:
    if cache is None:
        return cache_key
    return cache.store(
        source=source,
        query=query,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
        response=response,
    )


def _parse_source_response(adapter: Any, source: str, body: str, raw_snapshot_ref: str) -> list[dict[str, Any]]:
    if source == "arxiv":
        return adapter.parse_atom(body, raw_snapshot_ref=raw_snapshot_ref)
    payload = json.loads(body)
    if source == "openalex":
        return adapter.parse_works_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    if source == "crossref":
        return adapter.parse_works_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    if source == "semantic_scholar":
        return adapter.parse_search_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    if source == "nber":
        return adapter.parse_dump_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    raise ValueError(f"지원하지 않는 source입니다: {source}")


def _record_fetch_health(health: dict[str, Any], page_fetch: SourcePageFetch, response: Any) -> None:
    health["request_count"] += 1
    health["http_status_summary"][str(response.status or "unknown")] += 1
    health["request_latency_ms"] += page_fetch.request_latency_ms
    health["rate_limit_wait_seconds"] += page_fetch.rate_limit_wait_seconds
    if page_fetch.rate_limit_wait_seconds > 0:
        health["rate_limit_wait_count"] += 1
    cache_status = page_fetch.cache_status
    if cache_status == "hit":
        health["request_cache_hit_count"] += 1
    elif cache_status == "stale":
        health["request_cache_stale_count"] += 1
        health["request_cache_miss_count"] += 1
    elif cache_status in {"miss", "disabled"}:
        health["request_cache_miss_count"] += int(cache_status == "miss")


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


def _parallel_source_collection_enabled(config: dict[str, Any], sources: list[str]) -> bool:
    if len(sources) <= 1:
        return False
    policy = _refresh_policy(config)
    if policy.get("source_parallelism_enabled") is False:
        return False
    return bool(policy.get("source_parallelism", 1) and int(policy.get("source_parallelism", 1)) > 1)


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


def _collection_plan(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
) -> dict[str, Any]:
    adapter_registry = getattr(args, "adapter_registry", None)
    return {
        "run_id": args.run_id,
        "query_set": args.query_set,
        "query_set_name": query_set.get("name") or args.query_set,
        "branch_hint": query_set.get("branch_hint"),
        "downstream_route": query_set.get("downstream_route"),
        "management_lane": query_set.get("management_lane"),
        "allowed_sources": query_set.get("allowed_sources", []),
        "region_scope": query_set.get("region_scope"),
        "required_input_policy": query_set.get("required_input_policy"),
        "refresh_cadence_days": query_set.get("refresh_cadence_days"),
        "precision_mode": query_set.get("precision_mode"),
        "notes": query_set.get("notes"),
        "request_budget": estimate_collection_request_budget(
            args=args,
            config=config,
            sources=sources,
            query_set=query_set,
            adapter_registry=adapter_registry,
        ),
        "exclude_keywords": query_set.get("exclude_keywords", []),
        "required_keyword_groups": query_set.get("required_keyword_groups", []),
        "relevance_defaults": config.get("queries", {}).get("relevance_defaults", {}),
        "planned_sources": _planned_collection_sources(args, config, paths, sources, query_set, adapter_registry),
        "offline": bool(getattr(args, "offline", False)),
        "dry_run": bool(args.dry_run),
        "outputs": _collection_output_paths(args, paths, query_set),
        "guardrails_ko": _collection_guardrails(),
    }


def _planned_collection_sources(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
    adapter_registry: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    planned_sources = []
    for source in sources:
        adapter = _adapter_for_source(source, config, adapter_registry=adapter_registry)
        planned_sources.append(
            {
                "source": source,
                "queries": _queries_for_source(query_set, source),
                "max_results": _source_max_results(args, query_set, source, adapter),
                "page_size": _source_page_size(args, query_set, source, adapter),
                "missing_key_note_ko": _missing_key_note(source, adapter),
                "request_cache": _request_cache_plan(config, query_set),
                "output_raw_dir": str(paths.data_dir / "raw" / source / args.run_id),
            }
        )
    return planned_sources


def _collection_output_paths(args: argparse.Namespace, paths: ProjectPaths, query_set: dict[str, Any]) -> dict[str, str | None]:
    management_lane = query_set.get("management_lane")
    return {
        "collected_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl"),
        "normalized_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_papers.jsonl"),
        "lane_papers_jsonl": str(paths.data_dir / "normalized" / f"{management_lane}_papers.jsonl") if management_lane else None,
        "evidence_cards_jsonl": str(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl"),
        "lane_evidence_jsonl": str(paths.data_dir / "evidence" / f"{management_lane}_items.jsonl") if management_lane else None,
        "reports_dir": str(paths.reports_dir),
    }


def _collection_guardrails() -> list[str]:
    return [
        "PDF fulltext 수집은 기본 비활성화입니다.",
        "비상업 연구 목적에서는 CC BY-NC 계열 license도 metadata/abstract 후보 수집을 허용합니다.",
        "Google Scholar live request는 수행하지 않습니다.",
        "EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.",
        "backtest, adoption decision, valuation scoring은 수행하지 않습니다.",
    ]


def estimate_collection_request_budget(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    sources: list[str],
    query_set: dict[str, Any],
    adapter_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_budgets = []
    for source in sources:
        adapter = _adapter_for_source(source, config, adapter_registry=adapter_registry)
        source_limit = _source_max_results(args, query_set, source, adapter)
        page_size = _source_page_size(args, query_set, source, adapter)
        queries = _queries_for_source(query_set, source)
        pages_per_query_cap = _ceil_div(source_limit, page_size) if source_limit else 0
        full_page_request_count = pages_per_query_cap
        worst_case_request_count = pages_per_query_cap * len(queries)
        min_interval = float(getattr(adapter, "config", {}).get("min_interval_seconds", 0.0) or 0.0)
        source_budgets.append(
            {
                "source": source,
                "query_count": len(queries),
                "max_results": source_limit,
                "page_size": page_size,
                "full_page_request_count": full_page_request_count,
                "worst_case_request_count": worst_case_request_count,
                "min_interval_seconds": min_interval,
                "estimated_min_rate_limit_wait_seconds": round(max(0, worst_case_request_count - 1) * min_interval, 3),
            }
        )
    return {
        "source_count": len(sources),
        "full_page_request_count": sum(item["full_page_request_count"] for item in source_budgets),
        "worst_case_request_count": sum(item["worst_case_request_count"] for item in source_budgets),
        "estimated_min_rate_limit_wait_seconds": round(
            sum(item["estimated_min_rate_limit_wait_seconds"] for item in source_budgets),
            3,
        ),
        "request_cache_enabled": bool(config.get("policy", {}).get("request_cache", {}).get("enabled", False)),
        "sources": source_budgets,
        "notes_ko": [
            "full_page_request_count는 첫 query가 page를 충분히 채우는 경우의 최소 상한입니다.",
            "worst_case_request_count는 query별 page cap을 합산한 보수적 상한입니다.",
            "실제 요청 수는 source 응답 건수, cache hit, early stop에 따라 더 작을 수 있습니다.",
        ],
    }


def _queries_for_source(query_set: dict[str, Any], source: str) -> list[str]:
    overrides = query_set.get("source_overrides", {}).get(source, {})
    if overrides.get("queries"):
        return [str(query) for query in overrides["queries"] if str(query).strip()]
    if query_set.get("queries"):
        return [str(query) for query in query_set["queries"] if str(query).strip()]
    keywords = [str(keyword) for keyword in query_set.get("keywords", []) if str(keyword).strip()]
    if keywords:
        return [" ".join(keywords)]
    raise ValueError("query-set에 queries 또는 keywords가 없습니다.")


def _request_cache_plan(config: dict[str, Any], query_set: dict[str, Any]) -> dict[str, Any]:
    policy = config.get("policy", {})
    metadata = policy.get("policy_metadata", {})
    cache_policy = policy.get("request_cache", {})
    return {
        "enabled": bool(cache_policy.get("enabled", False)),
        "policy_version": str(metadata.get("policy_version") or cache_policy.get("policy_version") or "research_policy.v1"),
        "ttl_days": int(query_set.get("refresh_cadence_days") or cache_policy.get("default_ttl_days") or _refresh_policy(config).get("interval_days") or 14),
        "cache_key_fields": ["source", "query", "page_size", "offset", "page_number", "policy_version"],
    }


def _ceil_div(value: int, divisor: int) -> int:
    if divisor <= 0:
        return 0
    return (value + divisor - 1) // divisor


def _source_max_results(args: argparse.Namespace, query_set: dict[str, Any], source: str, adapter: Any) -> int:
    if args.max_results is not None:
        return max(0, int(args.max_results))
    overrides = query_set.get("source_overrides", {}).get(source, {})
    if overrides.get("max_results") is not None:
        return max(0, int(overrides["max_results"]))
    if query_set.get("max_results") is not None:
        return max(0, int(query_set["max_results"]))
    return int(
        getattr(adapter, "default_max_results", None)
        or getattr(adapter, "default_per_page", None)
        or getattr(adapter, "default_rows", None)
        or getattr(adapter, "default_limit", 25)
    )


def _source_page_size(args: argparse.Namespace, query_set: dict[str, Any], source: str, adapter: Any) -> int:
    if args.page_size is not None:
        return max(1, int(args.page_size))
    overrides = query_set.get("source_overrides", {}).get(source, {})
    if overrides.get("page_size") is not None:
        return max(1, int(overrides["page_size"]))
    return int(
        getattr(adapter, "default_max_results", None)
        or getattr(adapter, "default_per_page", None)
        or getattr(adapter, "default_rows", None)
        or getattr(adapter, "default_limit", 25)
    )


def _collection_summary(
    args: argparse.Namespace,
    sources: list[str],
    query_set: dict[str, Any],
    *,
    raw_counts: dict[str, int],
    normalized_count: int,
    plan: dict[str, Any],
    relevance_rejected_count: int = 0,
    relevance_manual_review_count: int = 0,
) -> dict[str, Any]:
    return {
        "run_id": args.run_id,
        "timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "selected_sources": sources,
        "selected_query_set": args.query_set,
        "selected_branch_hint": query_set.get("branch_hint"),
        "selected_management_lane": query_set.get("management_lane"),
        "query_set_description_ko": query_set.get("description_ko"),
        "raw_records_collected_by_source": raw_counts,
        "normalized_records_written": normalized_count,
        "records_rejected_by_relevance": relevance_rejected_count,
        "records_manual_review_by_relevance": relevance_manual_review_count,
        "pdf_fulltext_used": False,
        "plan": plan,
    }


def _collection_relevance_rows(accepted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for paper in [*accepted, *rejected]:
        assessment = paper.get("collection_relevance", {})
        rows.append(
            {
                "canonical_paper_id": paper.get("canonical_paper_id"),
                "title": paper.get("title"),
                "source_adapters": paper.get("source_adapters", []),
                "research_query_sets": paper.get("research_query_sets", []),
                "research_management_lanes": paper.get("research_management_lanes", []),
                "status": assessment.get("status"),
                "positive_keyword_hits": assessment.get("positive_keyword_hits", []),
                "exclude_keyword_hits": assessment.get("exclude_keyword_hits", []),
                "required_keyword_group_hits": assessment.get("required_keyword_group_hits", {}),
                "abstract_available": assessment.get("abstract_available"),
                "manual_review_required": assessment.get("manual_review_required"),
                "reason_ko": assessment.get("reason_ko"),
            }
        )
    return rows
