"""Build v0.3 selector label dry-run summaries.

The script reads StrategyCandidate registry rows and EvaluationEvidence
markdown packets, then derives nullable selector labels from approved
metric_summary evidence only. It does not write outputs in dry-run mode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    import tomli as tomllib  # type: ignore[no-redef]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_REGISTRY = Path("Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_registry.jsonl")
DEFAULT_EVIDENCE_DIR = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence")
DEFAULT_RULES = Path("Quant_mvp/config/v0_3_selector_label_rules.toml")

LABEL_SCHEMA_VERSION = "v0_3_selector_label_0_1"
NULL_LABEL = None


def _get(payload: dict[str, Any] | None, path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compact_list(value: Any) -> list[str]:
    return sorted(str(item) for item in _as_list(value) if item is not None and str(item) != "")


def _load_rules(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        rules = tomllib.load(handle)
    if rules.get("schema_version") != "v0_3_selector_label_rules_0_1":
        raise ValueError(f"unsupported selector label rules schema_version: {rules.get('schema_version')}")
    rules["_rules_path"] = str(path)
    return rules


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            rows.append(payload)
    return rows


def _parse_json_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"{path} does not contain a json fenced block")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} json fenced block must contain an object")
    payload["_source_path"] = str(path)
    return payload


def read_evaluation_evidence(evidence_dir: Path) -> list[dict[str, Any]]:
    if not evidence_dir.exists():
        return []
    return [_parse_json_markdown(path) for path in sorted(evidence_dir.rglob("ee_v0_3_*.md"))]


def _evidence_sort_key(evidence: dict[str, Any]) -> tuple[int, str, str]:
    status_priority = 1 if evidence.get("status") == "evidence_recorded" else 0
    timestamp = str(evidence.get("updated_at") or evidence.get("created_at") or "")
    return (status_priority, timestamp, str(evidence.get("evaluation_id") or ""))


def evidence_index_by_candidate(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for evidence in records:
        candidate_id = evidence.get("candidate_id")
        if candidate_id:
            grouped.setdefault(str(candidate_id), []).append(evidence)
    return {
        candidate_id: sorted(items, key=_evidence_sort_key, reverse=True)[0]
        for candidate_id, items in grouped.items()
    }


def _first_path(payload: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        value = _get(payload, path)
        if value is not None:
            return value
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_payload(registry_record: dict[str, Any]) -> dict[str, Any]:
    candidate = registry_record.get("strategy_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("registry record missing strategy_candidate object")
    return candidate


def _candidate_id(registry_record: dict[str, Any]) -> str:
    candidate_id = _candidate_payload(registry_record).get("candidate_id")
    if not candidate_id:
        raise ValueError("strategy_candidate.candidate_id is required")
    return str(candidate_id)


def _candidate_version(registry_record: dict[str, Any]) -> Any:
    candidate = _candidate_payload(registry_record)
    return candidate.get("candidate_version") or candidate.get("version")


def _hypothesis_id(registry_record: dict[str, Any]) -> Any:
    candidate = _candidate_payload(registry_record)
    return (
        candidate.get("linked_strategy_hypothesis_id")
        or candidate.get("hypothesis_id")
        or _get(registry_record, "linked_strategy_hypothesis.strategy_hypothesis_id")
    )


def _null_label_row(
    registry_record: dict[str, Any],
    evidence: dict[str, Any] | None,
    *,
    rules: dict[str, Any],
    reason: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _base_label_row(registry_record, evidence, rules=rules) | {
        "label_pass_minimum_gate": NULL_LABEL,
        "label_review_preferred": NULL_LABEL,
        "label_source": None,
        "label_null_reason": reason,
        "label_detail": details or {},
    }


def _base_label_row(
    registry_record: dict[str, Any],
    evidence: dict[str, Any] | None,
    *,
    rules: dict[str, Any],
) -> dict[str, Any]:
    candidate = _candidate_payload(registry_record)
    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "rule_version": rules.get("rule_version"),
        "rule_config_ref": str(rules.get("_rules_path") or DEFAULT_RULES),
        "candidate_id": _candidate_id(registry_record),
        "candidate_version": _candidate_version(registry_record),
        "hypothesis_id": _hypothesis_id(registry_record),
        "candidate_status": candidate.get("status"),
        "evaluation_id": evidence.get("evaluation_id") if evidence else None,
        "evaluation_status": evidence.get("status") if evidence else "missing_evaluation_evidence",
        "evaluation_evidence_ref": evidence.get("_source_path") if evidence else None,
        "evaluation_failure_flags": _compact_list(evidence.get("failure_flags") if evidence else []),
        "actual_metric_summary_available": isinstance(evidence.get("metric_summary"), dict) if evidence else False,
    }


def _return_vs_benchmark_pass(evidence: dict[str, Any], rule: dict[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    total_return = _to_float(_get(evidence, str(rule["total_return_path"])))
    if total_return is None:
        return (None, {"reason": "total_return_missing"})
    benchmark = _to_float(_first_path(evidence, list(rule.get("benchmark_return_paths", []))))
    if benchmark is not None:
        return (total_return > benchmark, {"total_return": total_return, "benchmark_return": benchmark})
    relative_return = _to_float(_first_path(evidence, list(rule.get("benchmark_relative_return_paths", []))))
    if relative_return is None:
        return (None, {"reason": "benchmark_return_missing"})
    minimum_relative = float(rule.get("minimum_relative_return", 0.0))
    return (relative_return > minimum_relative, {"total_return": total_return, "benchmark_relative_return": relative_return})


def _minimum_metric_pass(evidence: dict[str, Any], rule: dict[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    value = _to_float(_first_path(evidence, list(rule.get("paths", []))))
    if value is None:
        return (None, {"reason": "metric_missing", "paths": list(rule.get("paths", []))})
    minimum = float(rule["minimum"])
    return (value >= minimum, {"value": value, "minimum": minimum})


def _safety_result(evidence: dict[str, Any], rules: dict[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    safety = rules["safety_rules"]
    failure_flags = set(_compact_list(evidence.get("failure_flags")))
    blocking_flags = sorted(failure_flags & set(_compact_list(safety.get("blocking_failure_flags"))))
    if blocking_flags:
        return (False, {"blocking_failure_flags": blocking_flags})
    values = [str(_get(evidence, path) or "") for path in safety.get("no_lookahead_paths", [])]
    failures = set(_compact_list(safety.get("no_lookahead_failure_statuses")))
    lowered_values = [value.lower() for value in values if value]
    if any(value in failures for value in lowered_values):
        return (False, {"no_lookahead_failure": lowered_values})
    if safety.get("missing_no_lookahead_check_is_null") and not lowered_values:
        return (None, {"reason": "no_lookahead_check_missing"})
    return (True, {"no_lookahead_values": values})


def _oos_result(evidence: dict[str, Any], rules: dict[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    rule = rules["oos_rule"]
    raw_status = _first_path(evidence, list(rule.get("paths", [])))
    status = str(raw_status or "").lower()
    if not status and rule.get("missing_is_null"):
        return (None, {"reason": "oos_status_missing"})
    if status in set(_compact_list(rule.get("passing_statuses"))):
        return (True, {"status": status})
    if status in set(_compact_list(rule.get("failing_statuses"))):
        return (False, {"status": status})
    if status in set(_compact_list(rule.get("null_statuses"))):
        return (None, {"status": status or "missing"})
    return (None, {"status": status, "reason": "oos_status_not_recognized"})


def build_label_row(
    registry_record: dict[str, Any],
    evidence: dict[str, Any] | None,
    *,
    rules: dict[str, Any],
) -> dict[str, Any]:
    eligibility = rules["eligibility"]
    if evidence is None:
        return _null_label_row(registry_record, evidence, rules=rules, reason="missing_evaluation_evidence")

    evidence_status = str(evidence.get("status") or "")
    if evidence_status in set(_compact_list(eligibility.get("null_evidence_statuses"))):
        return _null_label_row(
            registry_record,
            evidence,
            rules=rules,
            reason=f"evaluation_status_not_label_eligible:{evidence_status}",
        )
    if evidence_status != str(eligibility["required_evidence_status"]):
        return _null_label_row(
            registry_record,
            evidence,
            rules=rules,
            reason=f"evaluation_status_not_label_eligible:{evidence_status}",
        )
    failure_flags = set(_compact_list(evidence.get("failure_flags")))
    null_flags = sorted(failure_flags & set(_compact_list(eligibility.get("null_failure_flags"))))
    if null_flags:
        return _null_label_row(
            registry_record,
            evidence,
            rules=rules,
            reason="evaluation_failure_flag_requires_null",
            details={"null_failure_flags": null_flags},
        )
    if not isinstance(evidence.get("metric_summary"), dict):
        return _null_label_row(registry_record, evidence, rules=rules, reason="metric_summary_missing")

    metric_rules = rules["metric_rules"]
    conditions: dict[str, Any] = {}
    total_pass, total_detail = _return_vs_benchmark_pass(evidence, metric_rules["total_return_vs_benchmark"])
    sharpe_pass, sharpe_detail = _minimum_metric_pass(evidence, metric_rules["sharpe"])
    drawdown_pass, drawdown_detail = _minimum_metric_pass(evidence, metric_rules["max_drawdown"])
    safety_pass, safety_detail = _safety_result(evidence, rules)
    oos_pass, oos_detail = _oos_result(evidence, rules)
    conditions["total_return_vs_benchmark"] = {"passed": total_pass, **total_detail}
    conditions["sharpe"] = {"passed": sharpe_pass, **sharpe_detail}
    conditions["max_drawdown"] = {"passed": drawdown_pass, **drawdown_detail}
    conditions["safety"] = {"passed": safety_pass, **safety_detail}
    conditions["oos"] = {"passed": oos_pass, **oos_detail}

    minimum_conditions = [total_pass, sharpe_pass, drawdown_pass, safety_pass]
    if any(value is False for value in minimum_conditions):
        minimum_label: int | None = 0
    elif any(value is None for value in minimum_conditions):
        minimum_label = None
    else:
        minimum_label = 1

    if minimum_label == 0 or oos_pass is False:
        review_label: int | None = 0
    elif minimum_label == 1 and oos_pass is True:
        review_label = 1
    else:
        review_label = None

    null_reasons = []
    if minimum_label is None:
        null_reasons.append("minimum_gate_evidence_insufficient")
    if review_label is None:
        null_reasons.append("review_preferred_evidence_insufficient")
    return _base_label_row(registry_record, evidence, rules=rules) | {
        "label_pass_minimum_gate": minimum_label,
        "label_review_preferred": review_label,
        "label_source": eligibility.get("label_source") if minimum_label is not None or review_label is not None else None,
        "label_null_reason": "|".join(null_reasons) if null_reasons else None,
        "label_detail": conditions,
    }


def build_selector_label_rows(
    registry: Path,
    evidence_dir: Path,
    rules_path: Path,
) -> list[dict[str, Any]]:
    rules = _load_rules(rules_path)
    registry_rows = read_jsonl(registry)
    evidence_by_candidate = evidence_index_by_candidate(read_evaluation_evidence(evidence_dir))
    return [
        build_label_row(row, evidence_by_candidate.get(_candidate_id(row)), rules=rules)
        for row in sorted(registry_rows, key=_candidate_id)
    ]


def _label_counter(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter = Counter("null" if row.get(field) is None else str(row.get(field)) for row in rows)
    return dict(sorted(counter.items()))


def build_dry_run_summary(
    rows: list[dict[str, Any]],
    *,
    registry: Path,
    evidence_dir: Path,
    rules_path: Path,
    include_rows: bool = False,
) -> dict[str, Any]:
    review_counts = _label_counter(rows, "label_review_preferred")
    minimum_counts = _label_counter(rows, "label_pass_minimum_gate")
    result: dict[str, Any] = {
        "mode": "dry_run",
        "output_written": False,
        "schema_version": "v0_3_selector_label_dry_run_0_1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "registry_ref": str(registry),
        "evaluation_evidence_dir": str(evidence_dir),
        "rule_config_ref": str(rules_path),
        "candidate_count": len(rows),
        "label_pass_minimum_gate_counts": minimum_counts,
        "label_review_preferred_counts": review_counts,
        "label_possible_count": sum(row.get("label_review_preferred") is not None for row in rows),
        "label_unavailable_count": sum(row.get("label_review_preferred") is None for row in rows),
        "evaluation_status_counts": dict(sorted(Counter(str(row.get("evaluation_status")) for row in rows).items())),
        "evidence_failure_flag_counts": dict(
            sorted(Counter(flag for row in rows for flag in row.get("evaluation_failure_flags", [])).items())
        ),
        "metric_summary_available_count": sum(row.get("actual_metric_summary_available") is True for row in rows),
        "null_reason_counts": dict(
            sorted(Counter(str(row.get("label_null_reason")) for row in rows if row.get("label_null_reason")).items())
        ),
        "no_feedback_check": "selector labels are evidence-only and must not feed runtime scores, rankings, reports, backtests, trading, or auto adoption",
        "activation_boundary": "production activation requires a later root-approved gate",
    }
    if include_rows:
        result["rows"] = rows
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print a summary without writing outputs.")
    parser.add_argument("--include-rows", action="store_true", help="Include per-candidate label rows in dry-run output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        raise SystemExit("--dry-run is required; this entrypoint does not write label artifacts yet")
    rows = build_selector_label_rows(args.registry, args.evidence_dir, args.rules)
    print(
        json.dumps(
            build_dry_run_summary(
                rows,
                registry=args.registry,
                evidence_dir=args.evidence_dir,
                rules_path=args.rules,
                include_rows=args.include_rows,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
