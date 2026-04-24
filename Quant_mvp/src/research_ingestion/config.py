from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


CONFIG_FILES = {
    "sources": "research_sources.toml",
    "queries": "research_queries.toml",
    "policy": "research_policy.toml",
    "classification": "research_classification.toml",
    "scholar_discovery": "research_scholar_discovery.toml",
}
ROOT_MARKER_CONFIG = "research_sources.toml"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def data_dir(self) -> Path:
        return self.root / "data" / "research"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports" / "research_ingestion"


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    candidates = [current, current / "Quant_mvp", *current.parents]
    candidates.extend(parent / "Quant_mvp" for parent in current.parents)
    for candidate in candidates:
        if (
            (candidate / "AGENTS.md").exists()
            and (candidate / "config" / ROOT_MARKER_CONFIG).exists()
        ):
            return candidate
    raise FileNotFoundError("Could not locate Quant_mvp project root with AGENTS.md and config/.")


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required config file: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_research_config(root: Path | None = None) -> dict[str, Any]:
    paths = ProjectPaths(find_project_root(root))
    loaded: dict[str, Any] = {}
    for key, filename in CONFIG_FILES.items():
        loaded[key] = load_toml(paths.config_dir / filename)
    return loaded


def get_source_config(config: dict[str, Any], source_name: str) -> dict[str, Any]:
    try:
        source = config["sources"]["sources"][source_name]
    except KeyError as exc:
        raise KeyError(f"Unknown research source: {source_name}") from exc
    defaults = config["sources"].get("defaults", {})
    merged = {**defaults, **source}
    merged["name"] = source_name
    return merged


def get_query_set(config: dict[str, Any], query_set: str) -> dict[str, Any]:
    try:
        return config["queries"]["query_sets"][query_set]
    except KeyError as exc:
        available = ", ".join(sorted(config.get("queries", {}).get("query_sets", {})))
        raise ValueError(f"알 수 없는 research query-set입니다: {query_set}. 사용 가능: {available}") from exc


def validate_policy(config: dict[str, Any]) -> None:
    guardrails = config["policy"].get("guardrails", {})
    required_true = [
        "no_score_adoption",
        "no_backtest",
        "no_alpha_claim",
        "do_not_infer_valuation_from_price",
    ]
    disabled = [name for name in required_true if guardrails.get(name) is not True]
    if disabled:
        raise ValueError(f"Research policy guardrails must remain enabled: {', '.join(disabled)}")


def validate_pdf_policy(config: dict[str, Any], allow_pdf: bool, confirmed: bool) -> None:
    pdf_policy = config["policy"].get("pdf_policy", {})
    if not allow_pdf:
        return
    if not pdf_policy.get("allow_pdf", False):
        raise ValueError("PDF use is disabled by research_policy.toml.")
    if pdf_policy.get("explicit_confirmation_required", True) and not confirmed:
        raise ValueError("--allow-pdf requires explicit policy confirmation.")
