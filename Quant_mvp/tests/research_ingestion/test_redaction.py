from __future__ import annotations

from research_ingestion.persistence import raw_snapshot_path, store_raw_response
from research_ingestion.redaction import redact_headers, redact_mapping, redact_url


def test_api_key_redaction(monkeypatch):
    monkeypatch.setenv("SECRET_ENV", "super-secret")
    assert "super-secret" not in redact_url("https://api.test?q=x&api_key=super-secret", env_var_names=["SECRET_ENV"])
    assert redact_headers({"Authorization": "Bearer secret"})["Authorization"] == "[REDACTED]"
    redacted = redact_mapping({"nested": {"token": "abc", "url": "https://x.test?a=1&key=super-secret"}}, env_var_names=["SECRET_ENV"])
    assert "super-secret" not in str(redacted)
    assert "abc" not in str(redacted)


def test_raw_persistence_path_construction_and_secret_redaction(workspace_tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key")
    path = raw_snapshot_path(workspace_tmp_path, "openalex", "run", "body", ".json")
    assert path.as_posix().endswith("/data/research/raw/openalex/run/230d8358dc8e8890.json")
    snapshot = store_raw_response(
        root=workspace_tmp_path,
        source="openalex",
        run_id="run",
        response_body="body",
        suffix=".json",
        request_metadata={"request_url": "https://api.test?api_key=secret-key"},
        redaction_env_vars=["OPENALEX_API_KEY"],
    )
    metadata = open(snapshot["metadata_path"], encoding="utf-8").read()
    assert "secret-key" not in metadata
