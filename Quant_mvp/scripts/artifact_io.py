"""Shared artifact I/O helpers for Quant route builder scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(payload)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def parse_json_fenced_markdown(path: Path, *, required: bool = True) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    if not match:
        if required:
            raise ValueError(f"{path} does not contain a json fenced block")
        return None
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} json fenced block is not an object")
    payload["_source_path"] = str(path)
    return payload
