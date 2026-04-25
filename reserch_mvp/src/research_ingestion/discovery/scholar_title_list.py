from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .schema import make_discovery_seed
from ..normalize import clean_text


def parse_title_list_file(path: str | Path, source_channel: str = "google_scholar_manual_title_list") -> list[dict[str, Any]]:
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        return _parse_csv(file_path, source_channel)
    return _parse_text(file_path, source_channel)


def _parse_csv(path: Path, source_channel: str) -> list[dict[str, Any]]:
    seeds = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = row.get("title") or row.get("raw_title")
            if not clean_text(title):
                continue
            authors = [author.strip() for author in (row.get("authors") or "").split(";") if author.strip()]
            seeds.append(
                make_discovery_seed(
                    source_channel=source_channel,
                    raw_title=title or "",
                    raw_authors=authors,
                    raw_venue=row.get("venue"),
                    raw_year=_int_or_none(row.get("year")),
                    raw_snippet=None,
                    raw_link=row.get("link"),
                    alert_query=row.get("query") or row.get("alert_query"),
                    local_input_path=path,
                    candidate_doi=row.get("doi"),
                    candidate_arxiv_id=row.get("arxiv_id"),
                )
            )
    return seeds


def _parse_text(path: Path, source_channel: str) -> list[dict[str, Any]]:
    seeds = []
    for line in path.read_text(encoding="utf-8").splitlines():
        title = clean_text(line)
        if not title or title.startswith("#"):
            continue
        seeds.append(
            make_discovery_seed(
                source_channel=source_channel,
                raw_title=title,
                local_input_path=path,
            )
        )
    return seeds


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
