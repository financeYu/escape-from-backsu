from __future__ import annotations

from research_ingestion.sources.semantic_scholar_adapter import SemanticScholarAdapter


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
    assert adapter.build_batch_payload(["S2-1"])["ids"] == ["S2-1"]
