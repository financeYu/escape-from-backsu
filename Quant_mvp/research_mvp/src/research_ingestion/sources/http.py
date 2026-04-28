from __future__ import annotations

from collections.abc import Callable
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

MAX_SOURCE_RESPONSE_WAIT_SECONDS = 300.0


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


class SourceResponseTimeoutSkip(TimeoutError):
    """Raised when a source response waits too long and should be skipped."""


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
    timeout_seconds = _bounded_response_timeout_seconds(timeout_seconds)
    retryable = _retry_statuses(retry_statuses)
    attempts = _request_attempts(max_retries)
    if requests is not None:
        return _fetch_with_requests(
            url=url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            attempts=attempts,
            retryable=retryable,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    return _urlopen_with_retries(
        url=url,
        request_factory=lambda: Request(url, headers=headers),
        timeout_seconds=timeout_seconds,
        attempts=attempts,
        retryable=retryable,
        retry_backoff_seconds=retry_backoff_seconds,
        failure_message="source request failed without a response",
    )


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
    timeout_seconds = _bounded_response_timeout_seconds(timeout_seconds)
    retryable = _retry_statuses(retry_statuses)
    attempts = _request_attempts(max_retries)
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
    return _urlopen_with_retries(
        url=url,
        request_factory=lambda: Request(url, headers=request_headers, data=body, method="POST"),
        timeout_seconds=timeout_seconds,
        attempts=attempts,
        retryable=retryable,
        retry_backoff_seconds=retry_backoff_seconds,
        failure_message="source POST request failed without a response",
    )


def _retry_statuses(retry_statuses: set[int] | None) -> set[int]:
    return retry_statuses or {429, 500, 502, 503, 504}


def _request_attempts(max_retries: int) -> int:
    return max(0, int(max_retries)) + 1


def _bounded_response_timeout_seconds(timeout_seconds: float) -> float:
    return min(max(0.001, float(timeout_seconds)), MAX_SOURCE_RESPONSE_WAIT_SECONDS)


def _urlopen_with_retries(
    *,
    url: str,
    request_factory: Callable[[], Request],
    timeout_seconds: float,
    attempts: int,
    retryable: set[int],
    retry_backoff_seconds: float,
    failure_message: str,
) -> SourceResponse:
    last_error: URLError | None = None

    for attempt in range(attempts):
        started = time.monotonic()
        try:
            with urlopen(request_factory(), timeout=timeout_seconds) as response:
                return _response_from_urlopen(url, response, attempt)
        except HTTPError as exc:
            if exc.code in retryable and attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt, exc.headers.get("Retry-After"))
                continue
            return _response_from_http_error(url, exc, attempt)
        except URLError as exc:
            last_error = exc
            if _is_timeout_exception(exc) and _waited_at_least_skip_threshold(started):
                raise SourceResponseTimeoutSkip(
                    "source response exceeded no-response threshold=300s; skipping this source page"
                ) from exc
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError(failure_message)


def _response_from_urlopen(url: str, response, retry_count: int) -> SourceResponse:
    raw = response.read()
    return SourceResponse(
        url=url,
        body=raw.decode("utf-8", errors="replace"),
        status=getattr(response, "status", None) or response.getcode(),
        headers={key: value for key, value in response.headers.items()},
        retry_count=retry_count,
    )


def _response_from_http_error(url: str, exc: HTTPError, retry_count: int) -> SourceResponse:
    raw = exc.read()
    return SourceResponse(
        url=url,
        body=raw.decode("utf-8", errors="replace"),
        status=exc.code,
        headers={key: value for key, value in exc.headers.items()},
        retry_count=retry_count,
    )


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
        started = time.monotonic()
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
            if _is_timeout_exception(exc) and _waited_at_least_skip_threshold(started):
                raise SourceResponseTimeoutSkip(
                    "source response exceeded no-response threshold=300s; skipping this source page"
                ) from exc
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
        started = time.monotonic()
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
            if _is_timeout_exception(exc) and _waited_at_least_skip_threshold(started):
                raise SourceResponseTimeoutSkip(
                    "source response exceeded no-response threshold=300s; skipping this source page"
                ) from exc
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


def _is_timeout_exception(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if requests is not None and isinstance(exc, requests.Timeout):  # type: ignore[union-attr]
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, BaseException):
        return _is_timeout_exception(reason)
    name = type(exc).__name__.lower()
    return "timeout" in name or "timed out" in str(exc).lower()


def _waited_at_least_skip_threshold(started: float) -> bool:
    return (time.monotonic() - started) >= MAX_SOURCE_RESPONSE_WAIT_SECONDS
