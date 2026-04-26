from __future__ import annotations

from research_ingestion import dedupe
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


def test_dedupe_updates_incremental_index_after_merge(sample_paper, monkeypatch):
    rebuild_calls = []

    def fail_rebuild(self, papers):
        rebuild_calls.append(len(papers))
        raise AssertionError("dedupe should not rebuild the full index for each merge")

    monkeypatch.setattr(dedupe.PaperDedupeIndex, "rebuild", fail_rebuild)
    left = sample_paper(doi="10.1000/base", title="Base momentum paper", source_adapter="openalex")
    duplicate_with_new_id = sample_paper(
        doi="10.1000/base",
        semantic_scholar_id="S2-base",
        title="Base momentum paper",
        source_adapter="semantic_scholar",
    )
    later_semantic_duplicate = sample_paper(
        doi=None,
        semantic_scholar_id="S2-base",
        title="Base momentum paper duplicate",
        source_adapter="semantic_scholar",
    )

    merged = deduplicate_papers([left, duplicate_with_new_id, later_semantic_duplicate])

    assert rebuild_calls == []
    assert len(merged) == 1
    assert "semantic_scholar" in merged[0]["source_adapters"]
