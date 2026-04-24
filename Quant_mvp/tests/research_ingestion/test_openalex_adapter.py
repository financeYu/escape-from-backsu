from __future__ import annotations

from research_ingestion.sources.openalex_adapter import OpenAlexAdapter, reconstruct_abstract


OPENALEX_PAYLOAD = {
    "results": [
        {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1000/openalex",
            "title": "Momentum with liquidity",
            "authorships": [{"author": {"display_name": "Jane Doe"}}],
            "publication_year": 2024,
            "publication_date": "2024-03-02",
            "primary_location": {"source": {"display_name": "Quant Journal"}, "landing_page_url": "https://example.test/paper"},
            "best_oa_location": {"license": "cc-by", "pdf_url": "https://example.test/paper.pdf"},
            "abstract_inverted_index": {"Momentum": [0], "uses": [1], "volume": [2]},
            "topics": [{"display_name": "Technical analysis"}],
            "primary_topic": {"display_name": "Finance"},
            "open_access": {"is_oa": True, "oa_status": "gold"},
            "cited_by_count": 10,
            "is_retracted": True,
        }
    ]
}


def test_openalex_abstract_reconstruction():
    assert reconstruct_abstract({"a": [0], "test": [1]}) == "a test"


def test_openalex_json_parsing_topics_and_retraction():
    adapter = OpenAlexAdapter({"base_url": "https://api.openalex.org/works"})
    paper = adapter.parse_works_json(OPENALEX_PAYLOAD)[0]
    assert paper["openalex_id"] == "https://openalex.org/W1"
    assert paper["abstract"] == "Momentum uses volume"
    assert "Finance" in paper["topics"]
    assert "Technical analysis" in paper["topics"]
    assert paper["is_retracted"] is True


def test_openalex_redacts_api_key_in_request_metadata(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-openalex-key")
    adapter = OpenAlexAdapter({"base_url": "https://api.openalex.org/works", "api_key_env_var": "OPENALEX_API_KEY"})
    metadata = adapter.request_metadata("https://api.openalex.org/works?api_key=secret-openalex-key")
    assert "secret-openalex-key" not in str(metadata)
