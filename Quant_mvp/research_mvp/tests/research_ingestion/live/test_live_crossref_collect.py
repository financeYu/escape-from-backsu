from __future__ import annotations

import json
import os

import pytest

from research_ingestion.sources.crossref_adapter import CrossrefAdapter


pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_RESEARCH_API_TESTS") != "1", reason="live API tests are opt-in")


def test_live_crossref_collect_one_record():
    adapter = CrossrefAdapter({"default_rows": 1, "polite_email_env_var": "CROSSREF_MAILTO"})
    response = adapter.fetch_search_response("daily stock momentum", rows=1)
    assert response.ok
    papers = adapter.parse_works_json(json.loads(response.body))
    assert len(papers) <= 1
