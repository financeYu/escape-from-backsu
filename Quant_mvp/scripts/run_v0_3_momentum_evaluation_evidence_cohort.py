"""Run approved v0.3 EvaluationEvidence for the momentum cohort.

This script consumes the existing momentum-evaluable StrategyCandidate cohort
and local daily price CSV files, then writes evidence-only EvaluationEvidence
records. It does not train a model, write runtime rankings, or approve
strategies.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.candidate_rank_adapter import CandidateRankingSnapshotConfig
from Quant_mvp.backtest_mvp.evaluation_evidence import (
    run_v0_3_evaluation_evidence,
    strategy_candidate_payload,
    validate_evaluation_evidence_output_path,
    write_evaluation_evidence_markdown,
)
from Quant_mvp.scripts.build_v0_3_momentum_evaluation_evidence_packets import (
    DEFAULT_COHORT_ID,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REGISTRY,
    load_registry,
    select_momentum_evaluable_candidates,
)
from Quant_mvp.scripts.v0_3_ml_label_policy import (
    GENERIC_PROXY_LABEL_ROLE,
    GENERIC_PROXY_LABEL_STATUS,
    GENERIC_PROXY_LIMITATION,
    GENERIC_PROXY_REVIEW_NOTE,
)


DEFAULT_PRICES_DIR = Path("chart_mvp/data")
DEFAULT_PRICE_GLOB = "*_daily_prices.csv"
DEFAULT_MOMENTUM_WINDOW = 20
DEFAULT_REBALANCE_STEP_DAYS = 20
DEFAULT_ENTRY_PERCENTILE_THRESHOLD = 0.80
DEFAULT_HOLDING_PERIOD_DAYS = 20
DEFAULT_EXECUTION_LAG_DAYS = 1
DEFAULT_TRANSACTION_COST_BPS = 10.0
DEFAULT_SLIPPAGE_BPS = 5.0
RECORDED_EVIDENCE_STATUS = "evidence_recorded"
EVALUATION_EVIDENCE_CONTRACT_REF = "docs/extension/v0_3_evaluation_evidence_contract.md"
STRATEGY_CANDIDATE_REGISTRY_CONTRACT_REF = (
    "docs/extension/v0_3_strategy_candidate_registry_contract.md"
)
EVALUATION_EVIDENCE_METHOD_REF = "Quant_mvp/backtest_mvp/evaluation_evidence.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--price-glob", default=DEFAULT_PRICE_GLOB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT_ID)
    parser.add_argument("--expected-count", type=int, help="Optional selected-candidate count guard.")
    parser.add_argument("--created-at", default=date.today().isoformat(), help="YYYY-MM-DD evidence date.")
    parser.add_argument("--max-date", help="Optional YYYY-MM-DD upper bound for price rows.")
    return parser.parse_args(argv)


def load_chart_daily_prices(
    prices_dir: Path,
    *,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(prices_dir.glob(price_glob)):
        ticker = path.name.removesuffix("_daily_prices.csv")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if len(fieldnames) < 7:
                raise ValueError(f"{path} does not look like a daily price CSV")
            date_column, close_column = fieldnames[0], fieldnames[1]
            open_column, high_column, low_column, volume_column = (
                fieldnames[3],
                fieldnames[4],
                fieldnames[5],
                fieldnames[6],
            )
            for row in reader:
                row_date = str(row.get(date_column) or "")
                if max_date and row_date > max_date:
                    continue
                rows.append(
                    {
                        "ticker": ticker,
                        "date": row_date,
                        "open": row.get(open_column),
                        "high": row.get(high_column),
                        "low": row.get(low_column),
                        "close": row.get(close_column),
                        "volume": row.get(volume_column),
                    }
                )
    if not rows:
        raise ValueError(f"no daily price rows found under {prices_dir}")
    return pd.DataFrame(rows)


def candidate_test_period_window(candidate: dict[str, Any]) -> tuple[str | None, str | None]:
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(candidate.get("test_period") or ""))
    if len(dates) < 2:
        return (None, None)
    return (dates[0], dates[1])


def effective_candidate_max_date(
    candidate: dict[str, Any],
    *,
    created_at: str,
    max_date: str | None,
) -> str:
    _, test_period_end = candidate_test_period_window(candidate)
    bounds = [created_at]
    if max_date:
        bounds.append(max_date)
    if test_period_end:
        bounds.append(test_period_end)
    return min(bounds)


def filter_prices_for_candidate(price_frame: pd.DataFrame, candidate_max_date: str) -> pd.DataFrame:
    filtered = price_frame.loc[price_frame["date"].astype(str).le(candidate_max_date)].copy()
    if filtered.empty:
        raise ValueError(f"no daily price rows available on or before candidate max date {candidate_max_date}")
    return filtered


def _parse_first_int(value: Any, *, default: int) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else default


def _parse_first_float(value: Any, *, default: float) -> float:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else default


def ranking_config_from_candidate(candidate: dict[str, Any]) -> CandidateRankingSnapshotConfig:
    signal_inputs = candidate.get("signal_inputs")
    scope = candidate.get("experiment_scope")
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    scope = scope if isinstance(scope, dict) else {}
    entry_percentile = _parse_first_float(
        scope.get("entry_rule") or signal_inputs.get("entry_rule"),
        default=DEFAULT_ENTRY_PERCENTILE_THRESHOLD,
    )
    if entry_percentile > 1.0:
        entry_percentile = entry_percentile / 100.0
    rebalance_rule = scope.get("rebalance_rule") or signal_inputs.get("rebalance_rule")
    return CandidateRankingSnapshotConfig(
        momentum_window=_parse_first_int(
            signal_inputs.get("signal_calculation_window"),
            default=DEFAULT_MOMENTUM_WINDOW,
        ),
        rebalance_step_days=_parse_first_int(
            rebalance_rule,
            default=DEFAULT_REBALANCE_STEP_DAYS,
        ),
        entry_percentile_threshold=entry_percentile,
    )


def backtest_config_from_candidate(candidate: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    scope = candidate.get("experiment_scope")
    signal_inputs = candidate.get("signal_inputs")
    scope = scope if isinstance(scope, dict) else {}
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    return {
        "defaults": {
            "holding_period_days": _parse_first_int(
                scope.get("holding_period") or signal_inputs.get("exit_rule"),
                default=DEFAULT_HOLDING_PERIOD_DAYS,
            ),
            "execution_lag_days": DEFAULT_EXECUTION_LAG_DAYS,
            "transaction_cost_bps": DEFAULT_TRANSACTION_COST_BPS,
            "slippage_bps": DEFAULT_SLIPPAGE_BPS,
        }
    }


def source_refs_for_run(registry: Path, prices_dir: Path) -> list[str]:
    return [
        EVALUATION_EVIDENCE_CONTRACT_REF,
        STRATEGY_CANDIDATE_REGISTRY_CONTRACT_REF,
        str(registry),
        str(prices_dir),
        EVALUATION_EVIDENCE_METHOD_REF,
    ]


def candidate_rule_fingerprint(candidate: dict[str, Any]) -> str:
    scope = candidate.get("experiment_scope")
    signal_inputs = candidate.get("signal_inputs")
    scope = scope if isinstance(scope, dict) else {}
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    payload = {
        "strategy_type": scope.get("strategy_type"),
        "entry_rule": scope.get("entry_rule") or signal_inputs.get("entry_rule"),
        "exit_rule": scope.get("exit_rule") or signal_inputs.get("exit_rule"),
        "holding_period": scope.get("holding_period"),
        "rebalance_rule": scope.get("rebalance_rule") or signal_inputs.get("rebalance_rule"),
        "signal_calculation_window": signal_inputs.get("signal_calculation_window"),
        "signal_definition": signal_inputs.get("signal_definition"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def mark_generic_proxy_label(evidence: dict[str, Any]) -> None:
    evidence["label_use_status"] = GENERIC_PROXY_LABEL_STATUS
    evidence["supervised_label_eligible"] = False
    evidence.setdefault("known_limitations", [])
    if GENERIC_PROXY_LIMITATION not in evidence["known_limitations"]:
        evidence["known_limitations"].append(GENERIC_PROXY_LIMITATION)
    evidence.setdefault("review_notes", [])
    evidence["review_notes"].append(GENERIC_PROXY_REVIEW_NOTE)
    if isinstance(evidence.get("metric_summary"), dict):
        evidence["metric_summary"]["label_role"] = GENERIC_PROXY_LABEL_ROLE


def require_recorded_candidate_evidence(evidence: dict[str, Any]) -> None:
    valid_count = None
    metric_summary = evidence.get("metric_summary")
    if isinstance(metric_summary, dict):
        valid_count = metric_summary.get("valid_security_count")
    if evidence.get("status") != RECORDED_EVIDENCE_STATUS or not valid_count:
        raise ValueError(
            "momentum cohort actual run did not produce candidate-level metric_summary labels "
            f"for {evidence.get('candidate_id')}: status={evidence.get('status')}, "
            f"valid_security_count={valid_count}. Keep this candidate contract_only until "
            "approved price coverage and candidate-specific rules produce a valid run."
        )


def resolve_output_dir(output_dir: Path, *, project_root: Path) -> Path:
    boundary_probe = output_dir / "__boundary_probe__.md"
    return validate_evaluation_evidence_output_path(
        boundary_probe,
        project_root=project_root,
    ).parent


def write_manifest(
    evidence_records: list[dict[str, Any]],
    paths: list[Path],
    *,
    output_dir: Path,
    project_root: Path,
    cohort_id: str,
    prices_dir: Path,
    price_row_count: int,
) -> Path:
    root = project_root.resolve()
    resolved_output_dir = resolve_output_dir(output_dir, project_root=project_root)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = resolved_output_dir / "manifest.json"
    limitation_counts = Counter(
        str(flag)
        for record in evidence_records
        for flag in record.get("known_limitations", [])
    )
    label_use_status_counts = Counter(str(record.get("label_use_status") or "candidate_specific") for record in evidence_records)
    status_counts = Counter(str(record["status"]) for record in evidence_records)
    manifest_status = next(iter(status_counts)) if len(status_counts) == 1 else "mixed"
    manifest = {
        "schema_version": "v0_3_evaluation_evidence_cohort_manifest_0_2",
        "cohort_id": cohort_id,
        "status": manifest_status,
        "candidate_count": len(evidence_records),
        "evaluation_ids": [str(record["evaluation_id"]) for record in evidence_records],
        "candidate_ids": [str(record["candidate_id"]) for record in evidence_records],
        "evidence_status_counts": dict(sorted(status_counts.items())),
        "failure_flag_counts": dict(
            sorted(Counter(str(flag) for record in evidence_records for flag in record.get("failure_flags", [])).items())
        ),
        "known_limitation_counts": dict(sorted(limitation_counts.items())),
        "label_use_status_counts": dict(sorted(label_use_status_counts.items())),
        "required_evaluation_check_ids": sorted(
            str(check_id)
            for record in evidence_records[:1]
            for check_id in record.get("required_evaluation_checks", {})
        ),
        "price_input_ref": str(prices_dir),
        "price_row_count": price_row_count,
        "packet_paths": [
            str(path.resolve().relative_to(root)).replace("\\", "/")
            for path in paths
        ],
        "generated_output_boundary": "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
        "model_training_status": "not_run_metric_summary_generation_only",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def run_momentum_evaluation_evidence_cohort(
    *,
    registry: Path,
    prices_dir: Path,
    output_dir: Path,
    project_root: Path,
    cohort_id: str,
    created_at: str,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
    expected_count: int | None = None,
) -> dict[str, Any]:
    registry_rows = load_registry(registry)
    selected = select_momentum_evaluable_candidates(registry_rows)
    if expected_count is not None and len(selected) != expected_count:
        raise ValueError(f"expected {expected_count} momentum evaluable candidates, found {len(selected)}")

    price_frame = load_chart_daily_prices(prices_dir, price_glob=price_glob, max_date=max_date or created_at)
    candidate_rule_counts = Counter(
        candidate_rule_fingerprint(dict(strategy_candidate_payload(registry_record)))
        for registry_record in selected
    )
    resolved_output_dir = resolve_output_dir(output_dir, project_root=project_root)
    evidence_records: list[dict[str, Any]] = []
    paths: list[Path] = []
    for registry_record in selected:
        candidate = dict(strategy_candidate_payload(registry_record))
        candidate_max_date = effective_candidate_max_date(
            candidate,
            created_at=created_at,
            max_date=max_date,
        )
        candidate_price_frame = filter_prices_for_candidate(price_frame, candidate_max_date)
        evidence_result = run_v0_3_evaluation_evidence(
            registry_record,
            candidate_price_frame,
            ranking_config=ranking_config_from_candidate(candidate),
            backtest_config=backtest_config_from_candidate(candidate),
            created_at=created_at,
            source_refs=source_refs_for_run(registry, prices_dir),
        )
        evidence = evidence_result.to_dict()
        require_recorded_candidate_evidence(evidence)
        if candidate_rule_counts[candidate_rule_fingerprint(candidate)] > 1:
            mark_generic_proxy_label(evidence)
        packet_path = resolved_output_dir / f"{evidence['evaluation_id']}.md"
        paths.append(
            write_evaluation_evidence_markdown(
                evidence,
                packet_path,
                project_root=project_root,
            )
        )
        evidence_records.append(evidence)

    manifest_path = write_manifest(
        evidence_records,
        paths,
        output_dir=output_dir,
        project_root=project_root,
        cohort_id=cohort_id,
        prices_dir=prices_dir,
        price_row_count=len(price_frame),
    )
    return {
        "cohort_id": cohort_id,
        "candidate_count": len(evidence_records),
        "status_counts": dict(sorted(Counter(str(record["status"]) for record in evidence_records).items())),
        "manifest": str(manifest_path),
        "packet_paths": [str(path) for path in paths],
        "price_row_count": len(price_frame),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_momentum_evaluation_evidence_cohort(
        registry=args.registry,
        prices_dir=args.prices_dir,
        output_dir=args.output_dir,
        project_root=args.project_root,
        cohort_id=args.cohort_id,
        created_at=args.created_at,
        price_glob=args.price_glob,
        max_date=args.max_date,
        expected_count=args.expected_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
