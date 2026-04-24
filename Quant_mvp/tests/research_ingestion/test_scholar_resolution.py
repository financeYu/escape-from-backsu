from __future__ import annotations

import pytest

from research_ingestion.discovery.schema import make_discovery_seed
from research_ingestion.discovery.scholar_resolution import assert_approved_resolution_url, resolve_seed, write_unresolved_scholar_seeds


def test_scholar_seed_resolution_by_doi(sample_paper):
    paper = sample_paper()
    seed = make_discovery_seed(
        source_channel="google_scholar_manual_title_list",
        raw_title="Daily momentum and reversal in equity returns",
        raw_year=2024,
        candidate_doi="10.1000/example",
        local_input_path="titles.csv",
    )
    resolved = resolve_seed(seed, {"openalex": [paper]})
    assert resolved["canonical_lookup_status"] == "matched_openalex"
    assert resolved["canonical_paper_id"] == paper["canonical_paper_id"]
    assert resolved["manual_review_required"] is False


def test_unresolved_scholar_seed_reporting(workspace_tmp_path):
    seed = make_discovery_seed(
        source_channel="google_scholar_manual_title_list",
        raw_title="Unknown title",
        local_input_path="titles.txt",
    )
    resolved = resolve_seed(seed, {"openalex": []})
    out = workspace_tmp_path / "unresolved.jsonl"
    write_unresolved_scholar_seeds(out, [resolved])
    assert "Unknown title" in out.read_text(encoding="utf-8")


def test_guard_fails_on_live_scholar_request():
    with pytest.raises(RuntimeError):
        assert_approved_resolution_url("https://scholar.google.com/scholar?q=momentum")


def test_scholar_seed_resolution_ignores_malformed_raw_authors(sample_paper):
    paper = sample_paper()
    seed = make_discovery_seed(
        source_channel="google_scholar_manual_title_list",
        raw_title="Daily momentum and reversal in equity returns",
        raw_year=2024,
        local_input_path="titles.csv",
    )
    seed["raw_authors"] = "Jane Doe"

    resolved = resolve_seed(seed, {"openalex": [paper]})

    assert resolved["canonical_lookup_status"] == "matched_openalex"
