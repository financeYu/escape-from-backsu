"""One-click daily update pipeline using the modular stock_core interfaces."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Callable, Iterable, Optional

import pandas as pd

from stock_core.cache.csv_cache import DEFAULT_PRICE_CACHE_POLICY, PriceCachePolicy
from stock_core.indicators.technicals import add_indicators
from stock_core.providers.kospi200_universe_provider import UniverseEntry, get_universe_constituents
from stock_core.providers.naver_price_provider import get_price_df
from stock_core.ranking.scorer import LEGACY_PLACEHOLDER_SCORE_NOTICE, score_stock
from stock_core.ranking.selector import select_top_stocks
from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN, INDICATOR_COLUMNS, PRICE_COLUMNS, VOLUME_COLUMN
from stock_core.utils.daily_update_schedule import DailyUpdateDueStatus, get_daily_update_due_status
from stock_core.utils.logging_utils import get_logger
from stock_core.utils.market_specs import KOSPI200_UNIVERSE_SPEC, NAVER_PRICE_PROVIDER_SPEC, PriceProviderSpec, UniverseSpec
from stock_core.utils.paths import DATA_DIR, OUTPUTS_CHARTS_DIR, OUTPUTS_DIR, RESULTS_DIR


logger = get_logger(__name__)
MIN_CHART_PAGES = 7
CHART_WARMUP_PAGES = 3
KOSPI200_MARKET_CAP_LEADER_CODES = (
    "005930",
    "000660",
    "005380",
    "373220",
    "402340",
)
MARKET_CAP_OVERRIDE_MESSAGE = (
    "시가총액 상위 고정 종목 우선 선택 옵션이 활성화되었습니다."
)
DEFAULT_BATCH_WORKERS = 8
DEFAULT_TOP_N = 5
LATEST_TOP_CSV_NAME = "latest_top.csv"
LATEST_TOP_JSON_NAME = "latest_top.json"
LATEST_SCORE_TOP_CSV_NAME = "latest_score_top.csv"
LATEST_SCORE_TOP_JSON_NAME = "latest_score_top.json"
LEGACY_LATEST_TOP_CSV_NAME = "latest_top5.csv"
LEGACY_LATEST_TOP_JSON_NAME = "latest_top5.json"
ALGORITHM_RANKING_SOURCE = "root src.scanner.latest_ranking"
ALGORITHM_RANKING_SNAPSHOT_SOURCE = "latest_score_top"


@dataclass(frozen=True)
class BatchRuntimePolicy:
    """Runtime policy for a batch scan without changing scoring semantics."""

    universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC
    price_provider_spec: PriceProviderSpec = NAVER_PRICE_PROVIDER_SPEC
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY
    rows_per_page: int = NAVER_PRICE_PROVIDER_SPEC.rows_per_page
    market_cap_leader_codes: tuple[str, ...] = KOSPI200_MARKET_CAP_LEADER_CODES
    market_cap_override_message: str = MARKET_CAP_OVERRIDE_MESSAGE
    refresh_financials_with_price: bool = False
    runtime_boundary_notice: str = LEGACY_PLACEHOLDER_SCORE_NOTICE


DEFAULT_BATCH_RUNTIME_POLICY = BatchRuntimePolicy()
ROWS_PER_NAVER_PAGE = DEFAULT_BATCH_RUNTIME_POLICY.rows_per_page
MARKET_CAP_LEADER_CODES = list(DEFAULT_BATCH_RUNTIME_POLICY.market_cap_leader_codes)


@dataclass
class DailyUpdateRow:
    code: str
    name: str
    score: float
    latest_date: str
    latest_close: float
    latest_change: float
    latest_volume: float
    rsi14: float
    data_source: str
    df: pd.DataFrame


@dataclass
class DailyUpdateResult:
    as_of: str
    output_path: Path
    chart_paths: list[Path]
    rankings: pd.DataFrame
    failed_codes: list[str]


def _resolve_worker_count(explicit_workers: Optional[int] = None) -> int:
    """Return a conservative worker count for local batch processing."""

    if explicit_workers is not None and explicit_workers > 0:
        return explicit_workers
    return DEFAULT_BATCH_WORKERS


def _resolve_top_n(explicit_top_n: int) -> int:
    """Return a validated ranking size."""

    if explicit_top_n < 1:
        raise ValueError("top_n must be greater than or equal to 1.")
    return explicit_top_n


def _build_rankings_frame(
    rows: Iterable[DailyUpdateRow],
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "종목코드": row.code,
                "종목명": row.name,
                "점수": row.score,
                "최신일": row.latest_date,
                "종가": row.latest_close,
                "전일대비": row.latest_change,
                "거래량": row.latest_volume,
                "RSI14": row.rsi14,
                "데이터소스": row.data_source,
                "runtime_boundary_notice": runtime_policy.runtime_boundary_notice,
            }
            for row in rows
        ]
    )


def _build_universe_entries(
    refresh_universe: bool = False,
    universe_spec: UniverseSpec = KOSPI200_UNIVERSE_SPEC,
) -> list[UniverseEntry]:
    constituents = get_universe_constituents(universe_spec, refresh=refresh_universe)
    entries: list[UniverseEntry] = []
    for item in constituents:
        metadata = {
            key: str(value)
            for key, value in item.items()
            if key not in {"code", "name"} and pd.notna(value)
        }
        entries.append(
            UniverseEntry(
                code=item["code"],
                name=item["name"],
                asset_class=universe_spec.asset_class,
                metadata=metadata,
            )
        )
    return entries


def _load_universe_name_map() -> dict[str, str]:
    """Return local KOSPI200 code-to-name metadata for display only."""

    try:
        constituents = get_universe_constituents(KOSPI200_UNIVERSE_SPEC, refresh=False)
    except Exception as exc:
        logger.warning("Could not load local KOSPI200 names for ranking display: %s", exc)
        return {}

    return {
        str(item["code"]).zfill(6): str(item["name"])
        for item in constituents
        if item.get("code") and item.get("name")
    }


def _normalize_latest_algorithm_ranking_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Map canonical algorithm ranking columns to the GUI-compatible shape."""

    normalized = frame.copy()
    if "ticker" in normalized.columns:
        normalized["ticker"] = normalized["ticker"].astype(str).str.zfill(6)
    if "종목코드" in normalized.columns:
        normalized["종목코드"] = normalized["종목코드"].astype(str).str.zfill(6)
    elif "ticker" in normalized.columns:
        normalized["종목코드"] = normalized["ticker"]

    if "순위" not in normalized.columns and "rank" in normalized.columns:
        normalized["순위"] = normalized["rank"]
    if "최신일" not in normalized.columns and "date" in normalized.columns:
        normalized["최신일"] = normalized["date"].astype(str).str.slice(0, 10)
    if "점수" not in normalized.columns:
        if "final_composite_score" in normalized.columns:
            normalized["점수"] = normalized["final_composite_score"]
        elif "technical_composite_score" in normalized.columns:
            normalized["점수"] = normalized["technical_composite_score"]

    if "종목명" not in normalized.columns and "종목코드" in normalized.columns:
        name_map = _load_universe_name_map()
        normalized["종목명"] = normalized["종목코드"].map(name_map).fillna(normalized["종목코드"])

    normalized["ranking_snapshot_source"] = ALGORITHM_RANKING_SNAPSHOT_SOURCE
    normalized["canonical_ranking_source"] = ALGORITHM_RANKING_SOURCE
    if "runtime_boundary_notice" not in normalized.columns:
        if "technical_only_notice" in normalized.columns:
            normalized["runtime_boundary_notice"] = normalized["technical_only_notice"]
        else:
            normalized["runtime_boundary_notice"] = "KOSPI200 technical-only scanner v0.1; no valuation/fundamental data."

    return normalized


def load_latest_algorithm_ranking_snapshot() -> pd.DataFrame:
    """Load the canonical latest algorithm ranking snapshot when exported."""

    latest_csv = OUTPUTS_DIR / LATEST_SCORE_TOP_CSV_NAME
    if not latest_csv.exists():
        return pd.DataFrame()

    frame = pd.read_csv(latest_csv, dtype={"ticker": str, "종목코드": str})
    return _normalize_latest_algorithm_ranking_frame(frame)


def load_latest_top5_snapshot(prefer_algorithm: bool = True) -> pd.DataFrame:
    """Load the most recent top-ranked output if available."""

    if prefer_algorithm:
        algorithm_frame = load_latest_algorithm_ranking_snapshot()
        if not algorithm_frame.empty:
            return algorithm_frame

    candidate_paths = [
        OUTPUTS_DIR / LATEST_TOP_CSV_NAME,
        OUTPUTS_DIR / LEGACY_LATEST_TOP_CSV_NAME,
    ]
    latest_csv = next((path for path in candidate_paths if path.exists()), None)
    if latest_csv is None:
        return pd.DataFrame()
    frame = pd.read_csv(latest_csv, dtype={"종목코드": str})
    if "종목코드" in frame.columns:
        frame["종목코드"] = frame["종목코드"].astype(str).str.zfill(6)
    return frame


def _select_latest_summary_row(df: pd.DataFrame) -> pd.Series:
    """Choose the most recent row suitable for summary tables.

    If the newest row is an incomplete same-day row with zero volume, prefer the
    latest row that has positive volume.
    """

    latest = df.iloc[-1]
    if float(latest.get(VOLUME_COLUMN, 0.0)) > 0:
        return latest

    completed_rows = df[df[VOLUME_COLUMN] > 0]
    if not completed_rows.empty:
        return completed_rows.iloc[-1]

    return latest


def _calculate_latest_change(df: pd.DataFrame, summary_row: pd.Series) -> float:
    """Calculate signed day-over-day close change for the selected summary row."""

    if df.empty:
        return 0.0

    try:
        summary_position = int(df.index.get_loc(summary_row.name))
    except KeyError:
        summary_position = len(df) - 1

    if summary_position <= 0:
        return 0.0

    current_close = float(summary_row[CLOSE_COLUMN])
    previous_close = float(df.iloc[summary_position - 1][CLOSE_COLUMN])
    return current_close - previous_close


def _process_universe_entry(
    entry: UniverseEntry,
    pages: int,
    use_cache: bool,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> DailyUpdateRow:
    """Fetch, enrich, and score a single universe member."""

    base_df = get_price_df(
        entry.code,
        pages=pages,
        use_cache=use_cache,
        provider_spec=runtime_policy.price_provider_spec,
        cache_policy=runtime_policy.cache_policy,
        refresh_financials=runtime_policy.refresh_financials_with_price,
    )
    indicator_df = add_indicators(base_df)
    latest = _select_latest_summary_row(indicator_df)
    latest_change = _calculate_latest_change(indicator_df, latest)
    return DailyUpdateRow(
        code=entry.code,
        name=entry.name,
        score=score_stock(indicator_df),
        latest_date=pd.Timestamp(latest[DATE_COLUMN]).strftime("%Y-%m-%d"),
        latest_close=float(latest[CLOSE_COLUMN]),
        latest_change=latest_change,
        latest_volume=float(latest[VOLUME_COLUMN]),
        rsi14=float(latest.get("RSI14", float("nan"))),
        data_source="cache_or_fetch" if use_cache else "direct_fetch",
        df=indicator_df,
    )


def _apply_market_cap_leader_override(
    results_df: pd.DataFrame,
    top_n: int,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> pd.DataFrame:
    """Prioritize the configured market-cap leaders, then fill any remaining slots."""

    logger.info(runtime_policy.market_cap_override_message)

    selected_frames: list[pd.DataFrame] = []
    for code in runtime_policy.market_cap_leader_codes:
        matched = results_df[results_df["종목코드"] == code]
        if not matched.empty:
            selected_frames.append(matched.head(1))

    if not selected_frames:
        logger.warning("Market-cap override could not match any stocks; using selector fallback.")
        return select_top_stocks(results_df, top_n=top_n)

    top_rankings = pd.concat(selected_frames, ignore_index=True).head(top_n)
    if len(top_rankings) < top_n:
        excluded_codes = set(top_rankings["종목코드"].tolist())
        remaining = results_df[~results_df["종목코드"].isin(excluded_codes)].copy()
        fallback = select_top_stocks(remaining, top_n=top_n - len(top_rankings))
        fallback = fallback.drop(columns=["순위"], errors="ignore")
        top_rankings = pd.concat([top_rankings, fallback], ignore_index=True)

    top_rankings.insert(0, "순위", range(1, len(top_rankings) + 1))
    ordered_columns = ["순위", "종목코드", "종목명", "점수", "최신일", "종가", "전일대비", "거래량", "RSI14", "데이터소스"]
    ordered_columns.append("runtime_boundary_notice")
    return top_rankings.loc[:, [column for column in ordered_columns if column in top_rankings.columns]]


def get_minimum_chart_pages(requested_pages: int) -> int:
    """Return a chart-friendly page count that covers at least about three months."""

    return max(requested_pages, MIN_CHART_PAGES)


def prepare_chart_dataframe(
    code: str,
    requested_pages: int,
    use_cache: bool = True,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> pd.DataFrame:
    """Fetch extra history for indicators, then trim to the display window."""

    display_pages = get_minimum_chart_pages(requested_pages)
    fetch_pages = display_pages + CHART_WARMUP_PAGES
    display_rows = display_pages * runtime_policy.rows_per_page

    base_df = get_price_df(
        code=code,
        pages=fetch_pages,
        use_cache=use_cache,
        provider_spec=runtime_policy.price_provider_spec,
        cache_policy=runtime_policy.cache_policy,
    )
    indicator_df = add_indicators(base_df)
    return indicator_df.tail(display_rows).reset_index(drop=True)


def _reuse_processed_chart_dataframe(
    row: DailyUpdateRow,
    requested_pages: int,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> pd.DataFrame | None:
    """Return already processed indicator data when it covers the chart window."""

    display_pages = get_minimum_chart_pages(requested_pages)
    display_rows = display_pages * runtime_policy.rows_per_page
    required_columns = {DATE_COLUMN, *PRICE_COLUMNS, *INDICATOR_COLUMNS}
    if row.df.empty or len(row.df) < display_rows:
        return None
    if not required_columns.issubset(set(row.df.columns)):
        return None
    return row.df.tail(display_rows).reset_index(drop=True).copy()


def _export_outputs(top_rankings: pd.DataFrame, meta: dict) -> None:
    top_rankings.to_csv(OUTPUTS_DIR / LATEST_TOP_CSV_NAME, index=False, encoding="utf-8-sig")
    top_rankings.to_json(OUTPUTS_DIR / LATEST_TOP_JSON_NAME, orient="records", force_ascii=False, indent=2)
    top_rankings.to_csv(OUTPUTS_DIR / LEGACY_LATEST_TOP_CSV_NAME, index=False, encoding="utf-8-sig")
    top_rankings.to_json(OUTPUTS_DIR / LEGACY_LATEST_TOP_JSON_NAME, orient="records", force_ascii=False, indent=2)
    (OUTPUTS_DIR / "last_run_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _render_selected_charts(
    rows: Iterable[DailyUpdateRow],
    selected_codes: set[str],
    pages: int,
    use_cache: bool,
    output_dir: Path,
    file_name_builder: Callable[[DailyUpdateRow], str],
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> tuple[list[str], list[str]]:
    """Render charts for selected rows while isolating per-stock failures."""

    from stock_core.charts.renderer import render_stock_chart

    output_dir.mkdir(parents=True, exist_ok=True)

    chart_paths: list[str] = []
    chart_failed_codes: list[str] = []

    for row in rows:
        if row.code not in selected_codes:
            continue

        chart_path = output_dir / file_name_builder(row)
        try:
            chart_df = _reuse_processed_chart_dataframe(row, pages, runtime_policy)
            if chart_df is None:
                chart_df = prepare_chart_dataframe(
                    row.code,
                    requested_pages=pages,
                    use_cache=use_cache,
                    runtime_policy=runtime_policy,
                )
            render_stock_chart(chart_df, row.code, row.name, str(chart_path))
            chart_paths.append(str(chart_path))
        except Exception as exc:
            chart_failed_codes.append(row.code)
            logger.warning("Failed to render chart for %s (%s): %s", row.name, row.code, exc)

    return chart_paths, chart_failed_codes


def run_daily_update(
    pages: int = 20,
    render_charts: bool = True,
    chart_dir: Optional[str] = None,
    limit: Optional[int] = None,
    top_n: int = DEFAULT_TOP_N,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> DailyUpdateResult:
    """Run the daily update pipeline end-to-end for the configured universe."""

    top_n = _resolve_top_n(top_n)
    universe = _build_universe_entries(refresh_universe=False, universe_spec=runtime_policy.universe_spec)
    if limit is not None:
        universe = universe[:limit]

    logger.info("Running daily update for %s stocks", len(universe))

    rows: list[DailyUpdateRow] = []
    failed_codes: list[str] = []

    for entry in universe:
        try:
            base_df = get_price_df(
                entry.code,
                pages=pages,
                use_cache=True,
                provider_spec=runtime_policy.price_provider_spec,
                cache_policy=runtime_policy.cache_policy,
            )
            indicator_df = add_indicators(base_df)
            latest = _select_latest_summary_row(indicator_df)
            latest_change = _calculate_latest_change(indicator_df, latest)
            rows.append(
                DailyUpdateRow(
                    code=entry.code,
                    name=entry.name,
                    score=score_stock(indicator_df),
                    latest_date=pd.Timestamp(latest[DATE_COLUMN]).strftime("%Y-%m-%d"),
                    latest_close=float(latest[CLOSE_COLUMN]),
                    latest_change=latest_change,
                    latest_volume=float(latest[VOLUME_COLUMN]),
                    rsi14=float(latest.get("RSI14", float("nan"))),
                    data_source="cache_or_fetch",
                    df=indicator_df,
                )
            )
        except Exception as exc:
            failed_codes.append(entry.code)
            logger.warning("Failed to update %s (%s): %s", entry.name, entry.code, exc)

    if not rows:
        raise ValueError("No stocks were updated successfully.")

    rankings = _build_rankings_frame(rows, runtime_policy=runtime_policy)
    top_rankings = select_top_stocks(rankings, top_n=top_n)
    as_of = datetime.now().strftime("%Y%m%d")
    output_path = RESULTS_DIR / f"top{top_n}_scan_{as_of}.csv"
    top_rankings.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("Saved top rankings to %s", output_path)

    chart_output_dir = Path(chart_dir) if chart_dir else DATA_DIR / "scan_results" / f"charts_{as_of}"
    chart_paths: list[Path] = []
    if render_charts:
        selected_codes = set(top_rankings["종목코드"].tolist())
        rendered_chart_paths, _ = _render_selected_charts(
            rows=rows,
            selected_codes=selected_codes,
            pages=pages,
            use_cache=True,
            output_dir=chart_output_dir,
            file_name_builder=lambda row: f"{row.code}_{as_of}.png",
            runtime_policy=runtime_policy,
        )
        chart_paths = [Path(path) for path in rendered_chart_paths]

    return DailyUpdateResult(
        as_of=as_of,
        output_path=output_path,
        chart_paths=chart_paths,
        rankings=top_rankings,
        failed_codes=failed_codes,
    )


def run_daily_top5_update(
    pages: int = 20,
    use_cache: bool = True,
    refresh_universe: bool = False,
    render_charts: bool = True,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    top_n: int = DEFAULT_TOP_N,
    use_market_cap_override: bool = False,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> tuple[pd.DataFrame, dict]:
    """Run the configured universe batch and export the latest top-ranked artifacts."""

    top_n = _resolve_top_n(top_n)
    universe = _build_universe_entries(refresh_universe=refresh_universe, universe_spec=runtime_policy.universe_spec)
    worker_count = _resolve_worker_count(max_workers)
    logger.info(
        "Running daily Top-N update for %s stocks (pages=%s, use_cache=%s, refresh_universe=%s, workers=%s, top_n=%s)",
        len(universe),
        pages,
        use_cache,
        refresh_universe,
        worker_count,
        top_n,
    )

    rows: list[DailyUpdateRow] = []
    failed_codes: list[str] = []
    completed_count = 0

    future_to_entry: dict = {}
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="topn") as executor:
        for entry in universe:
            future = executor.submit(_process_universe_entry, entry, pages, use_cache, runtime_policy)
            future_to_entry[future] = entry

        for future in as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                rows.append(future.result())
            except Exception as exc:
                failed_codes.append(entry.code)
                logger.warning("Failed to process %s (%s): %s", entry.name, entry.code, exc)
            finally:
                completed_count += 1
                if progress_callback is not None:
                    progress_callback(completed_count, len(universe), len(failed_codes))

    if not rows:
        raise ValueError("No stocks were processed successfully.")

    results_df = _build_rankings_frame(rows, runtime_policy=runtime_policy)
    ordered_results = results_df.sort_values(
        by=["점수", "최신일", "종목코드"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    if use_market_cap_override:
        top_df = _apply_market_cap_leader_override(ordered_results, top_n=top_n, runtime_policy=runtime_policy)
    else:
        top_df = select_top_stocks(ordered_results, top_n=top_n)

    chart_paths: list[str] = []
    chart_failed_codes: list[str] = []
    if render_charts:
        selected_codes = set(top_df["종목코드"].tolist())
        chart_paths, chart_failed_codes = _render_selected_charts(
            rows=rows,
            selected_codes=selected_codes,
            pages=pages,
            use_cache=use_cache,
            output_dir=OUTPUTS_CHARTS_DIR,
            file_name_builder=lambda row: f"{row.code}.png",
            runtime_policy=runtime_policy,
        )

    completed_at = datetime.now()
    meta = {
        "as_of": completed_at.strftime("%Y-%m-%d"),
        "completed_at": completed_at.isoformat(timespec="seconds"),
        "last_successful_update_date": completed_at.strftime("%Y-%m-%d"),
        "pages": pages,
        "top_n": top_n,
        "use_market_cap_override": use_market_cap_override,
        "use_cache": use_cache,
        "refresh_universe": refresh_universe,
        "render_charts": render_charts,
        "max_workers": worker_count,
        "universe_id": runtime_policy.universe_spec.universe_id,
        "universe_name": runtime_policy.universe_spec.display_name,
        "price_provider_id": runtime_policy.price_provider_spec.provider_id,
        "universe_size": len(universe),
        "processed_count": len(rows),
        "failed_count": len(failed_codes),
        "failed_codes": failed_codes,
        "output_csv": str(OUTPUTS_DIR / LATEST_TOP_CSV_NAME),
        "output_json": str(OUTPUTS_DIR / LATEST_TOP_JSON_NAME),
        "output_meta": str(OUTPUTS_DIR / "last_run_meta.json"),
        "chart_paths": chart_paths,
        "chart_failed_count": len(chart_failed_codes),
        "chart_failed_codes": chart_failed_codes,
        "live_universe_enabled": runtime_policy.universe_spec.live_refresh_supported,
        "market_cap_override": use_market_cap_override,
        "market_cap_override_message": runtime_policy.market_cap_override_message if use_market_cap_override else "",
        "market_cap_override_codes": list(runtime_policy.market_cap_leader_codes) if use_market_cap_override else [],
        "runtime_boundary_notice": runtime_policy.runtime_boundary_notice,
        "canonical_ranking_source": "root src.scanner.latest_ranking",
        "financial_refresh_with_price": runtime_policy.refresh_financials_with_price,
    }
    _export_outputs(top_df, meta)
    logger.info("Exported latest top-ranked outputs to %s", OUTPUTS_DIR)

    return top_df, meta


def get_daily_top5_due_status() -> DailyUpdateDueStatus:
    """Return whether the Top-N output is due for the business-day schedule."""

    return get_daily_update_due_status(OUTPUTS_DIR / "last_run_meta.json")


def run_daily_top5_update_if_due(
    pages: int = 20,
    use_cache: bool = True,
    refresh_universe: bool = False,
    render_charts: bool = True,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    top_n: int = DEFAULT_TOP_N,
    use_market_cap_override: bool = False,
    runtime_policy: BatchRuntimePolicy = DEFAULT_BATCH_RUNTIME_POLICY,
) -> tuple[Optional[pd.DataFrame], dict]:
    """Run the Top-N update only when the business-day 21:00 deadline is due."""

    due_status = get_daily_top5_due_status()
    due_meta = {
        "due_check": True,
        "is_due": due_status.is_due,
        "due_at": due_status.due_at.isoformat(timespec="seconds") if due_status.due_at else None,
        "due_last_successful_update_date": (
            due_status.last_successful_update_date.isoformat()
            if due_status.last_successful_update_date
            else None
        ),
        "reason": due_status.reason,
    }

    if not due_status.is_due:
        return None, due_meta

    top_df, meta = run_daily_top5_update(
        pages=pages,
        use_cache=use_cache,
        refresh_universe=refresh_universe,
        render_charts=render_charts,
        max_workers=max_workers,
        progress_callback=progress_callback,
        top_n=top_n,
        use_market_cap_override=use_market_cap_override,
        runtime_policy=runtime_policy,
    )
    meta.update(due_meta)
    return top_df, meta
