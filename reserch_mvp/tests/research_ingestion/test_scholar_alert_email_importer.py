from __future__ import annotations

from research_ingestion.discovery.scholar_alert_email import parse_alert_file


def test_scholar_alerts_local_file_parsing(workspace_tmp_path):
    path = workspace_tmp_path / "alert.txt"
    path.write_text(
        "Alert query: momentum KOSPI\n\nTitle: Momentum and reversal in stocks\nSnippet: Scholar-only snippet\nLink: https://scholar.google.com/scholar?q=x\n",
        encoding="utf-8",
    )
    seeds = parse_alert_file(path)
    assert seeds[0]["source_channel"] == "google_scholar_alert_email"
    assert seeds[0]["raw_title"] == "Momentum and reversal in stocks"
    assert seeds[0]["canonical_lookup_status"] == "unresolved"
    assert seeds[0]["guardrails"]["not_evidence"] is True
