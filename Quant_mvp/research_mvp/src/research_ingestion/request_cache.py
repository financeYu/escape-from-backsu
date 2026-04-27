from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

from .persistence import ensure_parent, read_json, write_json
from .redaction import redact_mapping, redact_text
from .sources.http import SourceResponse


CACHE_FILENAME_HASH_CHARS = 32


@dataclass(frozen=True)
class CacheLookup:
    response: SourceResponse | None
    cache_key: str
    status: str


class RequestCache:
    def __init__(
        self,
        *,
        root: Path,
        enabled: bool,
        policy_version: str,
        ttl_days: int,
        redaction_env_vars: list[str] | None = None,
    ):
        self.root = root
        self.enabled = enabled
        self.policy_version = policy_version
        self.ttl_days = max(0, int(ttl_days))
        self.redaction_env_vars = redaction_env_vars or []

    def get(
        self,
        *,
        source: str,
        query: str,
        page_size: int,
        offset: int,
        page_number: int,
    ) -> CacheLookup:
        cache_key = self.cache_key(
            source=source,
            query=query,
            page_size=page_size,
            offset=offset,
            page_number=page_number,
        )
        if not self.enabled:
            return CacheLookup(response=None, cache_key=cache_key, status="disabled")
        path = self._cache_path(source, cache_key)
        payload = read_json(path, default=None)
        if not isinstance(payload, dict):
            return CacheLookup(response=None, cache_key=cache_key, status="miss")
        if payload.get("cache_key") not in {None, cache_key}:
            return CacheLookup(response=None, cache_key=cache_key, status="miss")
        if self._is_stale(payload):
            return CacheLookup(response=None, cache_key=cache_key, status="stale")
        response = payload.get("response") or {}
        return CacheLookup(
            response=SourceResponse(
                url=str(response.get("url") or ""),
                body=str(response.get("body") or ""),
                status=response.get("status"),
                headers=dict(response.get("headers") or {}),
                retry_count=int(response.get("retry_count", 0) or 0),
            ),
            cache_key=cache_key,
            status="hit",
        )

    def store(
        self,
        *,
        source: str,
        query: str,
        page_size: int,
        offset: int,
        page_number: int,
        response: SourceResponse,
    ) -> str:
        cache_key = self.cache_key(
            source=source,
            query=query,
            page_size=page_size,
            offset=offset,
            page_number=page_number,
        )
        if not self.enabled or not response.ok:
            return cache_key
        payload = {
            "source": source,
            "cache_key": cache_key,
            "query": query,
            "page_size": page_size,
            "offset": offset,
            "page_number": page_number,
            "policy_version": self.policy_version,
            "ttl_days": self.ttl_days,
            "cached_at_utc": _utc_now(),
            "response": {
                "url": redact_text(response.url, self.redaction_env_vars),
                "body": redact_text(response.body, self.redaction_env_vars),
                "status": response.status,
                "headers": redact_mapping(response.headers, env_var_names=self.redaction_env_vars),
                "retry_count": response.retry_count,
            },
        }
        path = self._cache_path(source, cache_key)
        ensure_parent(path)
        write_json(path, payload)
        return cache_key

    def cache_key(
        self,
        *,
        source: str,
        query: str,
        page_size: int,
        offset: int,
        page_number: int,
    ) -> str:
        payload = {
            "source": source,
            "query": query,
            "page_size": page_size,
            "offset": offset,
            "page_number": page_number,
            "policy_version": self.policy_version,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_path(self, source: str, cache_key: str) -> Path:
        return self.root / "data" / "research" / "request_cache" / source / f"{self._cache_filename(cache_key)}.json"

    def _cache_filename(self, cache_key: str) -> str:
        return str(cache_key)[:CACHE_FILENAME_HASH_CHARS]

    def _is_stale(self, payload: dict[str, Any]) -> bool:
        if self.ttl_days <= 0:
            return True
        cached_at = payload.get("cached_at_utc")
        if not cached_at:
            return True
        try:
            cached_dt = datetime.fromisoformat(str(cached_at).replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(UTC) - cached_dt > timedelta(days=self.ttl_days)


def request_cache_from_config(
    *,
    root: Path,
    config: dict[str, Any],
    query_set: dict[str, Any],
    redaction_env_vars: list[str] | None = None,
) -> RequestCache:
    policy = config.get("policy", {})
    metadata = policy.get("policy_metadata", {})
    cache_policy = policy.get("request_cache", {})
    refresh_policy = policy.get("refresh_policy", {})
    ttl_days = int(
        query_set.get("refresh_cadence_days")
        or cache_policy.get("default_ttl_days")
        or refresh_policy.get("interval_days")
        or 14
    )
    return RequestCache(
        root=root,
        enabled=bool(cache_policy.get("enabled", False)),
        policy_version=str(metadata.get("policy_version") or cache_policy.get("policy_version") or "research_policy.v1"),
        ttl_days=ttl_days,
        redaction_env_vars=redaction_env_vars,
    )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
