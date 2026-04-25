from __future__ import annotations

from research_ingestion.sources.semantic_scholar_adapter import SemanticScholarAdapter
from research_ingestion.sources.http import SourceResponse


def test_semantic_scholar_fixture_parsing_and_batch_payload():
    adapter = SemanticScholarAdapter({"fields": ["paperId", "title"], "default_limit": 10})
    payload = {
        "data": [
            {
                "paperId": "S2-1",
                "externalIds": {"DOI": "10.1000/s2", "ArXiv": "2401.00001v1"},
                "title": "Daily reversal",
                "authors": [{"name": "Kim"}],
                "year": 2022,
                "publicationDate": "2022-01-01",
                "venue": "S2 Venue",
                "abstract": "We define a reversal signal for daily returns.",
                "fieldsOfStudy": ["Finance"],
                "citationCount": 7,
                "influentialCitationCount": 1,
                "isRetracted": True,
                "isOpenAccess": True,
                "openAccessPdf": {"url": "https://example.test/s2.pdf"},
                "url": "https://semanticscholar.org/paper/S2-1",
            }
        ]
    }
    paper = adapter.parse_search_json(payload)[0]
    assert paper["semantic_scholar_id"] == "S2-1"
    assert paper["arxiv_id"] == "2401.00001"
    assert paper["fields_of_study"] == ["Finance"]
    assert paper["is_retracted"] is True
    assert adapter.build_batch_payload(["S2-1"])["ids"] == ["S2-1"]


def test_semantic_scholar_external_id_url_encodes_doi_slash():
    adapter = SemanticScholarAdapter({"fields": ["paperId", "title"]})
    url = adapter.build_paper_url("DOI:10.1000/example")
    assert "DOI:10.1000%2Fexample" in url


def test_semantic_scholar_fetch_uses_configured_rate_limiter(monkeypatch):
    adapter = SemanticScholarAdapter({"fields": ["paperId", "title"], "min_interval_seconds": 1.0, "max_concurrency": 1})
    calls: list[str] = []

    def fake_fetch_text_with_retries(**kwargs):
        calls.append("fetch")
        return SourceResponse(url=kwargs["url"], body='{"data":[]}', status=200, headers={}, retry_count=0)

    monkeypatch.setattr(adapter._rate_limiter, "wait_before_request", lambda: calls.append("wait"))
    monkeypatch.setattr(adapter._rate_limiter, "mark_request_complete", lambda: calls.append("mark"))
    monkeypatch.setattr("research_ingestion.sources.semantic_scholar_adapter.fetch_text_with_retries", fake_fetch_text_with_retries)

    adapter.fetch_search_response("momentum", limit=1)

    assert calls == ["wait", "fetch", "mark"]
