from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
import research_ingestion.cli as cli_module
from research_ingestion.cli import cmd_refresh, main
from research_ingestion.config import ProjectPaths, load_research_config
from research_ingestion.persistence import read_json, read_jsonl, write_json, write_jsonl
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
    assert payload["selected_profile"] == "fast_refresh"
    assert "technical_momentum" in payload["selected_query_sets"]
    assert payload["selected_sources"] == ["openalex"]
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


def test_refresh_valuation_query_requires_explicit_opt_in():
    with pytest.raises(ValueError, match="--include-valuation"):
        main(["refresh", "--dry-run", "--run-id", "valuation_block", "--query-sets", "fundamental_valuation"])


def test_refresh_source_health_counts_new_candidate_routes(sample_paper, workspace_tmp_path, monkeypatch):
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", [])

    def fake_collect(child_args, _config, child_paths):
        paper = sample_paper(
            doi="10.1000/source-health-new",
            title="New technical momentum paper",
            source_adapter="arxiv",
            source_record_id="arxiv:source-health-new",
            source_query_set=child_args.query_set,
            query_run_id=child_args.run_id,
            research_query_set=child_args.query_set,
            research_query_sets=[child_args.query_set],
            research_branch_hint="technical",
            research_branch_hints=["technical"],
        )
        write_jsonl(
            child_paths.data_dir / "normalized" / f"{child_args.run_id}_collected_papers.jsonl",
            [paper],
        )
        write_json(
            child_paths.data_dir / "indexes" / f"{child_args.run_id}_collection_summary.json",
            {
                "raw_records_collected_by_source": {"arxiv": 1},
                "records_rejected_by_relevance": 0,
                "records_manual_review_by_relevance": 0,
            },
        )
        write_json(
            child_paths.data_dir / "indexes" / f"{child_args.run_id}_source_health.json",
            {
                "arxiv": {
                    "source": "arxiv",
                    "adapter_version": "research_ingestion.v1",
                    "query_set": child_args.query_set,
                    "status": "ok",
                    "request_count": 1,
                    "rate_limit_wait_count": 0,
                    "success_count": 1,
                    "failure_count": 0,
                    "http_status_summary": {"200": 1},
                    "http_429_count": 0,
                    "parse_error_count": 0,
                    "schema_error_count": 0,
                    "dedup_ratio": None,
                    "new_item_count": 1,
                    "candidate_route_counts": {},
                    "reject_reason_counts": {},
                    "manual_review_required_count": 0,
                    "unresolved_seed_count": 0,
                    "pdf_download_attempt_count": 0,
                    "rate_limit_observations": [],
                    "missing_api_key_note_ko": None,
                    "skipped_source_reason": None,
                }
            },
        )

    monkeypatch.setattr(cli_module, "cmd_collect", fake_collect)
    args = Namespace(
        run_id="refresh_health",
        dry_run=False,
        offline=False,
        sources="arxiv",
        query_sets="technical_momentum",
        max_results=1,
        page_size=None,
    )
    cli_module.cmd_refresh(args, config, paths)

    health = read_json(paths.data_dir / "indexes" / "source_health_report.json")
    arxiv = health["arxiv"]
    assert arxiv["new_item_count"] == 1
    assert arxiv["dedup_ratio"] == 0.0
    assert arxiv["candidate_route_counts"] == {"technical_score_architect": 1}
    assert arxiv["manual_review_required_count"] == 1


def test_refresh_incremental_classifies_only_new_papers(sample_paper, workspace_tmp_path, monkeypatch):
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    existing = sample_paper(doi="10.1000/existing-incremental", title="Existing incremental paper")
    new = sample_paper(doi="10.1000/new-incremental", title="New incremental paper", source_adapter="openalex")
    write_jsonl(paths.data_dir / "normalized" / "papers.jsonl", [existing])
    write_json(
        paths.data_dir / "indexes" / "evidence_policy_version.json",
        cli_module._current_policy_versions(config),
    )
    write_jsonl(paths.data_dir / "evidence" / "evidence_cards.jsonl", [_minimal_card(existing)])

    def fake_collect(child_args, _config, child_paths):
        write_jsonl(child_paths.data_dir / "normalized" / f"{child_args.run_id}_collected_papers.jsonl", [existing, new])
        write_json(
            child_paths.data_dir / "indexes" / f"{child_args.run_id}_collection_summary.json",
            {
                "raw_records_collected_by_source": {"openalex": 2},
                "records_rejected_by_relevance": 0,
                "records_manual_review_by_relevance": 0,
            },
        )
        write_json(child_paths.data_dir / "indexes" / f"{child_args.run_id}_source_health.json", {"openalex": _minimal_health("openalex")})

    classify_calls: list[str] = []

    def fake_classify(paper, _classification, _policy):
        classify_calls.append(paper["canonical_paper_id"])
        return {
            "research_branch": "technical",
            "downstream_route": "technical_score_architect",
            "main_score_branch_candidate": "technical",
            "manual_review_required": False,
        }

    monkeypatch.setattr(cli_module, "cmd_collect", fake_collect)
    monkeypatch.setattr(cli_module, "classify_paper", fake_classify)
    monkeypatch.setattr(
        cli_module,
        "generate_evidence_cards",
        lambda papers, classifications, run_id: [
            _minimal_card(paper, classification)
            for paper, classification in zip(papers, classifications, strict=True)
        ],
    )

    args = Namespace(
        run_id="refresh_incremental",
        dry_run=False,
        offline=False,
        profile=None,
        sources="openalex",
        query_sets="technical_momentum",
        include_valuation=False,
        max_results=2,
        page_size=None,
    )
    cli_module.cmd_refresh(args, config, paths)

    assert classify_calls == [new["canonical_paper_id"]]
    summary = read_json(paths.data_dir / "indexes" / "refresh_incremental_refresh_summary.json")
    assert summary["incremental_pipeline"]["classification_scope"] == "new_papers_only"
    assert summary["incremental_pipeline"]["existing_evidence_cards_reused"] == 1


def _minimal_card(paper, classification=None):
    return {
        "paper": {
            "canonical_paper_id": paper["canonical_paper_id"],
            "source_adapters": paper.get("source_adapters", []),
        },
        "classification": classification
        or {
            "research_branch": "technical",
            "downstream_route": "technical_score_architect",
            "main_score_branch_candidate": "technical",
            "management_lane": None,
            "manual_review_required": False,
        },
    }


def _minimal_health(source):
    return {
        "source": source,
        "adapter_version": "research_ingestion.v1",
        "query_set": "technical_momentum",
        "status": "ok",
        "request_count": 1,
        "rate_limit_wait_count": 0,
        "rate_limit_wait_seconds": 0.0,
        "request_latency_ms": 1.0,
        "parse_ms": 1.0,
        "dedupe_ms": 0.0,
        "classification_ms": 0.0,
        "success_count": 1,
        "failure_count": 0,
        "http_status_summary": {"200": 1},
        "http_429_count": 0,
        "parse_error_count": 0,
        "schema_error_count": 0,
        "dedup_ratio": None,
        "new_item_count": 1,
        "candidate_route_counts": {},
        "reject_reason_counts": {},
        "relevance_reject_reason_counts": {},
        "manual_review_required_count": 0,
        "request_cache_hit_count": 0,
        "request_cache_miss_count": 0,
        "request_cache_stale_count": 0,
        "unresolved_seed_count": 0,
        "pdf_download_attempt_count": 0,
        "rate_limit_observations": [],
        "missing_api_key_note_ko": None,
        "skipped_source_reason": None,
    }
