from __future__ import annotations

from pathlib import Path

from research_ingestion.api_keys import load_api_keys_for_project


def _research_root(tmp_path: Path) -> Path:
    root = tmp_path / "Project" / "master_mvp" / "Quant_mvp" / "research_mvp"
    root.mkdir(parents=True)
    return root


def test_load_api_keys_from_parent_api_management(tmp_path):
    root = _research_root(tmp_path)
    api_dir = tmp_path / "Project" / "api_management"
    api_dir.mkdir()
    (api_dir / ".env").write_text(
        "\n".join(
            [
                "OPENALEX_API_KEY=openalex-test-key",
                'SEMANTIC_SCHOLAR_API_KEY="semantic-test-key"',
                "UNRELATED_SECRET=must-not-load",
            ]
        ),
        encoding="utf-8",
    )
    env: dict[str, str] = {}

    result = load_api_keys_for_project(root, env)

    assert env["OPENALEX_API_KEY"] == "openalex-test-key"
    assert env["SEMANTIC_SCHOLAR_API_KEY"] == "semantic-test-key"
    assert "UNRELATED_SECRET" not in env
    assert result.source_path == api_dir / ".env"
    assert result.loaded_env_vars == ("OPENALEX_API_KEY", "SEMANTIC_SCHOLAR_API_KEY")


def test_load_api_keys_preserves_existing_environment_values(tmp_path):
    root = _research_root(tmp_path)
    api_dir = tmp_path / "Project" / "api_management"
    api_dir.mkdir()
    (api_dir / ".env").write_text("OPENALEX_API_KEY=file-key", encoding="utf-8")
    env = {"OPENALEX_API_KEY": "existing-key"}

    result = load_api_keys_for_project(root, env)

    assert env["OPENALEX_API_KEY"] == "existing-key"
    assert result.loaded_env_vars == ()
    assert result.skipped_existing_env_vars == ("OPENALEX_API_KEY",)


def test_load_api_keys_does_not_read_project_root_env(tmp_path):
    root = _research_root(tmp_path)
    (tmp_path / "Project" / ".env").write_text("CROSSREF_PLUS_API_TOKEN=crossref-test-token", encoding="utf-8")
    env: dict[str, str] = {}

    result = load_api_keys_for_project(root, env)

    assert "CROSSREF_PLUS_API_TOKEN" not in env
    assert result.source_path is None
    assert result.attempted_paths == tuple(
        (tmp_path / "Project" / "api_management" / filename).resolve()
        for filename in [".env", "api_keys.env", "api-keys.env", "keys.env"]
    )


def test_load_api_keys_autoload_can_be_disabled(tmp_path):
    root = _research_root(tmp_path)
    api_dir = tmp_path / "Project" / "api_management"
    api_dir.mkdir()
    (api_dir / ".env").write_text("OPENALEX_API_KEY=openalex-test-key", encoding="utf-8")
    env = {"MASTER_MVP_API_KEYS_AUTOLOAD": "0"}

    result = load_api_keys_for_project(root, env)

    assert "OPENALEX_API_KEY" not in env
    assert result.disabled_reason == "autoload_disabled"
