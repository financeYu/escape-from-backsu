from __future__ import annotations

from pathlib import Path

from research_ingestion.cli import main
from research_ingestion.config import load_research_config
from research_ingestion.pdf_manifest import build_pdf_ready_manifest
from research_ingestion.persistence import read_json, read_jsonl, write_jsonl


def test_pdf_ready_manifest_classifies_cc_and_excluded_rows(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    input_path = workspace_tmp_path / "papers.jsonl"
    output_path = workspace_tmp_path / "manifest.jsonl"
    summary_path = workspace_tmp_path / "summary.json"
    rows = [
        _trace_ready(sample_paper, doi="10.1000/auto", license="cc-by"),
        _trace_ready(
            sample_paper,
            doi="10.1000/nc",
            license="cc-by-nc",
            license_name="CC BY-NC 4.0",
            license_url="https://creativecommons.org/licenses/by-nc/4.0/",
        ),
        sample_paper(doi="10.1000/no-pdf", pdf_urls=[], license="cc-by"),
        _trace_ready(
            sample_paper,
            doi="10.1000/other",
            license="custom-open-license",
            license_name="custom-open-license",
            license_url="custom-open-license",
            oa_status="gold",
        ),
        _trace_ready(
            sample_paper,
            doi="10.1000/tdm",
            license="Wiley TDM License",
            license_name="Wiley TDM License",
            license_url="Wiley TDM License",
        ),
    ]
    write_jsonl(input_path, rows)

    result = build_pdf_ready_manifest(
        input_path=input_path,
        output_path=output_path,
        summary_path=summary_path,
        config=config,
        run_id="pdf_manifest_unit",
    )

    manifest_rows = read_jsonl(output_path)
    summary = read_json(summary_path)
    categories = [row["category"] for row in manifest_rows]
    assert categories == ["auto_cc", "noncommercial_cc", "excluded", "manual_review", "excluded"]
    assert result["summary"]["auto_cc_count"] == 1
    assert summary["noncommercial_cc_count"] == 1
    assert summary["excluded_count"] == 2
    assert summary["manual_review_count"] == 1
    assert summary["download_performed"] is False
    assert manifest_rows[0]["category_allowed_by_policy"] is True
    assert manifest_rows[1]["category_allowed_by_policy"] is True
    assert manifest_rows[1]["collection_basis"] == "noncommercial_research_only"
    assert manifest_rows[1]["external_upload_allowed"] is False
    assert manifest_rows[4]["exclusion_reasons"] == ["blocked_publisher_tdm_license"]


def test_pdf_ready_manifest_records_missing_trace(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    input_path = workspace_tmp_path / "papers.jsonl"
    output_path = workspace_tmp_path / "manifest.jsonl"
    summary_path = workspace_tmp_path / "summary.json"
    write_jsonl(
        input_path,
        [
            sample_paper(
                doi="10.1000/missing-trace",
                pdf_urls=["https://example.test/paper.pdf"],
                license="cc-by",
            )
        ],
    )

    build_pdf_ready_manifest(
        input_path=input_path,
        output_path=output_path,
        summary_path=summary_path,
        config=config,
        run_id="pdf_missing_trace_manifest",
    )

    row = read_jsonl(output_path)[0]
    summary = read_json(summary_path)
    assert row["category"] == "auto_cc"
    assert row["trace_complete"] is False
    assert "license_name" in row["missing_trace_fields"]
    assert row["external_upload_allowed"] is False
    assert row["external_upload_allowed_source"] == "default_false_no_explicit_basis"
    assert summary["missing_trace_count"] == 1
    assert summary["next_step_download_ready_count"] == 0


def test_pdf_ready_manifest_allows_explicit_upload_or_redistribution_trace(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    input_path = workspace_tmp_path / "papers.jsonl"
    output_path = workspace_tmp_path / "manifest.jsonl"
    summary_path = workspace_tmp_path / "summary.json"
    write_jsonl(
        input_path,
        [
            _trace_ready(
                sample_paper,
                doi="10.1000/explicit-upload",
                redistribution_allowed=True,
                external_upload_allowed=True,
            )
        ],
    )

    build_pdf_ready_manifest(
        input_path=input_path,
        output_path=output_path,
        summary_path=summary_path,
        config=config,
        run_id="pdf_explicit_upload_manifest",
    )

    row = read_jsonl(output_path)[0]
    summary = read_json(summary_path)
    assert row["category"] == "auto_cc"
    assert row["trace_complete"] is True
    assert row["redistribution_allowed"] is True
    assert row["external_upload_allowed"] is True
    assert row["next_step_download_ready"] is True
    assert summary["next_step_download_ready_count"] == 1


def test_pdf_ready_manifest_cli_writes_manifest(sample_paper, workspace_tmp_path, monkeypatch):
    input_path = workspace_tmp_path / "papers.jsonl"
    output_path = workspace_tmp_path / "manifest.jsonl"
    summary_path = workspace_tmp_path / "summary.json"
    write_jsonl(input_path, [_trace_ready(sample_paper, doi="10.1000/cli", license="cc-by-sa")])
    monkeypatch.chdir(Path(__file__).resolve().parents[2])

    result = main(
        [
            "pdf-ready-manifest",
            "--run-id",
            "pdf_manifest_cli",
            "--input-path",
            str(input_path),
            "--output-path",
            str(output_path),
            "--summary-path",
            str(summary_path),
        ]
    )

    assert result == 0
    assert read_jsonl(output_path)[0]["category"] == "auto_cc"
    assert read_json(summary_path)["auto_cc_count"] == 1


def _trace_ready(sample_paper, **overrides):
    payload = {
        "pdf_urls": ["https://example.test/paper.pdf"],
        "license": "cc-by",
        "license_name": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "license_checked_at": "2026-04-28T00:00:00Z",
        "license_evidence_quote": "Creative Commons license",
        "collection_basis": "open_access_license_verified",
        "fulltext_source_type": "publisher_pdf",
        "fulltext_review_scope": "local_license_verified_pdf",
        "redistribution_allowed": False,
        "external_upload_allowed": False,
    }
    payload.update(overrides)
    return sample_paper(**payload)
