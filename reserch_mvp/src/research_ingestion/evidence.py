from __future__ import annotations

from typing import Any
import hashlib
import re


EVIDENCE_REQUIRED_TOP_LEVEL = [
    "evidence_card_id",
    "source_run_id",
    "source",
    "paper",
    "extraction",
    "classification",
    "candidate_idea",
    "backtest_context",
    "risks",
    "guardrails",
]


def generate_evidence_card(
    paper: dict[str, Any],
    classification: dict[str, Any],
    source_run_id: str,
    parent_evidence_card_id: str | None = None,
) -> dict[str, Any]:
    candidate = classification.get("candidate_idea", {})
    branch = classification["research_branch"]
    abstract = paper.get("abstract")
    card = {
        "evidence_card_id": _evidence_id(source_run_id, paper["canonical_paper_id"], parent_evidence_card_id),
        "parent_evidence_card_id": parent_evidence_card_id,
        "source_run_id": source_run_id,
        "source": _build_source_section(paper, source_run_id),
        "paper": _build_paper_section(paper),
        "extraction": _build_extraction_section(paper, abstract),
        "classification": _build_classification_section(paper, classification, branch),
        "candidate_idea": _build_candidate_idea_section(paper, candidate, branch),
        "valuation_boundary": _build_valuation_boundary_section(branch),
        "risks": _build_risks_section(candidate, branch),
        "backtest_context": _build_backtest_context_section(paper, classification, candidate),
        "guardrails": _build_guardrails_section(),
    }
    if paper.get("is_retracted") is True:
        _mark_retracted_card(card)
    validate_evidence_card(card)
    return card


def _build_source_section(paper: dict[str, Any], source_run_id: str) -> dict[str, Any]:
    return {
        "source_adapter": paper.get("source_adapter") or next(iter(paper.get("source_adapters", [])), None),
        "source_record_id": paper.get("source_record_id"),
        "source_query_set": paper.get("source_query_set") or paper.get("research_query_set"),
        "query_run_id": paper.get("query_run_id") or source_run_id,
        "retrieved_at": paper.get("retrieved_at") or paper.get("collected_at_utc"),
        "seed_origin_type": paper.get("seed_origin_type", "metadata_api"),
        "seed_origin_is_evidence": False,
        "canonical_resolution_status": paper.get("canonical_resolution_status", "resolved"),
        "resolution_confidence": paper.get("resolution_confidence", "medium"),
        "dedup_key": paper.get("dedup_key") or paper.get("canonical_paper_id"),
        "duplicate_of": paper.get("duplicate_of"),
        "metadata_license": paper.get("metadata_license") or paper.get("license"),
        "citation_count_metadata_only": True,
    }


def _build_paper_section(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_paper_id": paper["canonical_paper_id"],
        "doi": paper.get("doi"),
        "arxiv_id": paper.get("arxiv_id"),
        "openalex_id": paper.get("openalex_id"),
        "semantic_scholar_id": paper.get("semantic_scholar_id"),
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "publication_year": paper.get("publication_year"),
        "publication_date": paper.get("publication_date"),
        "venue": paper.get("venue"),
        "source_adapters": paper.get("source_adapters", []),
        "source_urls": paper.get("source_urls", []),
        "oa_status": paper.get("oa_status"),
        "license": paper.get("license"),
        "is_retracted": paper.get("is_retracted"),
    }


def _build_extraction_section(paper: dict[str, Any], abstract: str | None) -> dict[str, Any]:
    return {
        "extraction_scope": "abstract_only" if abstract else "metadata_only",
        "evidence_status": "abstract_supported" if abstract else "metadata_only",
        "abstract_available": bool(abstract),
        "fulltext_available": bool(paper.get("fulltext_available", False)),
        "fulltext_used": False,
        "pdf_downloaded": False,
        "evidence_snippets_short": _abstract_snippets(abstract),
        "extraction_limitations_ko": "MVP에서는 metadata와 abstract만 사용했습니다. Google Scholar snippet은 evidence로 사용하지 않았고, PDF fulltext는 기본 비활성화입니다.",
    }


def _build_classification_section(paper: dict[str, Any], classification: dict[str, Any], branch: str) -> dict[str, Any]:
    return {
        "research_branch": branch,
        "downstream_route": classification["downstream_route"],
        "main_score_branch_candidate": classification["main_score_branch_candidate"],
        "classification_confidence": classification["classification_confidence"],
        "manual_review_required": bool(classification["manual_review_required"] or paper.get("is_retracted") is True),
        "classification_reason_ko": classification["classification_reason_ko"],
        "card_scope": "research_ingestion_evidence",
        "branch_hint": classification.get("branch_hint") or paper.get("research_branch_hint"),
        "paper_claim_type": classification.get("paper_claim_type", "paper_claim_only"),
        "paper_reported_backtest_treatment": classification.get("paper_reported_backtest_treatment", "diagnostic_note_only"),
        "guardrail_violations": classification.get("guardrail_violations", []),
        "rule_names": classification.get("rule_names", []),
        "manual_review_priority": classification.get("manual_review_priority", "low"),
        "management_lane": classification.get("management_lane") or paper.get("research_management_lane"),
        "source_query_sets": classification.get("source_query_sets") or paper.get("research_query_sets", []),
    }


def _build_candidate_idea_section(paper: dict[str, Any], candidate: dict[str, Any], branch: str) -> dict[str, Any]:
    return {
        "candidate_name": candidate.get("candidate_name"),
        "idea_summary_ko": candidate.get("idea_summary_ko"),
        "idea_summary_en": candidate.get("idea_summary_en"),
        "signal_family_candidate": candidate.get("signal_family_candidate"),
        "required_inputs": candidate.get("required_inputs", []),
        "unavailable_inputs": candidate.get("unavailable_inputs", []),
        "ohlcv_compatible": bool(candidate.get("ohlcv_compatible", branch == "technical")),
        "daily_frequency_compatible": bool(candidate.get("daily_frequency_compatible", True)),
        "point_in_time_fundamentals_required": bool(candidate.get("point_in_time_fundamentals_required", False)),
        "valuation_content_present": bool(candidate.get("valuation_content_present", branch in {"valuation", "hybrid"})),
        "hybrid_split_required": bool(candidate.get("hybrid_split_required", branch == "hybrid")),
        "technical_portion_summary": candidate.get("technical_portion_summary"),
        "valuation_portion_summary": candidate.get("valuation_portion_summary"),
        "universe_market": candidate.get("universe_market"),
        "universe_region": candidate.get("universe_region"),
        "universe_asset_class": candidate.get("universe_asset_class"),
        "universe_frequency": candidate.get("universe_frequency"),
        "universe_mismatch_risk": bool(candidate.get("universe_mismatch_risk", True)),
        "transfer_assumption_required": bool(candidate.get("transfer_assumption_required", False)),
        "formula_clarity": candidate.get("formula_clarity", "not_specified"),
        "implementation_readiness": candidate.get("implementation_readiness", 0),
        "blocked_by_data": branch in {"valuation", "hybrid"} or paper.get("is_retracted") is True,
        "intraday_required": branch == "out_of_scope" and _contains(paper, "intraday"),
        "order_book_required": branch == "out_of_scope" and _contains(paper, "order book"),
        "alternative_data_required": False,
        "data_compatibility": ["daily_ohlcv"] if branch == "technical" else [],
    }


def _build_valuation_boundary_section(branch: str) -> dict[str, Any]:
    return {
        "valuation_status": "unavailable" if branch in {"valuation", "hybrid"} else "not_applicable",
        "valuation_verdict": "unavailable" if branch in {"valuation", "hybrid"} else "not_applicable",
        "valuation_agent_required": branch in {"valuation", "hybrid"},
        "point_in_time_requirements_ko": "point-in-time fundamentals 검증이 필요합니다." if branch in {"valuation", "hybrid"} else None,
    }


def _build_risks_section(candidate: dict[str, Any], branch: str) -> dict[str, Any]:
    return {
        "lookahead_risk_flag": branch in {"valuation", "hybrid"},
        "data_snooping_risk_flag": True,
        "transaction_cost_missing_flag": True,
        "turnover_risk_flag": True,
        "universe_mismatch_flag": True,
        "survivorship_bias_risk_flag": True,
        "point_in_time_data_risk_flag": branch in {"valuation", "hybrid"},
        "publication_bias_risk_flag": True,
        "redundancy_risk_flag": False,
        "lookahead_risk": branch in {"valuation", "hybrid"},
        "data_snooping_risk": True,
        "transaction_cost_risk": True,
        "survivorship_bias_risk": True,
        "publication_bias_risk": True,
        "redundancy_risk": False,
        "universe_mismatch_risk": bool(candidate.get("universe_mismatch_risk", True)),
        "notes_ko": "논문 claim은 아직 검증된 alpha가 아니며, score adoption 전 별도 검토가 필요합니다.",
    }


def _build_backtest_context_section(paper: dict[str, Any], classification: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_reported_backtest_present": bool(classification.get("paper_reported_backtest_present", _contains(paper, "backtest"))),
        "paper_reported_backtest_treatment": "diagnostic_note_only",
        "reported_metrics": [],
        "reported_universe": candidate.get("universe_market"),
        "reported_period": None,
        "transaction_costs_discussed": _contains(paper, "transaction cost"),
        "survivorship_bias_discussed": _contains(paper, "survivorship"),
        "lookahead_bias_discussed": _contains(paper, "lookahead"),
        "reproducibility_level": "not_reported",
        "limitations_ko": "Paper-reported backtest is diagnostic metadata only; repository backtest 또는 alpha 검증을 수행하지 않았습니다.",
    }


def _build_guardrails_section() -> dict[str, Any]:
    return {
        "paper_claim_not_verified": True,
        "no_score_adopted": True,
        "no_backtest_performed": True,
        "valuation_not_inferred_from_price": True,
        "citation_count_metadata_only": True,
        "notes_ko": "EvidenceCard만 생성했고 score 채택, backtest, valuation review는 수행하지 않았습니다.",
    }


def _mark_retracted_card(card: dict[str, Any]) -> None:
    card["classification"]["downstream_route"] = "reject_log"
    card["classification"]["manual_review_required"] = True
    card["guardrails"]["notes_ko"] += " retracted flag가 있어 보수적으로 차단/검토 대상으로 표시했습니다."


def generate_evidence_cards(
    papers: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
    source_run_id: str,
) -> list[dict[str, Any]]:
    return [
        generate_evidence_card(paper, classification, source_run_id)
        for paper, classification in zip(papers, classifications, strict=True)
    ]


def validate_evidence_card(card: dict[str, Any]) -> None:
    missing = [field for field in EVIDENCE_REQUIRED_TOP_LEVEL if field not in card]
    if missing:
        raise ValueError(f"EvidenceCard is missing required fields: {', '.join(missing)}")
    guardrails = card["guardrails"]
    for field in [
        "paper_claim_not_verified",
        "no_score_adopted",
        "no_backtest_performed",
        "valuation_not_inferred_from_price",
    ]:
        if guardrails.get(field) is not True:
            raise ValueError(f"EvidenceCard hard guardrail must be true: {field}")
    if card["extraction"].get("fulltext_used") or card["extraction"].get("pdf_downloaded"):
        raise ValueError("MVP EvidenceCards must not use fulltext/PDF by default.")
    if card["source"].get("seed_origin_is_evidence") is not False:
        raise ValueError("Discovery seeds must remain non-evidence until canonical metadata resolution.")
    if card["source"].get("citation_count_metadata_only") is not True or card["guardrails"].get("citation_count_metadata_only") is not True:
        raise ValueError("Citation counts must remain metadata only.")
    if card["backtest_context"].get("paper_reported_backtest_treatment") != "diagnostic_note_only":
        raise ValueError("Paper-reported backtest is diagnostic metadata only.")
    if card["classification"]["research_branch"] == "technical" and card["candidate_idea"].get("point_in_time_fundamentals_required"):
        raise ValueError("Technical EvidenceCard cannot require point-in-time fundamentals.")
    if (
        card["classification"]["research_branch"] == "technical"
        and card["candidate_idea"].get("valuation_content_present")
    ):
        raise ValueError("Technical EvidenceCard cannot carry valuation content directly.")


def _evidence_id(run_id: str, canonical_paper_id: str, parent: str | None) -> str:
    basis = f"{run_id}|{canonical_paper_id}|{parent or ''}"
    return "ecard:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def _abstract_snippets(abstract: str | None) -> list[str]:
    if not abstract:
        return []
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", abstract) if sentence.strip()]
    return sentences[:2]


def _contains(paper: dict[str, Any], phrase: str) -> bool:
    text = f"{paper.get('title') or ''} {paper.get('abstract') or ''}".lower()
    return phrase in text
