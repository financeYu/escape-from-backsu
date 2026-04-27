from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import os
from time import perf_counter
from typing import Any

from .config import ProjectPaths, get_source_config
from .persistence import store_raw_response
from .sources.arxiv_adapter import ArxivAdapter
from .sources.crossref_adapter import CrossrefAdapter
from .sources.nber_adapter import NberAdapter
from .sources.openalex_adapter import OpenAlexAdapter
from .sources.semantic_scholar_adapter import SemanticScholarAdapter


@dataclass(frozen=True)
class SourcePageFetch:
    response: Any
    cache_status: str
    cache_key: str | None
    request_latency_ms: float
    rate_limit_wait_seconds: float


def _adapter_total_wait_seconds(adapter: Any) -> float:
    limiter = getattr(adapter, "_rate_limiter", None)
    return float(getattr(limiter, "total_wait_seconds", 0.0) or 0.0)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000.0, 3)


def _request_metadata(
    adapter: Any,
    url: str,
    query_id: str,
    query_set: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
) -> dict[str, Any]:
    headers = adapter.request_headers() if hasattr(adapter, "request_headers") else {}
    metadata = adapter.request_metadata(url, headers) if hasattr(adapter, "request_metadata") else {"request_url": url, "headers": headers}
    return {
        "query_id": query_id,
        "query_set": query_set,
        "query": query,
        "page_size": page_size,
        "offset": offset,
        "page_number": page_number,
        "adapter_request": metadata,
    }


def _store_source_response_snapshot(
    *,
    paths: ProjectPaths,
    config: dict[str, Any],
    adapter: Any,
    source: str,
    run_id: str,
    response: Any,
    query_id: str,
    query_set: str,
    query: str,
    page_size: int,
    offset: int,
    page_number: int,
    cache_status: str = "disabled",
    cache_key: str | None = None,
) -> dict[str, Any]:
    request_metadata = _request_metadata(adapter, response.url, query_id, query_set, query, page_size, offset, page_number)
    request_metadata["request_cache"] = {
        "status": cache_status,
        "cache_key": cache_key,
        "raw_snapshot_preserved_for_run": True,
    }
    return store_raw_response(
        root=paths.root,
        source=source,
        run_id=run_id,
        response_body=response.body,
        suffix=_raw_suffix(source),
        request_metadata=request_metadata,
        http_status=response.status,
        retry_count=response.retry_count,
        redaction_env_vars=_redaction_env_vars(config, adapter),
    )


def _refresh_policy(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("policy", {}).get("refresh_policy", {})


def _dedup_ratio(collected_count: int, new_item_count: int) -> float:
    if collected_count <= 0:
        return 0.0
    ratio = 1.0 - (new_item_count / collected_count)
    return max(0.0, min(1.0, ratio))


def _adapter_for_source(source: str, config: dict[str, Any], adapter_registry: dict[str, Any] | None = None) -> Any:
    if adapter_registry is not None and source in adapter_registry:
        return adapter_registry[source]
    if source == "arxiv":
        return ArxivAdapter(get_source_config(config, "arxiv"))
    if source == "openalex":
        return OpenAlexAdapter(get_source_config(config, "openalex"))
    if source == "crossref":
        return CrossrefAdapter(get_source_config(config, "crossref"))
    if source == "semantic_scholar":
        return SemanticScholarAdapter(get_source_config(config, "semantic_scholar"))
    if source == "nber":
        return NberAdapter(get_source_config(config, "nber"))
    raise ValueError(f"승인되지 않은 research metadata source입니다: {source}")


def _source_adapter_registry(config: dict[str, Any], sources: list[str]) -> dict[str, Any]:
    return {source: _adapter_for_source(source, config) for source in sorted(set(sources))}


def _validate_sources(sources: list[str], config: dict[str, Any]) -> None:
    approved = {"arxiv", "openalex", "crossref", "semantic_scholar", "nber"}
    unknown = [source for source in sources if source not in approved]
    if unknown:
        raise ValueError(f"승인되지 않은 source입니다: {', '.join(unknown)}. 사용 가능: {', '.join(sorted(approved))}")
    disabled = [source for source in sources if not config["sources"]["sources"].get(source, {}).get("enabled", False)]
    if disabled:
        raise ValueError(f"config에서 비활성화된 source입니다: {', '.join(disabled)}")


def _validate_query_allowed_sources(sources: list[str], query_set: dict[str, Any]) -> None:
    allowed = [str(source) for source in query_set.get("allowed_sources", []) if str(source).strip()]
    if not allowed:
        return
    disallowed = [source for source in sources if source not in allowed]
    if disallowed:
        raise ValueError(
            "query-set allowed_sources 밖의 source입니다: "
            f"{', '.join(disallowed)}. 사용 가능: {', '.join(sorted(allowed))}"
        )



def _missing_key_note(source: str, adapter: Any) -> str | None:
    if source == "openalex" and getattr(adapter, "api_key_env_var", None) and not os.environ.get(adapter.api_key_env_var):
        if adapter.config.get("anonymous_allowed", False):
            return "OPENALEX_API_KEY가 없어 limited anonymous/demo mode로 실행합니다."
        return "OPENALEX_API_KEY가 없어 OpenAlex live 수집을 실행할 수 없습니다."
    if source == "semantic_scholar" and getattr(adapter, "api_key_env_var", None) and not os.environ.get(adapter.api_key_env_var):
        if adapter.config.get("public_without_key_allowed", True):
            return "SEMANTIC_SCHOLAR_API_KEY가 없어 public mode로 실행합니다."
        return "SEMANTIC_SCHOLAR_API_KEY가 없어 실행할 수 없습니다."
    if source == "crossref" and getattr(adapter, "polite_email_env_var", None) and not os.environ.get(adapter.polite_email_env_var):
        return "CROSSREF_MAILTO가 없어 기본 User-Agent로 실행합니다. 가능하면 polite email을 설정하세요."
    return None


def _missing_key_skip_reason(source: str, adapter: Any) -> str | None:
    note = _missing_key_note(source, adapter)
    if not note:
        return None
    if "실행할 수 없습니다" in note:
        return note
    return None


def _new_source_health(
    sources: list[str],
    config: dict[str, Any],
    adapter_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    health: dict[str, Any] = {}
    for source in sources:
        adapter = _adapter_for_source(source, config, adapter_registry=adapter_registry)
        health[source] = {
            "source": source,
            "adapter_version": "research_ingestion.v1",
            "query_set": None,
            "status": "planned",
            "request_count": 0,
            "rate_limit_wait_count": 0,
            "rate_limit_wait_seconds": 0.0,
            "request_latency_ms": 0.0,
            "parse_ms": 0.0,
            "dedupe_ms": 0.0,
            "classification_ms": 0.0,
            "success_count": 0,
            "failure_count": 0,
            "http_status_summary": Counter(),
            "http_429_count": 0,
            "parse_error_count": 0,
            "schema_error_count": 0,
            "dedup_ratio": None,
            "new_item_count": 0,
            "candidate_route_counts": {},
            "reject_reason_counts": {},
            "relevance_reject_reason_counts": {},
            "manual_review_required_count": 0,
            "request_cache_hit_count": 0,
            "request_cache_miss_count": 0,
            "request_cache_stale_count": 0,
            "unresolved_seed_count": 0,
            "pdf_download_attempt_count": 0,
            "rate_limit_observations": [],
            "missing_api_key_note_ko": _missing_key_note(source, adapter),
            "skipped_source_reason": None,
        }
    return health


def _empty_source_health(sources: list[str], skipped_reason: str) -> dict[str, Any]:
    return {
        source: {
            "source": source,
            "adapter_version": "research_ingestion.v1",
            "query_set": None,
            "status": "skipped",
            "request_count": 0,
            "rate_limit_wait_count": 0,
            "rate_limit_wait_seconds": 0.0,
            "request_latency_ms": 0.0,
            "parse_ms": 0.0,
            "dedupe_ms": 0.0,
            "classification_ms": 0.0,
            "success_count": 0,
            "failure_count": 0,
            "http_status_summary": {},
            "http_429_count": 0,
            "parse_error_count": 0,
            "schema_error_count": 0,
            "dedup_ratio": None,
            "new_item_count": 0,
            "candidate_route_counts": {},
            "reject_reason_counts": {},
            "relevance_reject_reason_counts": {},
            "manual_review_required_count": 0,
            "request_cache_hit_count": 0,
            "request_cache_miss_count": 0,
            "request_cache_stale_count": 0,
            "unresolved_seed_count": 0,
            "pdf_download_attempt_count": 0,
            "rate_limit_observations": [],
            "missing_api_key_note_ko": None,
            "skipped_source_reason": skipped_reason,
        }
        for source in sources
    }


def _raw_suffix(source: str) -> str:
    return ".xml" if source == "arxiv" else ".json"


def _redaction_env_vars(config: dict[str, Any], adapter: Any) -> list[str]:
    values = list(config["sources"].get("redaction", {}).get("redact_env_vars", []))
    for name in [
        getattr(adapter, "api_key_env_var", None),
        getattr(adapter, "mailto_env_var", None),
        getattr(adapter, "polite_email_env_var", None),
        getattr(adapter, "plus_api_token_env_var", None),
    ]:
        if name and name not in values:
            values.append(name)
    return values


def _safe_error_message(exc: Exception, redaction_env_vars: list[str] | None = None) -> str:
    message = str(exc)
    for name in [
        "OPENALEX_API_KEY",
        "OPENALEX_MAILTO",
        "SEMANTIC_SCHOLAR_API_KEY",
        "CROSSREF_MAILTO",
        "CROSSREF_PLUS_API_TOKEN",
        *(redaction_env_vars or []),
    ]:
        value = os.environ.get(name)
        if value:
            message = message.replace(value, "[REDACTED]")
    return message


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
