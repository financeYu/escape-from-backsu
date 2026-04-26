from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from .config import ProjectPaths
from .dedupe import deduplicate_papers
from .persistence import read_jsonl, write_jsonl
from .cli_common import (
    _adapter_total_wait_seconds,
    _adapter_for_source,
    _elapsed_ms,
    _empty_source_health,
    _missing_key_skip_reason,
    _new_source_health,
    _redaction_env_vars,
    _safe_error_message,
    _split_csv,
    _store_source_response_snapshot,
    _validate_sources,
)
from .cli_outputs import (
    _dedupe_index_row,
    _normalized_papers_path_for_run,
    _write_enrichment_metadata,
    _write_normalized_papers,
)


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


def _parse_semantic_scholar_batch_response(adapter: Any, body: str, raw_snapshot_ref: str) -> list[dict[str, Any]]:
    payload = json.loads(body)
    if not isinstance(payload, list):
        return []
    if hasattr(adapter, "parse_batch_json"):
        return adapter.parse_batch_json(payload, raw_snapshot_ref=raw_snapshot_ref)
    return [
        adapter.parse_paper_json(item, raw_snapshot_ref=raw_snapshot_ref)
        for item in payload
        if isinstance(item, dict) and item.get("title")
    ]


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


def cmd_enrich(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    *,
    fetch_response: Callable[[Any, dict[str, Any]], Any] | None = None,
) -> None:
    use_default_fetch_response = fetch_response is None or fetch_response is _fetch_enrichment_response
    if fetch_response is None:
        fetch_response = _fetch_enrichment_response
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

    target_loop = targets
    if use_default_fetch_response and "semantic_scholar" in sources:
        batch_targets = [target for target in targets if target["source"] == "semantic_scholar"]
        if batch_targets:
            batch_records, batch_index, batch_counts = _enrich_semantic_scholar_batches(
                args=args,
                config=config,
                paths=paths,
                targets=batch_targets,
                health=health,
            )
            enrichment_records.extend(batch_records)
            enrichment_index.extend(batch_index)
            raw_counts.update(batch_counts)
            target_loop = [target for target in targets if target["source"] != "semantic_scholar"]

    for target in target_loop:
        source = target["source"]
        adapter = _adapter_for_source(source, config)
        skipped = _missing_key_skip_reason(source, adapter)
        if skipped:
            health[source]["status"] = "skipped"
            health[source]["skipped_source_reason"] = skipped
            enrichment_index.append({**target, "status": "skipped", "notes_ko": skipped})
            continue
        try:
            response = fetch_response(adapter, target)
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


def _enrich_semantic_scholar_batches(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    targets: list[dict[str, Any]],
    health: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    source = "semantic_scholar"
    adapter = _adapter_for_source(source, config)
    records: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    raw_counts: Counter[str] = Counter()
    skipped = _missing_key_skip_reason(source, adapter)
    if skipped:
        health[source]["status"] = "skipped"
        health[source]["skipped_source_reason"] = skipped
        return (
            records,
            [{**target, "status": "skipped", "notes_ko": skipped} for target in targets],
            raw_counts,
        )

    batch_size = max(1, int(getattr(adapter, "config", {}).get("batch_max_ids", 100) or 100))
    for batch_number, batch in enumerate(_chunks(targets, batch_size), start=1):
        lookup_ids = [str(target["lookup_id"]) for target in batch]
        wait_before = _adapter_total_wait_seconds(adapter)
        started = perf_counter()
        try:
            response = adapter.fetch_batch_response(lookup_ids)
        except Exception as exc:
            health[source]["request_count"] += 1
            health[source]["failure_count"] += 1
            health[source]["status"] = "failed"
            health[source]["last_error_ko"] = f"semantic_scholar batch enrichment 요청 실패: {type(exc).__name__}: {_safe_error_message(exc, _redaction_env_vars(config, adapter))}"
            index_rows.extend({**target, "status": "failed", "notes_ko": health[source]["last_error_ko"]} for target in batch)
            continue

        health[source]["request_count"] += 1
        health[source]["request_latency_ms"] += _elapsed_ms(started)
        rate_wait = max(0.0, _adapter_total_wait_seconds(adapter) - wait_before)
        health[source]["rate_limit_wait_seconds"] += rate_wait
        if rate_wait > 0:
            health[source]["rate_limit_wait_count"] += 1
        health[source]["http_status_summary"][str(response.status or "unknown")] += 1
        query_id = f"enrich_batch:{source}:batch{batch_number}"
        snapshot = _store_source_response_snapshot(
            paths=paths,
            config=config,
            adapter=adapter,
            source=source,
            run_id=args.run_id,
            response=response,
            query_id=query_id,
            query_set="enrichment",
            query=",".join(lookup_ids),
            page_size=len(batch),
            offset=(batch_number - 1) * batch_size,
            page_number=batch_number,
        )
        if not response.ok:
            health[source]["failure_count"] += 1
            health[source]["status"] = "failed"
            health[source]["last_raw_snapshot_ref"] = snapshot["body_path"]
            if response.status in {403, 429}:
                health[source]["rate_limit_observations"].append(f"HTTP {response.status} observed for {query_id}")
            if response.status == 429:
                health[source]["http_429_count"] += 1
            index_rows.extend(
                {
                    **target,
                    "status": "failed",
                    "http_status": response.status,
                    "raw_snapshot_ref": snapshot["body_path"],
                    "notes_ko": "approved metadata API batch enrichment 응답이 성공 상태가 아닙니다.",
                }
                for target in batch
            )
            continue

        parsed = _parse_semantic_scholar_batch_response(adapter, response.body, snapshot["body_path"])
        if parsed:
            records.extend(parsed)
            raw_counts[source] += len(parsed)
            health[source]["success_count"] += 1
            health[source]["status"] = "ok"
            index_rows.extend(
                {
                    **target,
                    "status": "batch_submitted",
                    "http_status": response.status,
                    "raw_snapshot_ref": snapshot["body_path"],
                }
                for target in batch
            )
        else:
            health[source]["failure_count"] += 1
            health[source]["status"] = "partial"
            index_rows.extend(
                {
                    **target,
                    "status": "no_parseable_metadata",
                    "http_status": response.status,
                    "raw_snapshot_ref": snapshot["body_path"],
                }
                for target in batch
            )
    return records, index_rows, raw_counts


def _chunks(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


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
