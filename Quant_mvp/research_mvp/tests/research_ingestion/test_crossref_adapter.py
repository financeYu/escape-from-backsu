from __future__ import annotations

from research_ingestion.sources.crossref_adapter import CrossrefAdapter
from research_ingestion.sources.http import SourceResponse


def test_crossref_doi_fixture_parsing():
    payload = {
        "message": {
            "DOI": "10.1000/crossref",
            "title": ["Technical trading rules"],
            "author": [{"given": "A", "family": "Lee"}],
            "published-online": {"date-parts": [[2023, 5, 2]]},
            "container-title": ["Journal"],
            "URL": "https://doi.org/10.1000/crossref",
            "subject": ["Finance"],
            "is-referenced-by-count": 4,
        }
    }
    paper = CrossrefAdapter({}).parse_works_json(payload)[0]
    assert paper["doi"] == "10.1000/crossref"
    assert paper["authors"] == ["A Lee"]
    assert paper["publication_date"] == "2023-05-02"


def test_crossref_rate_limit_header_handling():
    parsed = CrossrefAdapter({}).parse_rate_limit_headers(
        {"X-Rate-Limit-Limit": "50", "X-Rate-Limit-Interval": "1s", "Retry-After": "2"}
    )
    assert parsed == {"limit": "50", "interval": "1s", "retry_after": "2"}


def test_crossref_parser_tolerates_malformed_optional_lists():
    payload = {
        "message": {
            "DOI": "10.1000/malformed",
            "title": [None, "Fallback title"],
            "author": [],
            "published-online": {"date-parts": [["bad-year"]]},
            "container-title": [None, "Fallback Journal"],
            "license": [None, {"content-version": "vor"}],
        }
    }

    paper = CrossrefAdapter({}).parse_works_json(payload)[0]

    assert paper["title"] == "Fallback title"
    assert paper["publication_date"] is None
    assert paper["venue"] == "Fallback Journal"
    assert paper["license"] == "vor"


def test_crossref_fetch_uses_configured_rate_limiter(monkeypatch):
    adapter = CrossrefAdapter({"min_interval_seconds": 1.0, "max_concurrency": 1})
    calls: list[str] = []

    def fake_fetch_text_with_retries(**kwargs):
        calls.append("fetch")
        return SourceResponse(url=kwargs["url"], body='{"message":{"items":[]}}', status=200, headers={}, retry_count=0)

    monkeypatch.setattr(adapter._rate_limiter, "wait_before_request", lambda: calls.append("wait"))
    monkeypatch.setattr(adapter._rate_limiter, "mark_request_complete", lambda: calls.append("mark"))
    monkeypatch.setattr("research_ingestion.sources.crossref_adapter.fetch_text_with_retries", fake_fetch_text_with_retries)

    adapter.fetch_search_response("momentum", rows=1)

    assert calls == ["wait", "fetch", "mark"]
