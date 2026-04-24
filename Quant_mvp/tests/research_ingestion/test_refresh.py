from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from research_ingestion.cli import cmd_refresh, main
from research_ingestion.config import ProjectPaths, load_research_config
from research_ingestion.persistence import read_jsonl, write_jsonl
from research_ingestion.refresh import select_unseen_papers


def test_select_unseen_papers_filters_existing_duplicates(sample_paper):
    existing = [sample_paper(doi="10.1000/existing", title="Existing momentum paper")]
    duplicate = sample_paper(doi="10.1000/existing", title="Existing momentum paper from another source", source_adapter="openalex")
    new = sample_paper(doi="10.1000/new", title="New technical momentum paper")

    unseen = select_unseen_papers(existing, [duplicate, new])

    assert len(unseen) == 1
    assert unseen[0]["doi"] == "10.1000/new"


def test_refresh_dry_run_uses_policy_defaults(capsys):
    result = main(["refresh", "--dry-run", "--run-id", "refresh_dry"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "periodic_refresh"
    assert "technical_momentum" in payload["selected_query_sets"]
    assert "arxiv" in payload["selected_sources"]
    assert payload["refresh_policy"]["interval_days"] == 14
    assert "Google Scholar live request는 수행하지 않습니다." in payload["guardrails_ko"]


def test_refresh_offline_writes_empty_new_artifact_and_preserves_existing(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    existing = sample_paper(doi="10.1000/keep", title="Keep existing paper")
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", [existing])

    args = Namespace(
        run_id="refresh_offline",
        dry_run=False,
        offline=True,
        sources="arxiv",
        query_sets="technical_momentum",
        max_results=1,
        page_size=None,
    )
    cmd_refresh(args, config, paths)

    new_artifact = paths.data_dir / "normalized" / "refresh_offline_refresh_new_papers.jsonl"
    summary_path = paths.data_dir / "indexes" / "refresh_offline_refresh_summary.json"
    assert read_jsonl(new_artifact) == []
    assert read_jsonl(paths.data_dir / "normalized" / "papers.jsonl") == [existing]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["refresh_existing_paper_count"] == 1
    assert summary["refresh_new_paper_count"] == 0
