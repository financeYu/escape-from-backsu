"""Public KOSPI200 universe-provider wrappers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_core.providers.universe import CsvUniverseProvider, Kospi200UniverseProvider, UniverseEntry
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.market_specs import KOSPI200_UNIVERSE_SPEC, UniverseSpec
from stock_core.utils.paths import UNIVERSE_FILE, UNIVERSE_SNAPSHOT_PATH, get_packaged_universe_file, get_universe_snapshot_path


logger = get_logger(__name__)


def normalize_stock_code(value: object) -> str:
    """Normalize stock codes while preserving valid 6-character alphanumerics."""

    return KOSPI200_UNIVERSE_SPEC.symbol_policy.normalize(value)


def _normalize_universe_frame(frame: pd.DataFrame, universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC) -> pd.DataFrame:
    """Normalize universe data to the required snapshot schema."""

    normalized = frame.copy()
    required_columns = {"code", "name"}
    missing_columns = required_columns.difference(normalized.columns)
    if missing_columns:
        raise ValueError(f"Universe data is missing columns: {sorted(missing_columns)}")

    normalized = normalized.loc[:, ["code", "name"]].dropna(subset=["code", "name"]).copy()
    normalized["code"] = normalized["code"].map(universe_spec.symbol_policy.normalize)
    normalized["name"] = normalized["name"].astype(str).str.strip()
    normalized = normalized[normalized["name"] != ""]
    normalized = normalized.drop_duplicates(subset=["code"], keep="first").reset_index(drop=True)
    return normalized


def load_universe_snapshot(universe_spec: UniverseSpec, snapshot_path: Path | None = None) -> pd.DataFrame:
    """Load and validate a configured local universe snapshot CSV."""

    fallback_path = get_packaged_universe_file(universe_spec)
    default_snapshot_path = get_universe_snapshot_path(universe_spec)
    resolved_path = snapshot_path or (default_snapshot_path if default_snapshot_path.exists() else fallback_path)
    frame = pd.read_csv(resolved_path, dtype={"code": str, "name": str})
    normalized = _normalize_universe_frame(frame, universe_spec=universe_spec)
    universe_spec.validate_size(len(normalized))
    return normalized


def load_kospi200_snapshot(snapshot_path: Path | None = None) -> pd.DataFrame:
    """Load the local KOSPI200 snapshot CSV."""

    return load_universe_snapshot(KOSPI200_UNIVERSE_SPEC, snapshot_path=snapshot_path)


def fetch_kospi200_universe_live() -> pd.DataFrame:
    """Live universe retrieval stub.

    The repository currently uses the local snapshot path because a reliable
    live source is not wired in yet.
    """

    raise NotImplementedError("Live KOSPI200 retrieval is not implemented yet; use the snapshot CSV path.")


def get_universe_constituents(
    universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC,
    *,
    refresh: bool = False,
) -> list[dict]:
    """Return configured universe constituents as a list of dicts with code/name."""

    if refresh:
        try:
            if universe_spec != KOSPI200_UNIVERSE_SPEC or not universe_spec.live_refresh_supported:
                raise NotImplementedError(
                    f"Live {universe_spec.display_name} retrieval is not implemented yet; use the snapshot CSV path."
                )
            logger.info("Attempting live %s universe refresh", universe_spec.display_name)
            frame = fetch_kospi200_universe_live()
            normalized = _normalize_universe_frame(frame, universe_spec=universe_spec)
        except Exception as exc:
            logger.warning("Falling back to local %s snapshot: %s", universe_spec.display_name, exc)
            normalized = load_universe_snapshot(universe_spec)
    else:
        normalized = load_universe_snapshot(universe_spec)

    return normalized.to_dict(orient="records")


def get_kospi200_constituents(refresh: bool = False) -> list[dict]:
    """Return KOSPI200 constituents as a list of dicts with code/name."""

    return get_universe_constituents(KOSPI200_UNIVERSE_SPEC, refresh=refresh)

__all__ = [
    "CsvUniverseProvider",
    "UniverseEntry",
    "Kospi200UniverseProvider",
    "fetch_kospi200_universe_live",
    "get_kospi200_constituents",
    "get_universe_constituents",
    "load_kospi200_snapshot",
    "load_universe_snapshot",
    "normalize_stock_code",
]
