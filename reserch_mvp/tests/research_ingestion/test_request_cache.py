from __future__ import annotations

from research_ingestion.request_cache import RequestCache
from research_ingestion.sources.http import SourceResponse


def test_request_cache_key_uses_policy_version_and_page_fields(workspace_tmp_path):
    cache_v1 = RequestCache(root=workspace_tmp_path, enabled=True, policy_version="policy.v1", ttl_days=7)
    cache_v2 = RequestCache(root=workspace_tmp_path, enabled=True, policy_version="policy.v2", ttl_days=7)

    key_v1 = cache_v1.cache_key(source="openalex", query="momentum", page_size=25, offset=0, page_number=1)
    key_v2 = cache_v2.cache_key(source="openalex", query="momentum", page_size=25, offset=0, page_number=1)
    key_page_2 = cache_v1.cache_key(source="openalex", query="momentum", page_size=25, offset=25, page_number=2)

    assert key_v1 != key_v2
    assert key_v1 != key_page_2


def test_request_cache_returns_cached_source_response(workspace_tmp_path):
    cache = RequestCache(root=workspace_tmp_path, enabled=True, policy_version="policy.v1", ttl_days=7)
    response = SourceResponse(
        url="https://api.openalex.org/works?search=momentum",
        body='{"results":[]}',
        status=200,
        headers={"content-type": "application/json"},
        retry_count=0,
    )

    cache.store(
        source="openalex",
        query="momentum",
        page_size=25,
        offset=0,
        page_number=1,
        response=response,
    )
    lookup = cache.get(source="openalex", query="momentum", page_size=25, offset=0, page_number=1)

    assert lookup.status == "hit"
    assert lookup.response is not None
    assert lookup.response.body == '{"results":[]}'
