from __future__ import annotations

from research_ingestion.sources.crossref_adapter import CrossrefAdapter


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
