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
DEFAULT_FEEDBACK_JSONL_NAME = "v0_3_research_feedback_queue.jsonl"
DEFAULT_FEEDBACK_CSV_NAME = "v0_3_research_feedback_queue.csv"
DEFAULT_FEEDBACK_MANIFEST_NAME = "v0_3_research_feedback_manifest.json"

SELECTOR_INPUT_DISCLAIMER = (
    "This selector input is candidate-only evidence metadata. It is not a "
    "production ranking input, not a final score input, not a runtime model "
    "feature source, not an adoption decision, and not proof of future "
    "outcomes."
)

FEEDBACK_QUEUE_DISCLAIMER = (
    "This feedback queue is research-collection guidance only. It does not run "
    "external collection, does not expand market data ingestion, does not feed "
    "production scores or rankings, and does not authorize adoption."
)

FORBIDDEN_SELECTOR_KEYS = {
    "technical_composite_score",
    "final_composite_score",
    "prob_up_1d_candidate",
    "rank",
    "ranking",
    "paper_title",
    "candidate_name",
    "idea_summary_ko",
    "idea_summary_en",
    "evidence_snippets_short",
    "source_urls",
}

LIST_COLUMNS = {
    "source_adapters",
    "required_inputs",
    "unavailable_inputs",
    "data_compatibility",
    "risk_flags",
    "blocked_reasons",
    "collection_reasons",
    "suggested_collection_actions",
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


def _source_reference_id(card: dict[str, Any]) -> Any:
    return (
        _get(card, "paper.canonical_paper_id")
        or _get(card, "paper.doi")
        or _get(card, "paper.arxiv_id")
        or _get(card, "evidence_card_id")
    )


def _neutral_mechanism_summary(card: dict[str, Any]) -> str:
    family = _get(card, "candidate_idea.signal_family_candidate") or "unspecified"
    branch = _get(card, "classification.research_branch") or "needs_route_review"
    route = _get(card, "classification.downstream_route") or "needs_route_review"
    inputs = _as_list(_get(card, "candidate_idea.required_inputs"))
    input_text = ", ".join(str(item) for item in inputs) if inputs else "required_inputs_not_specified"
    return (
        f"mechanism_metadata: branch={branch}; route={route}; "
        f"signal_family={family}; required_inputs={input_text}"
    )


def _paper_claim_language_present(card: dict[str, Any]) -> bool:
    source_texts = [
        _get(card, "paper.title"),
        _get(card, "candidate_idea.candidate_name"),
        _get(card, "candidate_idea.idea_summary_ko"),
        _get(card, "candidate_idea.idea_summary_en"),
        *_as_list(_get(card, "extraction.evidence_snippets_short")),
    ]
    return any(bool(str(text).strip()) for text in source_texts if text is not None)


def _korea_relevance(card: dict[str, Any]) -> bool:
    texts = [
        _get(card, "paper.title"),
        _get(card, "source.source_query_set"),
        *_as_list(_get(card, "classification.source_query_sets")),
    ]
    joined = " ".join(str(text).lower() for text in texts if text)
    return any(token in joined for token in ("korea", "korean", "kospi", "south korea"))


def _risk_flags(card: dict[str, Any]) -> list[str]:
    risks = _get(card, "risks", {})
    if not isinstance(risks, dict):
        return []
    if _as_bool(risks.get("project_internal_risk_readable")) is not True:
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


def _importance_score(card: dict[str, Any], ml_use_status: str, blocked_reasons: list[str]) -> int:
    if ml_use_status.startswith("excluded_"):
        return 0
    if "valuation_lane" in blocked_reasons or "out_of_scope_or_rejected" in blocked_reasons:
        return 0

    score = 0
    branch = _get(card, "classification.research_branch")
    route = _get(card, "classification.downstream_route")
    required_inputs = set(str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs")))
    readiness = _get(card, "candidate_idea.implementation_readiness", 0)
    try:
        readiness_int = int(readiness)
    except (TypeError, ValueError):
        readiness_int = 0

    if ml_use_status == "eligible_for_candidate_selector_review":
        score += 35
    if branch == "technical" and route == "technical_score_architect":
        score += 15
    if "daily_ohlcv" in required_inputs:
        score += 10
    score += min(max(readiness_int, 0), 3) * 8

    formula_clarity = _get(card, "candidate_idea.formula_clarity")
    if formula_clarity == "exact":
        score += 15
    elif formula_clarity == "partial":
        score += 8

    confidence = _get(card, "classification.classification_confidence")
    if confidence == "high":
        score += 10
    elif confidence == "medium":
        score += 5

    evidence_status = _get(card, "extraction.evidence_status")
    if evidence_status == "open_access_fulltext_supported":
        score += 10
    elif evidence_status == "abstract_supported":
        score += 5

    if _korea_relevance(card):
        score += 8

    if blocked_reasons:
        score -= min(len(blocked_reasons) * 5, 20)
    return max(min(score, 100), 0)


def _importance_bucket(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 55:
        return "medium"
    if score > 0:
        return "low"
    return "not_collectable"


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
    ml_use_status = _ml_use_status(card, blocked_reasons)
    importance_score = _importance_score(card, ml_use_status, blocked_reasons)
    record = {
        "schema_version": "v0_3_selector_input_0_1",
        "selector_input_boundary": SELECTOR_INPUT_DISCLAIMER,
        "ml_use_status": ml_use_status,
        "importance_score": importance_score,
        "importance_bucket": _importance_bucket(importance_score),
        "evidence_card_id": _get(card, "evidence_card_id"),
        "parent_evidence_card_id": _get(card, "parent_evidence_card_id"),
        "source_run_id": _get(card, "source_run_id"),
        "source_reference_id": _source_reference_id(card),
        "canonical_paper_id": _get(card, "paper.canonical_paper_id"),
        "doi": _get(card, "paper.doi"),
        "arxiv_id": _get(card, "paper.arxiv_id"),
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
        "neutral_mechanism_summary": _neutral_mechanism_summary(card),
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


def _collection_reasons(selector_record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if selector_record.get("importance_bucket") != "high":
        return reasons
    if selector_record.get("evidence_status") in {"metadata_only", "abstract_supported", "paper_claim_only"}:
        reasons.append("evidence_depth_needs_review")
    if selector_record.get("formula_clarity") in {None, "partial", "vague", "not_specified"}:
        reasons.append("formula_details_need_collection")
    if selector_record.get("license_status") in {None, "", "unknown"}:
        reasons.append("license_status_needs_review")
    if selector_record.get("transaction_costs_discussed") is not True:
        reasons.append("transaction_cost_context_needed")
    if selector_record.get("survivorship_bias_discussed") is not True:
        reasons.append("survivorship_bias_context_needed")
    return reasons


def _suggested_collection_actions(collection_reasons: list[str]) -> list[str]:
    actions: list[str] = []
    if "formula_details_need_collection" in collection_reasons:
        actions.append("collect_formula_or_rule_details_from_approved_metadata_or_license_review")
    if "license_status_needs_review" in collection_reasons:
        actions.append("review_source_license_before_fulltext_or_pdf_use")
    if "evidence_depth_needs_review" in collection_reasons:
        actions.append("refresh_approved_metadata_sources_for_related_records")
    if {
        "transaction_cost_context_needed",
        "survivorship_bias_context_needed",
    } & set(collection_reasons):
        actions.append("collect_diagnostic_context_for_cost_bias_and_robustness_review")
    return actions


def selector_record_to_feedback_record(selector_record: dict[str, Any]) -> dict[str, Any] | None:
    """Create a research follow-up queue item for high-priority candidates."""

    collection_reasons = _collection_reasons(selector_record)
    if not collection_reasons:
        return None
    record = {
        "schema_version": "v0_3_research_feedback_0_1",
        "feedback_boundary": FEEDBACK_QUEUE_DISCLAIMER,
        "feedback_id": f"rfq:{selector_record.get('evidence_card_id')}",
        "feedback_status": "research_collection_requested",
        "evidence_card_id": selector_record.get("evidence_card_id"),
        "canonical_paper_id": selector_record.get("canonical_paper_id"),
        "source_reference_id": selector_record.get("source_reference_id"),
        "ml_use_status": selector_record.get("ml_use_status"),
        "importance_score": selector_record.get("importance_score"),
        "importance_bucket": selector_record.get("importance_bucket"),
        "research_branch": selector_record.get("research_branch"),
        "downstream_route": selector_record.get("downstream_route"),
        "signal_family_candidate": selector_record.get("signal_family_candidate"),
        "formula_clarity": selector_record.get("formula_clarity"),
        "evidence_status": selector_record.get("evidence_status"),
        "license_status": selector_record.get("license_status"),
        "paper_claim_language_present": selector_record.get("paper_claim_language_present"),
        "collection_reasons": collection_reasons,
        "suggested_collection_actions": _suggested_collection_actions(collection_reasons),
        "allowed_collection_scope": "approved_research_metadata_and_license_review_only",
        "blocked_collection_scope": "no_market_data_ingestion_no_production_features",
        "no_feedback_check": "collection_feedback_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
    }
    validate_feedback_record(record)
    return record


def validate_feedback_record(record: dict[str, Any]) -> None:
    serialized_keys = {str(key).lower() for key in record}
    forbidden = sorted(serialized_keys & FORBIDDEN_SELECTOR_KEYS)
    if forbidden:
        raise ValueError(f"forbidden feedback keys present: {forbidden}")
    if record.get("importance_bucket") != "high":
        raise ValueError("feedback queue may include only high importance records")
    if not record.get("collection_reasons"):
        raise ValueError("feedback record requires collection_reasons")
    if not record.get("suggested_collection_actions"):
        raise ValueError("feedback record requires suggested_collection_actions")
    if "research-collection guidance only" not in str(record.get("feedback_boundary", "")):
        raise ValueError("feedback boundary disclaimer is missing")
    if "no_market_data_ingestion" not in str(record.get("blocked_collection_scope", "")):
        raise ValueError("feedback record must block market data ingestion")


def validate_selector_record(record: dict[str, Any]) -> None:
    serialized_keys = {str(key).lower() for key in record}
    forbidden = sorted(serialized_keys & FORBIDDEN_SELECTOR_KEYS)
    if forbidden:
        raise ValueError(f"forbidden selector keys present: {forbidden}")
    if not record.get("neutral_mechanism_summary"):
        raise ValueError("neutral_mechanism_summary is required")
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
    importance_counts = Counter(str(record.get("importance_bucket")) for record in records)
    branch_counts = Counter(str(record.get("research_branch")) for record in records)
    route_counts = Counter(str(record.get("downstream_route")) for record in records)
    return {
        "schema_version": "v0_3_selector_input_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "ml_use_status_counts": dict(sorted(status_counts.items())),
        "importance_bucket_counts": dict(sorted(importance_counts.items())),
        "research_branch_counts": dict(sorted(branch_counts.items())),
        "downstream_route_counts": dict(sorted(route_counts.items())),
        "selector_input_boundary": SELECTOR_INPUT_DISCLAIMER,
        "no_feedback_check": "selector_inputs_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_feedback_manifest(records: list[dict[str, Any]], *, source_path: Path, run_id: str) -> dict[str, Any]:
    reason_counts = Counter(
        reason
        for record in records
        for reason in _as_list(record.get("collection_reasons"))
    )
    return {
        "schema_version": "v0_3_research_feedback_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "collection_reason_counts": dict(sorted(reason_counts.items())),
        "feedback_boundary": FEEDBACK_QUEUE_DISCLAIMER,
        "no_feedback_check": "collection_feedback_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "blocked_collection_scope": "no_market_data_ingestion_no_production_features",
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
    feedback_records = [
        feedback_record
        for record in records
        if (feedback_record := selector_record_to_feedback_record(record)) is not None
    ]
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    feedback_jsonl_path = output_dir / DEFAULT_FEEDBACK_JSONL_NAME
    feedback_manifest_path = output_dir / DEFAULT_FEEDBACK_MANIFEST_NAME
    write_jsonl(jsonl_path, records)
    write_jsonl(feedback_jsonl_path, feedback_records)

    manifest = build_manifest(records, source_path=input_path, run_id=run_id)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    feedback_manifest = build_feedback_manifest(feedback_records, source_path=input_path, run_id=run_id)
    feedback_manifest_path.write_text(
        json.dumps(feedback_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    paths = {
        "jsonl": jsonl_path,
        "manifest": manifest_path,
        "feedback_jsonl": feedback_jsonl_path,
        "feedback_manifest": feedback_manifest_path,
    }
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        feedback_csv_path = output_dir / DEFAULT_FEEDBACK_CSV_NAME
        write_csv(csv_path, records)
        write_csv(feedback_csv_path, feedback_records)
        paths["csv"] = csv_path
        paths["feedback_csv"] = feedback_csv_path
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
