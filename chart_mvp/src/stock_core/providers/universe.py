"""Universe providers for batch stock scans."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stock_core.utils.paths import UNIVERSE_FILE


def _normalize_stock_code(value: object) -> str:
    normalized = str(value).strip().upper()
    if normalized.isdigit():
        return normalized.zfill(6)

    compact = "".join(character for character in normalized if character.isalnum())
    if len(compact) == 6:
        return compact

    return compact or normalized


@dataclass(frozen=True)
class UniverseEntry:
    code: str
    name: str


class Kospi200UniverseProvider:
    """Load the KOSPI200 universe from a local CSV file."""

    def __init__(self, csv_path=UNIVERSE_FILE) -> None:
        self.csv_path = csv_path

    def load(self) -> list[UniverseEntry]:
        frame = pd.read_csv(self.csv_path, dtype={"code": str, "name": str})
        required_columns = {"code", "name"}
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            raise ValueError(f"Universe file is missing columns: {sorted(missing_columns)}")

        cleaned = frame.dropna(subset=["code", "name"]).copy()
        cleaned["code"] = cleaned["code"].map(_normalize_stock_code)
        cleaned["name"] = cleaned["name"].astype(str).str.strip()
        cleaned = cleaned[cleaned["name"] != ""]
        cleaned = cleaned.drop_duplicates(subset=["code"], keep="first").reset_index(drop=True)

        if len(cleaned) != 200:
            raise ValueError(f"KOSPI200 universe file must contain exactly 200 unique stocks, found {len(cleaned)}")

        return [UniverseEntry(code=row.code, name=row.name) for row in cleaned.itertuples(index=False)]
