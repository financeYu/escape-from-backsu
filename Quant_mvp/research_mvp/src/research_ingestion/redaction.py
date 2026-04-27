from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DEFAULT_SECRET_QUERY_KEYS = {"api_key", "apikey", "token", "key"}
DEFAULT_SECRET_HEADERS = {"authorization", "x-api-key", "crossref-plus-api-token"}
REDACTED = "[REDACTED]"


def _configured_values(env_var_names: list[str] | None = None) -> set[str]:
    values: set[str] = set()
    for name in env_var_names or []:
        value = os.environ.get(name)
        if value:
            values.add(value)
    return values


def redact_text(text: str | None, env_var_names: list[str] | None = None) -> str | None:
    if text is None:
        return None
    redacted = str(text)
    for value in _configured_values(env_var_names):
        redacted = redacted.replace(value, REDACTED)
    return redacted


def redact_url(
    url: str | None,
    secret_query_keys: set[str] | None = None,
    env_var_names: list[str] | None = None,
) -> str | None:
    if not url:
        return url
    secret_keys = {key.lower() for key in (secret_query_keys or DEFAULT_SECRET_QUERY_KEYS)}
    parts = urlsplit(redact_text(url, env_var_names) or "")
    query = [
        (key, REDACTED if key.lower() in secret_keys else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def redact_headers(
    headers: Mapping[str, object] | None,
    secret_headers: set[str] | None = None,
    env_var_names: list[str] | None = None,
) -> dict[str, object]:
    if not headers:
        return {}
    secret = {name.lower() for name in (secret_headers or DEFAULT_SECRET_HEADERS)}
    result: dict[str, object] = {}
    for key, value in headers.items():
        lowered = str(key).lower()
        if lowered in secret:
            result[str(key)] = REDACTED
        elif isinstance(value, str):
            result[str(key)] = redact_text(value, env_var_names)
        else:
            result[str(key)] = redact_mapping(value, secret_headers=secret, env_var_names=env_var_names)
    return result


def redact_mapping(
    value: object,
    *,
    secret_query_keys: set[str] | None = None,
    secret_headers: set[str] | None = None,
    env_var_names: list[str] | None = None,
) -> object:
    if isinstance(value, str):
        return redact_text(value, env_var_names)
    if isinstance(value, list):
        return [
            redact_mapping(
                item,
                secret_query_keys=secret_query_keys,
                secret_headers=secret_headers,
                env_var_names=env_var_names,
            )
            for item in value
        ]
    if not isinstance(value, Mapping):
        return deepcopy(value)

    result: dict[str, object] = {}
    header_keys = {name.lower() for name in (secret_headers or DEFAULT_SECRET_HEADERS)}
    query_keys = {name.lower() for name in (secret_query_keys or DEFAULT_SECRET_QUERY_KEYS)}
    for key, item in value.items():
        lowered = str(key).lower()
        if lowered in header_keys or lowered in query_keys:
            result[str(key)] = REDACTED
        elif lowered in {"url", "request_url", "raw_link"}:
            result[str(key)] = redact_url(str(item), query_keys, env_var_names)
        elif lowered == "headers" and isinstance(item, Mapping):
            result[str(key)] = redact_headers(item, header_keys, env_var_names=env_var_names)
        else:
            result[str(key)] = redact_mapping(
                item,
                secret_query_keys=query_keys,
                secret_headers=header_keys,
                env_var_names=env_var_names,
            )
    return result


def assert_no_scholar_request(url: str) -> None:
    host = urlsplit(url).netloc.lower()
    if host == "scholar.google.com" or host.endswith(".scholar.google.com"):
        raise RuntimeError("Live requests to scholar.google.com are prohibited.")
