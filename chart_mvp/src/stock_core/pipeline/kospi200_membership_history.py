"""Build local KOSPI200 membership-history CSVs for evidence data collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from stock_core.utils.local_env import load_local_env_for_project
from stock_core.utils.market_specs import KOREAN_EQUITY_SYMBOL_POLICY
from stock_core.utils.paths import DATA_DIR, PROJECT_ROOT


MEMBERSHIP_SCHEMA_VERSION = "v0_3_kospi200_membership_history_0_1"
MEMBERSHIP_BOUNDARY = (
    "KOSPI200 membership history for v0.3 evidence and ML data preparation only; "
    "not a production scanner universe, ranking input, trading signal, valuation "
    "input, or automatic production activation."
)
DEFAULT_INDEX_TICKER = "1028"
DEFAULT_OUTPUT_PATH = DATA_DIR / "kospi200_membership_history.csv"


@dataclass(frozen=True)
class MembershipBuildConfig:
    """Settings for constructing a local membership-history CSV."""

    start_date: date
    end_date: date
    index_ticker: str = DEFAULT_INDEX_TICKER
    frequency: str = "ME"
    allow_current_universe_fallback: bool = False
    current_universe_csv: Path = PROJECT_ROOT / "universe" / "kospi200_snapshot.csv"
    max_empty_snapshots_before_fallback: int = 3
    snapshot_backfill_days: int = 7
    min_observed_unique_tickers: int | None = None


@dataclass(frozen=True)
class SnapshotObservation:
    """One requested KOSPI200 membership observation and the source date used."""

    requested_date: date
    source_date: date
    constituents: dict[str, dict[str, str]]


def _as_date(value: object) -> date:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value}")
    return parsed.date()


def _snapshot_dates(start_date: date, end_date: date, frequency: str) -> list[date]:
    dates = [item.date() for item in pd.date_range(start=start_date, end=end_date, freq=frequency)]
    if end_date not in dates:
        dates.append(end_date)
    return sorted(set(dates))


def _record_from_value(value: object) -> dict[str, str] | None:
    if isinstance(value, pd.Series):
        raw: dict[str, Any] = value.to_dict()
    elif isinstance(value, dict):
        raw = value
    else:
        ticker = KOREAN_EQUITY_SYMBOL_POLICY.normalize(value)
        if not KOREAN_EQUITY_SYMBOL_POLICY.is_valid(ticker):
            return None
        return {
            "ticker": ticker,
            "company_name": ticker,
            "isin": "unknown",
            "security_id": f"krx:{ticker}",
        }

    ticker_value = (
        raw.get("ticker")
        or raw.get("code")
        or raw.get("symbol")
        or raw.get("ISU_SRT_CD")
        or raw.get("단축코드")
    )
    ticker = KOREAN_EQUITY_SYMBOL_POLICY.normalize(ticker_value)
    if not KOREAN_EQUITY_SYMBOL_POLICY.is_valid(ticker):
        return None

    company_name = str(
        raw.get("company_name")
        or raw.get("name")
        or raw.get("security_name")
        or raw.get("ISU_ABBRV")
        or raw.get("종목명")
        or ticker
    ).strip()
    isin = str(raw.get("isin") or raw.get("ISIN_CODE") or raw.get("표준코드") or "unknown").strip() or "unknown"
    security_id = str(raw.get("security_id") or "").strip()
    if not security_id:
        security_id = f"krx_isin:{isin}" if isin != "unknown" else f"krx:{ticker}"
    return {
        "ticker": ticker,
        "company_name": company_name or ticker,
        "isin": isin,
        "security_id": security_id,
    }


def _normalize_constituent_records(values: Iterable[object] | pd.DataFrame) -> dict[str, dict[str, str]]:
    iterable: Iterable[object]
    if values is None:
        return {}
    if isinstance(values, pd.DataFrame):
        iterable = values.to_dict(orient="records")
    else:
        iterable = values
    records: dict[str, dict[str, str]] = {}
    for value in iterable:
        record = _record_from_value(value)
        if record is not None:
            records[record["ticker"]] = record
    return dict(sorted(records.items()))


def _normalize_tickers(values: Iterable[object] | pd.DataFrame) -> list[str]:
    return sorted(_normalize_constituent_records(values))


def _load_pykrx_login_env(
    environ: dict[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    env = os.environ if environ is None else environ
    load_local_env_for_project(project_root, env)
    if env.get("KRX_PASSWORD") and not env.get("KRX_PW"):
        env["KRX_PW"] = env["KRX_PASSWORD"]
    if env.get("KRX_PW") and not env.get("KRX_PASSWORD"):
        env["KRX_PASSWORD"] = env["KRX_PW"]


def _stable_hash(parts: Iterable[object], *, length: int = 16) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]


def _membership_row(
    *,
    security_id: str,
    isin: str,
    ticker: str,
    company_name: str,
    effective_start: date,
    effective_end: str,
    listing_status: str,
    change_type: str,
    index_ticker: str,
    frequency: str,
    source_observed_at: str,
    source_snapshot_start: date,
    source_snapshot_end: date,
    source_ref: str | None = None,
    observation_policy: str | None = None,
) -> dict[str, str]:
    row_key = [
        "KOSPI200",
        security_id,
        ticker,
        effective_start.isoformat(),
        effective_end or "active",
        change_type,
        source_snapshot_start.isoformat(),
        source_snapshot_end.isoformat(),
    ]
    return {
        "schema_version": MEMBERSHIP_SCHEMA_VERSION,
        "collection_boundary": MEMBERSHIP_BOUNDARY,
        "membership_id": "kospi200_membership:" + _stable_hash(row_key),
        "index_code": "KOSPI200",
        "security_id": security_id,
        "isin": isin,
        "ticker": ticker,
        "company_name": company_name,
        "effective_start": effective_start.isoformat(),
        "effective_end": effective_end,
        "change_type": change_type,
        "listing_status": listing_status,
        "source_ref": source_ref
        or f"pykrx.get_index_portfolio_deposit_file({index_ticker}, snapshot_date)",
        "observation_policy": observation_policy or f"{frequency}_snapshot_observed_interval_with_backfill",
        "source_observed_at": source_observed_at,
        "source_observed_at_utc": source_observed_at,
        "source_snapshot_start": source_snapshot_start.isoformat(),
        "source_snapshot_end": source_snapshot_end.isoformat(),
        "as_of_policy": f"{frequency}_source_snapshots_point_in_time",
        "raw_record_hash": _stable_hash(row_key, length=24),
    }


def pykrx_index_portfolio_fetcher(index_ticker: str, snapshot_date: date) -> list[str]:
    """Fetch a KOSPI200 constituent snapshot through pykrx when KRX allows it."""

    _load_pykrx_login_env()

    from pykrx import stock

    result = stock.get_index_portfolio_deposit_file(index_ticker, snapshot_date.strftime("%Y%m%d"))
    if isinstance(result, pd.DataFrame):
        if "ISU_SRT_CD" in result.columns:
            return _normalize_tickers(result["ISU_SRT_CD"])
        if not result.empty:
            return _normalize_tickers(result.iloc[:, 0])
        return []
    return _normalize_tickers(result)


def load_current_universe_proxy(path: str | Path, *, start_date: date) -> pd.DataFrame:
    """Create a fallback membership frame from the packaged current KOSPI200 snapshot."""

    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {"code", "name"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"current universe CSV missing required columns: {missing}")

    rows = []
    source_observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for row in frame.to_dict(orient="records"):
        ticker = KOREAN_EQUITY_SYMBOL_POLICY.normalize(row["code"])
        rows.append(
            _membership_row(
                security_id=f"krx:{ticker}",
                isin="unknown",
                ticker=ticker,
                company_name=str(row["name"]).strip() or ticker,
                effective_start=start_date,
                effective_end="",
                listing_status="listed_current_snapshot_proxy",
                change_type="unknown",
                index_ticker=DEFAULT_INDEX_TICKER,
                frequency="current_snapshot_proxy",
                source_observed_at=source_observed_at,
                source_snapshot_start=start_date,
                source_snapshot_end=start_date,
                source_ref=str(path),
                observation_policy="current_universe_proxy_when_historical_krx_snapshots_unavailable",
            )
        )
    return pd.DataFrame(rows).sort_values(["ticker"]).reset_index(drop=True)


def _fetch_snapshot_observation(
    *,
    index_ticker: str,
    requested_date: date,
    snapshot_backfill_days: int,
    snapshot_fetcher: Callable[[str, date], Iterable[object] | pd.DataFrame],
) -> SnapshotObservation:
    if snapshot_backfill_days < 0:
        raise ValueError("snapshot_backfill_days must be greater than or equal to 0")
    for offset in range(snapshot_backfill_days + 1):
        source_date = requested_date - timedelta(days=offset)
        constituents = _normalize_constituent_records(snapshot_fetcher(index_ticker, source_date))
        if constituents:
            return SnapshotObservation(
                requested_date=requested_date,
                source_date=source_date,
                constituents=constituents,
            )
    return SnapshotObservation(requested_date=requested_date, source_date=requested_date, constituents={})


def _validate_observed_ticker_count(all_tickers: list[str], *, minimum: int | None) -> None:
    if minimum is None:
        return
    if minimum < 1:
        raise ValueError("min_observed_unique_tickers must be greater than or equal to 1")
    if len(all_tickers) < minimum:
        raise RuntimeError(
            "observed KOSPI200 history has fewer unique tickers than required: "
            f"{len(all_tickers)} < {minimum}"
        )


def build_membership_history(
    *,
    config: MembershipBuildConfig,
    snapshot_fetcher: Callable[[str, date], list[str]] = pykrx_index_portfolio_fetcher,
) -> pd.DataFrame:
    """Build membership intervals from observed KOSPI200 snapshots."""

    if config.start_date > config.end_date:
        raise ValueError("start_date must be on or before end_date")
    if config.max_empty_snapshots_before_fallback < 1:
        raise ValueError("max_empty_snapshots_before_fallback must be greater than or equal to 1")

    observed: dict[date, SnapshotObservation] = {}
    empty_count = 0
    for snapshot_date in _snapshot_dates(config.start_date, config.end_date, config.frequency):
        observation = _fetch_snapshot_observation(
            index_ticker=config.index_ticker,
            requested_date=snapshot_date,
            snapshot_backfill_days=config.snapshot_backfill_days,
            snapshot_fetcher=snapshot_fetcher,
        )
        if not observation.constituents:
            empty_count += 1
            continue
        observed[observation.source_date] = observation

    if not observed:
        if config.min_observed_unique_tickers is not None:
            raise RuntimeError("no observed KOSPI200 snapshots were collected")
        if config.allow_current_universe_fallback and empty_count >= config.max_empty_snapshots_before_fallback:
            return load_current_universe_proxy(config.current_universe_csv, start_date=config.start_date)
        raise RuntimeError("no KOSPI200 membership snapshots were collected")

    rows = []
    source_observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshot_dates = sorted(observed)
    all_tickers = sorted({ticker for observation in observed.values() for ticker in observation.constituents})
    _validate_observed_ticker_count(all_tickers, minimum=config.min_observed_unique_tickers)
    for ticker in all_tickers:
        interval_start: date | None = None
        interval_change_type = "unknown"
        interval_meta: dict[str, str] | None = None
        latest_meta: dict[str, str] | None = None
        previous_snapshot_date: date | None = None
        for snapshot_date in snapshot_dates:
            observation = observed[snapshot_date]
            is_member = ticker in observation.constituents
            if is_member and interval_start is None:
                interval_start = snapshot_date
                interval_change_type = "initial_snapshot" if snapshot_date == snapshot_dates[0] else "added"
                interval_meta = observation.constituents[ticker]
                latest_meta = interval_meta
            elif is_member:
                latest_meta = observation.constituents[ticker]
            elif not is_member and interval_start is not None:
                meta = latest_meta or interval_meta or {
                    "ticker": ticker,
                    "company_name": ticker,
                    "isin": "unknown",
                    "security_id": f"krx:{ticker}",
                }
                rows.append(
                    _membership_row(
                        security_id=meta["security_id"],
                        isin=meta["isin"],
                        ticker=ticker,
                        company_name=meta["company_name"],
                        effective_start=interval_start,
                        effective_end=(previous_snapshot_date or snapshot_date).isoformat(),
                        listing_status="removed_or_unlisted",
                        change_type="removed",
                        index_ticker=config.index_ticker,
                        frequency=config.frequency,
                        source_observed_at=source_observed_at,
                        source_snapshot_start=interval_start,
                        source_snapshot_end=previous_snapshot_date or snapshot_date,
                    )
                )
                interval_start = None
                interval_meta = None
                latest_meta = None
            previous_snapshot_date = snapshot_date

        if interval_start is not None:
            meta = latest_meta or interval_meta or {
                "ticker": ticker,
                "company_name": ticker,
                "isin": "unknown",
                "security_id": f"krx:{ticker}",
            }
            rows.append(
                _membership_row(
                    security_id=meta["security_id"],
                    isin=meta["isin"],
                    ticker=ticker,
                    company_name=meta["company_name"],
                    effective_start=interval_start,
                    effective_end="",
                    listing_status="listed",
                    change_type=interval_change_type,
                    index_ticker=config.index_ticker,
                    frequency=config.frequency,
                    source_observed_at=source_observed_at,
                    source_snapshot_start=interval_start,
                    source_snapshot_end=snapshot_dates[-1],
                )
            )
    return pd.DataFrame(rows).sort_values(["ticker", "effective_start"]).reset_index(drop=True)


def write_membership_history(frame: pd.DataFrame, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-krx-login", action="store_true", help="Check local KRX login materials and exit.")
    parser.add_argument(
        "--run-krx-login-session",
        action="store_true",
        help="Run visible KRX login automation and persist a local session state.",
    )
    parser.add_argument("--check-krx-api-key", action="store_true", help="Check local KRX Open API key material and exit.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--index-ticker", default=DEFAULT_INDEX_TICKER)
    parser.add_argument("--frequency", default="ME")
    parser.add_argument("--allow-current-universe-fallback", action="store_true")
    parser.add_argument("--current-universe-csv", type=Path, default=PROJECT_ROOT / "universe" / "kospi200_snapshot.csv")
    parser.add_argument("--max-empty-snapshots-before-fallback", type=int, default=3)
    parser.add_argument(
        "--snapshot-backfill-days",
        type=int,
        default=7,
        help="Try this many prior calendar days when a scheduled KOSPI200 snapshot date returns empty.",
    )
    parser.add_argument(
        "--min-observed-unique-tickers",
        type=int,
        help="Fail unless observed historical snapshots contain at least this many unique tickers.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check_krx_api_key:
        from stock_core.providers.krx_login import check_krx_api_key_readiness, load_krx_api_key_config

        readiness = check_krx_api_key_readiness(load_krx_api_key_config())
        print(json.dumps(readiness.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if readiness.status == "ready" else 2

    if args.check_krx_login:
        from stock_core.providers.krx_login import check_krx_login_readiness, load_krx_login_config

        readiness = check_krx_login_readiness(load_krx_login_config())
        print(json.dumps(readiness.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if readiness.status == "ready" else 2

    if args.run_krx_login_session:
        from stock_core.providers.krx_login import run_krx_login_session

        result = run_krx_login_session()
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.status in {"ready", "manual_required"} else 2

    if not args.start_date:
        raise ValueError("--start-date is required unless a KRX readiness/login mode is used")

    frame = build_membership_history(
        config=MembershipBuildConfig(
            start_date=_as_date(args.start_date),
            end_date=_as_date(args.end_date),
            index_ticker=args.index_ticker,
            frequency=args.frequency,
            allow_current_universe_fallback=args.allow_current_universe_fallback,
            current_universe_csv=args.current_universe_csv,
            max_empty_snapshots_before_fallback=args.max_empty_snapshots_before_fallback,
            snapshot_backfill_days=args.snapshot_backfill_days,
            min_observed_unique_tickers=args.min_observed_unique_tickers,
        )
    )
    output_path = write_membership_history(frame, args.output)
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "rows": int(len(frame)),
                "unique_tickers": int(frame["ticker"].nunique()),
                "observation_policy": sorted(frame["observation_policy"].unique().tolist()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
