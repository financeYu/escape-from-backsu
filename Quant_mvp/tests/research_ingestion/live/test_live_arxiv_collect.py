from __future__ import annotations

import os

import pytest

from research_ingestion.sources.arxiv_adapter import ArxivAdapter


pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_RESEARCH_API_TESTS") != "1", reason="live API tests are opt-in")


def test_live_arxiv_collect_one_record():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1, "default_max_results": 1})
    response = adapter.fetch_search_response("daily stock momentum", max_results=1)
    assert response.ok
    papers = adapter.parse_atom(response.body)
    assert len(papers) <= 1
