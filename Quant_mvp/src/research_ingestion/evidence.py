from __future__ import annotations

from typing import Any
import hashlib
import re


EVIDENCE_REQUIRED_TOP_LEVEL = [
    "evidence_card_id",
    "source_run_id",
    "paper",
    "extraction",
    "classification",
    "candidate_idea",
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
        "paper": {
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
        },
        "extraction": {
            "extraction_scope": "abstract_only" if abstract else "metadata_only",
            "evidence_status": "abstract_supported" if abstract else "metadata_only",
            "abstract_available": bool(abstract),
            "fulltext_used": False,
            "pdf_downloaded": False,
            "evidence_snippets_short": _abstract_snippets(abstract),
            "extraction_limitations_ko": "MVP에서는 metadata와 abstract만 사용했습니다. Google Scholar snippet은 evidence로 사용하지 않았고, PDF fulltext는 기본 비활성화입니다.",
        },
        "classification": {
            "research_branch": branch,
            "downstream_route": classification["downstream_route"],
            "main_score_branch_candidate": classification["main_score_branch_candidate"],
            "classification_confidence": classification["classification_confidence"],
            "manual_review_required": bool(classification["manual_review_required"] or paper.get("is_retracted") is True),
            "classification_reason_ko": classification["classification_reason_ko"],
            "management_lane": classification.get("management_lane") or paper.get("research_management_lane"),
            "source_query_sets": classification.get("source_query_sets") or paper.get("research_query_sets", []),
        },
        "candidate_idea": {
            "candidate_name": candidate.get("candidate_name"),
            "idea_summary_ko": candidate.get("idea_summary_ko"),
            "idea_summary_en": candidate.get("idea_summary_en"),
            "signal_family_candidate": candidate.get("signal_family_candidate"),
            "required_inputs": candidate.get("required_inputs", []),
            "unavailable_inputs": candidate.get("unavailable_inputs", []),
            "point_in_time_fundamentals_required": bool(candidate.get("point_in_time_fundamentals_required", False)),
            "formula_clarity": candidate.get("formula_clarity", "not_specified"),
            "implementation_readiness": candidate.get("implementation_readiness", 0),
            "blocked_by_data": branch in {"valuation", "hybrid"} or paper.get("is_retracted") is True,
            "intraday_required": branch == "out_of_scope" and _contains(paper, "intraday"),
            "order_book_required": branch == "out_of_scope" and _contains(paper, "order book"),
            "alternative_data_required": False,
            "data_compatibility": ["daily_ohlcv"] if branch == "technical" else [],
        },
        "valuation_boundary": {
            "valuation_status": "unavailable" if branch in {"valuation", "hybrid"} else "not_applicable",
            "valuation_verdict": "unavailable" if branch in {"valuation", "hybrid"} else "not_applicable",
            "valuation_agent_required": branch in {"valuation", "hybrid"},
            "point_in_time_requirements_ko": "point-in-time fundamentals 검증이 필요합니다." if branch in {"valuation", "hybrid"} else None,
        },
        "risks": {
            "lookahead_risk_flag": branch in {"valuation", "hybrid"},
            "data_snooping_risk_flag": True,
            "transaction_cost_missing_flag": True,
            "turnover_risk_flag": True,
            "universe_mismatch_flag": True,
            "survivorship_bias_risk_flag": True,
            "point_in_time_data_risk_flag": branch in {"valuation", "hybrid"},
            "publication_bias_risk_flag": True,
            "redundancy_risk_flag": False,
            "notes_ko": "논문 claim은 아직 검증된 alpha가 아니며, score adoption 전 별도 검토가 필요합니다.",
        },
        "guardrails": {
            "paper_claim_not_verified": True,
            "no_score_adopted": True,
            "no_backtest_performed": True,
            "valuation_not_inferred_from_price": True,
            "notes_ko": "EvidenceCard만 생성했고 score 채택, backtest, valuation review는 수행하지 않았습니다.",
        },
    }
    if paper.get("is_retracted") is True:
        card["classification"]["downstream_route"] = "reject_log"
        card["classification"]["manual_review_required"] = True
        card["guardrails"]["notes_ko"] += " retracted flag가 있어 보수적으로 차단/검토 대상으로 표시했습니다."
    validate_evidence_card(card)
    return card


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
    if card["classification"]["research_branch"] == "technical" and card["candidate_idea"].get("point_in_time_fundamentals_required"):
        raise ValueError("Technical EvidenceCard cannot require point-in-time fundamentals.")


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
