from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from step20_fixtures import adoption_synthesis_table, normalized_score_frame  # noqa: E402


def test_mvp_latest_ranking_cli_writes_canonical_csv(tmp_path: Path) -> None:
    normalized_path = tmp_path / "normalized_scores.csv"
    adoption_path = tmp_path / "adoption_synthesis.csv"
    output_path = tmp_path / "latest_ranking.csv"
    manifest_path = tmp_path / "latest_ranking_manifest.json"
    normalized_score_frame().to_csv(normalized_path, index=False)
    adoption_synthesis_table().to_csv(adoption_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mvp_latest_ranking.py",
            "--normalized-scores",
            str(normalized_path),
            "--adoption-synthesis",
            str(adoption_path),
            "--as-of-date",
            "2026-04-24",
            "--max-allowed-date",
            "2026-04-24",
            "--top-n",
            "2",
            "--output",
            str(output_path),
            "--manifest-output",
            str(manifest_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.stdout == ""
    output = pd.read_csv(output_path, dtype={"ticker": str})
    assert output["ticker"].tolist() == ["000660", "005930"]
    assert output["rank"].tolist() == [1, 2]
    assert output["final_composite_score"].equals(output["technical_composite_score"])
    assert output["technical_only_notice"].str.contains("kospi200_technical_only").all()
    manifest = pd.read_json(manifest_path, typ="series")
    assert manifest["scope"] == "kospi200_technical_mvp_v0_1_latest_ranking"
    assert manifest["parameters"]["as_of_date"] == "2026-04-24"
    assert manifest["parameters"]["max_allowed_date"] == "2026-04-24"
    assert manifest["inputs"]["normalized_scores"]["sha256"]
    assert manifest["inputs"]["adoption_synthesis"]["sha256"]


def test_mvp_latest_ranking_cli_prints_csv_when_output_is_omitted(tmp_path: Path) -> None:
    normalized_path = tmp_path / "normalized_scores.csv"
    adoption_path = tmp_path / "adoption_synthesis.csv"
    normalized_score_frame().to_csv(normalized_path, index=False)
    adoption_synthesis_table().to_csv(adoption_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mvp_latest_ranking.py",
            "--normalized-scores",
            str(normalized_path),
            "--adoption-synthesis",
            str(adoption_path),
            "--as-of-date",
            "2026-04-24",
            "--max-allowed-date",
            "2026-04-24",
            "--top-n",
            "1",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "ticker,date,rank,technical_composite_score,final_composite_score" in result.stdout
    assert "000660" in result.stdout


def test_mvp_latest_ranking_cli_requires_explicit_reproducibility_dates(tmp_path: Path) -> None:
    normalized_path = tmp_path / "normalized_scores.csv"
    adoption_path = tmp_path / "adoption_synthesis.csv"
    normalized_score_frame().to_csv(normalized_path, index=False)
    adoption_synthesis_table().to_csv(adoption_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mvp_latest_ranking.py",
            "--normalized-scores",
            str(normalized_path),
            "--adoption-synthesis",
            str(adoption_path),
            "--as-of-date",
            "2026-04-24",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "--max-allowed-date" in result.stderr
