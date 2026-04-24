from __future__ import annotations

import json
import os

import pytest

from research_ingestion.sources.openalex_adapter import OpenAlexAdapter


pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_RESEARCH_API_TESTS") != "1", reason="live API tests are opt-in")


def test_live_openalex_collect_one_record():
    adapter = OpenAlexAdapter({"default_per_page": 1, "api_key_env_var": "OPENALEX_API_KEY"})
    response = adapter.fetch_search_response("daily stock momentum", per_page=1)
    assert response.ok
    papers = adapter.parse_works_json(json.loads(response.body))
    assert len(papers) <= 1
