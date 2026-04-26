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

from app.cli import main as cli_main
from app.cli import run_single_stock
from stock_core.pipeline.daily_update import DailyUpdateRow, _render_selected_charts, load_latest_top5_snapshot


class CliTests(unittest.TestCase):
    def test_default_cli_path_uses_modern_daily_top5_pipeline(self) -> None:
        top_df = pd.DataFrame({"종목코드": ["005930"]})
        meta = {
            "output_csv": "latest_top.csv",
            "output_json": "latest_top.json",
            "chart_paths": [],
            "failed_count": 0,
        }

        with patch("app.cli.run_daily_top5_update", return_value=(top_df, meta)) as mock_run:
            exit_code = cli_main([])

        self.assertEqual(exit_code, 0)
        mock_run.assert_called_once_with(
            pages=20,
            use_cache=True,
            refresh_universe=False,
            render_charts=True,
            max_workers=None,
            top_n=5,
            use_market_cap_override=False,
        )

    def test_due_only_cli_path_uses_due_checked_pipeline(self) -> None:
        with patch(
            "app.cli.run_daily_top5_update_if_due",
            return_value=(None, {"reason": "already updated", "due_at": None, "due_last_successful_update_date": "2026-04-20"}),
        ) as mock_run:
            exit_code = cli_main(["scan", "--due-only"])

        self.assertEqual(exit_code, 0)
        mock_run.assert_called_once_with(
            pages=20,
            use_cache=True,
            refresh_universe=False,
            render_charts=True,
            max_workers=None,
            top_n=5,
            use_market_cap_override=False,
        )

    def test_single_stock_cli_normalizes_alphanumeric_code_before_fetch(self) -> None:
        price_df = pd.DataFrame({"날짜": ["2026-04-24"], "종가": [574000]})

        with (
            patch("app.cli.fetch_stock_name", return_value="Samsung Epis") as mock_name,
            patch(
                "app.cli.refresh_stock_data",
                return_value=(price_df, "fetched"),
            ) as mock_refresh,
            patch(
                "app.cli.get_cache_path",
                return_value=PROJECT_ROOT / "data" / "0126Z0_daily_prices.csv",
            ),
            patch("app.cli.plot_stock_data"),
        ):
            exit_code = run_single_stock("0126z0", pages=1, show_chart=False)

        self.assertEqual(exit_code, 0)
        mock_name.assert_called_once_with("0126Z0")
        mock_refresh.assert_called_once_with(code="0126Z0", pages=1)


class DailyUpdateTests(unittest.TestCase):
    def test_latest_snapshot_prefers_algorithm_ranking_output(self) -> None:
        legacy_frame = pd.DataFrame(
            [
                [
                    1,
                    "000080",
                    "Legacy",
                    0.0,
                ]
            ],
            columns=["순위", "종목코드", "종목명", "점수"],
        )
        algorithm_frame = pd.DataFrame(
            [
                {
                    "ticker": "005930",
                    "date": "2026-04-20",
                    "rank": 1,
                    "technical_composite_score": 1.23,
                    "final_composite_score": 1.23,
                    "ranking_validity_flag": "valid",
                    "technical_only_notice": "KOSPI200 technical-only scanner v0.1; no valuation/fundamental data.",
                }
            ]
        )

        def fake_exists(path: Path) -> bool:
            return path.name in {"latest_score_top.csv", "latest_top.csv"}

        def fake_read_csv(path: Path, **_kwargs: object) -> pd.DataFrame:
            return algorithm_frame.copy() if path.name == "latest_score_top.csv" else legacy_frame.copy()

        with (
            patch("stock_core.pipeline.daily_update.OUTPUTS_DIR", Path("outputs")),
            patch("pathlib.Path.exists", fake_exists),
            patch("stock_core.pipeline.daily_update.pd.read_csv", side_effect=fake_read_csv),
            patch(
                "stock_core.pipeline.daily_update.get_universe_constituents",
                return_value=[{"code": "005930", "name": "Samsung Electronics"}],
            ),
        ):
            frame = load_latest_top5_snapshot()

        self.assertEqual(frame.iloc[0]["종목코드"], "005930")
        self.assertEqual(frame.iloc[0]["종목명"], "Samsung Electronics")
        self.assertEqual(frame.iloc[0]["순위"], 1)
        self.assertEqual(frame.iloc[0]["점수"], 1.23)
        self.assertEqual(frame.iloc[0]["ranking_snapshot_source"], "latest_score_top")
        self.assertEqual(frame.iloc[0]["canonical_ranking_source"], "root src.scanner.latest_ranking")

    def test_latest_snapshot_can_fallback_to_legacy_output(self) -> None:
        legacy_frame = pd.DataFrame(
            [
                {
                    "순위": 1,
                    "종목코드": "80",
                    "종목명": "Legacy",
                    "점수": 0.0,
                }
            ]
        )

        def fake_exists(path: Path) -> bool:
            return path.name == "latest_top.csv"

        with (
            patch("stock_core.pipeline.daily_update.OUTPUTS_DIR", Path("outputs")),
            patch("pathlib.Path.exists", fake_exists),
            patch("stock_core.pipeline.daily_update.pd.read_csv", return_value=legacy_frame.copy()),
        ):
            frame = load_latest_top5_snapshot()

        self.assertEqual(frame.iloc[0]["종목코드"], "000080")
        self.assertEqual(frame.iloc[0]["종목명"], "Legacy")

    def test_chart_render_failure_does_not_abort_batch(self) -> None:
        rows = [
            DailyUpdateRow(
                code="005930",
                name="A",
                score=0.0,
                latest_date="2026-04-21",
                latest_close=1.0,
                latest_change=0.0,
                latest_volume=1.0,
                rsi14=50.0,
                data_source="cache_or_fetch",
                df=pd.DataFrame(),
            ),
            DailyUpdateRow(
                code="000660",
                name="B",
                score=0.0,
                latest_date="2026-04-21",
                latest_close=1.0,
                latest_change=0.0,
                latest_volume=1.0,
                rsi14=50.0,
                data_source="cache_or_fetch",
                df=pd.DataFrame(),
            ),
        ]

        def fake_render_stock_chart(_df: pd.DataFrame, code: str, _name: str, _out_path: str) -> None:
            if code == "005930":
                raise RuntimeError("chart boom")

        with patch(
            "stock_core.pipeline.daily_update.prepare_chart_dataframe",
            return_value=pd.DataFrame({"x": [1]}),
        ), patch(
            "stock_core.charts.renderer.render_stock_chart",
            side_effect=fake_render_stock_chart,
        ):
            chart_paths, chart_failed_codes = _render_selected_charts(
                rows=rows,
                selected_codes={"005930", "000660"},
                pages=20,
                use_cache=True,
                output_dir=PROJECT_ROOT / "outputs" / "charts",
                file_name_builder=lambda row: f"{row.code}.png",
            )

        self.assertEqual(chart_paths, [str(PROJECT_ROOT / "outputs" / "charts" / "000660.png")])
        self.assertEqual(chart_failed_codes, ["005930"])


if __name__ == "__main__":
    unittest.main()
