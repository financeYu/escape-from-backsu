from __future__ import annotations

import pytest

from research_ingestion.sources import http as http_module
from research_ingestion.sources.http import (
    SourceRateLimiter,
    SourceResponseTimeoutSkip,
    _bounded_response_timeout_seconds,
    fetch_text_with_retries,
    _retry_after_seconds,
)


def test_retry_after_seconds_numeric_value():
    assert _retry_after_seconds("2") == 2.0


def test_retry_after_seconds_invalid_value_returns_none():
    assert _retry_after_seconds("not-a-date") is None


def test_response_timeout_is_capped_at_five_minutes():
    assert _bounded_response_timeout_seconds(999.0) == 300.0


def test_short_configured_timeout_does_not_skip_before_five_minutes(monkeypatch):
    calls: list[float] = []

    def fake_get(url, headers, timeout):
        calls.append(timeout)
        raise http_module.requests.Timeout("timed out")

    times = iter([0.0, 20.0, 21.0, 41.0])
    monkeypatch.setattr(http_module.requests, "get", fake_get)
    monkeypatch.setattr(http_module.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(http_module.time, "sleep", lambda seconds: None)

    with pytest.raises(http_module.requests.Timeout):
        fetch_text_with_retries(
            url="https://api.example.test/works",
            headers={},
            timeout_seconds=20.0,
            max_retries=1,
        )

    assert calls == [20.0, 20.0]


def test_five_minute_timeout_is_recorded_as_skip(monkeypatch):
    calls: list[float] = []

    def fake_get(url, headers, timeout):
        calls.append(timeout)
        raise http_module.requests.Timeout("timed out")

    times = iter([0.0, 301.0])
    monkeypatch.setattr(http_module.requests, "get", fake_get)
    monkeypatch.setattr(http_module.time, "monotonic", lambda: next(times))

    with pytest.raises(SourceResponseTimeoutSkip):
        fetch_text_with_retries(
            url="https://api.example.test/works",
            headers={},
            timeout_seconds=999.0,
            max_retries=1,
        )

    assert calls == [300.0]


def test_source_rate_limiter_sleeps_for_remaining_interval(monkeypatch):
    limiter = SourceRateLimiter(min_interval_seconds=1.0, max_concurrency=1, source_name="test")
    limiter._last_request_ts = 10.0
    sleeps: list[float] = []

    monkeypatch.setattr("research_ingestion.sources.http.time.monotonic", lambda: 10.25)
    monkeypatch.setattr("research_ingestion.sources.http.time.sleep", lambda seconds: sleeps.append(seconds))

    limiter.wait_before_request()

    assert sleeps == [0.75]


def test_source_rate_limiter_rejects_unsupported_concurrency():
    with pytest.raises(ValueError):
        SourceRateLimiter(min_interval_seconds=1.0, max_concurrency=2, source_name="test")
