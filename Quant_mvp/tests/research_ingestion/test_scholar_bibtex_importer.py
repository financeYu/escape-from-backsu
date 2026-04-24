from __future__ import annotations

from research_ingestion.discovery.scholar_bibtex import parse_bibtex_file


def test_scholar_bibtex_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "manual.bib"
    path.write_text(
        "@article{paper,\n"
        " title={Technical Momentum in Equities},\n"
        " author={Doe, Jane and Kim, A},\n"
        " year={2024},\n"
        " journal={Manual Export},\n"
        " doi={10.1000/bibtex}\n"
        "}\n",
        encoding="utf-8",
    )
    seed = parse_bibtex_file(path)[0]
    assert seed["source_channel"] == "google_scholar_manual_bibtex"
    assert seed["raw_year"] == 2024
    assert seed["candidate_doi"] == "10.1000/bibtex"
