from __future__ import annotations

from research_ingestion.discovery.scholar_citation_export import parse_citation_export_file


def test_scholar_endnote_export_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "manual.enw"
    path.write_text(
        "%0 Journal Article\n"
        "%T Technical Momentum in Equities\n"
        "%A Doe, Jane\n"
        "%A Kim, A\n"
        "%D 2024\n"
        "%J Manual Export\n"
        "%R 10.1000/endnote\n"
        "%U https://example.test/endnote\n",
        encoding="utf-8",
    )
    seed = parse_citation_export_file(path, export_format="endnote")[0]
    assert seed["source_channel"] == "google_scholar_manual_endnote"
    assert seed["raw_year"] == 2024
    assert seed["candidate_doi"] == "10.1000/endnote"


def test_scholar_refman_export_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "manual.ris"
    path.write_text(
        "TY  - JOUR\n"
        "TI  - Daily reversal signals\n"
        "AU  - Lee, B\n"
        "PY  - 2023\n"
        "JO  - Manual Export\n"
        "DO  - 10.1000/refman\n"
        "UR  - https://example.test/refman\n"
        "ER  -\n",
        encoding="utf-8",
    )
    seed = parse_citation_export_file(path, export_format="refman")[0]
    assert seed["source_channel"] == "google_scholar_manual_refman"
    assert seed["raw_title"] == "Daily reversal signals"
    assert seed["candidate_doi"] == "10.1000/refman"
