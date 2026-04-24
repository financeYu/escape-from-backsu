from __future__ import annotations

from research_ingestion.normalize import make_normalized_paper, normalize_arxiv_id, normalize_doi, validate_normalized_paper


def test_normalized_paper_schema(sample_paper):
    paper = sample_paper()
    validate_normalized_paper(paper)
    assert paper["canonical_paper_id"] == "doi:10.1000/example"


def test_identifier_normalization():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_arxiv_id("2401.12345v3") == "2401.12345"


def test_normalized_without_doi_uses_title_hash():
    paper = make_normalized_paper(title="No DOI paper", source_adapter="fixture")
    assert paper["canonical_paper_id"].startswith("titlehash:")
