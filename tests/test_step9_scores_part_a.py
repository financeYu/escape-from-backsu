from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.mean_reversion_scores import (  # noqa: E402
    PartAScoreConfig,
    calculate_step9_part_a_raw_scores,
    load_part_a_score_config,
)
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY  # noqa: E402
from src.scores.schema import find_forbidden_output_columns  # noqa: E402
from src.scores.score_contracts import PART_A_RAW_COLUMNS  # noqa: E402


def make_test_config() -> PartAScoreConfig:
    return PartAScoreConfig(
        return_window=1,
        atr_window=14,
        rsi_window=14,
        realized_vol_window=20,
        realized_vol_percentile_window=3,
        minimum_history_by_score={
            "short_term_overreaction": 2,
            "atr_adjusted_oversold_distance": 2,
            "rsi_price_divergence": 2,
            "realized_vol_percentile": 2,
        },
        bollinger_window=2,
    )


def step7_frame(values: list[float], *, ticker: str = "005930") -> pd.DataFrame:
    rows = []
    previous_close: float | None = None
    for idx, value in enumerate(values, start=1):
        close = float(100 + idx)
        return_1d = pd.NA if previous_close is None else (close / previous_close) - 1.0
        rows.append(
            {
                "ticker": ticker,
                "date": f"2026-01-{idx:02d}",
                "close": close,
                "history_count": idx,
                "minimum_history_required": 2,
                "warmup_state": "ready" if idx >= 2 else "warmup",
                "return_1d": return_1d,
                "atr_14": 2.0,
                "bollinger_mid_2": close + 1.0,
                "rsi_14": 40.0 + idx,
                "realized_vol_20": value,
            }
        )
        previous_close = close
    return pd.DataFrame(rows)


class Step9PartAScoreTests(unittest.TestCase):
    def test_realized_vol_percentile_uses_current_and_prior_rows_only(self) -> None:
        frame = step7_frame([3.0, 1.0, 2.0, 4.0])

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())

        self.assertTrue(pd.isna(result.loc[0, "realized_vol_percentile_raw"]))
        self.assertAlmostEqual(result.loc[1, "realized_vol_percentile_raw"], 0.5)
        self.assertAlmostEqual(result.loc[2, "realized_vol_percentile_raw"], 2 / 3)
        self.assertAlmostEqual(result.loc[3, "realized_vol_percentile_raw"], 1.0)

    def test_no_lookahead_when_future_realized_vol_changes(self) -> None:
        base = step7_frame([3.0, 1.0, 2.0, 4.0])
        changed_future = base.copy()
        changed_future.loc[3, "realized_vol_20"] = 100.0

        result = calculate_step9_part_a_raw_scores(base, config=make_test_config())
        changed_result = calculate_step9_part_a_raw_scores(changed_future, config=make_test_config())

        self.assertEqual(
            result.loc[2, "realized_vol_percentile_raw"],
            changed_result.loc[2, "realized_vol_percentile_raw"],
        )

    def test_ticker_groups_do_not_contaminate_each_other(self) -> None:
        frame = pd.concat(
            [
                step7_frame([1.0, 2.0, 3.0], ticker="005930"),
                step7_frame([9.0], ticker="000660"),
            ],
            ignore_index=True,
        )

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())
        hynix = result[result["ticker"] == "000660"].reset_index(drop=True)

        self.assertTrue(pd.isna(hynix.loc[0, "realized_vol_percentile_raw"]))
        self.assertEqual(hynix.loc[0, "score_data_quality_flag"], "warmup")

    def test_date_sorting_is_deterministic_before_calculation(self) -> None:
        frame = step7_frame([3.0, 1.0, 2.0]).iloc[[2, 0, 1]].reset_index(drop=True)

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())

        self.assertEqual(result["date"].dt.strftime("%Y-%m-%d").tolist(), ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertAlmostEqual(result.loc[2, "realized_vol_percentile_raw"], 2 / 3)

    def test_ticker_leading_zero_is_preserved(self) -> None:
        result = calculate_step9_part_a_raw_scores(step7_frame([1.0, 2.0]), config=make_test_config())

        self.assertEqual(result.loc[0, "ticker"], "005930")
        self.assertEqual(str(result["ticker"].dtype), "string")

    def test_generic_symbol_policy_accepts_exchange_symbol(self) -> None:
        result = calculate_step9_part_a_raw_scores(
            step7_frame([1.0, 2.0, 3.0], ticker="AAPL"),
            config=make_test_config(),
            symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
        )

        self.assertEqual(result.loc[0, "ticker"], "AAPL")
        self.assertEqual(str(result["ticker"].dtype), "string")

    def test_insufficient_history_and_warmup_are_not_filled_optimistically(self) -> None:
        frame = step7_frame([1.0, 2.0, 3.0])
        frame.loc[1, "warmup_state"] = "insufficient_history"

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())

        self.assertTrue(pd.isna(result.loc[0, "realized_vol_percentile_raw"]))
        self.assertEqual(result.loc[0, "score_data_quality_flag"], "warmup")
        self.assertTrue(pd.isna(result.loc[1, "realized_vol_percentile_raw"]))
        self.assertEqual(result.loc[1, "score_data_quality_flag"], "insufficient_history")

    def test_nan_current_indicator_is_preserved_as_missing(self) -> None:
        frame = step7_frame([1.0, float("nan"), 3.0])

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())

        self.assertTrue(pd.isna(result.loc[1, "realized_vol_percentile_raw"]))
        self.assertEqual(result.loc[1, "realized_vol_percentile_missing_reason"], "missing_required_input")

    def test_forbidden_output_columns_are_absent(self) -> None:
        result = calculate_step9_part_a_raw_scores(step7_frame([1.0, 2.0, 3.0]), config=make_test_config())

        self.assertEqual(find_forbidden_output_columns(result.columns), [])
        self.assertNotIn("normalized_score", result.columns)
        self.assertNotIn("technical_composite_score", result.columns)

    def test_valuation_or_fundamental_input_columns_are_rejected(self) -> None:
        frame = step7_frame([1.0, 2.0, 3.0])
        frame["PER"] = [10.0, 11.0, 12.0]

        with self.assertRaisesRegex(ValueError, "valuation/fundamental columns"):
            calculate_step9_part_a_raw_scores(frame, config=make_test_config())

    def test_part_a_does_not_require_or_emit_part_b_scores(self) -> None:
        result = calculate_step9_part_a_raw_scores(step7_frame([1.0, 2.0, 3.0]), config=make_test_config())

        self.assertEqual(set(PART_A_RAW_COLUMNS), {column for column in result.columns if column.endswith("_raw")})
        self.assertNotIn("donchian_breakout_distance_raw", result.columns)
        self.assertNotIn("bollinger_width_squeeze_raw", result.columns)
        self.assertNotIn("cmf_confirmation_raw", result.columns)

    def test_locked_mean_reversion_formulas_are_deterministic(self) -> None:
        frame = step7_frame([1.0, 2.0, 3.0])
        frame["close"] = [100.0, 95.0, 90.0]
        frame["return_1d"] = [pd.NA, -0.05, (90.0 / 95.0) - 1.0]
        frame["atr_14"] = [2.0, 2.0, 3.0]
        frame["bollinger_mid_2"] = [100.0, 97.0, 93.0]
        frame["rsi_14"] = [50.0, 55.0, 60.0]

        result = calculate_step9_part_a_raw_scores(frame, config=make_test_config())
        ready_row = result[result["date"].eq(pd.Timestamp("2026-01-02"))].iloc[0]

        self.assertAlmostEqual(ready_row["short_term_overreaction_raw"], 0.05)
        self.assertAlmostEqual(ready_row["atr_adjusted_oversold_distance_raw"], 1.0)
        self.assertAlmostEqual(ready_row["rsi_price_divergence_raw"], 0.25)
        self.assertTrue(pd.isna(ready_row["short_term_overreaction_missing_reason"]))
        self.assertTrue(pd.isna(ready_row["atr_adjusted_oversold_distance_missing_reason"]))
        self.assertTrue(pd.isna(ready_row["rsi_price_divergence_missing_reason"]))

    def test_default_config_loads_quant_registry_values(self) -> None:
        config = load_part_a_score_config(
            windows_config_path=PROJECT_ROOT / "Quant_mvp" / "config" / "windows.toml",
            scores_config_path=PROJECT_ROOT / "Quant_mvp" / "config" / "scores.toml",
        )

        self.assertEqual(config.return_window, 5)
        self.assertEqual(config.bollinger_window, 20)
        self.assertEqual(config.realized_vol_window, 20)
        self.assertEqual(config.realized_vol_percentile_window, 252)
        self.assertEqual(config.minimum_history_by_score["realized_vol_percentile"], 120)


if __name__ == "__main__":
    unittest.main()
