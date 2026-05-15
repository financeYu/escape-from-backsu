from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
TEST_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "test_pipeline"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.pipeline.daily_update import (
    LEGACY_PLACEHOLDER_SCORE_NOTICE,
    DailyUpdateRow,
    _render_selected_charts,
    run_daily_top5_update,
    run_daily_top5_update_if_due,
)
from stock_core.providers.kospi200_universe_provider import UniverseEntry
from stock_core.utils.constants import DATE_COLUMN, INDICATOR_COLUMNS, PRICE_COLUMNS


def make_row(code: str, name: str, score: float = 0.0) -> DailyUpdateRow:
    return DailyUpdateRow(
        code=code,
        name=name,
        score=score,
        latest_date="2026-04-21",
        latest_close=100.0,
        latest_change=0.0,
        latest_volume=1000.0,
        rsi14=50.0,
        data_source="cache_or_fetch",
        df=pd.DataFrame(),
    )


def make_chart_ready_frame(rows: int = 80) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B")
    frame = pd.DataFrame(
        {
            DATE_COLUMN: dates,
            "종가": [100.0 + index for index in range(rows)],
            "전일비": [0.0 for _ in range(rows)],
            "시가": [99.0 + index for index in range(rows)],
            "고가": [101.0 + index for index in range(rows)],
            "저가": [98.0 + index for index in range(rows)],
            "거래량": [1000.0 + index for index in range(rows)],
        }
    )
    for column in INDICATOR_COLUMNS:
        frame[column] = 50.0
    assert set(PRICE_COLUMNS).issubset(frame.columns)
    return frame


class PipelineTests(unittest.TestCase):
    def test_render_selected_charts_continues_when_one_chart_fails(self) -> None:
        rows = [make_row("005930", "Samsung Electronics"), make_row("000660", "SK Hynix")]

        output_dir = TEST_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        def fake_render_stock_chart(_df: pd.DataFrame, code: str, _name: str, _out_path: str) -> None:
            if code == "000660":
                raise RuntimeError("chart boom")

        with (
            patch("stock_core.pipeline.daily_update.prepare_chart_dataframe", return_value=pd.DataFrame()),
            patch("stock_core.charts.renderer.render_stock_chart", side_effect=fake_render_stock_chart),
        ):
            chart_paths, chart_failed_codes = _render_selected_charts(
                rows=rows,
                selected_codes={"005930", "000660"},
                pages=1,
                use_cache=True,
                output_dir=output_dir,
                file_name_builder=lambda row: f"{row.code}.png",
            )

        self.assertEqual(len(chart_paths), 1)
        self.assertTrue(chart_paths[0].endswith("005930.png"))
        self.assertEqual(chart_failed_codes, ["000660"])

    def test_render_selected_charts_reuses_processed_indicator_data_when_sufficient(self) -> None:
        rows = [make_row("005930", "Samsung Electronics")]
        rows[0].df = make_chart_ready_frame()

        output_dir = TEST_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("stock_core.pipeline.daily_update.prepare_chart_dataframe") as mock_prepare,
            patch("stock_core.charts.renderer.render_stock_chart") as mock_render,
        ):
            chart_paths, chart_failed_codes = _render_selected_charts(
                rows=rows,
                selected_codes={"005930"},
                pages=1,
                use_cache=True,
                output_dir=output_dir,
                file_name_builder=lambda row: f"{row.code}.png",
            )

        mock_prepare.assert_not_called()
        rendered_frame = mock_render.call_args.args[0]
        self.assertEqual(len(rendered_frame), 70)
        self.assertEqual(chart_failed_codes, [])
        self.assertEqual(len(chart_paths), 1)

    def test_run_daily_top5_update_reports_chart_failures_without_raising(self) -> None:
        row = make_row("005930", "Samsung Electronics")

        with (
            patch("stock_core.pipeline.daily_update._build_universe_entries", return_value=[UniverseEntry(code="005930", name="Samsung Electronics")]),
            patch("stock_core.pipeline.daily_update._process_universe_entry", return_value=row),
            patch("stock_core.pipeline.daily_update._render_selected_charts", return_value=([], ["005930"])),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top5_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=True,
                max_workers=1,
            )

        self.assertEqual(len(top5_df), 1)
        self.assertEqual(meta["processed_count"], 1)
        self.assertEqual(meta["failed_count"], 0)
        self.assertEqual(meta["chart_failed_count"], 1)
        self.assertEqual(meta["chart_failed_codes"], ["005930"])
        self.assertEqual(meta["top_n"], 5)
        self.assertEqual(meta["runtime_boundary_notice"], LEGACY_PLACEHOLDER_SCORE_NOTICE)
        self.assertEqual(meta["canonical_ranking_source"], "root src.scanner.latest_ranking")
        self.assertFalse(meta["financial_refresh_with_price"])
        self.assertEqual(top5_df["runtime_boundary_notice"].tolist(), [LEGACY_PLACEHOLDER_SCORE_NOTICE])
        self.assertEqual(meta["kis_revision_raw_snapshot"]["status"], "skipped")

    def test_run_daily_top5_update_collects_kis_revision_snapshots_when_enabled(self) -> None:
        row = make_row("005930", "Samsung Electronics")
        calls = []
        token_calls = []

        class FakeKisResult:
            output_path = Path("data/kis_revision_raw_snapshots/fake.jsonl")
            records_written = 3
            endpoint_counts = {"estimate_perform": 1, "invest_opinion": 1, "invest_opbysec": 1}
            token_refreshed = False
            token_expires_at = "2999-01-01 00:00:00"

        class FakeTokenState:
            def redacted_summary(self):
                return {
                    "status": "ready",
                    "refreshed": True,
                    "expires_at": "2999-01-01 00:00:00",
                    "missing_materials": [],
                    "warnings": [],
                    "secret_values_redacted": True,
                }

        def fake_token_provider():
            token_calls.append("called")
            return FakeTokenState()

        def fake_collector(**kwargs):
            calls.append(kwargs)
            return FakeKisResult()

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code="005930", name="Samsung Electronics")],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", return_value=row),
            patch("stock_core.pipeline.daily_update._render_selected_charts", return_value=([], [])),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            _top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=True,
                max_workers=1,
                collect_kis_revision_snapshots=True,
                kis_revision_token_provider=fake_token_provider,
                kis_revision_snapshot_collector=fake_collector,
            )

        self.assertEqual(token_calls, ["called"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["codes"], ["005930"])
        self.assertEqual(calls[0]["max_pages"], 1)
        self.assertEqual(meta["kis_revision_raw_snapshot"]["status"], "collected")
        self.assertEqual(meta["kis_revision_raw_snapshot"]["token_preflight"]["status"], "ready")
        self.assertTrue(meta["kis_revision_raw_snapshot"]["token_preflight"]["refreshed"])
        self.assertEqual(meta["kis_revision_raw_snapshot"]["records_written"], 3)
        self.assertEqual(
            meta["kis_revision_raw_snapshot"]["feature_allowlist_state"],
            "blocked_candidate_only",
        )
        self.assertFalse(meta["kis_revision_raw_snapshot"]["usable_for_v1_4_feature_manifest"])
        self.assertFalse(meta["kis_revision_raw_snapshot"]["auto_reference_allowed"])
        self.assertIn(
            "must_not_feed_v1_4_features",
            meta["kis_revision_raw_snapshot"]["downstream_consumption_policy"],
        )

    def test_run_daily_top5_update_collects_krx_listed_info_when_enabled(self) -> None:
        row = make_row("005930", "Samsung Electronics")
        calls = []

        class FakeKrxResult:
            output_path = Path("data/krx_listed_info_raw_snapshots/fake.jsonl")
            records_written = 1
            total_count = 1
            pages_collected = 1
            selected_env_var = "DATA_GO_KR_API_KEY"

        def fake_krx_collector(**kwargs):
            calls.append(kwargs)
            return FakeKrxResult()

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code="005930", name="Samsung Electronics")],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", return_value=row),
            patch("stock_core.pipeline.daily_update._render_selected_charts", return_value=([], [])),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            _top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=True,
                max_workers=1,
                collect_krx_listed_info_snapshots=True,
                krx_listed_info_snapshot_collector=fake_krx_collector,
            )

        self.assertEqual(calls, [{"codes": ["005930"], "max_pages": 1}])
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["status"], "collected")
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["records_written"], 1)
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["total_count"], 1)
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["codes_requested"], 1)
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["query_mode"], "code_supplement_latest")
        self.assertEqual(
            meta["krx_listed_info_raw_snapshot"]["feature_allowlist_state"],
            "blocked_candidate_only",
        )
        self.assertFalse(meta["krx_listed_info_raw_snapshot"]["usable_for_v1_4_feature_manifest"])
        self.assertFalse(meta["krx_listed_info_raw_snapshot"]["auto_reference_allowed"])
        self.assertIn("code", meta["krx_listed_info_raw_snapshot"]["supplemented_mapping_fields"])
        self.assertIn("sector_revision_percentile", meta["krx_listed_info_raw_snapshot"]["blocked_fields"])

    def test_run_daily_top5_update_records_krx_listed_info_failure_without_raising(self) -> None:
        row = make_row("005930", "Samsung Electronics")

        def fake_krx_collector(**_kwargs):
            raise RuntimeError("KRX listed-info HTTP 403: Forbidden")

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code="005930", name="Samsung Electronics")],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", return_value=row),
            patch("stock_core.pipeline.daily_update._render_selected_charts", return_value=([], [])),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=True,
                max_workers=1,
                collect_krx_listed_info_snapshots=True,
                krx_listed_info_snapshot_collector=fake_krx_collector,
            )

        self.assertEqual(len(top_df), 1)
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["status"], "failed")
        self.assertEqual(meta["krx_listed_info_raw_snapshot"]["error_type"], "RuntimeError")

    def test_run_daily_top5_update_records_kis_snapshot_blocker_without_raising(self) -> None:
        row = make_row("005930", "Samsung Electronics")

        class FakeTokenState:
            def redacted_summary(self):
                return {
                    "status": "blocked",
                    "refreshed": False,
                    "expires_at": None,
                    "missing_materials": ["KIS_APP_KEY"],
                    "warnings": [],
                    "secret_values_redacted": True,
                }

        def fake_collector(**_kwargs):
            raise RuntimeError("KIS token is not ready: secret_values_redacted")

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code="005930", name="Samsung Electronics")],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", return_value=row),
            patch("stock_core.pipeline.daily_update._render_selected_charts", return_value=([], [])),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=True,
                max_workers=1,
                collect_kis_revision_snapshots=True,
                kis_revision_token_provider=lambda: FakeTokenState(),
                kis_revision_snapshot_collector=fake_collector,
            )

        self.assertEqual(len(top_df), 1)
        self.assertEqual(meta["kis_revision_raw_snapshot"]["status"], "blocked")
        self.assertEqual(meta["kis_revision_raw_snapshot"]["token_preflight"]["status"], "blocked")
        self.assertEqual(meta["kis_revision_raw_snapshot"]["error_type"], "RuntimeError")

    def test_run_daily_top5_update_honors_top_n(self) -> None:
        rows = [
            make_row("005930", "Samsung Electronics"),
            make_row("000660", "SK Hynix"),
            make_row("005380", "Hyundai Motor"),
            make_row("373220", "LG Energy Solution"),
            make_row("402340", "SK Square"),
            make_row("051910", "LG Chem"),
        ]

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code=row.code, name=row.name) for row in rows],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", side_effect=rows),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top5_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=False,
                max_workers=1,
                top_n=6,
            )

        self.assertEqual(len(top5_df), 6)
        self.assertEqual(meta["top_n"], 6)

    def test_run_daily_top5_update_does_not_force_market_cap_codes_by_default(self) -> None:
        rows = [
            make_row("005930", "Samsung Electronics", score=0.0),
            make_row("000001", "High Score", score=10.0),
        ]

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code=row.code, name=row.name) for row in rows],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", side_effect=rows),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=False,
                max_workers=1,
                top_n=1,
            )

        self.assertEqual(top_df["종목코드"].tolist(), ["000001"])
        self.assertFalse(meta["market_cap_override"])

    def test_run_daily_top5_update_can_prioritize_market_cap_codes_when_enabled(self) -> None:
        rows = [
            make_row("005930", "Samsung Electronics", score=0.0),
            make_row("000001", "High Score", score=10.0),
        ]

        with (
            patch(
                "stock_core.pipeline.daily_update._build_universe_entries",
                return_value=[UniverseEntry(code=row.code, name=row.name) for row in rows],
            ),
            patch("stock_core.pipeline.daily_update._process_universe_entry", side_effect=rows),
            patch("stock_core.pipeline.daily_update._export_outputs"),
        ):
            top_df, meta = run_daily_top5_update(
                pages=1,
                use_cache=True,
                refresh_universe=False,
                render_charts=False,
                max_workers=1,
                top_n=1,
                use_market_cap_override=True,
            )

        self.assertEqual(top_df["종목코드"].tolist(), ["005930"])
        self.assertTrue(meta["market_cap_override"])

    def test_run_daily_top5_update_if_due_skips_when_not_due(self) -> None:
        with (
            patch("stock_core.pipeline.daily_update.get_daily_top5_due_status") as mock_status,
            patch("stock_core.pipeline.daily_update.run_daily_top5_update") as mock_run,
        ):
            mock_status.return_value.is_due = False
            mock_status.return_value.due_at = None
            mock_status.return_value.last_successful_update_date = None
            mock_status.return_value.reason = "already done"

            top_df, meta = run_daily_top5_update_if_due(pages=1)

        self.assertIsNone(top_df)
        self.assertFalse(meta["is_due"])
        self.assertEqual(meta["reason"], "already done")
        mock_run.assert_not_called()

    def test_run_daily_top5_update_if_due_runs_when_due(self) -> None:
        expected_df = pd.DataFrame({"종목코드": ["005930"]})
        with (
            patch("stock_core.pipeline.daily_update.get_daily_top5_due_status") as mock_status,
            patch(
                "stock_core.pipeline.daily_update.run_daily_top5_update",
                return_value=(
                    expected_df,
                    {
                        "as_of": "2026-04-20",
                        "last_successful_update_date": "2026-04-20",
                    },
                ),
            ) as mock_run,
        ):
            mock_status.return_value.is_due = True
            mock_status.return_value.due_at = None
            mock_status.return_value.last_successful_update_date = pd.Timestamp("2026-04-17").date()
            mock_status.return_value.reason = "due"

            top_df, meta = run_daily_top5_update_if_due(pages=1, render_charts=False)

        self.assertIs(top_df, expected_df)
        self.assertTrue(meta["is_due"])
        self.assertEqual(meta["reason"], "due")
        self.assertEqual(meta["last_successful_update_date"], "2026-04-20")
        self.assertEqual(meta["due_last_successful_update_date"], "2026-04-17")
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
