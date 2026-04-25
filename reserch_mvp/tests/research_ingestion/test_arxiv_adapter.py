from __future__ import annotations

from research_ingestion.sources.arxiv_adapter import ArxivAdapter


ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <updated>2024-02-01T00:00:00Z</updated>
    <published>2024-01-15T00:00:00Z</published>
    <title> Daily Momentum Signals </title>
    <summary> We define a daily momentum signal using returns and volume. </summary>
    <author><name>Alice Kim</name></author>
    <arxiv:doi>10.48550/arXiv.2401.12345</arxiv:doi>
    <category term="q-fin.ST"/>
    <link href="http://arxiv.org/abs/2401.12345v2" rel="alternate"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.12345v2" rel="related" type="application/pdf"/>
  </entry>
</feed>"""


def test_arxiv_adapter_initialization_and_rate_limiter_settings():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1})
    assert adapter.min_interval_seconds >= 3.0
    assert adapter.max_concurrency == 1
    assert adapter.pdf_download_enabled is False


def test_arxiv_paging_parameter_generation():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1, "base_url": "https://export.arxiv.org/api/query"})
    url = adapter.build_search_url("momentum", start=50, max_results=25)
    assert "start=50" in url
    assert "max_results=25" in url
    assert "search_query=all%3Amomentum" in url


def test_arxiv_plain_multi_term_query_uses_and_terms():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1, "base_url": "https://export.arxiv.org/api/query"})
    url = adapter.build_search_url("stock momentum returns", start=0, max_results=2)
    assert "search_query=all%3Astock+AND+all%3Amomentum+AND+all%3Areturns" in url


def test_arxiv_advanced_query_passthrough():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1, "base_url": "https://export.arxiv.org/api/query"})
    url = adapter.build_search_url("cat:q-fin.ST AND all:momentum", start=0, max_results=2)
    assert "search_query=cat%3Aq-fin.ST+AND+all%3Amomentum" in url


def test_arxiv_xml_parsing_from_fixture():
    adapter = ArxivAdapter({"min_interval_seconds": 3.2, "max_concurrency": 1})
    papers = adapter.parse_atom(ARXIV_XML, raw_snapshot_ref="raw.xml")
    assert papers[0]["arxiv_id"] == "2401.12345"
    assert papers[0]["doi"] == "10.48550/arxiv.2401.12345"
    assert papers[0]["publication_year"] == 2024
    assert papers[0]["raw_snapshot_refs"] == ["raw.xml"]
