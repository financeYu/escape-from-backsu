from __future__ import annotations

import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


CONFIG_PATH = PROJECT_ROOT / "Quant_mvp" / "config" / "up_probability.toml"


def migration_config() -> dict:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))["primary_score_migration"]


def test_primary_score_migration_keeps_runtime_cutover_disabled() -> None:
    config = migration_config()

    assert config["primary_score_column"] == "next_horizon_up_probability_score"
    assert config["primary_score_status"] == "primary_candidate_pending_validation"
    assert config["primary_score_runtime_cutover_enabled"] is False
    assert config["legacy_score_runtime_fallback_enabled"] is False


def test_primary_score_migration_archives_old_scores_under_legacy_names() -> None:
    config = migration_config()

    assert config["legacy_score_archive_enabled"] is True
    assert config["legacy_score_archive_columns"] == [
        "legacy_technical_composite_score",
        "legacy_final_composite_score",
    ]
    assert config["legacy_score_archive_status"] == "archived_legacy_reference"


def test_primary_score_migration_blocks_old_active_score_columns_after_cutover() -> None:
    config = migration_config()

    assert config["forbidden_active_score_columns_after_cutover"] == [
        "technical_composite_score",
        "final_composite_score",
    ]
