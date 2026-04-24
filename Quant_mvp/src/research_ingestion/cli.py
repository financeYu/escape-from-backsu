from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .classify import classify_paper
from .config import ProjectPaths, find_project_root, get_query_set, load_research_config, validate_pdf_policy, validate_policy
from .dedupe import deduplicate_papers
from .discovery.scholar_alert_email import import_alerts_dir
from .discovery.scholar_bibtex import import_bibtex_dir
from .discovery.scholar_resolution import resolve_seeds, write_unresolved_scholar_seeds
from .discovery.scholar_title_list import parse_title_list_file
from .evidence import generate_evidence_cards
from .persistence import read_jsonl, store_raw_response, write_jsonl
from .reporting import generate_reports
from .sources.arxiv_adapter import ArxivAdapter
from .sources.openalex_adapter import OpenAlexAdapter


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = find_project_root(Path.cwd())
    config = load_research_config(root)
    validate_policy(config)
    validate_pdf_policy(config, allow_pdf=args.allow_pdf, confirmed=args.confirm_pdf_policy)
    paths = ProjectPaths(root)
    args.func(args, config, paths)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research_ingestion")
    parser.add_argument("--allow-pdf", action="store_true", help="Enable PDF handling only when policy allows it.")
    parser.add_argument("--confirm-pdf-policy", action="store_true", help="Explicit confirmation for --allow-pdf.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    _add_run_common(collect)
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

    titles = subparsers.add_parser("import-scholar-title-list")
    _add_run_common(titles)
    titles.add_argument("--input-path", required=True)
    titles.set_defaults(func=cmd_import_title_list)

    resolve = subparsers.add_parser("resolve-scholar-seeds")
    _add_run_common(resolve)
    resolve.add_argument("--sources", required=True)
    resolve.set_defaults(func=cmd_resolve_scholar_seeds)

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
    run_all.add_argument("--sources", required=True)
    run_all.add_argument("--query-set", required=True)
    run_all.set_defaults(func=cmd_run_all)
    return parser


def _add_run_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")


def cmd_collect(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    sources = _split_csv(args.sources)
    query_set = get_query_set(config, args.query_set)
    if args.dry_run:
        print(json.dumps({"planned_sources": sources, "query_set": args.query_set, "queries": query_set["queries"]}, ensure_ascii=False, indent=2))
        return
    papers: list[dict[str, Any]] = []
    for source in sources:
        adapter = _adapter_for_source(source, config)
        for query in query_set["queries"]:
            body = adapter.fetch_search(query)
            snapshot = store_raw_response(
                root=paths.root,
                source=source,
                run_id=args.run_id,
                response_body=body,
                suffix=".json" if source == "openalex" else ".xml",
                request_metadata={"query": query, "source": source},
                http_status=None,
                retry_count=0,
                redaction_env_vars=config["sources"].get("redaction", {}).get("redact_env_vars", []),
            )
            payload = json.loads(body) if source == "openalex" else body
            if source == "arxiv":
                papers.extend(adapter.parse_atom(payload, raw_snapshot_ref=snapshot["body_path"]))
            elif source == "openalex":
                papers.extend(adapter.parse_works_json(payload, raw_snapshot_ref=snapshot["body_path"]))
    write_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl", papers)


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


def cmd_normalize(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    collected = read_jsonl(paths.data_dir / "normalized" / f"{args.run_id}_collected_papers.jsonl")
    papers = deduplicate_papers(collected)
    if args.dry_run:
        print(f"would write {len(papers)} deduplicated normalized papers")
        return
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", papers)


def cmd_classify(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    classifications = [classify_paper(paper, config["classification"], config["policy"]) for paper in papers]
    if args.dry_run:
        print(f"would classify {len(classifications)} papers")
        return
    write_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl", classifications)


def cmd_evidence(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    classifications = read_jsonl(paths.data_dir / "indexes" / f"{args.run_id}_classifications.jsonl")
    cards = generate_evidence_cards(papers, classifications, args.run_id)
    if args.dry_run:
        print(f"would generate {len(cards)} EvidenceCards")
        return
    _write_evidence_outputs(paths, cards)


def cmd_report(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    papers = read_jsonl(paths.data_dir / "normalized" / "papers.jsonl")
    cards = read_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl")
    seeds = read_jsonl(_seeds_path(paths, args.run_id))
    if args.dry_run:
        print("would generate Korean research ingestion reports")
        return
    generate_reports(output_dir=paths.reports_dir, run_id=args.run_id, papers=papers, evidence_cards=cards, scholar_seeds=seeds)


def cmd_run_all(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    cmd_collect(args, config, paths)
    if args.dry_run:
        return
    cmd_normalize(args, config, paths)
    cmd_classify(args, config, paths)
    cmd_evidence(args, config, paths)
    cmd_report(args, config, paths)


def _adapter_for_source(source: str, config: dict[str, Any]) -> Any:
    if source == "arxiv":
        return ArxivAdapter(config["sources"]["sources"]["arxiv"])
    if source == "openalex":
        return OpenAlexAdapter(config["sources"]["sources"]["openalex"])
    raise ValueError(f"CLI collect MVP currently supports arxiv and openalex only: {source}")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _seeds_path(paths: ProjectPaths, run_id: str) -> Path:
    return paths.data_dir / "discovery" / "google_scholar" / f"{run_id}_seeds.jsonl"


def _write_evidence_outputs(paths: ProjectPaths, cards: list[dict[str, Any]]) -> None:
    evidence_dir = paths.data_dir / "evidence"
    write_jsonl(evidence_dir / "evidence_cards.jsonl", cards)
    write_jsonl(evidence_dir / "technical_candidates.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "technical_score_architect"])
    write_jsonl(evidence_dir / "valuation_candidates.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "valuation_agent_handoff"])
    write_jsonl(evidence_dir / "hybrid_review_required.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "hybrid_split_required"])
    write_jsonl(evidence_dir / "diagnostic_items.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "diagnostic_backlog"])
    write_jsonl(evidence_dir / "reject_log.jsonl", [card for card in cards if card["classification"]["downstream_route"] == "reject_log"])
