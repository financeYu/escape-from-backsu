from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .classify import classify_paper
from .api_keys import load_api_keys_for_project
from .config import ProjectPaths, find_project_root, load_research_config, validate_pdf_policy, validate_policy
from .evidence import generate_evidence_cards
from .persistence import validate_storage_segment
from .cli_collect import (
    _collection_plan,
    _collection_relevance_rows,
    _collection_summary,
    _update_source_health_from_collection,
    cmd_collect as _cmd_collect,
)
from .cli_common import (
    SourcePageFetch,
    _adapter_for_source,
    _empty_source_health,
    _safe_error_message,
    _split_csv,
    _source_adapter_registry,
    _validate_query_allowed_sources,
    _validate_sources,
)
from .cli_discovery import (
    cmd_import_alerts as _cmd_import_alerts,
    cmd_import_bibtex as _cmd_import_bibtex,
    cmd_import_endnote as _cmd_import_endnote,
    cmd_import_refman as _cmd_import_refman,
    cmd_import_refworks as _cmd_import_refworks,
    cmd_import_title_list as _cmd_import_title_list,
    cmd_resolve_scholar_seeds as _cmd_resolve_scholar_seeds,
)
from .cli_enrich import (
    _enrich_args_from_run_all,
    _enrichment_plan,
    _enrichment_summary,
    _enrichment_targets,
    _fetch_enrichment_response,
    _validate_enrichment_sources,
    cmd_enrich as _cmd_enrich,
)
from .cli_outputs import (
    _dedupe_index_row,
    _normalized_papers_path_for_run,
    _read_normalized_papers_for_run,
    _run_management_lane,
    _seeds_path,
    _write_evidence_outputs,
    _write_new_only_outputs,
    _write_normalized_papers,
)
from .pdf_downloader import cmd_download_pdfs as _cmd_download_pdfs
from .pdf_manifest import cmd_pdf_ready_manifest as _cmd_pdf_ready_manifest
from .cli_parser import build_parser as _build_parser
from .cli_refresh import (
    _current_policy_versions,
    _refresh_plan,
    _refresh_query_sets,
    _refresh_sources,
    cmd_refresh as _cmd_refresh,
)
from .cli_steps import (
    _run_all_plan,
    cmd_classify as _cmd_classify,
    cmd_evidence as _cmd_evidence,
    cmd_normalize as _cmd_normalize,
    cmd_report as _cmd_report,
    cmd_run_all as _cmd_run_all,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = find_project_root(Path.cwd())
    load_api_keys_for_project(root)
    config = load_research_config(root)
    validate_policy(config)
    validate_pdf_policy(config, allow_pdf=args.allow_pdf, confirmed=args.confirm_pdf_policy)
    validate_storage_segment(args.run_id, "run_id")
    paths = ProjectPaths(root)
    args.func(args, config, paths)
    return 0


def build_parser() -> argparse.ArgumentParser:
    return _build_parser(_command_handlers())


def _command_handlers() -> dict[str, Any]:
    return {
        "collect": cmd_collect,
        "import_alerts": cmd_import_alerts,
        "import_bibtex": cmd_import_bibtex,
        "import_endnote": cmd_import_endnote,
        "import_refman": cmd_import_refman,
        "import_refworks": cmd_import_refworks,
        "import_title_list": cmd_import_title_list,
        "resolve_scholar_seeds": cmd_resolve_scholar_seeds,
        "enrich": cmd_enrich,
        "normalize": cmd_normalize,
        "classify": cmd_classify,
        "evidence": cmd_evidence,
        "report": cmd_report,
        "run_all": cmd_run_all,
        "refresh": cmd_refresh,
        "download_pdfs": cmd_download_pdfs,
        "pdf_ready_manifest": cmd_pdf_ready_manifest,
    }


def cmd_collect(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_collect(args, config, paths)


def cmd_import_alerts(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_alerts(args, config, paths)


def cmd_import_bibtex(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_bibtex(args, config, paths)


def cmd_import_endnote(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_endnote(args, config, paths)


def cmd_import_refman(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_refman(args, config, paths)


def cmd_import_refworks(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_refworks(args, config, paths)


def cmd_import_title_list(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_import_title_list(args, config, paths)


def cmd_resolve_scholar_seeds(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_resolve_scholar_seeds(args, config, paths)


def cmd_enrich(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_enrich(args, config, paths, fetch_response=_fetch_enrichment_response)


def cmd_normalize(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_normalize(args, config, paths)


def cmd_classify(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_classify(args, config, paths, classify_func=classify_paper)


def cmd_evidence(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_evidence(args, config, paths, generate_cards_func=generate_evidence_cards)


def cmd_report(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_report(args, config, paths)


def cmd_run_all(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_run_all(
        args,
        config,
        paths,
        collect_command=cmd_collect,
        normalize_command=cmd_normalize,
        enrich_command=cmd_enrich,
        classify_command=cmd_classify,
        evidence_command=cmd_evidence,
        report_command=cmd_report,
    )


def cmd_refresh(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_refresh(
        args,
        config,
        paths,
        collect_command=cmd_collect,
        classify_func=classify_paper,
        generate_cards_func=generate_evidence_cards,
        current_policy_versions_func=_current_policy_versions,
    )


def cmd_download_pdfs(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_download_pdfs(args, config, paths)


def cmd_pdf_ready_manifest(args: argparse.Namespace, config: dict[str, Any], paths: ProjectPaths) -> None:
    return _cmd_pdf_ready_manifest(args, config, paths)
