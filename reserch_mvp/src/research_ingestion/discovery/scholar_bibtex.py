from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .schema import make_discovery_seed
from ..normalize import clean_text


def import_bibtex_dir(input_dir: str | Path, run_id: str | None = None) -> list[dict[str, Any]]:
    directory = Path(input_dir)
    seeds: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.bib")):
        seeds.extend(parse_bibtex_file(path))
    return seeds


def parse_bibtex_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    entries = parse_bibtex_entries(file_path.read_text(encoding="utf-8"))
    seeds = []
    for entry in entries:
        title = entry.get("title")
        if not title:
            continue
        authors = [clean_text(author) for author in re.split(r"\s+and\s+", entry.get("author", ""), flags=re.IGNORECASE)]
        year = _int_or_none(entry.get("year"))
        venue = entry.get("journal") or entry.get("booktitle") or entry.get("publisher")
        seeds.append(
            make_discovery_seed(
                source_channel="google_scholar_manual_bibtex",
                raw_title=title,
                raw_authors=[author for author in authors if author],
                raw_venue=venue,
                raw_year=year,
                raw_snippet=None,
                raw_link=entry.get("url"),
                alert_query=None,
                local_input_path=file_path,
                candidate_doi=entry.get("doi"),
                candidate_arxiv_id=entry.get("eprint") or entry.get("arxivid"),
            )
        )
    return seeds


def parse_bibtex_entries(text: str) -> list[dict[str, str]]:
    entries = []
    for raw_entry in _split_bibtex_entries(text):
        fields: dict[str, str] = {}
        for match in re.finditer(r"(\w+)\s*=\s*([{\"'])(.*?)(?:\2|})\s*,?", raw_entry, flags=re.DOTALL):
            key = match.group(1).lower()
            value = clean_text(match.group(3).replace("\n", " "))
            if value:
                fields[key] = value.strip("{}")
        entries.append(fields)
    return entries


def _split_bibtex_entries(text: str) -> list[str]:
    entries: list[str] = []
    start = None
    depth = 0
    for index, char in enumerate(text):
        if char == "@" and depth == 0:
            start = index
        if start is not None:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start : index + 1])
                    start = None
    return entries


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
