from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .schema import make_discovery_seed
from ..normalize import clean_text


FORMAT_CHANNELS = {
    "endnote": "google_scholar_manual_endnote",
    "refman": "google_scholar_manual_refman",
    "refworks": "google_scholar_manual_refworks",
}


def import_citation_export_dir(input_dir: str | Path, *, export_format: str, run_id: str | None = None) -> list[dict[str, Any]]:
    directory = Path(input_dir)
    seeds: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*")):
        if path.is_file() and path.suffix.lower() in {"", ".txt", ".enw", ".ris", ".ref", ".rw"}:
            seeds.extend(parse_citation_export_file(path, export_format=export_format))
    return seeds


def parse_citation_export_file(path: str | Path, *, export_format: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    channel = FORMAT_CHANNELS.get(export_format)
    if not channel:
        raise ValueError(f"Unsupported citation export format: {export_format}")
    if export_format == "endnote" or text.lstrip().startswith("%"):
        entries = _parse_endnote_entries(text)
    else:
        entries = _parse_ris_entries(text)
    return [_seed_from_entry(entry, channel, file_path) for entry in entries if entry.get("title")]


def _parse_endnote_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        match = re.match(r"^%([A-Z0-9])\s*(.*)$", line)
        if not match:
            continue
        tag, value = match.group(1), clean_text(match.group(2))
        if tag == "T":
            current["title"] = value
        elif tag == "A" and value:
            current.setdefault("authors", []).append(value)
        elif tag == "D":
            current["year"] = _year(value)
        elif tag in {"J", "B"}:
            current["venue"] = value
        elif tag == "R":
            current["doi"] = value
        elif tag == "U":
            current["url"] = value
    if current:
        entries.append(current)
    return entries


def _parse_ris_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw_line in text.splitlines():
        match = re.match(r"^([A-Z0-9]{2})\s*-\s*(.*)$", raw_line.rstrip())
        if not match:
            continue
        tag, value = match.group(1), clean_text(match.group(2))
        if tag == "TY":
            current = {}
        elif tag == "ER":
            if current:
                entries.append(current)
                current = {}
        elif tag in {"TI", "T1"}:
            current["title"] = value
        elif tag == "AU" and value:
            current.setdefault("authors", []).append(value)
        elif tag in {"PY", "Y1"}:
            current["year"] = _year(value)
        elif tag in {"JO", "JF", "JA", "T2"}:
            current["venue"] = value
        elif tag == "DO":
            current["doi"] = value
        elif tag == "UR":
            current["url"] = value
    if current:
        entries.append(current)
    return entries


def _seed_from_entry(entry: dict[str, Any], source_channel: str, path: Path) -> dict[str, Any]:
    return make_discovery_seed(
        source_channel=source_channel,
        raw_title=entry.get("title") or "",
        raw_authors=entry.get("authors", []),
        raw_venue=entry.get("venue"),
        raw_year=entry.get("year"),
        raw_link=entry.get("url"),
        local_input_path=path,
        candidate_doi=entry.get("doi"),
        notes_ko="Google Scholar 수동 citation export 파일에서 읽은 discovery seed입니다. 형식 지원은 MVP 수준이며 canonical metadata resolution이 필요합니다.",
    )


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", value)
    return int(match.group(0)) if match else None
