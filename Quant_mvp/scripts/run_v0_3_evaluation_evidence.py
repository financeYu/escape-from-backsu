"""Run a v0.3 candidate-only EvaluationEvidence packet.

This entrypoint connects a StrategyCandidate JSON record, OHLCV CSV input, and
optional config JSON into the candidate ranking snapshot adapter and the
ranking snapshot top_n conservative evaluator. It writes only EvaluationEvidence
artifacts under approved evidence-only paths.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from Quant_mvp.backtest_mvp.evaluation_evidence import (
    run_v0_3_evaluation_evidence,
    write_evaluation_evidence_markdown,
)


DEFAULT_OUTPUT = Path(
    "Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/evaluation_evidence.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path} is empty")
    if text.startswith("{"):
        payload = json.loads(text)
    else:
        first_line = next(line for line in text.splitlines() if line.strip())
        payload = json.loads(first_line)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return _read_json(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True, help="StrategyCandidate JSON or JSONL path.")
    parser.add_argument("--prices", type=Path, required=True, help="Daily OHLCV CSV path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Evidence-only markdown output path.")
    parser.add_argument("--ranking-config", type=Path, help="Optional CandidateRankingSnapshotConfig JSON path.")
    parser.add_argument("--backtest-config", type=Path, help="Optional BacktestConfig JSON path.")
    parser.add_argument("--evaluation-id", help="Optional stable EvaluationEvidence ID.")
    parser.add_argument("--created-at", help="Optional YYYY-MM-DD creation date.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Repository root for output boundary checks.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate = _read_json(args.candidate)
    prices = pd.read_csv(args.prices, dtype={"ticker": str})
    result = run_v0_3_evaluation_evidence(
        candidate,
        prices,
        ranking_config=_optional_json(args.ranking_config),
        backtest_config=_optional_json(args.backtest_config),
        evaluation_id=args.evaluation_id,
        created_at=args.created_at,
    )
    output = write_evaluation_evidence_markdown(
        result,
        args.output,
        project_root=args.project_root,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
