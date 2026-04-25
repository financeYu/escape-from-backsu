from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any

from .classify import classify_paper
from .config import ProjectPaths, find_project_root, get_query_set, get_source_config, load_research_config, validate_pdf_policy, validate_policy
from .dedupe import deduplicate_papers
from .discovery.scholar_alert_email import import_alerts_dir
from .discovery.scholar_bibtex import import_bibtex_dir
from .discovery.scholar_citation_export import import_citation_export_dir
from .discovery.scholar_resolution import resolve_seeds, write_unresolved_scholar_seeds
from .discovery.scholar_title_list import parse_title_list_file
from .evidence import generate_evidence_cards
from .persistence import read_json, read_jsonl, store_raw_response, validate_storage_segment, write_json, write_jsonl
from .relevance import apply_collection_relevance_gate
from .reporting import generate_reports
from .request_cache import RequestCache, request_cache_from_config
from .refresh import build_refresh_summary, select_unseen_papers
from .sources.arxiv_adapter import ArxivAdapter
from .sources.crossref_adapter import CrossrefAdapter
from .sources.openalex_adapter import OpenAlexAdapter
from .sources.semantic_scholar_adapter import SemanticScholarAdapter


@dataclass(frozen=True)
class SourcePageFetch:
    response: Any
    cache_status: str
    cache_key: str | None
    request_latency_ms: float
    rate_limit_wait_seconds: float


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = find_project_root(Path.cwd())
    config = load_research_config(root)
    validate_policy(config)
    validate_pdf_policy(config, allow_pdf=args.allow_pdf, confirmed=args.confirm_pdf_policy)
    validate_storage_segment(args.run_id, "run_id")
    paths = ProjectPaths(root)
    args.func(args, config, paths)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research_ingestion")
    _add_pdf_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    _add_run_common(collect)
    _add_collect_common(collect)
    collect.add_argument("--sources", required=True)
    collect.add_argument("--query-set", required=True)
    collect.set_defaults(func=cmd_collect)

    alerts = subparsers.add_parser("import-scholar-alerts")
    _add_run_common(alerts)
    alerts.add_argument("--input-dir", required=True)
    alerts.set_defaults(func=cmd_import_alerts)

    bibtex = subparsers.add_parser("import-scholar-bibtex")
    _add_run_common(bibtex)
    bibtex.add_argument("--input-dir", required=True)
    bibtex.set_defaults(func=cmd_import_bibtex)

    endnote = subparsers.add_parser("import-scholar-endnote")
    _add_run_common(endnote)
    endnote.add_argument("--input-dir", required=True)
    endnote.set_defaults(func=cmd_import_endnote)

    refman = subparsers.add_parser("import-scholar-refman")
    _add_run_common(refman)
    refman.add_argument("--input-dir", required=True)
    refman.set_defaults(func=cmd_import_refman)

    refworks = subparsers.add_parser("import-scholar-refworks")
    _add_run_common(refworks)
    refworks.add_argument("--input-dir", required=True)
    refworks.set_defaults(func=cmd_import_refworks)

    titles = subparsers.add_parser("import-scholar-title-list")
    _add_run_common(titles)
    titles.add_argument("--input-path", required=True)
    titles.set_defaults(func=cmd_import_title_list)

    resolve = subparsers.add_parser("resolve-scholar-seeds")
    _add_run_common(resolve)
    resolve.add_argument("--sources", required=True)
    resolve.set_defaults(func=cmd_resolve_scholar_seeds)

    enrich = subparsers.add_parser("enrich")
    _add_run_common(enrich)
    _add_pdf_options(enrich, set_defaults=False)
    enrich.add_argument("--sources", required=True)
    enrich.add_argument("--input-path", default=None)
    enrich.add_argument("--max-records", type=int, default=None)
    enrich.add_argument("--offline", action="store_true")
    enrich.set_defaults(func=cmd_enrich)

    normalize = subparsers.add_parser("normalize")
    _add_run_common(normalize)
    normalize.set_defaults(func=cmd_normalize)

    classify = subparsers.add_parser("classify")
    _add_run_common(classify)
    classify.set_defaults(func=cmd_classify)

    evidence = subparsers.add_parser("evidence")
    _add_run_common(evidence)
    evidence.set_defaults(func=cmd_evidence)

    report = subparsers.add_parser("report")
    _add_run_common(report)
    report.set_defaults(func=cmd_report)

    run_all = subparsers.add_parser("run-all")
    _add_run_common(run_all)
    _add_collect_common(run_all)
    run_all.add_argument("--sources", required=True)
    run_all.add_argument("--query-set", required=True)
    run_all.add_argument("--enrich-sources", default="", help="Optional enrichment sources, e.g. crossref,semantic_scholar.")
    run_all.add_argument("--enrich-max-records", type=int, default=None)
    run_all.set_defaults(func=cmd_run_all)

    refresh = subparsers.add_parser("refresh")
    _add_run_common(refresh)
    _add_collect_common(refresh)
    refresh.add_argument("--profile", default=None, help="Refresh operating profile, e.g. fast_refresh, full_refresh, diagnostic_refresh, regional_refresh.")
    refresh.add_argument("--sources", default=None, help="Comma-separated metadata sources. Defaults to the selected refresh profile.")
    refresh.add_argument("--query-sets", default=None, help="Comma-separated query sets. Defaults to the selected refresh profile.")
    refresh.add_argument("--include-valuation", action="store_true", help="Explicit opt-in for valuation/fundamental query sets.")
    refresh.set_defaults(func=cmd_refresh)
    return parser


def _add_run_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")


def _add_pdf_options(parser: argparse.ArgumentParser, *, set_defaults: bool = True) -> None:
    default = None if set_defaults else argparse.SUPPRESS
    parser.add_argument("--allow-pdf", dest="allow_pdf", action="store_true", default=default, help="Enable PDF handling only when policy allows it.")
    parser.add_argument("--no-pdf", dest="allow_pdf", action="store_false", default=default, help="Disable PDF fulltext handling. This is the default.")
    parser.add_argument("--confirm-pdf-policy", action="store_true", default=default, help="Explicit confirmation for --allow-pdf.")
    if set_defaults:
        parser.set_defaults(allow_pdf=False, confirm_pdf_policy=False)


def _add_collect_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-results", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=None)
    parser.add_argument("--offline", action="store_true")
    _add_pdf_options(parser, set_defaults=False)


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
        health = _empty_source_health(sources, skipped_reason="--offline 지정으로 network call을 수행하지 않았습니다.")
        for source_health in health.values():
            source_health["query_set"] = args.query_set
        summary = _collection_summary(args, sources, query_set, raw_counts={}, normalized_count=0, plan=plan)
        write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl", [])
        _write_run_metadata(paths, args.run_id, health, summary)
        print("offline mode: network call 없이 빈 collection artifact를 생성했습니다.")
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
    for source_health in health.values():
        source_health["http_status_summary"] = dict(source_health["http_status_summary"])
    papers = [_annotate_collection_lane(paper, args.query_set, query_set, args.run_id) for paper in papers]
    accepted_papers, rejected_papers = apply_collection_relevance_gate(
        papers,
        query_set,
        config.get("queries", {}).get("relevance_defaults", {}),
    )
    _update_source_health_from_collection(health, accepted_papers, rejected_papers)
    summary = _collection_summary(
        args,
        sources,
        query_set,
        raw_counts=dict(raw_counts),
        normalized_count=len(accepted_papers),
        plan=plan,
        relevance_rejected_count=len(rejected_papers),
        relevance_manual_review_count=sum(1 for paper in accepted_papers if paper.get("manual_review_required")),
    )
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl", accepted_papers)
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_rejected_collected_papers.jsonl", rejected_papers)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_collection_relevance.jsonl", _collection_relevance_rows(accepted_papers, rejected_papers))
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

    for query_index, query in enumerate(source_queries):
        source_offset = 0
        page_number = 1
        while source_total < source_limit:
            current_page_size = min(page_size, source_limit - source_total)
            query_id = f"{args.query_set}:{source}:{query_index}:page{page_number}"
            try:
                page_fetch = _fetch_source_page(
                    adapter,
                    source,
                    query,
                    current_page_size,
                    source_offset,
                    page_number,
                    cache=cache,
                )
            except Exception as exc:
                health["request_count"] += 1
                health["failure_count"] += 1
                health["status"] = "failed"
                health["last_error_ko"] = f"요청 실패: {type(exc).__name__}: {_safe_error_message(exc, _redaction_env_vars(config, adapter))}"
                break

            response = page_fetch.response
            _record_fetch_health(health, page_fetch, response)
            if not response.ok:
                snapshot = _store_source_response_snapshot(
                    paths=paths,
                    config=config,
                    adapter=adapter,
                    source=source,
                    run_id=args.run_id,
                    response=response,
                    query_id=query_id,
                    query_set=args.query_set,
                    query=query,
                    page_size=current_page_size,
                    offset=source_offset,
                    page_number=page_number,
                    cache_status=page_fetch.cache_status,
                    cache_key=page_fetch.cache_key,
                )
                health["failure_count"] += 1
                health["status"] = "failed"
                health["last_raw_snapshot_ref"] = snapshot["body_path"]
                if response.status in {403, 429}:
                    health["rate_limit_observations"].append(f"HTTP {response.status} observed for {query_id}")
                if response.status == 429:
                    health["http_429_count"] += 1
                break

            health["success_count"] += 1
            health["status"] = "ok"
            snapshot = _store_source_response_snapshot(
                paths=paths,
                config=config,
                adapter=adapter,
                source=source,
                run_id=args.run_id,
                response=response,
                query_id=query_id,
                query_set=args.query_set,
                query=query,
                page_size=current_page_size,
                offset=source_offset,
                page_number=page_number,
                cache_status=page_fetch.cache_status,
                cache_key=page_fetch.cache_key,
            )
            parse_started = perf_counter()
            parsed = _parse_source_response(adapter, source, response.body, snapshot["body_path"])
            health["parse_ms"] += _elapsed_ms(parse_started)
            raw_count += len(parsed)
            papers.extend(parsed)
            source_total += len(parsed)
            if len(parsed) < current_page_size:
                break
            source_offset += current_page_size
            page_number += 1
            if current_page_size <= 0:
                break
        if source_total >= source_limit:
            break
    health["http_status_summary"] = dict(health["http_status_summary"])
    return {"source": source, "papers": papers, "raw_count": raw_count, "health": health}


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
    cache_lookup = cache.get(
        source=source,
        query=query,
        page_size=page_size,
        offset=offset,
        page_number=page_number,
    ) if cache else None
    if cache_lookup and cache_lookup.response is not None:
        return SourcePageFetch(
            response=cache_lookup.response,
            cache_status=cache_lookup.status,
            cache_key=cache_lookup.cache_key,
            request_latency_ms=0.0,
            rate_limit_wait_seconds=0.0,
        )
    wait_before = _adapter_total_wait_seconds(adapter)
    started = perf_counter()
    if source == "arxiv":
        response = adapter.fetch_search_response(query, start=offset, max_results=page_size)
    elif source == "openalex":
        response = adapter.fetch_search_response(query, page=page_number, per_page=page_size)
    elif source == "crossref":
        response = adapter.fetch_search_response(query, rows=page_size, offset=offset)
    elif source == "semantic_scholar":
        response = adapter.fetch_search_response(query, limit=page_size, offset=offset)
    else:
        raise ValueError(f"지원하지 않는 source입니다: {source}")
    cache_status = cache_lookup.status if cache_lookup else "disabled"
    cache_key = cache_lookup.cache_key if cache_lookup else None
    if cache:
        cache_key = cache.store(
            source=source,
            query=query,
            page_size=page_size,
            offset=offset,
            page_number=page_number,
            response=response,
        )
    return SourcePageFetch(
        response=response,
        cache_status=cache_status,
        cache_key=cache_key,
        request_latency_ms=_elapsed_ms(started),
        rate_limit_wait_seconds=max(0.0, _adapter_total_wait_seconds(adapter) - wait_before),
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


def _adapter_total_wait_seconds(adapter: Any) -> float:
    limiter = getattr(adapter, "_rate_limiter", None)
    return float(getattr(limiter, "total_wait_seconds", 0.0) or 0.0)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000.0, 3)


def _request_metadata(
    adapter: Any,
    url: str,
    query_id: str,
    query_set: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
) -> dict[str, Any]:
    headers = adapter.request_headers() if hasattr(adapter, "request_headers") else {}
    metadata = adapter.request_metadata(url, headers) if hasattr(adapter, "request_metadata") else {"request_url": url, "headers": headers}
    return {
        "query_id": query_id,
        "query_set": query_set,
        "query": query,
        "page_size": page_size,
        "offset": offset,
        "page_number": page_number,
        "adapter_request": metadata,
    }


def _store_source_response_snapshot(
    *,
    paths: ProjectPaths,
    config: dict[str, Any],
    adapter: Any,
    source: str,
    run_id: str,
    response: Any,
    query_id: str,
    query_set: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
    cache_status: str = "disabled",
    cache_key: str | None = None,
) -> dict[str, Any]:
    request_metadata = _request_metadata(adapter, response.url, query_id, query_set, query, page_size, offset, page_number)
    request_metadata["request_cache"] = {
        "status": cache_status,
        "cache_key": cache_key,
        "raw_snapshot_preserved_for_run": True,
    }
    return store_raw_response(
        root=paths.root,
        source=source,
        run_id=run_id,
        response_body=response.body,
        suffix=_raw_suffix(source),
        request_metadata=request_metadata,
        http_status=response.status,
        retry_count=response.retry_count,
        redaction_env_vars=_redaction_env_vars(config, adapter),
    )


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


def _validate_enrichment_sources(sources: list[str], config: dict[str, Any]) -> None:
    approved = {"crossref", "semantic_scholar"}
    unknown = [source for source in sources if source not in approved]
    if unknown:
        raise ValueError(f"enrichment source는 crossref 또는 semantic_scholar만 허용됩니다: {', '.join(unknown)}")
    _validate_sources(sources, config)


def _enrichment_targets(papers: list[dict[str, Any]], sources: list[str], max_records: int | None = None) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    selected = papers if max_records is None else papers[: max(0, max_records)]
    for index, paper in enumerate(selected):
        if "crossref" in sources and paper.get("doi"):
            _append_target(targets, seen, paper, index, "crossref", "doi", paper["doi"])
        if "semantic_scholar" in sources:
            lookup = _semantic_scholar_lookup_id(paper)
            if lookup:
                kind = lookup.split(":", 1)[0].lower() if ":" in lookup else "paper_id"
                _append_target(targets, seen, paper, index, "semantic_scholar", kind, lookup)
    return targets


def _append_target(
    targets: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    paper: dict[str, Any],
    index: int,
    source: str,
    lookup_kind: str,
    lookup_id: str,
) -> None:
    key = (source, lookup_id)
    if key in seen:
        return
    seen.add(key)
    targets.append(
        {
            "target_index": index,
            "source": source,
            "lookup_kind": lookup_kind,
            "lookup_id": lookup_id,
            "canonical_paper_id": paper.get("canonical_paper_id"),
            "title": paper.get("title"),
        }
    )


def _semantic_scholar_lookup_id(paper: dict[str, Any]) -> str | None:
    source_ids = paper.get("source_ids", {})
    semantic_id = paper.get("semantic_scholar_id") or source_ids.get("semantic_scholar_id")
    if semantic_id:
        return str(semantic_id)
    doi = paper.get("doi") or source_ids.get("doi")
    if doi:
        return f"DOI:{doi}"
    arxiv_id = paper.get("arxiv_id") or source_ids.get("arxiv_id")
    if arxiv_id:
        return f"ARXIV:{arxiv_id}"
    return None


def _enrichment_plan(
    args: argparse.Namespace,
    paths: ProjectPaths,
    sources: list[str],
    input_path: Path,
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(target["source"] for target in targets)
    return {
        "run_id": args.run_id,
        "mode": "enrich",
        "selected_sources": sources,
        "input_path": str(input_path),
        "max_records": args.max_records,
        "offline": bool(getattr(args, "offline", False)),
        "dry_run": bool(args.dry_run),
        "target_count_by_source": dict(counts),
        "targets": targets,
        "outputs": {
            "enriched_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_enriched_papers.jsonl"),
            "merged_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_papers.jsonl"),
            "enrichment_index_jsonl": str(paths.data_dir / "indexes" / f"{args.run_id}_enrichment_index.jsonl"),
        },
        "guardrails_ko": [
            "Crossref와 Semantic Scholar는 metadata enrichment 용도이며 fulltext source가 아닙니다.",
            "citationCount 또는 Crossref score는 alpha evidence로 사용하지 않습니다.",
            "PDF fulltext는 다운로드하지 않습니다.",
            "score 채택, backtest, valuation scoring은 수행하지 않습니다.",
        ],
    }


def _fetch_enrichment_response(adapter: Any, target: dict[str, Any]) -> Any:
    if target["source"] == "crossref":
        return adapter.fetch_doi_response(target["lookup_id"])
    if target["source"] == "semantic_scholar":
        return adapter.fetch_paper_response(target["lookup_id"])
    raise ValueError(f"지원하지 않는 enrichment source입니다: {target['source']}")


def _parse_enrichment_response(adapter: Any, source: str, body: str, raw_snapshot_ref: str) -> list[dict[str, Any]]:
    payload = json.loads(body)
    if source == "crossref":
        return adapter.parse_works_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    if source == "semantic_scholar":
        return [adapter.parse_paper_json(payload, raw_snapshot_ref=raw_snapshot_ref)]
    raise ValueError(f"지원하지 않는 enrichment source입니다: {source}")


def _enrichment_summary(
    args: argparse.Namespace,
    sources: list[str],
    input_path: Path,
    targets: list[dict[str, Any]],
    *,
    raw_counts: dict[str, int],
    enriched_count: int,
    merged_count: int,
    plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": args.run_id,
        "timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "enrich",
        "selected_sources": sources,
        "input_path": str(input_path),
        "target_count": len(targets),
        "target_count_by_source": dict(Counter(target["source"] for target in targets)),
        "enriched_records_by_source": raw_counts,
        "enriched_records_written": enriched_count,
        "merged_paper_count": merged_count,
        "pdf_fulltext_used": False,
        "plan": plan,
    }


def cmd_import_alerts(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = import_alerts_dir(args.input_dir, run_id=args.run_id)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar alert seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_import_bibtex(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = import_bibtex_dir(args.input_dir, run_id=args.run_id)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar BibTeX seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_import_endnote(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = import_citation_export_dir(args.input_dir, export_format="endnote", run_id=args.run_id)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar EndNote seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_import_refman(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = import_citation_export_dir(args.input_dir, export_format="refman", run_id=args.run_id)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar RefMan seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_import_refworks(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = import_citation_export_dir(args.input_dir, export_format="refworks", run_id=args.run_id)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar RefWorks seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_import_title_list(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = parse_title_list_file(args.input_path)
    if args.dry_run:
        print(f"would import {len(seeds)} Scholar title-list seeds")
        return
    write_jsonl(_seeds_path(paths, args.run_id), seeds)


def cmd_resolve_scholar_seeds(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    seeds = read_jsonl(_seeds_path(paths, args.run_id))
    papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    candidates_by_source = {source: [paper for paper in papers if source in paper.get("source_adapters", [])] for source in _split_csv(args.sources)}
    resolved = resolve_seeds(seeds, candidates_by_source)
    if args.dry_run:
        print(f"would resolve {len(seeds)} Scholar seeds via {args.sources}")
        return
    write_jsonl(_seeds_path(paths, args.run_id), resolved)
    write_unresolved_scholar_seeds(paths.data_dir / "discovery" / "google_scholar" / "unresolved_scholar_seeds.jsonl", resolved)


def cmd_enrich(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    sources = _split_csv(args.sources)
    _validate_enrichment_sources(sources, config)
    input_path = Path(args.input_path) if args.input_path else _normalized_papers_path_for_run(paths, args.run_id)
    papers = read_jsonl(input_path)
    targets = _enrichment_targets(papers, sources, max_records=args.max_records)
    plan = _enrichment_plan(args, paths, sources, input_path, targets)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if args.offline:
        health = _empty_source_health(sources, skipped_reason="--offline 지정으로 enrichment network call을 수행하지 않았습니다.")
        summary = _enrichment_summary(args, sources, input_path, targets, raw_counts={}, enriched_count=0, merged_count=len(papers), plan=plan)
        _write_enrichment_metadata(paths, args.run_id, health, summary)
        write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_enriched_papers.jsonl", [])
        write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_enrichment_index.jsonl", [])
        print("offline mode: enrichment network call 없이 metadata artifact를 생성했습니다.")
        return

    health = _new_source_health(sources, config)
    enrichment_records: list[dict[str, Any]] = []
    enrichment_index: list[dict[str, Any]] = []
    raw_counts: Counter[str] = Counter()

    for target in targets:
        source = target["source"]
        adapter = _adapter_for_source(source, config)
        skipped = _missing_key_skip_reason(source, adapter)
        if skipped:
            health[source]["status"] = "skipped"
            health[source]["skipped_source_reason"] = skipped
            enrichment_index.append({**target, "status": "skipped", "notes_ko": skipped})
            continue
        try:
            response = _fetch_enrichment_response(adapter, target)
        except Exception as exc:
            health[source]["request_count"] += 1
            health[source]["failure_count"] += 1
            health[source]["status"] = "failed"
            health[source]["last_error_ko"] = f"enrichment 요청 실패: {type(exc).__name__}: {_safe_error_message(exc, _redaction_env_vars(config, adapter))}"
            enrichment_index.append({**target, "status": "failed", "notes_ko": health[source]["last_error_ko"]})
            continue

        health[source]["request_count"] += 1
        health[source]["http_status_summary"][str(response.status or "unknown")] += 1
        if not response.ok:
            snapshot = _store_source_response_snapshot(
                paths=paths,
                config=config,
                adapter=adapter,
                source=source,
                run_id=args.run_id,
                response=response,
                query_id=f"enrich:{source}:{target['lookup_kind']}:{target['target_index']}",
                query_set="enrichment",
                query=target["lookup_id"],
                page_size=1,
                offset=0,
                page_number=1,
            )
            health[source]["failure_count"] += 1
            health[source]["status"] = "failed"
            health[source]["last_raw_snapshot_ref"] = snapshot["body_path"]
            if response.status in {403, 429}:
                health[source]["rate_limit_observations"].append(f"HTTP {response.status} observed for enrichment {target['lookup_id']}")
            if response.status == 429:
                health[source]["http_429_count"] += 1
            enrichment_index.append({**target, "status": "failed", "http_status": response.status, "raw_snapshot_ref": snapshot["body_path"], "notes_ko": "approved metadata API enrichment 응답이 성공 상태가 아닙니다."})
            continue

        snapshot = _store_source_response_snapshot(
            paths=paths,
            config=config,
            adapter=adapter,
            source=source,
            run_id=args.run_id,
            response=response,
            query_id=f"enrich:{source}:{target['lookup_kind']}:{target['target_index']}",
            query_set="enrichment",
            query=target["lookup_id"],
            page_size=1,
            offset=0,
            page_number=1,
        )
        parsed = _parse_enrichment_response(adapter, source, response.body, snapshot["body_path"])
        if parsed:
            enrichment_records.extend(parsed)
            raw_counts[source] += len(parsed)
            health[source]["success_count"] += 1
            health[source]["status"] = "ok"
            enrichment_index.append({**target, "status": "matched", "http_status": response.status, "raw_snapshot_ref": snapshot["body_path"]})
        else:
            health[source]["failure_count"] += 1
            health[source]["status"] = "partial"
            enrichment_index.append({**target, "status": "no_parseable_metadata", "http_status": response.status, "raw_snapshot_ref": snapshot["body_path"]})

    for source_health in health.values():
        source_health["http_status_summary"] = dict(source_health["http_status_summary"])
    merged = deduplicate_papers([*papers, *enrichment_records])
    summary = _enrichment_summary(
        args,
        sources,
        input_path,
        targets,
        raw_counts=dict(raw_counts),
        enriched_count=len(enrichment_records),
        merged_count=len(merged),
        plan=plan,
    )
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_enriched_papers.jsonl", enrichment_records)
    _write_normalized_papers(paths, args.run_id, merged)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_enrichment_index.jsonl", enrichment_index)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_dedupe_index.jsonl", [_dedupe_index_row(paper) for paper in merged])
    _write_enrichment_metadata(paths, args.run_id, health, summary)


def cmd_normalize(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    collected = read_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl")
    papers = deduplicate_papers(collected)
    if args.dry_run:
        print(f"would write {len(papers)} deduplicated normalized papers")
        return
    _write_normalized_papers(paths, args.run_id, papers)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_dedupe_index.jsonl", [_dedupe_index_row(paper) for paper in papers])


def cmd_classify(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = _read_normalized_papers_for_run(paths, args.run_id)
    classifications = [classify_paper(paper, config["classification"], config["policy"]) for paper in papers]
    if args.dry_run:
        print(f"would classify {len(classifications)} papers")
        return
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl", classifications)
    write_jsonl(
        paths.data_dir / "indexes" / f"{args.run_id}_classified_papers.jsonl",
        [{"paper": paper, "classification": classification} for paper, classification in zip(papers, classifications, strict=True)],
    )


def cmd_evidence(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = _read_normalized_papers_for_run(paths, args.run_id)
    classifications = read_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl")
    cards = generate_evidence_cards(papers, classifications, args.run_id)
    if args.dry_run:
        print(f"would generate {len(cards)} EvidenceCards")
        return
    _write_evidence_outputs(paths, cards, run_id=args.run_id, management_lane=_run_management_lane(paths, args.run_id))
    write_jsonl(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl", cards)


def cmd_report(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = _read_normalized_papers_for_run(paths, args.run_id)
    cards = read_jsonl(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl")
    if not cards:
        cards = read_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl")
    seeds = read_jsonl(_seeds_path(paths, args.run_id))
    source_health = read_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health.json", default={})
    collection_summary = read_json(paths.data_dir / "indexes" / f"{args.run_id}_collection_summary.json", default={})
    enrichment_summary = read_json(paths.data_dir / "indexes" / f"{args.run_id}_enrichment_summary.json", default={})
    if args.dry_run:
        print("would generate Korean research ingestion reports")
        return
    generate_reports(
        output_dir=paths.reports_dir,
        run_id=args.run_id,
        papers=papers,
        evidence_cards=cards,
        scholar_seeds=seeds,
        source_health=source_health,
        collection_summary=collection_summary,
        enrichment_summary=enrichment_summary,
    )


def cmd_refresh(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    sources = _refresh_sources(args, config)
    _validate_sources(sources, config)
    query_sets = _refresh_query_sets(args, config)
    _validate_refresh_query_allowed_sources(sources, query_sets, config)
    selected_profile = _refresh_profile_name(args, config)
    setattr(args, "request_cache_ttl_days", _refresh_profile_config(args, config).get("request_cache_ttl_days"))
    plan = _refresh_plan(args, config, paths, sources, query_sets)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    existing_papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    if args.offline:
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
        return

    child_runs: list[str] = []
    candidate_papers: list[dict[str, Any]] = []
    raw_counts: Counter[str] = Counter()
    relevance_rejected_count = 0
    relevance_manual_review_count = 0
    adapter_registry = _source_adapter_registry(config, sources)

    for index, query_set in enumerate(query_sets):
        child_run_id = _refresh_child_run_id(args.run_id, query_set, index)
        child_runs.append(child_run_id)
        child_args = _refresh_collect_args(args, child_run_id, query_set, sources, adapter_registry)
        cmd_collect(child_args, config, paths)
        candidate_papers.extend(read_jsonl(paths.data_dir / "normalized" / f"{child_run_id}_collected_papers.jsonl"))
        child_summary = read_json(paths.data_dir / "indexes" / f"{child_run_id}_collection_summary.json", default={}) or {}
        raw_counts.update(child_summary.get("raw_records_collected_by_source", {}))
        relevance_rejected_count += int(child_summary.get("records_rejected_by_relevance", 0) or 0)
        relevance_manual_review_count += int(child_summary.get("records_manual_review_by_relevance", 0) or 0)

    dedupe_started = perf_counter()
    deduped_candidates = deduplicate_papers(candidate_papers)
    new_papers = select_unseen_papers(existing_papers, deduped_candidates)
    refreshed_papers = deduplicate_papers([*existing_papers, *new_papers])
    dedupe_ms = _elapsed_ms(dedupe_started)
    classification_started = perf_counter()
    new_classifications = [classify_paper(paper, config["classification"], config["policy"]) for paper in new_papers]
    classification_ms = _elapsed_ms(classification_started)
    new_cards = generate_evidence_cards(new_papers, new_classifications, args.run_id)
    existing_cards = read_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl")
    existing_version_state = _existing_evidence_version_state(paths, config)
    if existing_version_state["regenerate_existing_cards"]:
        classification_started = perf_counter()
        classifications = [classify_paper(paper, config["classification"], config["policy"]) for paper in refreshed_papers]
        classification_ms += _elapsed_ms(classification_started)
        cards = generate_evidence_cards(refreshed_papers, classifications, args.run_id)
        classifications_output = classifications
        classified_papers_output = [
            {"paper": paper, "classification": classification}
            for paper, classification in zip(refreshed_papers, classifications, strict=True)
        ]
    else:
        cards = _merge_existing_and_new_cards(existing_cards, new_cards)
        classifications_output = new_classifications
        classified_papers_output = [
            {"paper": paper, "classification": classification}
            for paper, classification in zip(new_papers, new_classifications, strict=True)
        ]
    source_health = _aggregate_refresh_source_health(paths, child_runs)
    _update_source_health_from_cards(source_health, new_cards, replace_new_item_count=True)
    pipeline_telemetry = _pipeline_telemetry(
        source_health=source_health,
        dedupe_ms=dedupe_ms,
        classification_ms=classification_ms,
        relevance_rejected_count=relevance_rejected_count,
    )
    _attach_pipeline_telemetry(source_health, pipeline_telemetry)
    current_versions = _current_policy_versions(config)
    if existing_version_state["missing_existing_cards"]:
        classification_scope = "full_corpus_due_to_missing_existing_cards"
    elif existing_version_state["regenerate_existing_cards"]:
        classification_scope = "full_corpus_due_to_policy_or_schema_version_change"
    else:
        classification_scope = "new_papers_only"
    incremental_pipeline = {
        "classification_scope": classification_scope,
        "new_papers_classified": len(new_classifications),
        "new_evidence_cards_generated": len(new_cards),
        "existing_evidence_cards_reused": 0 if existing_version_state["regenerate_existing_cards"] else len(existing_cards),
        "existing_evidence_cards_regenerated": bool(existing_version_state["regenerate_existing_cards"]),
        "missing_existing_cards": bool(existing_version_state["missing_existing_cards"]),
        "policy_version": current_versions["policy_version"],
        "evidence_schema_version": current_versions["evidence_schema_version"],
        "previous_policy_version": existing_version_state["previous_versions"].get("policy_version"),
        "previous_evidence_schema_version": existing_version_state["previous_versions"].get("evidence_schema_version"),
    }
    summary = build_refresh_summary(
        run_id=args.run_id,
        selected_sources=sources,
        selected_query_sets=query_sets,
        existing_count=len(existing_papers),
        candidate_count=len(deduped_candidates),
        new_count=len(new_papers),
        refreshed_count=len(refreshed_papers),
        child_runs=child_runs,
        raw_counts=raw_counts,
        relevance_rejected_count=relevance_rejected_count,
        relevance_manual_review_count=relevance_manual_review_count,
        plan=plan,
        selected_profile=selected_profile,
        pipeline_telemetry=pipeline_telemetry,
        incremental_pipeline=incremental_pipeline,
    )

    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_refresh_new_papers.jsonl", new_papers)
    _write_new_only_outputs(paths, new_papers, new_cards, read_jsonl(_seeds_path(paths, args.run_id)))
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", refreshed_papers)
    _write_lane_paper_outputs(paths, refreshed_papers)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_dedupe_index.jsonl", [_dedupe_index_row(paper) for paper in refreshed_papers])
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl", classifications_output)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_new_classifications.jsonl", new_classifications)
    write_jsonl(
        paths.data_dir / "indexes" / f"{args.run_id}_classified_papers.jsonl",
        classified_papers_output,
    )
    _write_evidence_outputs(paths, cards, run_id=args.run_id)
    write_jsonl(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl", cards)
    write_json(paths.data_dir / "indexes" / "evidence_policy_version.json", current_versions)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_refresh_summary.json", summary)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_collection_summary.json", summary)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health.json", source_health)
    write_json(paths.data_dir / "indexes" / f"{args.run_id}_source_health_report.json", source_health)
    write_json(paths.data_dir / "indexes" / "source_health_report.json", source_health)
    generate_reports(
        output_dir=paths.reports_dir,
        run_id=args.run_id,
        papers=refreshed_papers,
        evidence_cards=cards,
        scholar_seeds=read_jsonl(_seeds_path(paths, args.run_id)),
        source_health=source_health,
        collection_summary=summary,
    )
    print(f"periodic refresh complete: new_papers={len(new_papers)}, refreshed_papers={len(refreshed_papers)}")


def cmd_run_all(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    if args.dry_run:
        print(json.dumps(_run_all_plan(args, config, paths), ensure_ascii=False, indent=2))
        return
    cmd_collect(args, config, paths)
    cmd_normalize(args, config, paths)
    if _split_csv(getattr(args, "enrich_sources", "")):
        cmd_enrich(_enrich_args_from_run_all(args, paths), config, paths)
    cmd_classify(args, config, paths)
    cmd_evidence(args, config, paths)
    cmd_report(args, config, paths)


def _run_all_plan(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> dict[str, Any]:
    sources = _split_csv(args.sources)
    _validate_sources(sources, config)
    query_set = get_query_set(config, args.query_set)
    _validate_query_allowed_sources(sources, query_set)
    collect_plan = _collection_plan(args, config, paths, sources, query_set)
    enrich_sources = _split_csv(getattr(args, "enrich_sources", ""))
    enrich_plan = None
    if enrich_sources:
        _validate_enrichment_sources(enrich_sources, config)
        enrich_plan = {
            "mode": "enrich_after_normalize",
            "selected_sources": enrich_sources,
            "max_records": args.enrich_max_records,
            "input_path": str(paths.data_dir / "normalized" / f"{args.run_id}_papers.jsonl"),
            "guardrails_ko": [
                "run-all dry-run에서는 collect 결과가 아직 없으므로 enrichment target 수는 normalize 이후 확정됩니다.",
                "Crossref와 Semantic Scholar는 metadata enrichment 용도이며 fulltext source가 아닙니다.",
            ],
        }
    return {
        "run_id": args.run_id,
        "mode": "run_all",
        "collect": collect_plan,
        "enrich": enrich_plan,
        "pipeline": ["collect", "normalize", *(["enrich"] if enrich_plan else []), "classify", "evidence", "report"],
        "guardrails_ko": [
            "run-all은 score 구현, backtest, adoption decision을 수행하지 않습니다.",
            "PDF fulltext는 기본 비활성화입니다.",
            "Google Scholar direct request는 수행하지 않습니다.",
        ],
    }


def _parallel_source_collection_enabled(config: dict[str, Any], sources: list[str]) -> bool:
    if len(sources) <= 1:
        return False
    policy = _refresh_policy(config)
    if policy.get("source_parallelism_enabled") is False:
        return False
    return bool(policy.get("source_parallelism", 1) and int(policy.get("source_parallelism", 1)) > 1)


def _refresh_policy(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("policy", {}).get("refresh_policy", {})


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
        "outputs": {
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
        },
        "guardrails_ko": [
            "refresh는 기존 papers.jsonl을 보존하고 새로 발견된 논문만 병합합니다.",
            "PDF fulltext 수집은 기본 비활성화입니다.",
            "Google Scholar live request는 수행하지 않습니다.",
            "EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.",
            "backtest, adoption decision, valuation scoring은 수행하지 않습니다.",
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


def _existing_evidence_version_state(paths: ProjectPaths, config: dict[str, Any]) -> dict[str, Any]:
    previous_versions = read_json(paths.data_dir / "indexes" / "evidence_policy_version.json", default={}) or {}
    current_versions = _current_policy_versions(config)
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
            target = aggregate.setdefault(
                source,
                {
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
                },
            )
            target["child_runs"].append(child_run)
            target["request_count"] += int(payload.get("request_count", 0) or 0)
            target["rate_limit_wait_count"] += int(payload.get("rate_limit_wait_count", 0) or 0)
            target["rate_limit_wait_seconds"] += float(payload.get("rate_limit_wait_seconds", 0.0) or 0.0)
            target["request_latency_ms"] += float(payload.get("request_latency_ms", 0.0) or 0.0)
            target["parse_ms"] += float(payload.get("parse_ms", 0.0) or 0.0)
            target["dedupe_ms"] += float(payload.get("dedupe_ms", 0.0) or 0.0)
            target["classification_ms"] += float(payload.get("classification_ms", 0.0) or 0.0)
            target["success_count"] += int(payload.get("success_count", 0) or 0)
            target["failure_count"] += int(payload.get("failure_count", 0) or 0)
            target["http_429_count"] += int(payload.get("http_429_count", 0) or 0)
            target["parse_error_count"] += int(payload.get("parse_error_count", 0) or 0)
            target["schema_error_count"] += int(payload.get("schema_error_count", 0) or 0)
            target["new_item_count"] += int(payload.get("new_item_count", 0) or 0)
            target["manual_review_required_count"] += int(payload.get("manual_review_required_count", 0) or 0)
            target["request_cache_hit_count"] += int(payload.get("request_cache_hit_count", 0) or 0)
            target["request_cache_miss_count"] += int(payload.get("request_cache_miss_count", 0) or 0)
            target["request_cache_stale_count"] += int(payload.get("request_cache_stale_count", 0) or 0)
            target["unresolved_seed_count"] += int(payload.get("unresolved_seed_count", 0) or 0)
            target["pdf_download_attempt_count"] += int(payload.get("pdf_download_attempt_count", 0) or 0)
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
    for payload in aggregate.values():
        payload["http_status_summary"] = dict(payload["http_status_summary"])
        payload["child_runs"] = sorted(set(payload["child_runs"]))
        for field in ["rate_limit_wait_seconds", "request_latency_ms", "parse_ms", "dedupe_ms", "classification_ms"]:
            payload[field] = round(float(payload.get(field, 0.0) or 0.0), 3)
        if payload["failure_count"] and not payload["success_count"]:
            payload["status"] = "failed"
        elif payload["failure_count"]:
            payload["status"] = "partial"
        elif payload["success_count"]:
            payload["status"] = "ok"
        elif payload["request_count"] == 0:
            payload["status"] = "skipped"
    return aggregate


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


def _dedup_ratio(collected_count: int, new_item_count: int) -> float:
    if collected_count <= 0:
        return 0.0
    ratio = 1.0 - (new_item_count / collected_count)
    return max(0.0, min(1.0, ratio))


def _enrich_args_from_run_all(args: argparse.Namespace, paths: ProjectPaths) -> argparse.Namespace:
    return argparse.Namespace(
        run_id=args.run_id,
        dry_run=False,
        allow_pdf=getattr(args, "allow_pdf", False),
        confirm_pdf_policy=getattr(args, "confirm_pdf_policy", False),
        sources=args.enrich_sources,
        input_path=None,
        max_records=args.enrich_max_records,
        offline=getattr(args, "offline", False),
    )


def _adapter_for_source(source: str, config: dict[str, Any], adapter_registry: dict[str, Any] | None = None) -> Any:
    if adapter_registry is not None and source in adapter_registry:
        return adapter_registry[source]
    if source == "arxiv":
        return ArxivAdapter(get_source_config(config, "arxiv"))
    if source == "openalex":
        return OpenAlexAdapter(get_source_config(config, "openalex"))
    if source == "crossref":
        return CrossrefAdapter(get_source_config(config, "crossref"))
    if source == "semantic_scholar":
        return SemanticScholarAdapter(get_source_config(config, "semantic_scholar"))
    raise ValueError(f"승인되지 않은 research metadata source입니다: {source}")


def _source_adapter_registry(config: dict[str, Any], sources: list[str]) -> dict[str, Any]:
    return {source: _adapter_for_source(source, config) for source in sorted(set(sources))}


def _validate_sources(sources: list[str], config: dict[str, Any]) -> None:
    approved = {"arxiv", "openalex", "crossref", "semantic_scholar"}
    unknown = [source for source in sources if source not in approved]
    if unknown:
        raise ValueError(f"승인되지 않은 source입니다: {', '.join(unknown)}. 사용 가능: {', '.join(sorted(approved))}")
    disabled = [source for source in sources if not config["sources"]["sources"].get(source, {}).get("enabled", False)]
    if disabled:
        raise ValueError(f"config에서 비활성화된 source입니다: {', '.join(disabled)}")


def _validate_query_allowed_sources(sources: list[str], query_set: dict[str, Any]) -> None:
    allowed = [str(source) for source in query_set.get("allowed_sources", []) if str(source).strip()]
    if not allowed:
        return
    disallowed = [source for source in sources if source not in allowed]
    if disallowed:
        raise ValueError(
            "query-set allowed_sources 밖의 source입니다: "
            f"{', '.join(disallowed)}. 사용 가능: {', '.join(sorted(allowed))}"
        )


def _collection_plan(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    sources: list[str],
    query_set: dict[str, Any],
) -> dict[str, Any]:
    planned_sources = []
    adapter_registry = getattr(args, "adapter_registry", None)
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
        "exclude_keywords": query_set.get("exclude_keywords", []),
        "required_keyword_groups": query_set.get("required_keyword_groups", []),
        "relevance_defaults": config.get("queries", {}).get("relevance_defaults", {}),
        "planned_sources": planned_sources,
        "offline": bool(getattr(args, "offline", False)),
        "dry_run": bool(args.dry_run),
        "outputs": {
            "collected_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl"),
            "normalized_papers_jsonl": str(paths.data_dir / "normalized" / f"{args.run_id}_papers.jsonl"),
            "lane_papers_jsonl": str(paths.data_dir / "normalized" / f"{query_set.get('management_lane')}_papers.jsonl") if query_set.get("management_lane") else None,
            "evidence_cards_jsonl": str(paths.data_dir / "evidence" / f"{args.run_id}_evidence_cards.jsonl"),
            "lane_evidence_jsonl": str(paths.data_dir / "evidence" / f"{query_set.get('management_lane')}_items.jsonl") if query_set.get("management_lane") else None,
            "reports_dir": str(paths.reports_dir),
        },
        "guardrails_ko": [
            "PDF fulltext 수집은 기본 비활성화입니다.",
            "Google Scholar live request는 수행하지 않습니다.",
            "EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.",
            "backtest, adoption decision, valuation scoring은 수행하지 않습니다.",
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


def _missing_key_note(source: str, adapter: Any) -> str | None:
    if source == "openalex" and getattr(adapter, "api_key_env_var", None) and not os.environ.get(adapter.api_key_env_var):
        if adapter.config.get("anonymous_allowed", False):
            return "OPENALEX_API_KEY가 없어 limited anonymous/demo mode로 실행합니다."
        return "OPENALEX_API_KEY가 없어 OpenAlex live 수집을 실행할 수 없습니다."
    if source == "semantic_scholar" and getattr(adapter, "api_key_env_var", None) and not os.environ.get(adapter.api_key_env_var):
        if adapter.config.get("public_without_key_allowed", True):
            return "SEMANTIC_SCHOLAR_API_KEY가 없어 public mode로 실행합니다."
        return "SEMANTIC_SCHOLAR_API_KEY가 없어 실행할 수 없습니다."
    if source == "crossref" and getattr(adapter, "polite_email_env_var", None) and not os.environ.get(adapter.polite_email_env_var):
        return "CROSSREF_MAILTO가 없어 기본 User-Agent로 실행합니다. 가능하면 polite email을 설정하세요."
    return None


def _missing_key_skip_reason(source: str, adapter: Any) -> str | None:
    note = _missing_key_note(source, adapter)
    if not note:
        return None
    if "실행할 수 없습니다" in note:
        return note
    return None


def _new_source_health(
    sources: list[str],
    config: dict[str, Any],
    adapter_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    health: dict[str, Any] = {}
    for source in sources:
        adapter = _adapter_for_source(source, config, adapter_registry=adapter_registry)
        health[source] = {
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
            "missing_api_key_note_ko": _missing_key_note(source, adapter),
            "skipped_source_reason": None,
        }
    return health


def _empty_source_health(sources: list[str], skipped_reason: str) -> dict[str, Any]:
    return {
        source: {
            "source": source,
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
            "missing_api_key_note_ko": None,
            "skipped_source_reason": skipped_reason,
        }
        for source in sources
    }


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


def _raw_suffix(source: str) -> str:
    return ".xml" if source == "arxiv" else ".json"


def _redaction_env_vars(config: dict[str, Any], adapter: Any) -> list[str]:
    values = list(config["sources"].get("redaction", {}).get("redact_env_vars", []))
    for name in [
        getattr(adapter, "api_key_env_var", None),
        getattr(adapter, "mailto_env_var", None),
        getattr(adapter, "polite_email_env_var", None),
        getattr(adapter, "plus_api_token_env_var", None),
    ]:
        if name and name not in values:
            values.append(name)
    return values


def _safe_error_message(exc: Exception, redaction_env_vars: list[str] | None = None) -> str:
    message = str(exc)
    for name in [
        "OPENALEX_API_KEY",
        "OPENALEX_MAILTO",
        "SEMANTIC_SCHOLAR_API_KEY",
        "CROSSREF_MAILTO",
        "CROSSREF_PLUS_API_TOKEN",
        *(redaction_env_vars or []),
    ]:
        value = os.environ.get(name)
        if value:
            message = message.replace(value, "[REDACTED]")
    return message


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


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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
