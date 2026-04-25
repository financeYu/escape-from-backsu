from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any

from .schema import make_discovery_seed
from ..normalize import clean_text


class _AlertHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            title = clean_text(" ".join(self._text_parts))
            if title:
                self.links.append((title, self._href))
            self._href = None
            self._text_parts = []


def import_alerts_dir(input_dir: str | Path, run_id: str | None = None) -> list[dict[str, Any]]:
    directory = Path(input_dir)
    seeds: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() in {".txt", ".html", ".htm", ".eml"}:
            seeds.extend(parse_alert_file(path))
    return seeds


def parse_alert_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() in {".html", ".htm"} or "<html" in content.lower():
        return _parse_html_alert(content, file_path)
    return _parse_text_alert(content, file_path)


def _parse_html_alert(content: str, path: Path) -> list[dict[str, Any]]:
    parser = _AlertHTMLParser()
    parser.feed(content)
    alert_query = _extract_alert_query("\n".join(parser.text_parts))
    seeds = []
    for title, link in parser.links:
        if "scholar.google" in title.lower():
            continue
        seeds.append(
            make_discovery_seed(
                source_channel="google_scholar_alert_email",
                raw_title=title,
                raw_link=link,
                raw_snippet=None,
                alert_query=alert_query,
                local_input_path=path,
            )
        )
    return seeds


def _parse_text_alert(content: str, path: Path) -> list[dict[str, Any]]:
    alert_query = _extract_alert_query(content)
    blocks = [block for block in re.split(r"\n\s*\n", content) if clean_text(block)]
    seeds = []
    for block in blocks:
        title = _extract_labeled(block, "Title") or _first_candidate_line(block)
        if not title or title.lower().startswith(("google scholar", "alert query")):
            continue
        snippet = _extract_labeled(block, "Snippet")
        link = _extract_labeled(block, "Link") or _extract_url(block)
        seeds.append(
            make_discovery_seed(
                source_channel="google_scholar_alert_email",
                raw_title=title,
                raw_snippet=snippet,
                raw_link=link,
                alert_query=alert_query,
                local_input_path=path,
            )
        )
    return seeds


def _extract_alert_query(content: str) -> str | None:
    match = re.search(r"(?:Alert query|Query|검색어)\s*:\s*(.+)", content, flags=re.IGNORECASE)
    return clean_text(match.group(1)) if match else None


def _extract_labeled(block: str, label: str) -> str | None:
    match = re.search(rf"^{label}\s*:\s*(.+)$", block, flags=re.IGNORECASE | re.MULTILINE)
    return clean_text(match.group(1)) if match else None


def _extract_url(block: str) -> str | None:
    match = re.search(r"https?://\S+", block)
    return match.group(0).rstrip(".,)") if match else None


def _first_candidate_line(block: str) -> str | None:
    for line in block.splitlines():
        cleaned = clean_text(line)
        if cleaned and not cleaned.startswith(("http://", "https://")) and ":" not in cleaned[:20]:
            return cleaned
    return None
