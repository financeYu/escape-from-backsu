"""Backward-compatible accessors for universe providers."""

from stock_core.providers.universe import CsvUniverseProvider, Kospi200UniverseProvider, UniverseEntry

__all__ = ["UniverseEntry", "CsvUniverseProvider", "Kospi200UniverseProvider"]
