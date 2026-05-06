from __future__ import annotations

from datetime import date
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.pipeline.kospi200_membership_history import (  # noqa: E402
    MembershipBuildConfig,
    build_membership_history,
    load_current_universe_proxy,
    _load_pykrx_login_env,
)


class Kospi200MembershipHistoryTests(unittest.TestCase):
    def test_builds_intervals_from_snapshots(self) -> None:
        snapshots = {
            date(2026, 1, 31): ["005930", "000660"],
            date(2026, 2, 28): ["005930", "035420"],
        }

        def fetcher(index_ticker: str, snapshot_date: date) -> list[str]:
            self.assertEqual(index_ticker, "1028")
            return snapshots.get(snapshot_date, [])

        frame = build_membership_history(
            config=MembershipBuildConfig(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 2, 28),
                frequency="ME",
            ),
            snapshot_fetcher=fetcher,
        )

        samsung = frame[frame["ticker"] == "005930"].iloc[0]
        removed = frame[frame["ticker"] == "000660"].iloc[0]
        self.assertEqual(samsung["effective_end"], "")
        self.assertEqual(removed["listing_status"], "removed_or_unlisted")

    def test_falls_back_to_current_universe_when_snapshots_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kospi200_snapshot.csv"
            pd.DataFrame([{"code": "5930", "name": "Samsung"}]).to_csv(path, index=False)

            frame = build_membership_history(
                config=MembershipBuildConfig(
                    start_date=date(2016, 5, 6),
                    end_date=date(2026, 5, 6),
                    frequency="ME",
                    allow_current_universe_fallback=True,
                    current_universe_csv=path,
                    max_empty_snapshots_before_fallback=1,
                ),
                snapshot_fetcher=lambda index_ticker, snapshot_date: [],
            )

            self.assertEqual(frame.iloc[0]["ticker"], "005930")
            self.assertIn("current_universe_proxy", frame.iloc[0]["observation_policy"])

    def test_current_universe_fallback_waits_until_all_snapshots_are_tried(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kospi200_snapshot.csv"
            pd.DataFrame([{"code": "5930", "name": "Samsung"}]).to_csv(path, index=False)
            calls: list[date] = []
            snapshots = {
                date(2026, 3, 31): ["005930", "000660", "035420"],
            }

            def fetcher(index_ticker: str, snapshot_date: date) -> list[str]:
                calls.append(snapshot_date)
                return snapshots.get(snapshot_date, [])

            frame = build_membership_history(
                config=MembershipBuildConfig(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 3, 31),
                    frequency="ME",
                    allow_current_universe_fallback=True,
                    current_universe_csv=path,
                    max_empty_snapshots_before_fallback=1,
                    snapshot_backfill_days=0,
                ),
                snapshot_fetcher=fetcher,
            )

            self.assertGreaterEqual(len(calls), 3)
            self.assertEqual(set(frame["ticker"]), {"005930", "000660", "035420"})
            self.assertNotIn("current_universe_proxy", set(frame["observation_policy"]))

    def test_uses_prior_source_date_when_scheduled_snapshot_is_empty(self) -> None:
        snapshots = {
            date(2026, 3, 29): [
                {"ticker": "005930", "company_name": "Samsung", "isin": "KR7005930003"},
            ],
        }

        frame = build_membership_history(
            config=MembershipBuildConfig(
                start_date=date(2026, 3, 31),
                end_date=date(2026, 3, 31),
                frequency="ME",
                snapshot_backfill_days=3,
            ),
            snapshot_fetcher=lambda index_ticker, snapshot_date: snapshots.get(snapshot_date, []),
        )

        row = frame.iloc[0]
        self.assertEqual(row["ticker"], "005930")
        self.assertEqual(row["company_name"], "Samsung")
        self.assertEqual(row["isin"], "KR7005930003")
        self.assertEqual(row["effective_start"], "2026-03-29")
        self.assertEqual(row["source_snapshot_start"], "2026-03-29")

    def test_min_observed_unique_tickers_blocks_current_snapshot_sized_history(self) -> None:
        snapshots = {
            date(2026, 1, 31): ["005930", "000660"],
            date(2026, 2, 28): ["005930", "000660"],
        }

        with self.assertRaisesRegex(RuntimeError, "fewer unique tickers"):
            build_membership_history(
                config=MembershipBuildConfig(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 2, 28),
                    frequency="ME",
                    snapshot_backfill_days=0,
                    min_observed_unique_tickers=3,
                ),
                snapshot_fetcher=lambda index_ticker, snapshot_date: snapshots.get(snapshot_date, []),
            )

    def test_pykrx_login_env_adds_expected_password_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            project_root.mkdir(parents=True)
            env = {"KRX_PASSWORD": "secret"}

            _load_pykrx_login_env(env, project_root=project_root)

            self.assertEqual(env["KRX_PW"], "secret")

    def test_reentry_creates_separate_membership_intervals(self) -> None:
        snapshots = {
            date(2026, 1, 31): ["005930", "000660"],
            date(2026, 2, 28): ["000660"],
            date(2026, 3, 31): ["005930", "000660"],
        }

        frame = build_membership_history(
            config=MembershipBuildConfig(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                frequency="ME",
            ),
            snapshot_fetcher=lambda index_ticker, snapshot_date: snapshots.get(snapshot_date, []),
        )

        samsung = frame[frame["ticker"] == "005930"].reset_index(drop=True)
        self.assertEqual(len(samsung), 2)
        self.assertEqual(samsung.iloc[0]["effective_start"], "2026-01-31")
        self.assertEqual(samsung.iloc[0]["effective_end"], "2026-01-31")
        self.assertEqual(samsung.iloc[0]["listing_status"], "removed_or_unlisted")
        self.assertEqual(samsung.iloc[1]["effective_start"], "2026-03-31")
        self.assertEqual(samsung.iloc[1]["effective_end"], "")
        self.assertEqual(samsung.iloc[1]["listing_status"], "listed")

    def test_current_universe_proxy_requires_code_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.csv"
            pd.DataFrame([{"code": "005930"}]).to_csv(path, index=False)

            with self.assertRaises(ValueError):
                load_current_universe_proxy(path, start_date=date(2016, 5, 6))


if __name__ == "__main__":
    unittest.main()
