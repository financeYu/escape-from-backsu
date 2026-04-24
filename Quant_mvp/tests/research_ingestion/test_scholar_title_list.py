from __future__ import annotations

from research_ingestion.discovery.scholar_title_list import parse_title_list_file


def test_scholar_title_list_text_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "titles.txt"
    path.write_text("# comment\nA daily breakout paper\n", encoding="utf-8")
    seeds = parse_title_list_file(path)
    assert len(seeds) == 1
    assert seeds[0]["raw_title"] == "A daily breakout paper"


def test_scholar_title_list_csv_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "titles.csv"
    path.write_text("title,authors,year,doi\nDaily reversal,Doe;Kim,2020,10.1000/title\n", encoding="utf-8")
    seed = parse_title_list_file(path)[0]
    assert seed["raw_authors"] == ["Doe", "Kim"]
    assert seed["raw_year"] == 2020
