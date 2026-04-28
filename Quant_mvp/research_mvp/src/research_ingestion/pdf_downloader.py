from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
import hashlib
from typing import Any

from .config import ProjectPaths
from .license_policy import assess_pdf_fulltext_policy
from .pdf_policy import (
    TRACE_FIELDS,
    blocked_access_message,
    disallowed_manifest_category,
    first_pdf_url,
    has_trace_value,
    is_http_url,
    license_value,
    trace_fields,
)
from .persistence import ensure_parent, read_jsonl, validate_storage_segment, write_jsonl
from .redaction import assert_no_scholar_request, redact_url

try:
    import requests
except Exception:  # pragma: no cover - exercised only when requests is absent.
    requests = None  # type: ignore[assignment]


FetchPdfBytes = Callable[[str, float, dict[str, str], int], tuple[bytes, dict[str, str], int | None]]


def cmd_download_pdfs(args: Any, config: dict[str, Any], paths: ProjectPaths) -> None:
    if not getattr(args, "allow_pdf", False):
        raise ValueError("download-pdfs requires --allow-pdf and explicit policy confirmation.")
    input_path = Path(args.input_path) if args.input_path else paths.data_dir / "normalized" / f"{args.run_id}_papers.jsonl"
    papers = read_jsonl(input_path)
    summary = download_pdfs(
        papers=papers,
        config=config,
        paths=paths,
        run_id=args.run_id,
        max_records=args.max_records,
        dry_run=args.dry_run,
        input_path=input_path,
    )
    print(_summary_text(summary))


def download_pdfs(
    *,
    papers: Iterable[dict[str, Any]],
    config: dict[str, Any],
    paths: ProjectPaths,
    run_id: str,
    max_records: int | None = None,
    dry_run: bool = False,
    input_path: Path | None = None,
    fetch_pdf_bytes: FetchPdfBytes | None = None,
) -> dict[str, Any]:
    validate_storage_segment(run_id, "run_id")
    policy = config.get("policy", {})
    pdf_policy = policy.get("pdf_policy", {})
    max_downloads = _max_downloads(max_records, pdf_policy)
    rows = []
    downloaded = 0
    selected = 0
    candidates = list(papers)
    for paper in candidates:
        if selected >= max_downloads:
            break
        row = _candidate_row(paper, config, paths, run_id)
        if row["status"] == "planned" and not dry_run:
            row = _download_candidate(row, paths, run_id, pdf_policy, fetch_pdf_bytes or fetch_pdf)
        elif row["status"] == "planned" and dry_run:
            row["status"] = "planned_dry_run"
            row["notes_ko"] = "dry-run이라 PDF 파일을 저장하지 않았습니다."
        if row["status"] == "downloaded":
            downloaded += 1
            selected += 1
        elif row["status"] == "planned_dry_run":
            selected += 1
        rows.append(_manifest_row(row))

    manifest_path = paths.data_dir / "fulltext" / "manifests" / f"{run_id}_pdf_download_manifest.jsonl"
    write_jsonl(manifest_path, rows)
    return {
        "run_id": run_id,
        "input_path": str(input_path) if input_path else None,
        "manifest_path": str(manifest_path),
        "candidate_count": len(candidates),
        "processed_count": len(rows),
        "downloaded_count": downloaded,
        "max_downloads_per_run": max_downloads,
        "dry_run": dry_run,
        "policy_result_ko": "PDF 다운로드는 명시 license trace가 있는 항목만 로컬 저장 대상으로 처리했습니다.",
    }


def fetch_pdf(url: str, timeout_seconds: float, headers: dict[str, str], max_bytes: int) -> tuple[bytes, dict[str, str], int | None]:
    assert_no_scholar_request(url)
    if requests is not None:
        response = requests.get(url, headers=headers, timeout=timeout_seconds, stream=True)  # type: ignore[union-attr]
        return (
            _read_limited_chunks(response.iter_content(chunk_size=64 * 1024), max_bytes),
            {key: value for key, value in response.headers.items()},
            response.status_code,
        )
    from urllib.request import Request, urlopen

    with urlopen(Request(url, headers=headers), timeout=timeout_seconds) as response:
        return (
            _read_limited_reader(response, max_bytes),
            {key: value for key, value in response.headers.items()},
            getattr(response, "status", None),
        )


def _candidate_row(paper: dict[str, Any], config: dict[str, Any], paths: ProjectPaths, run_id: str) -> dict[str, Any]:
    url = first_pdf_url(paper)
    policy = config.get("policy", {})
    base = {
        "run_id": run_id,
        "canonical_paper_id": paper.get("canonical_paper_id"),
        "title": paper.get("title"),
        "_source_url": url,
        "source_url": redact_url(url),
        "local_pdf_path": None,
        "status": "planned",
        "skip_reason_ko": None,
        "checked_at_utc": _utc_now(),
        "license_collection_allowed": False,
        "license_use_basis": None,
        "pdf_fulltext_download_allowed": False,
        "pdf_fulltext_use_basis": None,
        "policy_notes_ko": None,
        **trace_fields(paper),
    }
    if not policy.get("pdf_policy", {}).get("allow_pdf", False):
        return _skipped(base, "research_policy.toml에서 PDF use가 비활성화되어 있습니다.")
    if not url:
        return _skipped(base, "pdf_url이 없어 다운로드하지 않았습니다.")
    if not is_http_url(url):
        return _skipped(base, "HTTP(S) URL만 PDF 다운로드 대상으로 허용합니다.")
    try:
        assert_no_scholar_request(url)
    except RuntimeError as exc:
        return _skipped(base, str(exc))
    disallowed_category = disallowed_manifest_category(paper, policy.get("pdf_policy", {}))
    if disallowed_category:
        return _skipped(base, f"PDF-ready manifest category가 허용 대상이 아닙니다: {disallowed_category}")
    blocked_access_reason = blocked_access_message(paper, url, policy.get("fulltext_access_policy", {}))
    if blocked_access_reason:
        return _skipped(base, blocked_access_reason)
    missing = [field for field in TRACE_FIELDS if not has_trace_value(paper, field)]
    if missing:
        return _skipped(base, f"PDF/fulltext trace field가 부족합니다: {', '.join(missing)}")
    assessment = assess_pdf_fulltext_policy(license_value(paper), policy.get("license_policy", {}))
    base.update(
        {
            "license_collection_allowed": assessment["license_collection_allowed"],
            "license_use_basis": assessment["license_use_basis"],
            "pdf_fulltext_download_allowed": assessment["pdf_fulltext_download_allowed"],
            "pdf_fulltext_use_basis": assessment["pdf_fulltext_use_basis"],
            "policy_notes_ko": assessment["pdf_fulltext_policy_notes_ko"],
        }
    )
    if not assessment["pdf_fulltext_download_allowed"]:
        return _skipped(base, assessment["pdf_fulltext_policy_notes_ko"])
    return base


def _download_candidate(
    row: dict[str, Any],
    paths: ProjectPaths,
    run_id: str,
    pdf_policy: dict[str, Any],
    fetch_pdf_bytes: FetchPdfBytes,
) -> dict[str, Any]:
    timeout = float(pdf_policy.get("timeout_seconds", 30.0))
    max_bytes = int(pdf_policy.get("max_pdf_bytes", 25 * 1024 * 1024) or 0)
    if max_bytes < 1:
        raise ValueError("pdf_policy.max_pdf_bytes must be at least 1.")
    headers = {"User-Agent": str(pdf_policy.get("user_agent", "research-ingestion-pdf-downloader/1.0"))}
    try:
        body, response_headers, status = fetch_pdf_bytes(row["_source_url"], timeout, headers, max_bytes)
    except ValueError as exc:
        return _skipped(row, str(exc))
    row["http_status"] = status
    row["response_content_type"] = response_headers.get("content-type") or response_headers.get("Content-Type")
    if status is not None and not (200 <= int(status) < 300):
        return _skipped(row, f"PDF 요청이 HTTP {status}로 실패했습니다.")
    if len(body) > max_bytes:
        return _skipped(row, f"PDF response exceeds max_pdf_bytes={max_bytes}.")
    if not body.startswith(b"%PDF-"):
        return _skipped(row, "응답 본문이 PDF signature로 시작하지 않아 저장하지 않았습니다.")
    local_path = _local_pdf_path(paths, run_id, row, body)
    ensure_parent(local_path)
    local_path.write_bytes(body)
    row["status"] = "downloaded"
    row["local_pdf_path"] = str(local_path)
    row["content_sha256"] = hashlib.sha256(body).hexdigest()
    row["bytes"] = len(body)
    row["notes_ko"] = "license trace 확인 후 로컬 PDF로 저장했습니다. 외부 업로드는 수행하지 않았습니다."
    return row


def _max_downloads(max_records: int | None, pdf_policy: dict[str, Any]) -> int:
    configured = int(pdf_policy.get("max_downloads_per_run", 1) or 1)
    if configured < 1:
        raise ValueError("pdf_policy.max_downloads_per_run must be at least 1.")
    requested = configured if max_records is None else int(max_records)
    if requested < 1:
        raise ValueError("--max-records must be at least 1 for PDF downloads.")
    if requested > configured:
        raise ValueError(
            f"PDF 대량 다운로드는 허용되지 않습니다. max_downloads_per_run={configured} 이하로 지정하세요."
        )
    return requested


def _skipped(row: dict[str, Any], reason_ko: str) -> dict[str, Any]:
    row["status"] = "skipped"
    row["skip_reason_ko"] = reason_ko
    return row


def _manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not str(key).startswith("_")}


def _local_pdf_path(paths: ProjectPaths, run_id: str, row: dict[str, Any], body: bytes) -> Path:
    paper_hash = hashlib.sha256(str(row.get("canonical_paper_id") or row.get("title") or "paper").encode("utf-8")).hexdigest()[:16]
    content_hash = hashlib.sha256(body).hexdigest()[:16]
    return paths.data_dir / "fulltext" / "pdf" / run_id / f"{paper_hash}_{content_hash}.pdf"


def _read_limited_chunks(chunks: Iterable[bytes], max_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    for chunk in chunks:
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"PDF response exceeds max_pdf_bytes={max_bytes}.")
        parts.append(chunk)
    return b"".join(parts)


def _read_limited_reader(reader: Any, max_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = reader.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"PDF response exceeds max_pdf_bytes={max_bytes}.")
        parts.append(chunk)
    return b"".join(parts)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _summary_text(summary: dict[str, Any]) -> str:
    import json

    return json.dumps(summary, ensure_ascii=False, indent=2)
