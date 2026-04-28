from __future__ import annotations

import json

from research_ingestion.sources.http import SourceResponse
from research_ingestion.sources.nber_adapter import NberAdapter


def _payload(**files: str) -> dict:
    return {
        "query": "momentum",
        "limit": 10,
        "offset": 0,
        "files": {
            name: {"url": f"https://data.nber.org/nber_paper_chapter_metadata/tsv/{name}.tsv", "status": 200, "body": body}
            for name, body in files.items()
        },
        "metadata_license": "nber_public_metadata",
    }


def test_nber_parse_tsv_dump_normalizes_metadata_only_record():
    adapter = NberAdapter({})
    payload = _payload(
        ref=(
            "paper\tauthor\ttitle\tissue_date\tdoi\n"
            "w12345\tJane Doe and John Smith\tMomentum and Reversal in Equity Returns\t2024-02-01\t10.3386/w12345\n"
            "w99999\tOther Author\tUnrelated Public Economics Paper\t2023-01-01\t\n"
        ),
        abs="paper\tabstract\nw12345\tWe study momentum in equity returns.\n",
        auth="paper\tauthor\nw12345\tJane Doe\nw12345\tJohn Smith\n",
        auths="paper\tname\n",
        title="paper\ttitle\n",
        jel="paper\tjel\nw12345\tG12\n",
        prog="paper\tprogram\nw12345\tAsset Pricing\n",
        published="paper\tpublished_text\nw12345\tNBER Working Paper\n",
    )

    papers = adapter.parse_dump_json(payload, raw_snapshot_ref="raw/nber/snapshot.json")

    assert len(papers) == 1
    paper = papers[0]
    assert paper["canonical_paper_id"] == "doi:10.3386/w12345"
    assert paper["nber_id"] == "w12345"
    assert paper["source_ids"]["nber_id"] == "w12345"
    assert paper["authors"] == ["Jane Doe", "John Smith"]
    assert paper["abstract_available"] is True
    assert paper["pdf_urls"] == []
    assert paper["pdf_downloaded"] is False
    assert paper["license_collection_allowed"] is True
    assert paper["license_noncommercial_allowed"] is True


def test_nber_without_doi_uses_nber_canonical_id():
    adapter = NberAdapter({})
    payload = _payload(
        ref="paper\tauthor\ttitle\tissue_date\tdoi\n12345\tJane Doe\tMomentum Research\t2024-02-01\t\n",
        abs="paper\tabstract\nw12345\tMomentum abstract.\n",
    )

    paper = adapter.parse_dump_json(payload)[0]

    assert paper["canonical_paper_id"] == "nber:w12345"
    assert paper["nber_id"] == "w12345"


def test_nber_fetch_uses_configured_rate_limiter(monkeypatch):
    adapter = NberAdapter({"files": ["ref", "abs"], "min_interval_seconds": 1.0, "max_concurrency": 1})
    calls: list[str] = []

    def fake_fetch_text_with_retries(**kwargs):
        calls.append(kwargs["url"].rsplit("/", 1)[-1])
        return SourceResponse(url=kwargs["url"], body="paper\ttitle\n", status=200, headers={}, retry_count=0)

    monkeypatch.setattr(adapter._rate_limiter, "wait_before_request", lambda: calls.append("wait"))
    monkeypatch.setattr(adapter._rate_limiter, "mark_request_complete", lambda: calls.append("mark"))
    monkeypatch.setattr("research_ingestion.sources.nber_adapter.fetch_text_with_retries", fake_fetch_text_with_retries)

    response = adapter.fetch_search_response("momentum", limit=1)
    body = json.loads(response.body)

    assert calls == ["wait", "ref.tsv", "mark", "wait", "abs.tsv", "mark"]
    assert sorted(body["files"]) == ["abs", "ref"]


def test_nber_optional_file_404_does_not_fail_source(monkeypatch):
    adapter = NberAdapter({"files": ["ref", "auths"]})
    responses = {
        "ref.tsv": SourceResponse(
            url="https://data.nber.org/nber_paper_chapter_metadata/tsv/ref.tsv",
            body="paper\ttitle\nw12345\tMomentum Research\n",
            status=200,
            headers={},
            retry_count=0,
        ),
        "auths.tsv": SourceResponse(
            url="https://data.nber.org/nber_paper_chapter_metadata/tsv/auths.tsv",
            body="",
            status=404,
            headers={},
            retry_count=0,
        ),
    }

    def fake_fetch_text_with_retries(**kwargs):
        return responses[kwargs["url"].rsplit("/", 1)[-1]]

    monkeypatch.setattr("research_ingestion.sources.nber_adapter.fetch_text_with_retries", fake_fetch_text_with_retries)

    response = adapter.fetch_search_response("momentum", limit=1)
    body = json.loads(response.body)

    assert response.ok is True
    assert body["files"]["auths"]["status"] == 404
