from __future__ import annotations

import argparse
from typing import Any

from .config import ProjectPaths
from .discovery.scholar_alert_email import import_alerts_dir
from .discovery.scholar_bibtex import import_bibtex_dir
from .discovery.scholar_citation_export import import_citation_export_dir
from .discovery.scholar_resolution import resolve_seeds, write_unresolved_scholar_seeds
from .discovery.scholar_title_list import parse_title_list_file
from .persistence import read_jsonl, write_jsonl
from .cli_common import _split_csv
from .cli_outputs import _seeds_path


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
