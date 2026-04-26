"""Non-visual adapter for the Quant backtest GUI.

This module intentionally wraps the existing Step 17 conservative backtest
engine without changing score, ranking, or report semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest import BacktestConfig, ConservativeBacktestResult, run_conservative_backtest


EVALUATION_ONLY_NOTICE = (
    "evaluation-only conservative backtest artifact; not a trading "
    "recommendation; does not redefine score or ranking formulas; uses "
    "technical-only upstream ranking context; valuation/fundamental scoring "
    "remains candidate-only until a separately approved post-freeze activation"
)


@dataclass(frozen=True)
class BacktestInputPaths:
    """CSV inputs selected by the GUI."""

    ranking_csv: Path
    price_csv: Path


@dataclass(frozen=True)
class BacktestRunRequest:
    """One GUI backtest run request."""

    inputs: BacktestInputPaths
    config: BacktestConfig


@dataclass(frozen=True)
class BacktestRunArtifacts:
    """Frames and metadata produced for GUI display or local export."""

    result: ConservativeBacktestResult
    summary: dict[str, Any]
    period_frame: pd.DataFrame
    security_frame: pd.DataFrame
    equity_frame: pd.DataFrame


def read_backtest_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV while preserving Korean stock-code tickers as strings."""

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"CSV file not found: {resolved}")
    frame = pd.read_csv(resolved, dtype={"ticker": "string"})
    if "ticker" in frame.columns:
        frame = frame.copy()
        frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    return frame


def run_backtest_from_csv(request: BacktestRunRequest) -> BacktestRunArtifacts:
    """Run the existing conservative backtest engine from GUI-selected CSVs."""

    ranking_frame = read_backtest_csv(request.inputs.ranking_csv)
    price_frame = read_backtest_csv(request.inputs.price_csv)
    result = run_conservative_backtest(
        ranking_frame,
        price_frame,
        config=request.config,
    )
    period_frame = result.to_period_frame()
    security_frame = result.to_security_frame()
    equity_frame = build_equity_curve(period_frame)
    summary = result.to_summary_dict()
    summary["boundary_notice"] = EVALUATION_ONLY_NOTICE
    return BacktestRunArtifacts(
        result=result,
        summary=summary,
        period_frame=period_frame,
        security_frame=security_frame,
        equity_frame=equity_frame,
    )


def build_equity_curve(period_frame: pd.DataFrame) -> pd.DataFrame:
    """Build a display-only equity curve from period backtest returns."""

    if period_frame.empty:
        return pd.DataFrame(columns=["decision_date", "period_return", "equity"])

    equity = 1.0
    rows: list[dict[str, Any]] = []
    for _, row in period_frame.iterrows():
        period_return = row.get("backtest_period_return")
        if pd.isna(period_return):
            period_return = 0.0
        period_return = float(period_return)
        equity *= 1.0 + period_return
        rows.append(
            {
                "decision_date": row.get("decision_date"),
                "period_return": period_return,
                "equity": equity,
            }
        )
    return pd.DataFrame(rows)


def export_result_bundle(
    artifacts: BacktestRunArtifacts,
    output_dir: str | Path,
    *,
    stem: str = "quant_backtest_gui",
) -> dict[str, Path]:
    """Write generated evaluation artifacts to a user-selected local directory."""

    resolved = Path(output_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    summary_path = resolved / f"{stem}_summary.json"
    period_path = resolved / f"{stem}_periods.csv"
    security_path = resolved / f"{stem}_securities.csv"
    equity_path = resolved / f"{stem}_equity.csv"

    summary_path.write_text(
        json.dumps(_json_ready(artifacts.summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    artifacts.period_frame.to_csv(period_path, index=False, encoding="utf-8-sig")
    artifacts.security_frame.to_csv(security_path, index=False, encoding="utf-8-sig")
    artifacts.equity_frame.to_csv(equity_path, index=False, encoding="utf-8-sig")
    return {
        "summary": summary_path,
        "periods": period_path,
        "securities": security_path,
        "equity": equity_path,
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value
