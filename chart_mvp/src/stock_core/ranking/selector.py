"""Helpers for selecting the highest-ranked legacy chart-runtime stocks."""

from __future__ import annotations

import pandas as pd


def select_top_stocks(rankings: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Return the top-N rows using current legacy placeholder ordering rules."""

    if rankings.empty:
        return rankings.copy()

    sort_columns: list[str] = []
    ascending: list[bool] = []

    if "점수" in rankings.columns:
        sort_columns.append("점수")
        ascending.append(False)
    if "최신일" in rankings.columns:
        sort_columns.append("최신일")
        ascending.append(False)
    if "종목코드" in rankings.columns:
        sort_columns.append("종목코드")
        ascending.append(True)

    sorted_rankings = rankings.sort_values(sort_columns, ascending=ascending).reset_index(drop=True)
    top_rankings = sorted_rankings.head(top_n).copy()
    top_rankings["순위"] = range(1, len(top_rankings) + 1)

    ordered_columns = [
        "순위",
        "종목코드",
        "종목명",
        "점수",
        "최신일",
        "종가",
        "전일대비",
        "거래량",
        "RSI14",
        "데이터소스",
        "runtime_boundary_notice",
    ]
    existing_columns = [column for column in ordered_columns if column in top_rankings.columns]
    return top_rankings.loc[:, existing_columns]
