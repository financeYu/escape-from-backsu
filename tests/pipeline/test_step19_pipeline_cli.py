from __future__ import annotations

import json
import subprocess
import sys
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
