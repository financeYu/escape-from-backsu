from __future__ import annotations

import pytest

from research_ingestion.sources.http import SourceRateLimiter, _retry_after_seconds


def test_retry_after_seconds_numeric_value():
    assert _retry_after_seconds("2") == 2.0


def test_retry_after_seconds_invalid_value_returns_none():
    assert _retry_after_seconds("not-a-date") is None


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
