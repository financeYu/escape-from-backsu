from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from typing import Any


def build_parser(command_handlers: Mapping[str, Callable[..., Any]]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research_ingestion")
    _add_pdf_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    _add_run_common(collect)
    _add_collect_common(collect)
    collect.add_argument("--sources", required=True)
    collect.add_argument("--query-set", required=True)
    collect.set_defaults(func=command_handlers["collect"])

    alerts = subparsers.add_parser("import-scholar-alerts")
    _add_run_common(alerts)
    alerts.add_argument("--input-dir", required=True)
    alerts.set_defaults(func=command_handlers["import_alerts"])

    bibtex = subparsers.add_parser("import-scholar-bibtex")
    _add_run_common(bibtex)
    bibtex.add_argument("--input-dir", required=True)
    bibtex.set_defaults(func=command_handlers["import_bibtex"])

    endnote = subparsers.add_parser("import-scholar-endnote")
    _add_run_common(endnote)
    endnote.add_argument("--input-dir", required=True)
    endnote.set_defaults(func=command_handlers["import_endnote"])

    refman = subparsers.add_parser("import-scholar-refman")
    _add_run_common(refman)
    refman.add_argument("--input-dir", required=True)
    refman.set_defaults(func=command_handlers["import_refman"])

    refworks = subparsers.add_parser("import-scholar-refworks")
    _add_run_common(refworks)
    refworks.add_argument("--input-dir", required=True)
    refworks.set_defaults(func=command_handlers["import_refworks"])

    titles = subparsers.add_parser("import-scholar-title-list")
    _add_run_common(titles)
    titles.add_argument("--input-path", required=True)
    titles.set_defaults(func=command_handlers["import_title_list"])

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

    refresh = subparsers.add_parser("refresh")
    _add_run_common(refresh)
    _add_collect_common(refresh)
    refresh.add_argument("--profile", default=None, help="Refresh operating profile, e.g. fast_refresh, full_refresh, diagnostic_refresh, regional_refresh.")
    refresh.add_argument("--sources", default=None, help="Comma-separated metadata sources. Defaults to the selected refresh profile.")
    refresh.add_argument("--query-sets", default=None, help="Comma-separated query sets. Defaults to the selected refresh profile.")
    refresh.add_argument("--include-valuation", action="store_true", help="Explicit opt-in for valuation/fundamental query sets.")
    refresh.set_defaults(func=command_handlers["refresh"])
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
