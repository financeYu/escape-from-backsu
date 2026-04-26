from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_cli_defaults_to_dry_run_and_prints_summary_only() -> None:
    summary_path = PROJECT_ROOT / "reports/pipeline/generated/step19_pipeline_summary.json"
    preexisting_summary = summary_path.exists()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_step19_pipeline.py",
            "--config",
            "config/step19_pipeline.toml",
            "--stage",
            "ranking",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    summary = json.loads(result.stdout)
    assert summary["run_mode"] == "dry_run"
    assert "latest_ranking" in summary["selected_stages"]
    assert summary["overall_status"] == "completed"
    assert summary_path.exists() is preexisting_summary


def test_cli_returns_nonzero_when_pipeline_is_blocked(tmp_path: Path) -> None:
    config_path = tmp_path / "blocked_step19_pipeline.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            [step19]
            default_run_mode = "dry_run"
            network_allowed = false
            secrets_allowed = false
            local_cache_required = false

            [boundary]
            no_semantics_changed = true
            valuation_fundamental_scoring_activation = false
            technical_composite_score_integration = false
            final_composite_score_activation = false
            kosdaq150_expansion = false
            futures_expansion = false
            options_expansion = false
            external_data_ingestion = false
            step20_final_validation = false

            [stages.preflight]
            order = 10
            enabled = true
            implementation_ref = "src.pipeline.step19_pipeline"
            required_input_paths = ["missing_cli_required_input.csv"]
            output_refs = ["reports/pipeline/generated/blocked.json"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_step19_pipeline.py",
            "--config",
            str(config_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["overall_status"] == "blocked"
