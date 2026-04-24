from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .redaction import redact_mapping


def content_hash(content: bytes | str) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def raw_snapshot_path(root: Path, source: str, run_id: str, body: bytes | str, suffix: str) -> Path:
    digest = content_hash(body)[:16]
    safe_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return root / "data" / "research" / "raw" / source / run_id / f"{digest}{safe_suffix}"


def store_raw_response(
    *,
    root: Path,
    source: str,
    run_id: str,
    response_body: bytes | str,
    suffix: str,
    request_metadata: dict[str, Any],
    http_status: int | None = None,
    retry_count: int = 0,
    redaction_env_vars: list[str] | None = None,
) -> dict[str, Any]:
    body_path = raw_snapshot_path(root, source, run_id, response_body, suffix)
    ensure_parent(body_path)
    if isinstance(response_body, bytes):
        body_path.write_bytes(response_body)
    else:
        body_path.write_text(response_body, encoding="utf-8")

    metadata = {
        "source": source,
        "run_id": run_id,
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "http_status": http_status,
        "retry_count": retry_count,
        "content_hash": content_hash(response_body),
        "response_body_path": str(body_path),
        "request": request_metadata,
    }
    metadata = redact_mapping(metadata, env_var_names=redaction_env_vars)
    metadata_path = body_path.with_suffix(body_path.suffix + ".metadata.json")
    write_json(metadata_path, metadata)
    return {
        "body_path": str(body_path),
        "metadata_path": str(metadata_path),
        "content_hash": metadata["content_hash"],
    }
