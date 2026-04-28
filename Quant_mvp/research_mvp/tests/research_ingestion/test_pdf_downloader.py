from __future__ import annotations

from pathlib import Path

import pytest

from research_ingestion.config import ProjectPaths, load_research_config
from research_ingestion.cli import main
from research_ingestion.pdf_downloader import download_pdfs
from research_ingestion.persistence import read_jsonl


def test_pdf_downloader_saves_license_verified_pdf(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)
    paper = _pdf_ready_paper(sample_paper)

    summary = download_pdfs(
        papers=[paper],
        config=config,
        paths=paths,
        run_id="pdf_unit",
        fetch_pdf_bytes=lambda url, timeout, headers, max_bytes: (b"%PDF-1.7\nunit\n", {"content-type": "application/pdf"}, 200),
    )

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert summary["downloaded_count"] == 1
    assert rows[0]["status"] == "downloaded"
    assert rows[0]["external_upload_allowed"] is False
    assert Path(rows[0]["local_pdf_path"]).exists()


def test_pdf_downloader_skips_when_trace_fields_are_missing(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)
    paper = sample_paper(pdf_urls=["https://example.test/paper.pdf"], license="cc-by")
    fetched = False

    def fetch(url, timeout, headers, max_bytes):
        nonlocal fetched
        fetched = True
        return b"%PDF-1.7\n", {}, 200

    summary = download_pdfs(
        papers=[paper],
        config=config,
        paths=paths,
        run_id="pdf_missing_trace",
        fetch_pdf_bytes=fetch,
    )

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert fetched is False
    assert summary["downloaded_count"] == 0
    assert rows[0]["status"] == "skipped"
    assert "trace field" in rows[0]["skip_reason_ko"]


def test_pdf_downloader_enforces_non_bulk_limit(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)

    with pytest.raises(ValueError, match="대량 다운로드"):
        download_pdfs(
            papers=[_pdf_ready_paper(sample_paper), _pdf_ready_paper(sample_paper, doi="10.1000/pdf2")],
            config=config,
            paths=paths,
            run_id="pdf_bulk",
            max_records=2,
        )


def test_pdf_downloader_continues_until_eligible_candidate(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)
    missing_trace = sample_paper(pdf_urls=["https://example.test/missing.pdf"], license="cc-by")
    eligible = _pdf_ready_paper(sample_paper, doi="10.1000/eligible")
    fetched_urls: list[str] = []

    def fetch(url, timeout, headers, max_bytes):
        fetched_urls.append(url)
        return b"%PDF-1.7\neligible\n", {"content-type": "application/pdf"}, 200

    summary = download_pdfs(
        papers=[missing_trace, eligible],
        config=config,
        paths=paths,
        run_id="pdf_after_skip",
        fetch_pdf_bytes=fetch,
    )

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert summary["downloaded_count"] == 1
    assert summary["processed_count"] == 2
    assert rows[0]["status"] == "skipped"
    assert rows[1]["status"] == "downloaded"
    assert fetched_urls == ["https://example.test/paper.pdf"]


def test_pdf_downloader_skips_scholar_urls(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)
    paper = _pdf_ready_paper(sample_paper, pdf_urls=["https://scholar.google.com/paper.pdf"])

    summary = download_pdfs(papers=[paper], config=config, paths=paths, run_id="pdf_scholar")

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert rows[0]["status"] == "skipped"
    assert "scholar.google.com" in rows[0]["skip_reason_ko"]


def test_pdf_downloader_default_policy_remains_disabled(sample_paper, workspace_tmp_path):
    config = load_research_config(Path(__file__).resolve().parents[2])
    paths = ProjectPaths(workspace_tmp_path)

    summary = download_pdfs(
        papers=[_pdf_ready_paper(sample_paper)],
        config=config,
        paths=paths,
        run_id="pdf_disabled",
    )

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert summary["downloaded_count"] == 0
    assert rows[0]["pdf_fulltext_download_allowed"] is False
    assert "비활성화" in rows[0]["skip_reason_ko"]


def test_pdf_downloader_manifest_redacts_tokenized_source_url(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    paths = ProjectPaths(workspace_tmp_path)
    paper = _pdf_ready_paper(
        sample_paper,
        pdf_urls=["https://example.test/paper.pdf?token=secret-token&ok=1"],
    )
    fetched_urls: list[str] = []

    def fetch(url, timeout, headers, max_bytes):
        fetched_urls.append(url)
        return b"%PDF-1.7\nunit\n", {"content-type": "application/pdf"}, 200

    summary = download_pdfs(
        papers=[paper],
        config=config,
        paths=paths,
        run_id="pdf_redacted_url",
        fetch_pdf_bytes=fetch,
    )

    manifest_text = Path(summary["manifest_path"]).read_text(encoding="utf-8")
    rows = read_jsonl(Path(summary["manifest_path"]))
    assert fetched_urls == ["https://example.test/paper.pdf?token=secret-token&ok=1"]
    assert "secret-token" not in manifest_text
    assert rows[0]["source_url"] == "https://example.test/paper.pdf?token=%5BREDACTED%5D&ok=1"
    assert "_source_url" not in rows[0]


def test_pdf_downloader_enforces_max_pdf_bytes(sample_paper, workspace_tmp_path):
    config = _enabled_pdf_config()
    config["policy"]["pdf_policy"]["max_pdf_bytes"] = 8
    paths = ProjectPaths(workspace_tmp_path)
    paper = _pdf_ready_paper(sample_paper)

    summary = download_pdfs(
        papers=[paper],
        config=config,
        paths=paths,
        run_id="pdf_too_large",
        fetch_pdf_bytes=lambda url, timeout, headers, max_bytes: (b"%PDF-1.7\nlarge\n", {"content-type": "application/pdf"}, 200),
    )

    rows = read_jsonl(Path(summary["manifest_path"]))
    assert summary["downloaded_count"] == 0
    assert rows[0]["status"] == "skipped"
    assert "max_pdf_bytes=8" in rows[0]["skip_reason_ko"]
    assert rows[0]["local_pdf_path"] is None


def test_download_pdfs_cli_requires_allow_pdf_flag():
    with pytest.raises(ValueError, match="--allow-pdf"):
        main(
            [
                "download-pdfs",
                "--run-id",
                "pdf_cli_requires_allow",
                "--dry-run",
                "--input-path",
                "tests/fixtures/missing.jsonl",
            ]
        )


def _enabled_pdf_config():
    config = load_research_config(Path(__file__).resolve().parents[2])
    config["policy"]["pdf_policy"] = {
        **config["policy"]["pdf_policy"],
        "allow_pdf": True,
        "max_downloads_per_run": 1,
    }
    config["policy"]["license_policy"] = {
        **config["policy"]["license_policy"],
        "fulltext_download_remains_disabled": False,
    }
    return config


def _pdf_ready_paper(sample_paper, **overrides):
    payload = {
        "pdf_urls": ["https://example.test/paper.pdf"],
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "license_name": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "license_checked_at": "2026-04-28T00:00:00Z",
        "license_evidence_quote": "Creative Commons Attribution 4.0 International",
        "collection_basis": "open_access_license_verified",
        "fulltext_source_type": "publisher_pdf",
        "fulltext_review_scope": "local_license_verified_pdf",
        "redistribution_allowed": False,
        "external_upload_allowed": False,
    }
    payload.update(overrides)
    return sample_paper(**payload)
