"""Collect Naver Finance data for historical KOSPI200 constituents."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from stock_core.indicators.technical import add_indicators
from stock_core.utils.market_specs import KOREAN_EQUITY_SYMBOL_POLICY, NAVER_PRICE_PROVIDER_SPEC
from stock_core.utils.normalization import clean_stock_data
from stock_core.utils.paths import DATA_DIR, PROJECT_ROOT


HISTORICAL_COLLECTION_SCHEMA_VERSION = "v0_3_kospi200_historical_naver_collection_0_1"
COLLECTION_BOUNDARY = (
    "KOSPI200 historical constituent data collection for v0.3 evidence and "
    "ML review only; not a production scanner universe, ranking input, trading "
    "signal, valuation input, or automatic production activation."
)
DEFAULT_OUTPUT_DIR = DATA_DIR / "historical_kospi200"
DEFAULT_LOOKBACK_YEARS = 10
DEFAULT_PRICE_PAGES = 260
DELISTED_STATUSES = {"delisted", "merged", "suspended"}
EXECUTION_ORDERS = {"forward", "reverse"}


@dataclass(frozen=True)
class HistoricalCollectionConfig:
    """Runtime settings for historical KOSPI200 Naver collection."""

    decision_date: date
    lookback_years: int = DEFAULT_LOOKBACK_YEARS
    pages: int = DEFAULT_PRICE_PAGES
    output_dir: Path = DEFAULT_OUTPUT_DIR
    refresh_financials: bool = True
    dry_run: bool = False
    offset: int = 0
    limit: int | None = None
    shard_count: int = 1
    shard_index: int = 0
    execution_order: str = "forward"
    resume_existing: bool = False
    resume_min_price_rows: int = 1
    status_file_name: str = "collection_status.csv"
    manifest_file_name: str = "collection_manifest.json"
    price_sleep_seconds: float = NAVER_PRICE_PROVIDER_SPEC.request_sleep_seconds
    require_krx_api_key: bool = False


def _as_date(value: object, *, fallback: date | None = None) -> date | None:
    if value is None or value == "":
        return fallback
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return fallback
    return parsed.date()


def _normalize_membership_columns(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "code": "ticker",
        "symbol": "ticker",
        "name": "company_name",
        "security_name": "company_name",
        "start": "effective_start",
        "end": "effective_end",
        "status": "listing_status",
    }
    normalized = frame.rename(columns={column: aliases.get(column, column) for column in frame.columns}).copy()
    required = {"ticker", "company_name", "effective_start"}
    missing = sorted(required - set(normalized.columns))
    if missing:
        raise ValueError(f"membership history missing required columns: {missing}")
    normalized["ticker"] = normalized["ticker"].map(KOREAN_EQUITY_SYMBOL_POLICY.normalize)
    normalized["company_name"] = normalized["company_name"].astype(str).str.strip()
    normalized["effective_start"] = pd.to_datetime(normalized["effective_start"], errors="coerce")
    if "effective_end" not in normalized.columns:
        normalized["effective_end"] = pd.NaT
    else:
        normalized["effective_end"] = pd.to_datetime(normalized["effective_end"], errors="coerce")
    if "index_code" not in normalized.columns:
        normalized["index_code"] = "KOSPI200"
    if "security_id" not in normalized.columns:
        normalized["security_id"] = "krx:" + normalized["ticker"].astype(str)
    if "listing_status" not in normalized.columns:
        normalized["listing_status"] = "unknown"
    normalized["listing_status"] = normalized["listing_status"].fillna("unknown").astype(str).str.strip().str.lower()
    invalid_dates = normalized["effective_start"].isna()
    if invalid_dates.any():
        raise ValueError("membership history contains invalid effective_start values")
    return normalized


def load_membership_history(path: str | Path) -> pd.DataFrame:
    """Load historical KOSPI200 membership records from a local CSV."""

    return _normalize_membership_columns(pd.read_csv(path, dtype=str).fillna(""))


def filter_membership_for_lookback(
    membership: pd.DataFrame,
    *,
    decision_date: date,
    lookback_years: int = DEFAULT_LOOKBACK_YEARS,
) -> pd.DataFrame:
    """Return membership intervals overlapping the decision-date lookback window."""

    if lookback_years < 1:
        raise ValueError("lookback_years must be greater than or equal to 1")
    normalized = _normalize_membership_columns(membership)
    window_end = pd.Timestamp(decision_date)
    window_start = window_end - pd.DateOffset(years=lookback_years)
    effective_end = normalized["effective_end"].fillna(window_end)
    overlaps = (normalized["effective_start"] <= window_end) & (effective_end >= window_start)
    scoped = normalized.loc[overlaps & (normalized["index_code"] == "KOSPI200")].copy()
    return scoped.sort_values(["ticker", "effective_start"]).reset_index(drop=True)


def build_security_collection_plan(membership: pd.DataFrame, *, decision_date: date) -> pd.DataFrame:
    """Build one collection row per security from scoped membership intervals."""

    rows: list[dict[str, Any]] = []
    for (security_id, ticker), group in membership.groupby(["security_id", "ticker"], sort=True, dropna=False):
        latest = group.sort_values("effective_start").iloc[-1]
        effective_end = _as_date(latest.get("effective_end"))
        listing_status = str(latest.get("listing_status") or "unknown").lower()
        if listing_status == "unknown" and effective_end is not None and effective_end < decision_date:
            listing_status = "removed_or_unlisted"
        rows.append(
            {
                "schema_version": HISTORICAL_COLLECTION_SCHEMA_VERSION,
                "collection_boundary": COLLECTION_BOUNDARY,
                "security_id": str(security_id),
                "ticker": str(ticker),
                "company_name": str(latest.get("company_name") or ticker),
                "membership_interval_count": int(len(group)),
                "first_membership_start": group["effective_start"].min().date().isoformat(),
                "last_membership_end": (
                    group["effective_end"].dropna().max().date().isoformat()
                    if group["effective_end"].notna().any()
                    else ""
                ),
                "listing_status": listing_status,
                "delisted_or_inactive": listing_status in DELISTED_STATUSES or listing_status == "removed_or_unlisted",
                "source_ref": str(latest.get("source_ref") or "membership_history_csv"),
            }
        )
    return pd.DataFrame(rows).sort_values(["ticker", "security_id"]).reset_index(drop=True)


def build_execution_plan(plan: pd.DataFrame, *, config: HistoricalCollectionConfig) -> pd.DataFrame:
    """Apply offset, limit, shard, and order controls for one collection worker."""

    if config.offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    if config.limit is not None and config.limit < 1:
        raise ValueError("limit must be greater than or equal to 1")
    if config.shard_count < 1:
        raise ValueError("shard_count must be greater than or equal to 1")
    if config.shard_index < 0 or config.shard_index >= config.shard_count:
        raise ValueError("shard_index must be greater than or equal to 0 and less than shard_count")
    if config.execution_order not in EXECUTION_ORDERS:
        raise ValueError(f"execution_order must be one of: {sorted(EXECUTION_ORDERS)}")

    execution_plan = plan.iloc[config.offset :].reset_index(drop=True)
    if config.limit is not None:
        execution_plan = execution_plan.head(config.limit).reset_index(drop=True)
    if config.shard_count > 1:
        total = len(execution_plan)
        start = (total * config.shard_index) // config.shard_count
        end = (total * (config.shard_index + 1)) // config.shard_count
        execution_plan = execution_plan.iloc[start:end].reset_index(drop=True)
    if config.execution_order == "reverse":
        execution_plan = execution_plan.iloc[::-1].reset_index(drop=True)
    return execution_plan


def _write_frame(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _count_existing_csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except UnicodeError:
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)


def _existing_price_cache_is_usable(path: Path, *, min_rows: int) -> tuple[bool, int]:
    if not path.exists() or path.stat().st_size <= 0:
        return False, 0
    row_count = _count_existing_csv_rows(path)
    return row_count >= min_rows, row_count


def _collect_price(
    ticker: str,
    *,
    pages: int,
    sleep_seconds: float,
    price_fetcher: Callable[..., pd.DataFrame],
) -> pd.DataFrame:
    raw = price_fetcher(
        code=ticker,
        pages=pages,
        sleep_seconds=sleep_seconds,
    )
    return add_indicators(clean_stock_data(raw))


def collect_historical_kospi200_naver_data(
    membership: pd.DataFrame,
    *,
    config: HistoricalCollectionConfig,
    price_fetcher: Callable[..., pd.DataFrame] | None = None,
    financial_fetcher: Callable[..., pd.DataFrame] | None = None,
) -> dict[str, Path | int]:
    """Collect available Naver price and financial data for scoped securities."""

    if price_fetcher is None or financial_fetcher is None:
        from stock_core.providers.naver_finance import crawl_financial_statements, crawl_stock_data

        price_fetcher = crawl_stock_data if price_fetcher is None else price_fetcher
        financial_fetcher = crawl_financial_statements if financial_fetcher is None else financial_fetcher

    scoped_membership = filter_membership_for_lookback(
        membership,
        decision_date=config.decision_date,
        lookback_years=config.lookback_years,
    )
    plan = build_security_collection_plan(scoped_membership, decision_date=config.decision_date)
    execution_plan = build_execution_plan(plan, config=config)
    output_dir = config.output_dir
    status_path = output_dir / config.status_file_name
    manifest_path = output_dir / config.manifest_file_name
    status_rows: list[dict[str, Any]] = []
    delisted_rows = plan[plan["delisted_or_inactive"]].copy()

    if not config.dry_run:
        _write_frame(scoped_membership, output_dir / "membership_history_scoped.csv")
        _write_frame(plan, output_dir / "collection_plan.csv")
        _write_frame(delisted_rows, output_dir / "delisted_or_inactive_securities.csv")

    for row in execution_plan.to_dict(orient="records"):
        ticker = str(row["ticker"])
        price_path = output_dir / "prices" / f"{ticker}_daily_prices.csv"
        financial_path = output_dir / "financials" / f"{ticker}_financial_statements.csv"
        status = {
            "schema_version": HISTORICAL_COLLECTION_SCHEMA_VERSION,
            "security_id": row["security_id"],
            "ticker": ticker,
            "company_name": row["company_name"],
            "listing_status": row["listing_status"],
            "delisted_or_inactive": row["delisted_or_inactive"],
            "price_status": "not_run" if config.dry_run else "pending",
            "financial_status": "not_run" if config.dry_run else "pending",
            "price_path": "",
            "financial_path": "",
            "error": "",
            "existing_price_rows": "",
        }
        if not config.dry_run:
            try:
                existing_price_usable, existing_price_rows = _existing_price_cache_is_usable(
                    price_path,
                    min_rows=config.resume_min_price_rows,
                )
                status["existing_price_rows"] = str(existing_price_rows)
                if config.resume_existing and existing_price_usable:
                    status["price_path"] = str(price_path)
                    status["price_status"] = "skipped_existing"
                else:
                    price_df = _collect_price(
                        ticker,
                        pages=config.pages,
                        sleep_seconds=config.price_sleep_seconds,
                        price_fetcher=price_fetcher,
                    )
                    status["price_path"] = str(_write_frame(price_df, price_path))
                    status["price_status"] = "collected"
            except Exception as exc:
                status["price_status"] = "delisted_or_unavailable" if row["delisted_or_inactive"] else "failed"
                status["error"] = str(exc)

            if config.refresh_financials:
                try:
                    if config.resume_existing and financial_path.exists() and financial_path.stat().st_size > 0:
                        status["financial_path"] = str(financial_path)
                        status["financial_status"] = "skipped_existing"
                    else:
                        financial_df = financial_fetcher(code=ticker)
                        status["financial_path"] = str(_write_frame(financial_df, financial_path))
                        status["financial_status"] = "collected"
                except Exception as exc:
                    status["financial_status"] = (
                        "delisted_or_unavailable" if row["delisted_or_inactive"] else "failed"
                    )
                    status["error"] = "; ".join(part for part in [status["error"], str(exc)] if part)
        status_rows.append(status)
        if not config.dry_run:
            _write_frame(pd.DataFrame(status_rows), status_path)

    status_frame = pd.DataFrame(status_rows)
    manifest = {
        "schema_version": HISTORICAL_COLLECTION_SCHEMA_VERSION,
        "collection_boundary": COLLECTION_BOUNDARY,
        "decision_date": config.decision_date.isoformat(),
        "lookback_years": config.lookback_years,
        "pages": config.pages,
        "dry_run": config.dry_run,
        "offset": config.offset,
        "limit": config.limit,
        "shard_count": config.shard_count,
        "shard_index": config.shard_index,
        "execution_order": config.execution_order,
        "resume_min_price_rows": config.resume_min_price_rows,
        "scoped_membership_rows": int(len(scoped_membership)),
        "security_count": int(len(plan)),
        "execution_security_count": int(len(execution_plan)),
        "delisted_or_inactive_count": int(len(delisted_rows)),
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "no_feedback_check": "historical_collection_must_not_change_runtime_universe_scores_rankings_reports_or_trading",
    }
    if not config.dry_run:
        _write_frame(status_frame, status_path)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return {
        "scoped_membership_rows": int(len(scoped_membership)),
        "security_count": int(len(plan)),
        "delisted_or_inactive_count": int(len(delisted_rows)),
        "status_path": status_path,
        "manifest_path": manifest_path,
    }


def check_required_krx_api_key(
    *,
    env: dict[str, str] | None = None,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, object]:
    """Return secret-safe KRX API key preflight status for automated runs."""

    from stock_core.providers.krx_login import check_krx_api_key_readiness, load_krx_api_key_config

    readiness = check_krx_api_key_readiness(load_krx_api_key_config(env=env, project_root=project_root))
    return readiness.to_dict()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--membership-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--decision-date", default=date.today().isoformat())
    parser.add_argument("--lookback-years", type=int, default=DEFAULT_LOOKBACK_YEARS)
    parser.add_argument("--pages", type=int, default=DEFAULT_PRICE_PAGES)
    parser.add_argument("--no-financials", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Split the selected execution plan into this many contiguous shards.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Zero-based shard index to run when --shard-count is greater than 1.",
    )
    parser.add_argument(
        "--execution-order",
        choices=sorted(EXECUTION_ORDERS),
        default="forward",
        help="Process the selected execution plan forward or reverse.",
    )
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument(
        "--resume-min-price-rows",
        type=int,
        default=1,
        help="Minimum CSV data rows required before --resume-existing treats a price file as complete.",
    )
    parser.add_argument("--status-file-name", default="collection_status.csv")
    parser.add_argument("--manifest-file-name", default="collection_manifest.json")
    parser.add_argument("--price-sleep-seconds", type=float, default=NAVER_PRICE_PROVIDER_SPEC.request_sleep_seconds)
    parser.add_argument(
        "--require-krx-api-key",
        action="store_true",
        help="Require a secret-safe ready KRX API key preflight before running the Naver batch.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    krx_api_key_preflight: dict[str, object] | None = None
    if args.require_krx_api_key:
        krx_api_key_preflight = check_required_krx_api_key()
        if krx_api_key_preflight.get("status") != "ready":
            print(
                json.dumps(
                    {
                        "status": "blocked",
                        "blocked_reason": "krx_api_key_preflight_failed",
                        "krx_api_key_preflight": krx_api_key_preflight,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 2

    membership = load_membership_history(args.membership_csv)
    decision_date = _as_date(args.decision_date)
    if decision_date is None:
        raise ValueError(f"invalid decision date: {args.decision_date}")
    if args.resume_min_price_rows < 1:
        raise ValueError("resume_min_price_rows must be greater than or equal to 1")
    result = collect_historical_kospi200_naver_data(
        membership,
        config=HistoricalCollectionConfig(
            decision_date=decision_date,
            lookback_years=args.lookback_years,
            pages=args.pages,
            output_dir=args.output_dir,
            refresh_financials=not args.no_financials,
            dry_run=args.dry_run,
            offset=args.offset,
            limit=args.limit,
            shard_count=args.shard_count,
            shard_index=args.shard_index,
            execution_order=args.execution_order,
            resume_existing=args.resume_existing,
            resume_min_price_rows=args.resume_min_price_rows,
            status_file_name=args.status_file_name,
            manifest_file_name=args.manifest_file_name,
            price_sleep_seconds=args.price_sleep_seconds,
            require_krx_api_key=args.require_krx_api_key,
        ),
    )
    if krx_api_key_preflight is not None:
        result["krx_api_key_status"] = str(krx_api_key_preflight.get("status"))
        result["krx_api_key_selected_env_var"] = str(
            krx_api_key_preflight.get("config_summary", {}).get("selected_env_var")
        )
    print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
