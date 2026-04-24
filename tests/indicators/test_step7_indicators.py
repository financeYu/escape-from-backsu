from __future__ import annotations

import shutil
import sys
import textwrap
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indicators.technical import (
    IndicatorWindows,
    calculate_technical_indicators,
    load_indicator_config,
    run_indicator_pipeline_from_config,
)


def windows(
    *,
    returns: dict[str, int] | None = None,
    volatility: dict[str, int] | None = None,
    indicators: dict[str, int] | None = None,
    statistics: dict[str, int] | None = None,
) -> IndicatorWindows:
    return IndicatorWindows(
        returns=returns or {},
        volatility=volatility or {},
        indicators=indicators or {},
        statistics=statistics or {},
        warmup={"minimum_price_history_days": 5},
    )


def sample_frame(close_values: list[float], *, ticker: str = "005930") -> pd.DataFrame:
    rows = []
    for idx, close in enumerate(close_values, start=1):
        rows.append(
            {
                "ticker": ticker,
                "date": f"2026-01-{idx:02d}",
                "open": close - 1,
                "high": close + 1,
                "low": close - 2,
                "close": close,
                "volume": 1000 + idx,
            }
        )
    return pd.DataFrame(rows)


class Step7IndicatorTests(unittest.TestCase):
    def test_returns_do_not_cross_ticker_boundaries(self) -> None:
        frame = pd.concat(
            [
                sample_frame([10, 11, 13], ticker="005930"),
                sample_frame([100, 100, 120], ticker="000660"),
            ],
            ignore_index=True,
        )

        result = calculate_technical_indicators(
            frame,
            windows=windows(returns={"short": 2}),
            as_of_date="2026-01-31",
        )

        first_rows = result.groupby("ticker", sort=False).head(1)
        self.assertTrue(first_rows["return_1d"].isna().all())
        samsung = result[result["ticker"] == "005930"].reset_index(drop=True)
        self.assertAlmostEqual(samsung.loc[1, "return_1d"], 0.1)
        self.assertAlmostEqual(samsung.loc[2, "return_2d"], 0.3)

    def test_donchian_prior_high_uses_previous_completed_bars(self) -> None:
        frame = sample_frame([10, 20, 15, 14])
        frame.loc[2, "high"] = 99

        result = calculate_technical_indicators(
            frame,
            windows=windows(indicators={"donchian": 2}),
            as_of_date="2026-01-31",
        )

        self.assertTrue(pd.isna(result.loc[1, "donchian_high_prior_2"]))
        self.assertEqual(result.loc[2, "donchian_high_prior_2"], 21)
        self.assertEqual(result.loc[3, "donchian_high_prior_2"], 99)

    def test_warmup_periods_preserve_missing_indicator_values(self) -> None:
        frame = sample_frame([10, 11, 12, 13])

        result = calculate_technical_indicators(
            frame,
            windows=windows(
                volatility={"atr": 3},
                indicators={"rsi": 3, "bollinger": 3},
            ),
            as_of_date="2026-01-31",
        )

        self.assertTrue(result.loc[:1, "atr_3"].isna().all())
        self.assertTrue(result.loc[:2, "rsi_3"].isna().all())
        self.assertFalse(pd.isna(result.loc[3, "rsi_3"]))
        self.assertTrue(result.loc[:1, "bollinger_width_3"].isna().all())

    def test_warmup_state_marks_ready_warmup_and_insufficient_history(self) -> None:
        result = calculate_technical_indicators(
            sample_frame([10, 11, 12, 13, 14, 15]),
            windows=windows(),
            as_of_date="2026-01-31",
        )

        self.assertEqual(result.loc[0, "history_count"], 1)
        self.assertEqual(result.loc[0, "minimum_history_required"], 5)
        self.assertEqual(result.loc[0, "warmup_state"], "warmup")
        self.assertEqual(result.loc[4, "warmup_state"], "ready")

        short_history = calculate_technical_indicators(
            sample_frame([10, 11, 12, 13]),
            windows=windows(),
            as_of_date="2026-01-31",
        )
        self.assertEqual(set(short_history["warmup_state"]), {"insufficient_history"})

    def test_future_dates_are_rejected_against_as_of_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "future dates"):
            calculate_technical_indicators(
                sample_frame([10, 11, 12]),
                windows=windows(),
                as_of_date="2026-01-02",
            )

    def test_zero_denominators_do_not_create_infinite_values(self) -> None:
        frame = sample_frame([10, 10, 10])
        frame[["open", "high", "low", "close"]] = 10

        result = calculate_technical_indicators(
            frame,
            windows=windows(indicators={"stochastic": 2, "williams_r": 2, "cmf": 2}),
            as_of_date="2026-01-31",
        )

        values = result[["stochastic_k_2", "williams_r_2", "cmf_2"]].to_numpy().ravel()
        finite_values = [value for value in values if pd.notna(value)]
        self.assertFalse(any(value in (float("inf"), float("-inf")) for value in finite_values))
        self.assertEqual(result.loc[2, "cmf_2"], 0)

    def test_indicator_layer_does_not_emit_forbidden_step7_columns(self) -> None:
        frame = sample_frame([10, 11, 12, 13, 14])

        result = calculate_technical_indicators(
            frame,
            windows=windows(
                returns={"short": 2},
                volatility={"atr": 3, "realized_vol": 3},
                indicators={"rsi": 3, "donchian": 3, "cmf": 3},
                statistics={"efficiency_ratio": 3},
            ),
            as_of_date="2026-01-31",
        )

        forbidden_tokens = ("score", "rank", "ranking", "composite", "alpha", "signal")
        self.assertFalse(
            [
                column
                for column in result.columns
                if any(token in column.lower() for token in forbidden_tokens)
            ]
        )

    def test_missing_required_ohlcv_column_fails_clear(self) -> None:
        frame = sample_frame([10, 11]).drop(columns=["volume"])

        with self.assertRaisesRegex(ValueError, "Missing required OHLCV columns: volume"):
            calculate_technical_indicators(frame, windows=windows(), as_of_date="2026-01-31")

    def test_config_driven_pipeline_writes_indicator_outputs(self) -> None:
        root = PROJECT_ROOT / "tests" / "_tmp" / "step7_indicator_fixture"
        if root.exists():
            shutil.rmtree(root)
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
        sample_frame([10, 11, 12, 13, 14, 15]).to_csv(
            root / "data" / "processed" / "daily_ohlcv.csv",
            index=False,
            encoding="utf-8",
        )
        (root / "config" / "data.toml").write_text(
            textwrap.dedent(
                """\
                [indicators]
                input_price_path = "data/processed/daily_ohlcv.csv"
                output_path = "data/processed/technical_indicators.csv"
                summary_report_path = "reports/indicators/indicator_summary.md"
                validation_report_path = "reports/indicators/indicator_validation_summary.csv"
                """
            ),
            encoding="utf-8",
        )
        (root / "config" / "windows.toml").write_text(
            textwrap.dedent(
                """\
                [returns]
                short = 2

                [volatility]
                atr = 3
                realized_vol = 3

                [indicators]
                rsi = 3
                bollinger = 3
                donchian = 3
                macd_fast = 2
                macd_slow = 3
                macd_trigger = 2

                [statistics]
                efficiency_ratio = 3

                [warmup]
                minimum_price_history_days = 5
                """
            ),
            encoding="utf-8",
        )

        try:
            result = run_indicator_pipeline_from_config(project_root=root)

            self.assertTrue(result.output_path.exists())
            self.assertTrue(result.summary_report_path.exists())
            self.assertTrue(result.validation_report_path.exists())
            self.assertIn("return_2d", result.indicators.columns)
            self.assertIn("macd_trigger_2", result.indicators.columns)
            self.assertNotIn("macd_signal_2", result.indicators.columns)
            self.assertIn("warmup_state", result.indicators.columns)
            self.assertIn("score 구현", result.summary_report_path.read_text(encoding="utf-8"))
            self.assertEqual(result.summary["score_implementation"], "not_performed")
            self.assertEqual(result.summary["backtest"], "not_performed")
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_root_step7_window_config_is_active(self) -> None:
        config = load_indicator_config(
            data_config_path=PROJECT_ROOT / "config" / "data.toml",
            windows_config_path=PROJECT_ROOT / "config" / "windows.toml",
        )

        self.assertEqual(config.paths.input_path, "data/processed/daily_ohlcv.csv")
        self.assertEqual(config.windows.returns["short"], 5)
        self.assertEqual(config.windows.volatility["atr"], 14)
        self.assertEqual(config.windows.indicators["rsi"], 14)
        self.assertEqual(config.windows.indicators["macd_trigger"], 9)
        self.assertEqual(config.windows.statistics["efficiency_ratio"], 20)


if __name__ == "__main__":
    unittest.main()
