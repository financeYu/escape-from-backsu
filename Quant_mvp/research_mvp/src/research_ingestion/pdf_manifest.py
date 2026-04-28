from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .license_policy import assess_pdf_fulltext_policy, normalize_license_token
from .pdf_policy import (
    AUTO_CC_TOKENS,
    NONCOMMERCIAL_CC_TOKENS,
    TRACE_FIELDS,
    blocked_access_code,
    category_allowed_by_policy,
    collection_basis,
    external_upload_allowed,
    has_open_access_marker,
    has_trace_value,
    is_http_url,
    is_scholar_url,
    known_content_type,
    license_value,
    pdf_urls,
)
from .persistence import read_jsonl, validate_storage_segment, write_json, write_jsonl
from .redaction import redact_url


def cmd_pdf_ready_manifest(args: Any, config: dict[str, Any], paths: Any) -> None:
    validate_storage_segment(args.run_id, "run_id")
    input_path = Path(args.input_path) if args.input_path else paths.data_dir / "normalized" / "papers.jsonl"
    output_path = (
        Path(args.output_path)
        if args.output_path
        else paths.data_dir / "fulltext" / "manifests" / f"{args.run_id}_pdf_ready_manifest.jsonl"
    )
    summary_path = (
        Path(args.summary_path)
        if args.summary_path
        else paths.data_dir / "fulltext" / "manifests" / f"{args.run_id}_pdf_ready_manifest_summary.json"
    )
    result = build_pdf_ready_manifest(
        input_path=input_path,
        output_path=output_path,
        summary_path=summary_path,
        config=config,
        run_id=args.run_id,
    )
    import json

    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


def build_pdf_ready_manifest(
    *,
    input_path: Path,
    output_path: Path,
    summary_path: Path,
    config: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    papers = read_jsonl(input_path)
    generated_at = _utc_now()
    rows = [
        classify_pdf_manifest_row(
            paper,
            config=config,
            run_id=run_id,
            input_path=input_path,
            generated_at_utc=generated_at,
        )
        for paper in papers
    ]
    summary = summarize_manifest(rows, input_path=input_path, output_path=output_path, run_id=run_id, generated_at_utc=generated_at)
    write_jsonl(output_path, rows)
    write_json(summary_path, summary)
    return {"rows": rows, "summary": summary, "manifest_path": str(output_path), "summary_path": str(summary_path)}


def classify_pdf_manifest_row(
    paper: dict[str, Any],
    *,
    config: dict[str, Any],
    run_id: str,
    input_path: Path,
    generated_at_utc: str,
) -> dict[str, Any]:
    urls = pdf_urls(paper)
    selected_pdf_url = _first_nonempty(urls)
    paper_license_value = license_value(paper)
    license_token = normalize_license_token(paper_license_value)
    missing_trace_fields = [field for field in TRACE_FIELDS if not has_trace_value(paper, field)]
    exclusion_reasons: list[str] = []
    manual_review_reasons: list[str] = []

    if not selected_pdf_url:
        exclusion_reasons.append("missing_pdf_url")
    elif not is_http_url(selected_pdf_url):
        exclusion_reasons.append("non_http_pdf_url")
    elif is_scholar_url(selected_pdf_url):
        exclusion_reasons.append("scholar_pdf_url")

    blocked_access_reason = blocked_access_code(
        paper,
        selected_pdf_url,
        config.get("policy", {}).get("fulltext_access_policy", {}),
    )
    if blocked_access_reason:
        exclusion_reasons.append(blocked_access_reason)

    content_type = known_content_type(paper)
    if content_type and "pdf" not in content_type:
        exclusion_reasons.append("known_non_pdf_response")

    if license_token:
        pdf_policy_result = assess_pdf_fulltext_policy(
            paper_license_value,
            {
                **config.get("policy", {}).get("license_policy", {}),
                "fulltext_download_remains_disabled": False,
            },
        )
        if pdf_policy_result["pdf_fulltext_use_basis"] == "blocked_publisher_tdm_license":
            exclusion_reasons.append("blocked_publisher_tdm_license")
    elif selected_pdf_url:
        manual_review_reasons.append("missing_explicit_license")

    if license_token and license_token not in AUTO_CC_TOKENS and license_token not in NONCOMMERCIAL_CC_TOKENS:
        if has_open_access_marker(paper):
            manual_review_reasons.append("other_oa_license")
        else:
            manual_review_reasons.append("other_license")

    pdf_policy = config.get("policy", {}).get("pdf_policy", {})
    category = _category(license_token, exclusion_reasons, manual_review_reasons)
    category_allowed = category_allowed_by_policy(category, pdf_policy)
    trace_complete = not missing_trace_fields
    next_step_download_ready = category_allowed and trace_complete

    return {
        "manifest_schema_version": "pdf_ready_manifest.v1",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "source_input_path": str(input_path),
        "canonical_paper_id": paper.get("canonical_paper_id"),
        "title": paper.get("title"),
        "doi": paper.get("doi"),
        "arxiv_id": paper.get("arxiv_id"),
        "openalex_id": paper.get("openalex_id"),
        "source_adapters": paper.get("source_adapters") or [],
        "pdf_url_count": len(urls),
        "pdf_url": redact_url(selected_pdf_url),
        "pdf_urls": [redact_url(url) for url in urls],
        "response_check_status": "not_checked_no_download",
        "known_content_type": content_type,
        "license": paper.get("license"),
        "license_name": paper.get("license_name"),
        "license_url": paper.get("license_url"),
        "license_checked_at": paper.get("license_checked_at"),
        "license_evidence_quote": paper.get("license_evidence_quote"),
        "license_token": license_token or None,
        "collection_basis": collection_basis(paper, category, pdf_policy),
        "fulltext_source_type": paper.get("fulltext_source_type"),
        "fulltext_review_scope": paper.get("fulltext_review_scope"),
        "redistribution_allowed": paper.get("redistribution_allowed") if isinstance(paper.get("redistribution_allowed"), bool) else False,
        "external_upload_allowed": external_upload_allowed(paper),
        "external_upload_allowed_source": (
            "paper_trace"
            if isinstance(paper.get("external_upload_allowed"), bool)
            else "default_false_no_explicit_basis"
        ),
        "category": category,
        "category_allowed_by_policy": category_allowed,
        "next_step_download_ready": next_step_download_ready,
        "download_performed": False,
        "missing_trace_fields": missing_trace_fields,
        "missing_trace_count": len(missing_trace_fields),
        "trace_complete": trace_complete,
        "exclusion_reasons": exclusion_reasons,
        "manual_review_reasons": manual_review_reasons,
        "policy_notes_ko": _policy_notes_ko(category, next_step_download_ready),
        "guardrails": {
            "no_pdf_download_performed": True,
            "no_external_upload": True,
            "no_redistribution": True,
            "no_score_adopted": True,
            "no_backtest_performed": True,
        },
    }


def summarize_manifest(
    rows: list[dict[str, Any]],
    *,
    input_path: Path,
    output_path: Path,
    run_id: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    counts = Counter(str(row["category"]) for row in rows)
    missing_trace_count = sum(1 for row in rows if row["missing_trace_count"] > 0)
    ready_count = sum(1 for row in rows if row["next_step_download_ready"])
    return {
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "input_path": str(input_path),
        "manifest_path": str(output_path),
        "paper_count": len(rows),
        "auto_cc_count": counts.get("auto_cc", 0),
        "noncommercial_cc_count": counts.get("noncommercial_cc", 0),
        "excluded_count": counts.get("excluded", 0),
        "manual_review_count": counts.get("manual_review", 0),
        "missing_trace_count": missing_trace_count,
        "next_step_download_ready_count": ready_count,
        "download_performed": False,
        "next_step_possible": ready_count > 0,
        "next_step_notes_ko": (
            "trace가 완비된 CC 후보가 있어 별도 승인 후 다음 단계 검토가 가능합니다."
            if ready_count
            else "trace가 완비된 CC 후보가 없어 다음 다운로드 단계로 진행하지 않습니다."
        ),
    }


def _category(license_token: str, exclusion_reasons: list[str], manual_review_reasons: list[str]) -> str:
    if exclusion_reasons:
        return "excluded"
    if manual_review_reasons:
        return "manual_review"
    if license_token in AUTO_CC_TOKENS:
        return "auto_cc"
    if license_token in NONCOMMERCIAL_CC_TOKENS:
        return "noncommercial_cc"
    return "manual_review"


def _policy_notes_ko(category: str, next_step_download_ready: bool) -> str:
    if next_step_download_ready:
        return "명시 license와 trace 필드가 있어 다음 단계 수동 검토 후보입니다. 이번 실행에서는 다운로드하지 않습니다."
    if category == "excluded":
        return "정책상 제외 또는 PDF URL 부족으로 다운로드 후보가 아닙니다."
    return "수동 검토가 필요합니다. 이번 실행에서는 다운로드하지 않습니다."


def _first_nonempty(values: list[str]) -> str | None:
    return next((value for value in values if value.strip()), None)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
