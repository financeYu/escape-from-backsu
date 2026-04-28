from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


TRACE_FIELDS = (
    "license_name",
    "license_url",
    "license_checked_at",
    "license_evidence_quote",
    "collection_basis",
    "fulltext_source_type",
    "fulltext_review_scope",
    "redistribution_allowed",
    "external_upload_allowed",
)

AUTO_CC_TOKENS = {"ccby", "ccbysa", "ccbynd"}
NONCOMMERCIAL_CC_TOKENS = {"ccbync", "ccbyncsa", "ccbyncnd"}


def pdf_urls(paper: dict[str, Any]) -> list[str]:
    urls = paper.get("pdf_urls") or []
    if isinstance(urls, str):
        return [urls] if urls.strip() else []
    return [str(url) for url in urls if str(url).strip()]


def first_pdf_url(paper: dict[str, Any]) -> str | None:
    return next((url for url in pdf_urls(paper) if url.strip()), None)


def license_value(paper: dict[str, Any]) -> str | None:
    return paper.get("license_url") or paper.get("license_name") or paper.get("license")


def has_trace_value(paper: dict[str, Any], field: str) -> bool:
    if field in {"redistribution_allowed", "external_upload_allowed"}:
        return isinstance(paper.get(field), bool)
    return bool(str(paper.get(field) or "").strip())


def trace_fields(paper: dict[str, Any]) -> dict[str, Any]:
    return {field: paper.get(field) for field in TRACE_FIELDS}


def collection_basis(paper: dict[str, Any], category: str, pdf_policy: dict[str, Any]) -> str | None:
    if category == "noncommercial_cc":
        return str(pdf_policy.get("noncommercial_collection_basis") or "noncommercial_research_only")
    value = str(paper.get("collection_basis") or "").strip()
    return value or None


def external_upload_allowed(paper: dict[str, Any]) -> bool:
    if isinstance(paper.get("external_upload_allowed"), bool):
        return bool(paper["external_upload_allowed"])
    return False


def is_http_url(url: str) -> bool:
    return urlsplit(url).scheme in {"http", "https"}


def is_scholar_url(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return host == "scholar.google.com" or host.endswith(".scholar.google.com")


def category_allowed_by_policy(category: str, pdf_policy: dict[str, Any]) -> bool:
    allowed = {
        str(item).strip()
        for item in pdf_policy.get("allowed_manifest_categories", [])
        if str(item).strip()
    }
    allowed = allowed or {"auto_cc", "noncommercial_cc"}
    return category in allowed


def disallowed_manifest_category(paper: dict[str, Any], pdf_policy: dict[str, Any]) -> str | None:
    category = str(paper.get("category") or "").strip()
    if not category or category_allowed_by_policy(category, pdf_policy):
        return None
    return category


def blocked_access_code(paper: dict[str, Any], url: str | None, access_policy: dict[str, Any]) -> str | None:
    source_type = str(paper.get("fulltext_source_type") or "").strip().lower()
    blocked_source_types = {
        str(item).strip().lower()
        for item in access_policy.get("blocked_source_types", [])
        if str(item).strip()
    }
    if source_type and source_type in blocked_source_types:
        return f"blocked_source_type:{source_type}"

    markers = [
        str(item).strip().lower()
        for item in access_policy.get("blocked_access_markers", [])
        if str(item).strip()
    ]
    checked_values = [
        url,
        paper.get("collection_basis"),
        paper.get("fulltext_review_scope"),
        paper.get("fulltext_source_type"),
    ]
    for value in checked_values:
        lowered = str(value or "").lower()
        marker = next((marker for marker in markers if marker in lowered), None)
        if marker:
            return f"blocked_access_marker:{marker}"
    return None


def blocked_access_message(paper: dict[str, Any], url: str | None, access_policy: dict[str, Any]) -> str | None:
    code = blocked_access_code(paper, url, access_policy)
    if not code:
        return None
    kind, value = code.split(":", 1)
    if kind == "blocked_source_type":
        return f"차단된 fulltext_source_type입니다: {value}"
    return f"paywall/login/TDM 차단 표식이 있어 PDF/fulltext를 수집하지 않습니다: {value}"


def known_content_type(paper: dict[str, Any]) -> str | None:
    for field in ("response_content_type", "content_type", "pdf_content_type"):
        value = str(paper.get(field) or "").strip().lower()
        if value:
            return value
    return None


def has_open_access_marker(paper: dict[str, Any]) -> bool:
    values = [
        paper.get("oa_status"),
        paper.get("open_access_status"),
        paper.get("license_use_basis"),
    ]
    return any("open" in str(value).lower() or "oa" in str(value).lower() for value in values if value)
