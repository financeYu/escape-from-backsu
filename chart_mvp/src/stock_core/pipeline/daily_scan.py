"""Daily batch scan pipeline for local stock analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from stock_core.cache.csv_cache import refresh_stock_data
from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.providers.universe import UniverseEntry
from stock_core.ranking.base import ScoreContext, StockScorer
from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN
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


def scan_universe(
    universe: Iterable[UniverseEntry],
    scorer: StockScorer,
    pages: int = 20,
    top_n: int = 5,
) -> BatchScanResult:
    """Run a batch scan across a universe and return the top-ranked table."""

    if top_n < 1:
        raise ValueError("top_n must be greater than or equal to 1.")

    candidates: list[ScanCandidate] = []
    failed_codes: list[str] = []

    for entry in universe:
        try:
            df, source = refresh_stock_data(code=entry.code, pages=pages)
            stock_name = resolve_stock_name(entry)
            score = scorer.score(
                df,
                ScoreContext(code=entry.code, name=stock_name, source=source),
            )
            latest = df.iloc[-1]
            candidates.append(
                ScanCandidate(
                    code=entry.code,
                    name=stock_name,
                    source=source,
                    score=float(score),
                    latest_date=pd.Timestamp(latest[DATE_COLUMN]),
                    latest_close=float(latest[CLOSE_COLUMN]),
                    rsi14=float(latest.get("RSI14", float("nan"))),
                    data=df,
                )
            )
            print(f"[Info] Scanned {stock_name} ({entry.code}) -> score={score:.2f}")
        except Exception as exc:
            failed_codes.append(entry.code)
            print(f"[Warning] Failed to scan {entry.code} ({entry.name}): {exc}")

    if not candidates:
        raise ValueError("No stocks were scanned successfully.")

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
    rankings = pd.DataFrame(ranking_rows)
    as_of = datetime.now().strftime("%Y%m%d")
    output_path = RESULTS_DIR / f"top{top_n}_scan_{as_of}.csv"
    rankings.to_csv(output_path, index=False, encoding="utf-8-sig")

    top_codes = set(rankings["종목코드"].tolist())
    top_candidates = [candidate for candidate in candidates if candidate.code in top_codes]
    rank_index = rankings.set_index("종목코드")
    top_candidates.sort(key=lambda item: rank_index.loc[item.code, "순위"])

    return BatchScanResult(
        as_of=as_of,
        output_path=output_path,
        rankings=rankings,
        top_candidates=top_candidates,
        failed_codes=failed_codes,
    )


def render_top_charts(result: BatchScanResult, show: bool = True) -> None:
    """Render charts for the selected top-ranked stocks."""

    for candidate in result.top_candidates:
        source_label = "평일 갱신" if candidate.source == "fetched" else "주말 캐시"
        plot_stock_data(candidate.data, stock_label=candidate.name, source_label=source_label, show=show)
