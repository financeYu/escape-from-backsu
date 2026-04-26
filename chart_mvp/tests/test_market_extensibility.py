from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preprocess.schema_validator import validate_standard_price_schema
from stock_core.cache.csv_cache import PriceCachePolicy, get_cache_path, get_financial_statement_cache_path
from stock_core.providers.universe import CsvUniverseProvider
from stock_core.utils.market_specs import (
    GENERIC_EXCHANGE_SYMBOL_POLICY,
    KOREAN_EQUITY_SYMBOL_POLICY,
    OPTIONS_ASSET_CLASS,
    UniverseSpec,
)


class MarketExtensibilityTests(unittest.TestCase):
    def test_csv_universe_provider_uses_configured_symbol_policy_and_size(self) -> None:
        universe_spec = UniverseSpec(
            universe_id="sample_us",
            display_name="Sample US",
            packaged_filename="sample_us.csv",
            snapshot_filename="sample_us_snapshot.csv",
            symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
            expected_size=2,
        )

        with patch(
            "stock_core.providers.universe.pd.read_csv",
            return_value=pd.DataFrame(
                [
                    {"code": "aapl", "name": "Apple"},
                    {"code": "msft", "name": "Microsoft"},
                ]
            ),
        ):
            entries = CsvUniverseProvider(csv_path=Path("sample.csv"), universe_spec=universe_spec).load()

        self.assertEqual([entry.code for entry in entries], ["AAPL", "MSFT"])

    def test_csv_universe_provider_size_rule_is_not_hardcoded_to_200(self) -> None:
        universe_spec = UniverseSpec(
            universe_id="sample_one",
            display_name="Sample One",
            packaged_filename="sample_one.csv",
            snapshot_filename="sample_one_snapshot.csv",
            symbol_policy=KOREAN_EQUITY_SYMBOL_POLICY,
            expected_size=1,
        )

        with patch(
            "stock_core.providers.universe.pd.read_csv",
            return_value=pd.DataFrame([{"code": "5930", "name": "Samsung Electronics"}]),
        ):
            entries = CsvUniverseProvider(csv_path=Path("sample.csv"), universe_spec=universe_spec).load()

        self.assertEqual(entries[0].code, "005930")

    def test_csv_universe_provider_preserves_declared_extension_metadata(self) -> None:
        universe_spec = UniverseSpec(
            universe_id="sample_options",
            display_name="Sample Options",
            packaged_filename="sample_options.csv",
            snapshot_filename="sample_options_snapshot.csv",
            symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
            asset_class=OPTIONS_ASSET_CLASS,
            metadata_columns=("underlying", "expiry", "strike", "option_type"),
            expected_size=1,
        )

        with patch(
            "stock_core.providers.universe.pd.read_csv",
            return_value=pd.DataFrame(
                [
                    {
                        "code": "aapl_20260619_200c",
                        "name": "AAPL Jun 2026 200 Call",
                        "underlying": "AAPL",
                        "expiry": "2026-06-19",
                        "strike": "200",
                        "option_type": "call",
                        "ignored_column": "not-declared",
                    }
                ]
            ),
        ):
            entries = CsvUniverseProvider(csv_path=Path("sample.csv"), universe_spec=universe_spec).load()

        self.assertEqual(entries[0].asset_class, OPTIONS_ASSET_CLASS)
        self.assertEqual(entries[0].code, "AAPL_20260619_200C")
        self.assertEqual(
            entries[0].metadata,
            {
                "underlying": "AAPL",
                "expiry": "2026-06-19",
                "strike": "200",
                "option_type": "call",
            },
        )

    def test_korean_symbol_policy_keeps_legacy_embedded_code_extraction(self) -> None:
        self.assertEqual(KOREAN_EQUITY_SYMBOL_POLICY.normalize("\uc0bc\uc131\uc804\uc790*005930"), "005930")

    def test_non_legacy_cache_policy_namespaces_provider_and_universe(self) -> None:
        cache_policy = PriceCachePolicy(provider_id="example_provider", universe_id="nasdaq100", legacy_layout=False)

        price_path = get_cache_path("AAPL", cache_policy=cache_policy)
        statement_path = get_financial_statement_cache_path("AAPL", cache_policy=cache_policy)

        self.assertEqual(price_path.parts[-5:], ("data", "market_cache", "example_provider", "nasdaq100", "AAPL_daily_prices.csv"))
        self.assertEqual(statement_path.name, "AAPL_financial_statements.csv")

    def test_schema_validator_accepts_configured_non_korean_symbol_policy(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "date": ["2026-04-23"],
                "open": [100],
                "high": [110],
                "low": [90],
                "close": [105],
                "volume": [1000],
                "source": ["fixture"],
            }
        )

        checks = validate_standard_price_schema(frame, symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY)
        failed = {check.check for check in checks if check.status == "fail"}

        self.assertNotIn("ticker_six_char_format", failed)
        self.assertNotIn("ticker_leading_zero_preserved", failed)


if __name__ == "__main__":
    unittest.main()
