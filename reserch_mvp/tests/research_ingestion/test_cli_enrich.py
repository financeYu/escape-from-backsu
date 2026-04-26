from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from research_ingestion import cli
import research_ingestion.cli_enrich as cli_enrich_module
from research_ingestion.cli import _enrichment_targets, cmd_enrich, main
from research_ingestion.config import ProjectPaths, load_research_config
from research_ingestion.persistence import write_jsonl
from research_ingestion.sources.http import SourceResponse


def test_enrichment_targets_use_doi_and_arxiv(sample_paper):
    paper = sample_paper(doi="10.1000/enrich", arxiv_id="2401.99999", semantic_scholar_id=None)
    targets = _enrichment_targets([paper], ["crossref", "semantic_scholar"])
    assert {target["source"] for target in targets} == {"crossref", "semantic_scholar"}
    assert any(target["lookup_id"] == "10.1000/enrich" for target in targets)
    assert any(target["lookup_id"] == "DOI:10.1000/enrich" for target in targets)


def test_enrich_dry_run_reports_targets(sample_paper, workspace_tmp_path, capsys):
    input_path = workspace_tmp_path / "papers.jsonl"
    write_jsonl(input_path, [sample_paper(doi="10.1000/enrich")])
    result = main(
        [
            "enrich",
            "--dry-run",
            "--sources",
            "crossref,semantic_scholar",
            "--input-path",
            str(input_path),
            "--run-id",
            "enrich_dry",
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "enrich"
    assert payload["target_count_by_source"] == {"crossref": 1, "semantic_scholar": 1}
    assert "score 채택" in " ".join(payload["guardrails_ko"])


def test_enrich_offline_writes_metadata_without_network(sample_paper, workspace_tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    input_path = workspace_tmp_path / "papers.jsonl"
    write_jsonl(input_path, [sample_paper(doi="10.1000/offline")])
    outputs = [
        root / "data" / "research" / "normalized" / "enrich_offline_enriched_papers.jsonl",
        root / "data" / "research" / "indexes" / "enrich_offline_enrichment_index.jsonl",
        root / "data" / "research" / "indexes" / "enrich_offline_enrichment_summary.json",
        root / "data" / "research" / "indexes" / "enrich_offline_source_health.json",
        root / "data" / "research" / "indexes" / "enrich_offline_collection_summary.json",
    ]
    try:
        result = main(
            [
                "enrich",
                "--offline",
                "--sources",
                "crossref",
                "--input-path",
                str(input_path),
                "--run-id",
                "enrich_offline",
            ]
        )
        assert result == 0
        assert outputs[0].exists()
        payload = json.loads(outputs[2].read_text(encoding="utf-8"))
        assert payload["plan"]["offline"] is True
    finally:
        for path in outputs:
            if path.exists():
                path.unlink()


def test_crossref_doi_enrichment_fixture_merges_metadata(sample_paper, workspace_tmp_path, monkeypatch):
    input_path = workspace_tmp_path / "input" / "papers.jsonl"
    write_jsonl(input_path, [sample_paper(doi="10.1000/crossref-enrich", title="Original title", source_adapter="fixture")])

    payload = {
        "message": {
            "DOI": "10.1000/crossref-enrich",
            "title": ["Crossref enriched title"],
            "author": [{"given": "A", "family": "Lee"}],
            "published-online": {"date-parts": [[2024, 1, 2]]},
            "container-title": ["Crossref Journal"],
            "URL": "https://doi.org/10.1000/crossref-enrich",
        }
    }

    def fake_fetch(adapter, target):
        return SourceResponse(
            url="https://api.crossref.org/works/10.1000%2Fcrossref-enrich",
            body=json.dumps(payload),
            status=200,
            headers={},
            retry_count=0,
        )

    monkeypatch.setattr(cli, "_fetch_enrichment_response", fake_fetch)
    args = Namespace(
        run_id="crossref_fixture",
        dry_run=False,
        sources="crossref",
        input_path=str(input_path),
        max_records=None,
        offline=False,
    )
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    cmd_enrich(args, config, paths)

    enriched = workspace_tmp_path / "data" / "research" / "normalized" / "crossref_fixture_enriched_papers.jsonl"
    merged = workspace_tmp_path / "data" / "research" / "normalized" / "papers.jsonl"
    index = workspace_tmp_path / "data" / "research" / "indexes" / "crossref_fixture_enrichment_index.jsonl"
    assert enriched.exists()
    merged_rows = [json.loads(line) for line in merged.read_text(encoding="utf-8").splitlines()]
    assert len(merged_rows) == 1
    assert "crossref" in merged_rows[0]["source_adapters"]
    assert "matched" in index.read_text(encoding="utf-8")


def test_semantic_scholar_enrichment_batches_default_fetch(sample_paper, workspace_tmp_path, monkeypatch):
    input_path = workspace_tmp_path / "input" / "papers.jsonl"
    write_jsonl(
        input_path,
        [
            sample_paper(doi="10.1000/batch-1", semantic_scholar_id="S2-batch-1", title="Batch paper 1"),
            sample_paper(doi="10.1000/batch-2", semantic_scholar_id="S2-batch-2", title="Batch paper 2"),
        ],
    )
    batch_calls: list[list[str]] = []

    class FakeSemanticScholarAdapter:
        source_name = "semantic_scholar"
        config = {"batch_max_ids": 100}

        def request_headers(self):
            return {}

        def request_metadata(self, url, headers):
            return {"request_url": url, "headers": headers}

        def fetch_batch_response(self, ids):
            batch_calls.append(list(ids))
            body = json.dumps(
                [
                    {
                        "paperId": "S2-batch-1",
                        "externalIds": {"DOI": "10.1000/batch-1"},
                        "title": "Batch paper 1",
                        "authors": [{"name": "A"}],
                        "year": 2024,
                    },
                    {
                        "paperId": "S2-batch-2",
                        "externalIds": {"DOI": "10.1000/batch-2"},
                        "title": "Batch paper 2",
                        "authors": [{"name": "B"}],
                        "year": 2024,
                    },
                ]
            )
            return SourceResponse(url="https://api.semanticscholar.org/graph/v1/paper/batch", body=body, status=200, headers={}, retry_count=0)

        def parse_batch_json(self, payload, raw_snapshot_ref=None):
            return [
                sample_paper(
                    doi=item["externalIds"]["DOI"],
                    semantic_scholar_id=item["paperId"],
                    title=item["title"],
                    source_adapter="semantic_scholar",
                    raw_snapshot_refs=[raw_snapshot_ref] if raw_snapshot_ref else [],
                )
                for item in payload
            ]

    monkeypatch.setattr(cli_enrich_module, "_adapter_for_source", lambda source, config: FakeSemanticScholarAdapter())
    args = Namespace(
        run_id="semantic_batch",
        dry_run=False,
        sources="semantic_scholar",
        input_path=str(input_path),
        max_records=None,
        offline=False,
    )
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)
    cmd_enrich(args, config, paths)

    index_rows = (workspace_tmp_path / "data" / "research" / "indexes" / "semantic_batch_enrichment_index.jsonl").read_text(encoding="utf-8")
    assert batch_calls == [["S2-batch-1", "S2-batch-2"]]
    assert "batch_submitted" in index_rows


def test_run_all_dry_run_can_plan_optional_enrichment(capsys):
    result = main(
        [
            "run-all",
            "--dry-run",
            "--sources",
            "arxiv",
            "--query-set",
            "technical_momentum",
            "--run-id",
            "run_all_dry",
            "--max-results",
            "1",
            "--enrich-sources",
            "crossref",
            "--enrich-max-records",
            "1",
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "run_all"
    assert payload["enrich"]["selected_sources"] == ["crossref"]
    assert "enrich" in payload["pipeline"]
