from __future__ import annotations

import json
import os

import pytest

from research_ingestion.sources.semantic_scholar_adapter import SemanticScholarAdapter


pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_RESEARCH_API_TESTS") != "1", reason="live API tests are opt-in")


def test_live_semantic_scholar_collect_one_record():
    adapter = SemanticScholarAdapter(
        {
            "default_limit": 1,
            "api_key_env_var": "SEMANTIC_SCHOLAR_API_KEY",
            "fields": ["paperId", "externalIds", "title", "authors", "year", "abstract", "url"],
        }
    )
    response = adapter.fetch_search_response("daily stock momentum", limit=1)
    assert response.ok
    papers = adapter.parse_search_json(json.loads(response.body))
    assert len(papers) <= 1
