from __future__ import annotations

from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUANT_ROOT = PROJECT_ROOT / "Quant_mvp"


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _resolve_quant_path(value: str) -> Path:
    return (QUANT_ROOT / value).resolve()


def test_research_intake_paths_resolve_from_quant_project_root():
    config = _load_toml(QUANT_ROOT / "config" / "research_intake.toml")

    assert config["path_resolution"]["base"] == "quant_project_root"

    allowed_inputs = config["allowed_inputs"]
    compatibility_inputs = config["compatibility_inputs"]
    expected_names = {
        "evidence_cards_jsonl",
        "technical_candidates_jsonl",
        "diagnostic_items_jsonl",
        "hybrid_review_required_jsonl",
    }
    assert set(allowed_inputs) == expected_names
    assert set(compatibility_inputs) == expected_names

    canonical_root = (QUANT_ROOT / "research_mvp" / "data" / "research" / "evidence").resolve()
    legacy_root = (QUANT_ROOT / "data" / "research" / "evidence").resolve()

    for value in allowed_inputs.values():
        path = _resolve_quant_path(str(value))
        assert path.is_relative_to(canonical_root)
        assert ".." not in Path(str(value)).parts

    for value in compatibility_inputs.values():
        path = _resolve_quant_path(str(value))
        assert path.is_relative_to(legacy_root)
        assert ".." not in Path(str(value)).parts


def test_quant_config_research_paths_do_not_escape_quant_root():
    checked_values = [
        _load_toml(QUANT_ROOT / "config" / "global.toml")["external_agents"]["research_ingestion_agent_path"],
        _load_toml(QUANT_ROOT / "config" / "scores.toml")["registry_status"]["research_adjustment_source"],
        _load_toml(QUANT_ROOT / "config" / "weights.toml")["research_adjustment"]["source_report"],
    ]

    for value in checked_values:
        text = str(value)
        path = _resolve_quant_path(text)
        assert path.is_relative_to(QUANT_ROOT.resolve())
        assert ".." not in Path(text).parts
