"""Daily batch scan pipeline for local stock analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from stock_core.cache.csv_cache import DEFAULT_PRICE_CACHE_POLICY, PriceCachePolicy, refresh_stock_data
from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.providers.universe import UniverseEntry
from stock_core.ranking.base import ScoreContext, StockScorer
from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN
from stock_core.utils.market_specs import NAVER_PRICE_PROVIDER_SPEC, PriceProviderSpec
from stock_core.utils.paths import RESULTS_DIR


@dataclass
class ScanCandidate:
    code: str
    name: str
    source: str
    score: float
    latest_date: pd.Timestamp
    latest_close: float
    rsi14: float
    data: pd.DataFrame


@dataclass
class BatchScanResult:
    as_of: str
    output_path: Path
    rankings: pd.DataFrame
    top_candidates: list[ScanCandidate]
    failed_codes: list[str]


def resolve_stock_name(entry: UniverseEntry) -> str:
    """Use the universe provider name to keep batch scans lightweight and stable."""

    return entry.name


def _scan_entry(
    entry: UniverseEntry,
    scorer: StockScorer,
    pages: int,
    provider_spec: PriceProviderSpec,
    cache_policy: PriceCachePolicy,
) -> ScanCandidate:
    df, source = refresh_stock_data(
        code=entry.code,
        pages=pages,
        provider_spec=provider_spec,
        cache_policy=cache_policy,
    )
    stock_name = resolve_stock_name(entry)
    score = scorer.score(
        df,
        ScoreContext(code=entry.code, name=stock_name, source=source),
    )
    latest = df.iloc[-1]
    candidate = ScanCandidate(
        code=entry.code,
        name=stock_name,
        source=source,
        score=float(score),
        latest_date=pd.Timestamp(latest[DATE_COLUMN]),
        latest_close=float(latest[CLOSE_COLUMN]),
        rsi14=float(latest.get("RSI14", float("nan"))),
        data=df,
    )
    print(f"[Info] Scanned {stock_name} ({entry.code}) -> score={score:.2f}")
    return candidate


def _build_scan_rankings(candidates: list[ScanCandidate], top_n: int) -> pd.DataFrame:
    ranking_rows = [
        {
            "순위": index,
            "종목코드": candidate.code,
            "종목명": candidate.name,
            "점수": candidate.score,
            "최신일": candidate.latest_date.strftime("%Y-%m-%d"),
            "종가": candidate.latest_close,
            "RSI14": candidate.rsi14,
            "데이터소스": candidate.source,
        }
        for index, candidate in enumerate(
            sorted(
                candidates,
                key=lambda item: (-item.score, item.code),
            )[:top_n],
            start=1,
        )
    ]
    return pd.DataFrame(ranking_rows)


def _select_top_candidates(candidates: list[ScanCandidate], rankings: pd.DataFrame) -> list[ScanCandidate]:
    top_codes = set(rankings["종목코드"].tolist())
    top_candidates = [candidate for candidate in candidates if candidate.code in top_codes]
    rank_index = rankings.set_index("종목코드")
    top_candidates.sort(key=lambda item: rank_index.loc[item.code, "순위"])
    return top_candidates


def _write_scan_rankings(rankings: pd.DataFrame, top_n: int, as_of: str) -> Path:
    output_path = RESULTS_DIR / f"top{top_n}_scan_{as_of}.csv"
    rankings.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def _finalize_scan_result(
    *,
    candidates: list[ScanCandidate],
    failed_codes: list[str],
    rankings: pd.DataFrame,
    top_n: int,
) -> BatchScanResult:
    as_of = datetime.now().strftime("%Y%m%d")
    return BatchScanResult(
        as_of=as_of,
        output_path=_write_scan_rankings(rankings, top_n, as_of),
        rankings=rankings,
        top_candidates=_select_top_candidates(candidates, rankings),
        failed_codes=failed_codes,
    )


def scan_universe(
    universe: Iterable[UniverseEntry],
    scorer: StockScorer,
    pages: int = 20,
    top_n: int = 5,
    provider_spec: PriceProviderSpec = NAVER_PRICE_PROVIDER_SPEC,
    cache_policy: PriceCachePolicy = DEFAULT_PRICE_CACHE_POLICY,
) -> BatchScanResult:
    """Run a batch scan across a universe and return the top-ranked table."""

    if top_n < 1:
        raise ValueError("top_n must be greater than or equal to 1.")

    candidates: list[ScanCandidate] = []
    failed_codes: list[str] = []

    for entry in universe:
        try:
            candidates.append(
                _scan_entry(
                    entry,
                    scorer,
                    pages,
                    provider_spec,
                    cache_policy,
                )
            )
        except Exception as exc:
            failed_codes.append(entry.code)
            print(f"[Warning] Failed to scan {entry.code} ({entry.name}): {exc}")

    if not candidates:
        raise ValueError("No stocks were scanned successfully.")

    return _finalize_scan_result(
        candidates=candidates,
        failed_codes=failed_codes,
        rankings=_build_scan_rankings(candidates, top_n),
        top_n=top_n,
    )


def render_top_charts(result: BatchScanResult, show: bool = True) -> None:
    """Render charts for the selected top-ranked stocks."""

    for candidate in result.top_candidates:
        source_label = "평일 갱신" if candidate.source == "fetched" else "주말 캐시"
        plot_stock_data(candidate.data, stock_label=candidate.name, source_label=source_label, show=show)
