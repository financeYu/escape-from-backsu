from __future__ import annotations

from research_ingestion.normalize import make_normalized_paper, normalize_arxiv_id, normalize_doi, normalize_nber_id, validate_normalized_paper


def test_normalized_paper_schema(sample_paper):
    paper = sample_paper()
    validate_normalized_paper(paper)
    assert paper["canonical_paper_id"] == "doi:10.1000/example"


def test_identifier_normalization():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_arxiv_id("2401.12345v3") == "2401.12345"
    assert normalize_nber_id("https://www.nber.org/papers/12345") == "w12345"


def test_normalized_without_doi_uses_title_hash():
    paper = make_normalized_paper(title="No DOI paper", source_adapter="fixture")
    assert paper["canonical_paper_id"].startswith("titlehash:")


def test_normalized_without_doi_uses_nber_id_when_available():
    paper = make_normalized_paper(title="NBER paper", source_adapter="nber", nber_id="12345")
    assert paper["canonical_paper_id"] == "nber:w12345"
    assert paper["source_ids"]["nber_id"] == "w12345"


def test_missing_title_uses_conservative_metadata_placeholder():
    paper = make_normalized_paper(
        title="",
        source_adapter="openalex",
        openalex_id="https://openalex.org/W123",
        publication_year=2024,
        venue="Journal",
    )

    assert paper["title"] == "Untitled paper metadata from openalex (OpenAlex https://openalex.org/W123; year 2024; venue Journal)"
    assert paper["manual_review_required"] is True
    assert "source_title_missing_conservative_placeholder_used" in paper["conflict_notes"]


def test_missing_title_without_identifier_uses_source_url_to_avoid_collision():
    first = make_normalized_paper(
        title="",
        source_adapter="fixture",
        source_urls=["https://metadata.example.test/record/a"],
    )
    second = make_normalized_paper(
        title="",
        source_adapter="fixture",
        source_urls=["https://metadata.example.test/record/b"],
    )

    assert first["canonical_paper_id"] != second["canonical_paper_id"]
    assert "source URL https://metadata.example.test/record/a" in first["title"]
    assert "source URL https://metadata.example.test/record/b" in second["title"]
