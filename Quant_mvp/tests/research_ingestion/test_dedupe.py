from __future__ import annotations

from research_ingestion.dedupe import deduplicate_papers


def test_dedupe_by_doi(sample_paper):
    paper = sample_paper()
    duplicate = dict(paper)
    duplicate["source_adapters"] = ["openalex"]
    merged = deduplicate_papers([paper, duplicate])
    assert len(merged) == 1
    assert "openalex" in merged[0]["source_adapters"]


def test_dedupe_by_arxiv(sample_paper):
    left = sample_paper(doi=None, arxiv_id="2401.00001", title="Arxiv test")
    right = sample_paper(doi=None, arxiv_id="2401.00001v2", title="Arxiv test updated", source_adapter="arxiv")
    assert len(deduplicate_papers([left, right])) == 1


def test_dedupe_by_title_year_first_author(sample_paper):
    left = sample_paper(doi=None, title="Daily momentum in stocks", authors=["Jane Doe"], publication_year=2024)
    right = sample_paper(doi=None, title="Daily Momentum in Stocks!", authors=["Jane Doe"], publication_year=2024, source_adapter="openalex")
    assert len(deduplicate_papers([left, right])) == 1
