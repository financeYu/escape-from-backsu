from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from research_ingestion.cli import _update_source_health_from_collection, cmd_classify, cmd_normalize, main
from research_ingestion.config import ProjectPaths, load_research_config
from research_ingestion.persistence import read_jsonl, write_json, write_jsonl


def test_collect_dry_run_reports_guardrails(capsys, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    result = main(
        [
            "collect",
            "--dry-run",
            "--sources",
            "arxiv,openalex",
            "--query-set",
            "technical_momentum",
            "--run-id",
            "dry_test",
            "--max-results",
            "2",
            "--page-size",
            "1",
            "--no-pdf",
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "dry_test"
    assert payload["planned_sources"][0]["source"] == "arxiv"
    assert payload["planned_sources"][0]["queries"] == [
        "cat:q-fin.ST AND all:momentum AND all:stock",
        "cat:q-fin.PM AND all:momentum",
    ]
    openalex_plan = next(source for source in payload["planned_sources"] if source["source"] == "openalex")
    assert "실행할 수 없습니다" in openalex_plan["missing_key_note_ko"]
    assert payload["relevance_defaults"]["reject_on_exclude_keyword"] is True
    assert "Google Scholar live request는 수행하지 않습니다." in payload["guardrails_ko"]


def test_offline_collect_writes_empty_artifacts(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    root = Path(__file__).resolve().parents[2]
    collected = root / "data" / "research" / "normalized" / "offline_test_collected_papers.jsonl"
    health = root / "data" / "research" / "indexes" / "offline_test_source_health.json"
    summary = root / "data" / "research" / "indexes" / "offline_test_collection_summary.json"
    try:
        result = main(
            [
                "collect",
                "--offline",
                "--sources",
                "arxiv",
                "--query-set",
                "technical_momentum",
                "--run-id",
                "offline_test",
                "--max-results",
                "1",
            ]
        )
        assert result == 0
        assert collected.exists()
        assert "--offline" in health.read_text(encoding="utf-8")
    finally:
        for path in [collected, health, summary]:
            if path.exists():
                path.unlink()


def test_collect_rejects_path_traversal_run_id():
    with pytest.raises(ValueError):
        main(
            [
                "collect",
                "--dry-run",
                "--sources",
                "arxiv",
                "--query-set",
                "technical_momentum",
                "--run-id",
                "..\\escape",
            ]
        )


def test_collect_source_health_counts_accepted_and_rejected_items(sample_paper):
    accepted = sample_paper(
        doi="10.1000/accepted-health",
        source_adapter="arxiv",
        collection_relevance={"status": "accepted", "manual_review_required": False},
    )
    rejected = sample_paper(
        doi="10.1000/rejected-health",
        source_adapter="arxiv",
        collection_relevance={
            "status": "rejected",
            "manual_review_required": True,
            "exclude_keyword_hits": ["intraday"],
            "required_keyword_group_hits": {},
        },
    )
    health = {
        "arxiv": {
            "new_item_count": 0,
            "manual_review_required_count": 0,
            "reject_reason_counts": {},
        }
    }

    _update_source_health_from_collection(health, [accepted], [rejected])

    assert health["arxiv"]["new_item_count"] == 1
    assert health["arxiv"]["manual_review_required_count"] == 0
    assert health["arxiv"]["reject_reason_counts"] == {"collection_exclude_keyword": 1}


def test_backtest_normalize_uses_run_and_lane_files_without_overwriting_global(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    technical_existing = sample_paper(doi="10.1000/tech-existing", title="Existing technical momentum paper")
    backtest_paper = sample_paper(
        doi="10.1000/backtest",
        title="Backtesting momentum trading strategies",
        abstract="Walk forward out of sample validation and data snooping checks for equity strategies.",
        research_query_set="backtest_methodology",
        research_query_sets=["backtest_methodology"],
        research_management_lane="backtest_methodology",
        research_management_lanes=["backtest_methodology"],
        topics=[],
        fields_of_study=[],
    )
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", [technical_existing])
    write_jsonl(paths.data_dir / "normalized" / "bt_run_collected_papers.jsonl", [backtest_paper])
    write_json(
        paths.data_dir / "indexes" / "bt_run_collection_summary.json",
        {
            "selected_query_set": "backtest_methodology",
            "selected_management_lane": "backtest_methodology",
        },
    )

    args = Namespace(run_id="bt_run", dry_run=False)
    cmd_normalize(args, config, paths)
    cmd_classify(args, config, paths)

    assert read_jsonl(paths.data_dir / "normalized" / "papers.jsonl") == [technical_existing]
    assert read_jsonl(paths.data_dir / "normalized" / "bt_run_papers.jsonl") == [backtest_paper]
    assert read_jsonl(paths.data_dir / "normalized" / "backtest_methodology_papers.jsonl") == [backtest_paper]
    classifications = read_jsonl(paths.data_dir / "indexes" / "bt_run_classifications.jsonl")
    assert classifications[0]["research_branch"] == "diagnostic"
    assert classifications[0]["management_lane"] == "backtest_methodology"
