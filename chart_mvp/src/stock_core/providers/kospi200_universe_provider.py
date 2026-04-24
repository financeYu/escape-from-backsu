"""Public KOSPI200 universe-provider wrappers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_core.providers.universe import Kospi200UniverseProvider, UniverseEntry
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.paths import UNIVERSE_FILE, UNIVERSE_SNAPSHOT_PATH


logger = get_logger(__name__)


def normalize_stock_code(value: object) -> str:
    """Normalize stock codes while preserving valid 6-character alphanumerics."""

    normalized = str(value).strip().upper()
    if normalized.isdigit():
        return normalized.zfill(6)

    compact = "".join(character for character in normalized if character.isalnum())
    if len(compact) == 6:
        return compact

    extracted = pd.Series([normalized]).astype(str).str.extract(r"([A-Z0-9]+)", expand=False).fillna(normalized).iloc[0]
    extracted = str(extracted).upper()
    if extracted.isdigit():
        return extracted.zfill(6)
    return extracted


def _normalize_universe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize universe data to the required snapshot schema."""

    normalized = frame.copy()
    required_columns = {"code", "name"}
    missing_columns = required_columns.difference(normalized.columns)
    if missing_columns:
        raise ValueError(f"Universe data is missing columns: {sorted(missing_columns)}")

    normalized = normalized.loc[:, ["code", "name"]].dropna(subset=["code", "name"]).copy()
    normalized["code"] = normalized["code"].map(normalize_stock_code)
    normalized["name"] = normalized["name"].astype(str).str.strip()
    normalized = normalized[normalized["name"] != ""]
    normalized = normalized.drop_duplicates(subset=["code"], keep="first").reset_index(drop=True)
    return normalized


def load_kospi200_snapshot(snapshot_path: Path | None = None) -> pd.DataFrame:
    """Load the local KOSPI200 snapshot CSV."""

    resolved_path = snapshot_path or (UNIVERSE_SNAPSHOT_PATH if UNIVERSE_SNAPSHOT_PATH.exists() else UNIVERSE_FILE)
    frame = pd.read_csv(resolved_path, dtype={"code": str, "name": str})
    normalized = _normalize_universe_frame(frame)
    if len(normalized) != 200:
        raise ValueError(f"KOSPI200 snapshot must contain exactly 200 unique stocks, found {len(normalized)}")
    return normalized


def fetch_kospi200_universe_live() -> pd.DataFrame:
    """Live universe retrieval stub.

    The repository currently uses the local snapshot path because a reliable
    live source is not wired in yet.
    """

    raise NotImplementedError("Live KOSPI200 retrieval is not implemented yet; use the snapshot CSV path.")


def get_kospi200_constituents(refresh: bool = False) -> list[dict]:
    """Return KOSPI200 constituents as a list of dicts with code/name."""

    if refresh:
        try:
            logger.info("Attempting live KOSPI200 universe refresh")
            frame = fetch_kospi200_universe_live()
            normalized = _normalize_universe_frame(frame)
        except Exception as exc:
            logger.warning("Falling back to local KOSPI200 snapshot: %s", exc)
            normalized = load_kospi200_snapshot()
    else:
        normalized = load_kospi200_snapshot()

    return normalized.to_dict(orient="records")

__all__ = [
    "UniverseEntry",
    "Kospi200UniverseProvider",
    "fetch_kospi200_universe_live",
    "get_kospi200_constituents",
    "load_kospi200_snapshot",
    "normalize_stock_code",
]
