from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from typing import Any


def build_parser(command_handlers: Mapping[str, Callable[..., Any]]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research_ingestion")
    _add_pdf_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_collect_parser(subparsers, command_handlers)
    _add_scholar_import_parsers(subparsers, command_handlers)
    _add_pipeline_parsers(subparsers, command_handlers)
    _add_pdf_parser(subparsers, command_handlers)
    _add_refresh_parser(subparsers, command_handlers)
    return parser


def _add_collect_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_handlers: Mapping[str, Callable[..., Any]],
) -> None:
    collect = subparsers.add_parser("collect")
    _add_run_common(collect)
    _add_collect_common(collect)
    collect.add_argument("--sources", required=True)
    collect.add_argument("--query-set", required=True)
    collect.set_defaults(func=command_handlers["collect"])


def _add_scholar_import_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_handlers: Mapping[str, Callable[..., Any]],
) -> None:
    import_commands = [
        ("import-scholar-alerts", "import_alerts", "--input-dir"),
        ("import-scholar-bibtex", "import_bibtex", "--input-dir"),
        ("import-scholar-endnote", "import_endnote", "--input-dir"),
        ("import-scholar-refman", "import_refman", "--input-dir"),
        ("import-scholar-refworks", "import_refworks", "--input-dir"),
        ("import-scholar-title-list", "import_title_list", "--input-path"),
    ]
    for command_name, handler_name, input_arg in import_commands:
        command = subparsers.add_parser(command_name)
        _add_run_common(command)
        command.add_argument(input_arg, required=True)
        command.set_defaults(func=command_handlers[handler_name])


def _add_pipeline_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_handlers: Mapping[str, Callable[..., Any]],
) -> None:
    resolve = subparsers.add_parser("resolve-scholar-seeds")
    _add_run_common(resolve)
    resolve.add_argument("--sources", required=True)
    resolve.set_defaults(func=command_handlers["resolve_scholar_seeds"])

    enrich = subparsers.add_parser("enrich")
    _add_run_common(enrich)
    _add_pdf_options(enrich, set_defaults=False)
    enrich.add_argument("--sources", required=True)
    enrich.add_argument("--input-path", default=None)
    enrich.add_argument("--max-records", type=int, default=None)
    enrich.add_argument("--offline", action="store_true")
    enrich.set_defaults(func=command_handlers["enrich"])

    normalize = subparsers.add_parser("normalize")
    _add_run_common(normalize)
    normalize.set_defaults(func=command_handlers["normalize"])

    classify = subparsers.add_parser("classify")
    _add_run_common(classify)
    classify.set_defaults(func=command_handlers["classify"])

    evidence = subparsers.add_parser("evidence")
    _add_run_common(evidence)
    evidence.set_defaults(func=command_handlers["evidence"])

    report = subparsers.add_parser("report")
    _add_run_common(report)
    report.set_defaults(func=command_handlers["report"])

    run_all = subparsers.add_parser("run-all")
    _add_run_common(run_all)
    _add_collect_common(run_all)
    run_all.add_argument("--sources", required=True)
    run_all.add_argument("--query-set", required=True)
    run_all.add_argument("--enrich-sources", default="", help="Optional enrichment sources, e.g. crossref,semantic_scholar.")
    run_all.add_argument("--enrich-max-records", type=int, default=None)
    run_all.set_defaults(func=command_handlers["run_all"])


def _add_refresh_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_handlers: Mapping[str, Callable[..., Any]],
) -> None:
    refresh = subparsers.add_parser("refresh")
    _add_run_common(refresh)
    _add_collect_common(refresh)
    refresh.add_argument("--profile", default=None, help="Refresh operating profile, e.g. fast_refresh, full_refresh, diagnostic_refresh, regional_refresh.")
    refresh.add_argument("--sources", default=None, help="Comma-separated metadata sources. Defaults to the selected refresh profile.")
    refresh.add_argument("--query-sets", default=None, help="Comma-separated query sets. Defaults to the selected refresh profile.")
    refresh.add_argument("--include-valuation", action="store_true", help="Explicit opt-in for valuation/fundamental query sets.")
    refresh.set_defaults(func=command_handlers["refresh"])


def _add_pdf_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_handlers: Mapping[str, Callable[..., Any]],
) -> None:
    download = subparsers.add_parser("download-pdfs")
    _add_run_common(download)
    _add_pdf_options(download, set_defaults=False)
    download.add_argument("--input-path", default=None)
    download.add_argument("--max-records", type=int, default=None)
    download.set_defaults(func=command_handlers["download_pdfs"])


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
