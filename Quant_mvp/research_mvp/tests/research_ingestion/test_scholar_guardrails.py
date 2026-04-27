from __future__ import annotations

import pytest

from research_ingestion.redaction import assert_no_scholar_request


@pytest.mark.parametrize(
    "url",
    [
        "https://scholar.google.com/scholar?q=momentum",
        "https://scholar.google.com/scholar?start=10&q=momentum",
        "https://scholar.google.com/search?q=momentum",
    ],
)
def test_google_scholar_direct_urls_are_blocked(url):
    with pytest.raises(RuntimeError):
        assert_no_scholar_request(url)
