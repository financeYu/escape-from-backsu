from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..redaction import assert_no_scholar_request

try:  # Prefer the installed project/runtime HTTP stack when available.
    import requests
except Exception:  # pragma: no cover - exercised only when requests is absent.
    requests = None  # type: ignore[assignment]


@dataclass(frozen=True)
class SourceResponse:
    url: str
    body: str
    status: int | None
    headers: dict[str, str]
    retry_count: int

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300


class SourceRateLimiter:
    def __init__(self, *, min_interval_seconds: float = 0.0, max_concurrency: int = 1, source_name: str = "source"):
        self.min_interval_seconds = max(0.0, float(min_interval_seconds))
        self.max_concurrency = int(max_concurrency)
        self.source_name = source_name
        self._last_request_ts = 0.0
        self.last_wait_seconds = 0.0
        self.total_wait_seconds = 0.0
        self.wait_count = 0
        if self.max_concurrency != 1:
            raise ValueError(f"{source_name} max_concurrency must be 1 for synchronous collection.")

    def wait_before_request(self) -> float:
        elapsed = time.monotonic() - self._last_request_ts
        wait_seconds = 0.0
        if elapsed < self.min_interval_seconds:
            wait_seconds = self.min_interval_seconds - elapsed
            time.sleep(wait_seconds)
        self.last_wait_seconds = wait_seconds
        if wait_seconds > 0:
            self.total_wait_seconds += wait_seconds
            self.wait_count += 1
        return wait_seconds

    def mark_request_complete(self) -> None:
        self._last_request_ts = time.monotonic()


def fetch_text_with_retries(
    *,
    url: str,
    headers: dict[str, str],
    timeout_seconds: float,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.0,
    retry_statuses: set[int] | None = None,
) -> SourceResponse:
    assert_no_scholar_request(url)
    retryable = retry_statuses or {429, 500, 502, 503, 504}
    attempts = max(0, int(max_retries)) + 1
    if requests is not None:
        return _fetch_with_requests(
            url=url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            attempts=attempts,
            retryable=retryable,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    last_error: URLError | None = None

    for attempt in range(attempts):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
                return SourceResponse(
                    url=url,
                    body=raw.decode("utf-8", errors="replace"),
                    status=getattr(response, "status", None) or response.getcode(),
                    headers={key: value for key, value in response.headers.items()},
                    retry_count=attempt,
                )
        except HTTPError as exc:
            raw = exc.read()
            if exc.code in retryable and attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt, exc.headers.get("Retry-After"))
                continue
            return SourceResponse(
                url=url,
                body=raw.decode("utf-8", errors="replace"),
                status=exc.code,
                headers={key: value for key, value in exc.headers.items()},
                retry_count=attempt,
            )
        except URLError as exc:
            last_error = exc
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("source request failed without a response")


def post_json_with_retries(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout_seconds: float,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.0,
    retry_statuses: set[int] | None = None,
) -> SourceResponse:
    assert_no_scholar_request(url)
    retryable = retry_statuses or {429, 500, 502, 503, 504}
    attempts = max(0, int(max_retries)) + 1
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **headers}
    if requests is not None:
        return _post_with_requests(
            url=url,
            headers=request_headers,
            payload=payload,
            timeout_seconds=timeout_seconds,
            attempts=attempts,
            retryable=retryable,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    last_error: URLError | None = None

    for attempt in range(attempts):
        request = Request(url, headers=request_headers, data=body, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
                return SourceResponse(
                    url=url,
                    body=raw.decode("utf-8", errors="replace"),
                    status=getattr(response, "status", None) or response.getcode(),
                    headers={key: value for key, value in response.headers.items()},
                    retry_count=attempt,
                )
        except HTTPError as exc:
            raw = exc.read()
            if exc.code in retryable and attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt, exc.headers.get("Retry-After"))
                continue
            return SourceResponse(
                url=url,
                body=raw.decode("utf-8", errors="replace"),
                status=exc.code,
                headers={key: value for key, value in exc.headers.items()},
                retry_count=attempt,
            )
        except URLError as exc:
            last_error = exc
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("source POST request failed without a response")


def _fetch_with_requests(
    *,
    url: str,
    headers: dict[str, str],
    timeout_seconds: float,
    attempts: int,
    retryable: set[int],
    retry_backoff_seconds: float,
) -> SourceResponse:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout_seconds)  # type: ignore[union-attr]
            if response.status_code in retryable and attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt, response.headers.get("Retry-After"))
                continue
            return SourceResponse(
                url=url,
                body=response.text,
                status=response.status_code,
                headers={key: value for key, value in response.headers.items()},
                retry_count=attempt,
            )
        except requests.RequestException as exc:  # type: ignore[union-attr]
            last_error = exc
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("source request failed without a response")


def _post_with_requests(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout_seconds: float,
    attempts: int,
    retryable: set[int],
    retry_backoff_seconds: float,
) -> SourceResponse:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)  # type: ignore[union-attr]
            if response.status_code in retryable and attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt, response.headers.get("Retry-After"))
                continue
            return SourceResponse(
                url=url,
                body=response.text,
                status=response.status_code,
                headers={key: value for key, value in response.headers.items()},
                retry_count=attempt,
            )
        except requests.RequestException as exc:  # type: ignore[union-attr]
            last_error = exc
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("source POST request failed without a response")


def _sleep_before_retry(backoff_seconds: float, attempt: int, retry_after: str | None = None) -> None:
    delay = _retry_after_seconds(retry_after)
    if delay is None:
        delay = max(0.0, float(backoff_seconds)) * (attempt + 1)
    if delay:
        time.sleep(delay)


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    stripped = value.strip()
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(stripped)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
