"""Build v0.3 candidate-only selector inputs from research EvidenceCards.

The generated records are allowlisted summaries for review/evaluator use only.
They are not production ranking inputs, score inputs, runtime model features, or
automatic adoption triggers.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("Quant_mvp/research_mvp/data/research/evidence/evidence_cards.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/selector_inputs")
DEFAULT_JSONL_NAME = "v0_3_selector_input.jsonl"
DEFAULT_CSV_NAME = "v0_3_selector_input.csv"
DEFAULT_MANIFEST_NAME = "v0_3_selector_input_manifest.json"

SELECTOR_INPUT_DISCLAIMER = (
    "This selector input is candidate-only evidence metadata. It is not a "
    "production ranking input, not a final score input, not a runtime model "
    "feature source, not an adoption decision, and not proof of future "
    "profitability."
)

FORBIDDEN_SELECTOR_KEYS = {
    "technical_composite_score",
    "final_composite_score",
    "prob_up_1d_candidate",
    "rank",
    "ranking",
    "recommendation",
    "buy",
    "sell",
    "hold",
    "expected_return",
    "proven_alpha",
}

PAPER_CLAIM_LANGUAGE_PATTERNS = (
    "abnormal return",
    "abnormal returns",
    "alpha",
    "beat",
    "buy",
    "expected return",
    "expected returns",
    "guaranteed",
    "outperform",
    "outperformance",
    "profitable",
    "profitability",
    "sell",
    "strong performance",
    "trading strategy",
)

LIST_COLUMNS = {
    "source_adapters",
    "required_inputs",
    "unavailable_inputs",
    "data_compatibility",
    "risk_flags",
    "blocked_reasons",
}


def _get(payload: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compact_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _paper_claim_language_present(card: dict[str, Any]) -> bool:
    texts = [
        _get(card, "candidate_idea.idea_summary_en"),
        _get(card, "paper.title"),
        *_as_list(_get(card, "extraction.evidence_snippets_short")),
    ]
    joined = " ".join(str(text).lower() for text in texts if text)
    return any(pattern in joined for pattern in PAPER_CLAIM_LANGUAGE_PATTERNS)


def _risk_flags(card: dict[str, Any]) -> list[str]:
    risks = _get(card, "risks", {})
    if not isinstance(risks, dict):
        return []
    return sorted(key for key, value in risks.items() if key.endswith("_flag") and _as_bool(value))


def _blocked_reasons(card: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    branch = _get(card, "classification.research_branch")
    route = _get(card, "classification.downstream_route")
    candidate = _get(card, "candidate_idea", {})
    paper = _get(card, "paper", {})

    if _as_bool(_get(card, "classification.manual_review_required")):
        reasons.append("manual_review_required")
    if _as_bool(_get(candidate, "blocked_by_data")):
        reasons.append("blocked_by_data")
    if _as_bool(_get(candidate, "intraday_required")):
        reasons.append("intraday_required")
    if _as_bool(_get(candidate, "order_book_required")):
        reasons.append("order_book_required")
    if _as_bool(_get(candidate, "alternative_data_required")):
        reasons.append("alternative_data_required")
    if _as_bool(_get(candidate, "point_in_time_fundamentals_required")):
        reasons.append("point_in_time_fundamentals_required")
    if _get(paper, "is_retracted") is True:
        reasons.append("retracted_source")
    if branch == "valuation" or route == "valuation_agent_handoff":
        reasons.append("valuation_lane")
    if branch == "hybrid" or route == "hybrid_split_required":
        reasons.append("hybrid_split_required")
    if branch == "diagnostic" or route == "diagnostic_backlog":
        reasons.append("diagnostic_only")
    if branch == "out_of_scope" or route == "reject_log":
        reasons.append("out_of_scope_or_rejected")

    guardrail_violations = _as_list(_get(card, "classification.guardrail_violations"))
    reasons.extend(str(item) for item in guardrail_violations if item)
    return sorted(set(reasons))


def _ml_use_status(card: dict[str, Any], blocked_reasons: list[str]) -> str:
    branch = _get(card, "classification.research_branch")
    route = _get(card, "classification.downstream_route")
    required_inputs = set(str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs")))

    if "out_of_scope_or_rejected" in blocked_reasons:
        return "excluded_rejected_or_out_of_scope"
    if "valuation_lane" in blocked_reasons:
        return "excluded_valuation_lane"
    if "hybrid_split_required" in blocked_reasons:
        return "needs_hybrid_split"
    if "diagnostic_only" in blocked_reasons:
        return "diagnostic_context_only"
    if blocked_reasons:
        return "needs_manual_or_data_review"
    if branch == "technical" and route == "technical_score_architect" and "daily_ohlcv" in required_inputs:
        return "eligible_for_candidate_selector_review"
    if branch == "technical":
        return "technical_candidate_needs_scope_review"
    return "needs_route_review"


def evidence_card_to_selector_record(card: dict[str, Any]) -> dict[str, Any]:
    """Convert one EvidenceCard into an allowlisted v0.3 selector input row."""

    blocked_reasons = _blocked_reasons(card)
    record = {
        "schema_version": "v0_3_selector_input_0_1",
        "selector_input_boundary": SELECTOR_INPUT_DISCLAIMER,
        "ml_use_status": _ml_use_status(card, blocked_reasons),
        "evidence_card_id": _get(card, "evidence_card_id"),
        "parent_evidence_card_id": _get(card, "parent_evidence_card_id"),
        "source_run_id": _get(card, "source_run_id"),
        "canonical_paper_id": _get(card, "paper.canonical_paper_id"),
        "doi": _get(card, "paper.doi"),
        "arxiv_id": _get(card, "paper.arxiv_id"),
        "paper_title": _compact_text(_get(card, "paper.title"), limit=300),
        "publication_year": _get(card, "paper.publication_year"),
        "publication_date": _get(card, "paper.publication_date"),
        "venue": _compact_text(_get(card, "paper.venue"), limit=160),
        "source_adapters": _as_list(_get(card, "paper.source_adapters")),
        "oa_status": _get(card, "paper.oa_status"),
        "license_status": _get(card, "paper.license"),
        "is_retracted": _get(card, "paper.is_retracted"),
        "research_branch": _get(card, "classification.research_branch"),
        "downstream_route": _get(card, "classification.downstream_route"),
        "main_score_branch_candidate": _get(card, "classification.main_score_branch_candidate"),
        "classification_confidence": _get(card, "classification.classification_confidence"),
        "manual_review_required": _as_bool(_get(card, "classification.manual_review_required")),
        "candidate_name": _compact_text(_get(card, "candidate_idea.candidate_name"), limit=240),
        "idea_summary_ko": _compact_text(_get(card, "candidate_idea.idea_summary_ko"), limit=500),
        "paper_claim_language_present": _paper_claim_language_present(card),
        "signal_family_candidate": _get(card, "candidate_idea.signal_family_candidate"),
        "formula_clarity": _get(card, "candidate_idea.formula_clarity"),
        "implementation_readiness": _get(card, "candidate_idea.implementation_readiness"),
        "required_inputs": _as_list(_get(card, "candidate_idea.required_inputs")),
        "unavailable_inputs": _as_list(_get(card, "candidate_idea.unavailable_inputs")),
        "data_compatibility": _as_list(_get(card, "candidate_idea.data_compatibility")),
        "blocked_by_data": _as_bool(_get(card, "candidate_idea.blocked_by_data")),
        "point_in_time_fundamentals_required": _as_bool(
            _get(card, "candidate_idea.point_in_time_fundamentals_required")
        ),
        "intraday_required": _as_bool(_get(card, "candidate_idea.intraday_required")),
        "order_book_required": _as_bool(_get(card, "candidate_idea.order_book_required")),
        "alternative_data_required": _as_bool(_get(card, "candidate_idea.alternative_data_required")),
        "valuation_status": _get(card, "valuation_boundary.valuation_status"),
        "valuation_agent_required": _as_bool(_get(card, "valuation_boundary.valuation_agent_required")),
        "evidence_status": _get(card, "extraction.evidence_status"),
        "extraction_scope": _get(card, "extraction.extraction_scope"),
        "abstract_available": _as_bool(_get(card, "extraction.abstract_available")),
        "fulltext_used": _as_bool(_get(card, "extraction.fulltext_used")),
        "pdf_downloaded": _as_bool(_get(card, "extraction.pdf_downloaded")),
        "paper_reported_backtest_present": _as_bool(
            _get(card, "backtest_context.paper_reported_backtest_present")
        ),
        "reproducibility_level": _get(card, "backtest_context.reproducibility_level"),
        "transaction_costs_discussed": _as_bool(_get(card, "backtest_context.transaction_costs_discussed")),
        "lookahead_bias_discussed": _as_bool(_get(card, "backtest_context.lookahead_bias_discussed")),
        "survivorship_bias_discussed": _as_bool(_get(card, "backtest_context.survivorship_bias_discussed")),
        "risk_flags": _risk_flags(card),
        "blocked_reasons": blocked_reasons,
        "paper_claim_not_verified": _as_bool(_get(card, "guardrails.paper_claim_not_verified")),
        "no_score_adopted": _as_bool(_get(card, "guardrails.no_score_adopted")),
        "no_backtest_performed": _as_bool(_get(card, "guardrails.no_backtest_performed")),
        "valuation_not_inferred_from_price": _as_bool(
            _get(card, "guardrails.valuation_not_inferred_from_price")
        ),
        "no_feedback_check": "must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    validate_selector_record(record)
    return record


def validate_selector_record(record: dict[str, Any]) -> None:
    serialized_keys = {str(key).lower() for key in record}
    forbidden = sorted(serialized_keys & FORBIDDEN_SELECTOR_KEYS)
    if forbidden:
        raise ValueError(f"forbidden selector keys present: {forbidden}")
    if record.get("paper_claim_not_verified") is not True:
        raise ValueError("paper_claim_not_verified must remain true")
    if record.get("no_score_adopted") is not True:
        raise ValueError("no_score_adopted must remain true")
    if record.get("no_backtest_performed") is not True:
        raise ValueError("no_backtest_performed must remain true")
    if record.get("valuation_not_inferred_from_price") is not True:
        raise ValueError("valuation_not_inferred_from_price must remain true")
    if "production ranking" not in str(record.get("selector_input_boundary", "")):
        raise ValueError("selector boundary disclaimer is missing")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(payload)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


def build_manifest(records: list[dict[str, Any]], *, source_path: Path, run_id: str) -> dict[str, Any]:
    status_counts = Counter(str(record.get("ml_use_status")) for record in records)
    branch_counts = Counter(str(record.get("research_branch")) for record in records)
    route_counts = Counter(str(record.get("downstream_route")) for record in records)
    return {
        "schema_version": "v0_3_selector_input_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "ml_use_status_counts": dict(sorted(status_counts.items())),
        "research_branch_counts": dict(sorted(branch_counts.items())),
        "downstream_route_counts": dict(sorted(route_counts.items())),
        "selector_input_boundary": SELECTOR_INPUT_DISCLAIMER,
        "no_feedback_check": "selector_inputs_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_selector_inputs(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    cards = read_jsonl(input_path)
    records = [evidence_card_to_selector_record(card) for card in cards]
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    write_jsonl(jsonl_path, records)

    manifest = build_manifest(records, source_path=input_path, run_id=run_id)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    paths = {"jsonl": jsonl_path, "manifest": manifest_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        write_csv(csv_path, records)
        paths["csv"] = csv_path
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("selector_input_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_selector_inputs(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
