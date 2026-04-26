"""Universe providers for batch stock scans."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from stock_core.utils.market_specs import KOREAN_EQUITY_SYMBOL_POLICY, KOSPI200_UNIVERSE_SPEC, SymbolPolicy, UniverseSpec
from stock_core.utils.paths import UNIVERSE_FILE, get_packaged_universe_file


def _normalize_stock_code(value: object, symbol_policy: SymbolPolicy = KOREAN_EQUITY_SYMBOL_POLICY) -> str:
    return symbol_policy.normalize(value)


@dataclass(frozen=True)
class UniverseEntry:
    code: str
    name: str
    asset_class: str = KOSPI200_UNIVERSE_SPEC.asset_class
    metadata: Mapping[str, str] = field(default_factory=dict)


class CsvUniverseProvider:
    """Load a configured instrument universe from a local CSV file."""

    def __init__(self, csv_path: str | Path | None = None, universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC) -> None:
        self.universe_spec = universe_spec
        self.csv_path = Path(csv_path) if csv_path is not None else get_packaged_universe_file(universe_spec)

    def load(self) -> list[UniverseEntry]:
        frame = pd.read_csv(self.csv_path, dtype={"code": str, "name": str})
        required_columns = {"code", "name"}
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            raise ValueError(f"Universe file is missing columns: {sorted(missing_columns)}")

        cleaned = frame.dropna(subset=["code", "name"]).copy()
        cleaned["code"] = cleaned["code"].map(lambda value: _normalize_stock_code(value, self.universe_spec.symbol_policy))
        cleaned["name"] = cleaned["name"].astype(str).str.strip()
        cleaned = cleaned[cleaned["name"] != ""]
        cleaned = cleaned.drop_duplicates(subset=["code"], keep="first").reset_index(drop=True)

        self.universe_spec.validate_size(len(cleaned))

        entries: list[UniverseEntry] = []
        metadata_columns = tuple(column for column in self.universe_spec.metadata_columns if column in cleaned.columns)
        for _, row in cleaned.iterrows():
            metadata = {
                column: str(row[column]).strip()
                for column in metadata_columns
                if pd.notna(row[column]) and str(row[column]).strip()
            }
            entries.append(
                UniverseEntry(
                    code=str(row["code"]),
                    name=str(row["name"]),
                    asset_class=self.universe_spec.asset_class,
                    metadata=metadata,
                )
            )
        return entries


class Kospi200UniverseProvider(CsvUniverseProvider):
    """Load the KOSPI200 universe from a local CSV file."""

    def __init__(self, csv_path=UNIVERSE_FILE) -> None:
        super().__init__(csv_path=csv_path, universe_spec=KOSPI200_UNIVERSE_SPEC)
