from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from typing import Any

from .classify import classify_paper
from .config import ProjectPaths, get_query_set
from .dedupe import deduplicate_papers
from .evidence import generate_evidence_cards
from .persistence import read_json, read_jsonl, write_jsonl
from .reporting import generate_reports
from .cli_collect import cmd_collect, _collection_plan
from .cli_common import _split_csv, _validate_query_allowed_sources, _validate_sources
from .cli_enrich import _enrich_args_from_run_all, _validate_enrichment_sources, cmd_enrich
from .cli_outputs import (
    _dedupe_index_row,
    _read_normalized_papers_for_run,
    _run_management_lane,
    _seeds_path,
    _write_evidence_outputs,
    _write_normalized_papers,
)


def cmd_normalize(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    collected = read_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl")
    papers = deduplicate_papers(collected)
    if args.dry_run:
        print(f"would write {len(papers)} deduplicated normalized papers")
        return
    _write_normalized_papers(paths, args.run_id, papers)
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_dedupe_index.jsonl", [_dedupe_index_row(paper) for paper in papers])


def cmd_classify(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    *,
    classify_func: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> None:
    if classify_func is None:
        classify_func = classify_paper
    papers = _read_normalized_papers_for_run(paths, args.run_id)
    classifications = [classify_func(paper, config["classification"], config["policy"]) for paper in papers]
    if args.dry_run:
        print(f"would classify {len(classifications)} papers")
        return
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl", classifications)
    write_jsonl(
        paths.data_dir / "indexes" / f"{args.run_id}_classified_papers.jsonl",
        [{"paper": paper, "classification": classification} for paper, classification in zip(papers, classifications, strict=True)],
    )


def cmd_evidence(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    *,
    generate_cards_func: Callable[[list[dict[str, Any]], list[dict[str, Any]], str], list[dict[str, Any]]] | None = None,
) -> None:
    if generate_cards_func is None:
        generate_cards_func = generate_evidence_cards
    papers = _read_normalized_papers_for_run(paths, args.run_id)
    classifications = read_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl")
    cards = generate_cards_func(papers, classifications, args.run_id)
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


def cmd_run_all(
    args: argparse.Namespace,
    config: dict[str, Any],
    paths: ProjectPaths,
    *,
    collect_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    normalize_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    enrich_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    classify_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    evidence_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
    report_command: Callable[[argparse.Namespace, dict[str, Any], ProjectPaths], None] | None = None,
) -> None:
    if collect_command is None:
        collect_command = cmd_collect
    if normalize_command is None:
        normalize_command = cmd_normalize
    if enrich_command is None:
        enrich_command = cmd_enrich
    if classify_command is None:
        classify_command = cmd_classify
    if evidence_command is None:
        evidence_command = cmd_evidence
    if report_command is None:
        report_command = cmd_report
    if args.dry_run:
        print(json.dumps(_run_all_plan(args, config, paths), ensure_ascii=False, indent=2))
        return
    collect_command(args, config, paths)
    normalize_command(args, config, paths)
    if _split_csv(getattr(args, "enrich_sources", "")):
        enrich_command(_enrich_args_from_run_all(args, paths), config, paths)
    classify_command(args, config, paths)
    evidence_command(args, config, paths)
    report_command(args, config, paths)


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
