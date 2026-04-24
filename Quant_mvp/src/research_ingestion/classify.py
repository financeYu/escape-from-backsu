from __future__ import annotations

import re
from typing import Any

from .normalize import normalize_title


ALLOWED_RESEARCH_BRANCHES = {"technical", "valuation", "hybrid", "diagnostic", "out_of_scope"}
ALLOWED_DOWNSTREAM_ROUTES = {
    "technical_score_architect",
    "valuation_agent_handoff",
    "hybrid_split_required",
    "diagnostic_backlog",
    "reject_log",
}
ALLOWED_MAIN_SCORE_BRANCHES = {"technical", "diagnostic", "out_of_scope", "unavailable"}


def classify_paper(
    paper: dict[str, Any],
    classification_config: dict[str, Any],
    policy_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = _paper_text(paper)
    management_lane = _management_lane(paper)
    branch_hits = {
        branch: _keyword_hits(text, classification_config.get("branches", {}).get(branch, {}).get("keywords", []))
        for branch in ["technical", "valuation", "diagnostic", "out_of_scope"]
    }

    if branch_hits["out_of_scope"]:
        branch = "out_of_scope"
    elif management_lane == "backtest_methodology":
        branch = "diagnostic"
    elif branch_hits["diagnostic"] and not branch_hits["technical"] and not branch_hits["valuation"]:
        branch = "diagnostic"
    elif branch_hits["technical"] and branch_hits["valuation"]:
        branch = "hybrid"
    elif branch_hits["valuation"]:
        branch = "valuation"
    elif branch_hits["technical"]:
        branch = "technical"
    elif branch_hits["diagnostic"]:
        branch = "diagnostic"
    else:
        fallback = classification_config.get("fallback", {})
        branch = fallback.get("research_branch", "out_of_scope")

    route = classification_config.get("routing", {}).get(branch, "reject_log")
    manual_review = _manual_review_required(branch, paper, policy_config)
    formula_clarity = _formula_clarity(paper)
    if formula_clarity in {"vague", "not_specified"}:
        manual_review = True
    if paper.get("is_retracted") is True:
        manual_review = True
        route = "reject_log"

    main_branch = _main_score_branch(branch)
    confidence = _confidence(branch, paper, formula_clarity, branch_hits)
    classification = {
        "research_branch": branch,
        "downstream_route": route,
        "main_score_branch_candidate": main_branch,
        "classification_confidence": confidence,
        "manual_review_required": manual_review,
        "classification_reason_ko": _reason_ko(branch, branch_hits, paper, management_lane),
        "management_lane": management_lane,
        "source_query_sets": list(paper.get("research_query_sets", [])),
        "candidate_idea": {
            "candidate_name": paper.get("title"),
            "idea_summary_ko": _idea_summary_ko(paper, branch),
            "idea_summary_en": paper.get("abstract"),
            "signal_family_candidate": None if management_lane == "backtest_methodology" else _signal_family(text, classification_config),
            "required_inputs": _required_inputs(branch, branch_hits),
            "unavailable_inputs": _unavailable_inputs(branch),
            "point_in_time_fundamentals_required": branch in {"valuation", "hybrid"},
            "formula_clarity": formula_clarity,
            "implementation_readiness": _implementation_readiness(formula_clarity, branch),
        },
    }
    validate_classification(classification)
    return classification


def validate_classification(classification: dict[str, Any]) -> None:
    if classification["research_branch"] not in ALLOWED_RESEARCH_BRANCHES:
        raise ValueError("Invalid research_branch")
    if classification["downstream_route"] not in ALLOWED_DOWNSTREAM_ROUTES:
        raise ValueError("Invalid downstream_route")
    if classification["main_score_branch_candidate"] not in ALLOWED_MAIN_SCORE_BRANCHES:
        raise ValueError("Invalid main_score_branch_candidate")
    if classification["research_branch"] == "valuation" and classification["main_score_branch_candidate"] == "valuation":
        raise ValueError("Valuation must not be emitted as main technical score branch.")


def _paper_text(paper: dict[str, Any]) -> str:
    parts = [
        paper.get("title") or "",
        paper.get("abstract") or "",
        " ".join(paper.get("topics") or []),
        " ".join(paper.get("fields_of_study") or []),
    ]
    return normalize_title(" ".join(parts))


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    hits = []
    for keyword in keywords:
        normalized = normalize_title(keyword)
        if not normalized:
            continue
        pattern = rf"(?<![a-z0-9가-힣]){re.escape(normalized)}(?![a-z0-9가-힣])"
        if re.search(pattern, text):
            hits.append(keyword)
    return hits


def _manual_review_required(branch: str, paper: dict[str, Any], policy_config: dict[str, Any] | None) -> bool:
    guardrails = (policy_config or {}).get("guardrails", {})
    if branch == "hybrid" and guardrails.get("require_manual_review_for_hybrid", True):
        return True
    if branch in {"valuation", "out_of_scope"}:
        return True
    if paper.get("is_retracted") is True:
        return True
    return False


def _management_lane(paper: dict[str, Any]) -> str | None:
    lanes: list[str] = []
    lane = paper.get("research_management_lane")
    if lane:
        lanes.append(str(lane))
    for value in paper.get("research_management_lanes") or []:
        text = str(value)
        if text not in lanes:
            lanes.append(text)
    if "backtest_methodology" in lanes:
        return "backtest_methodology"
    if lanes:
        return str(lanes[0])
    return None


def _formula_clarity(paper: dict[str, Any]) -> str:
    abstract = normalize_title(paper.get("abstract"))
    if not abstract:
        return "not_specified"
    if any(term in abstract for term in ["formula", "defined as", "we define", "computed as"]):
        return "partial"
    if len(abstract.split()) < 25:
        return "vague"
    return "partial"


def _main_score_branch(branch: str) -> str:
    if branch == "technical":
        return "technical"
    if branch == "diagnostic":
        return "diagnostic"
    if branch == "out_of_scope":
        return "out_of_scope"
    return "unavailable"


def _confidence(branch: str, paper: dict[str, Any], formula_clarity: str, hits: dict[str, list[str]]) -> str:
    if branch in {"hybrid", "out_of_scope"}:
        return "low"
    if not paper.get("abstract") or formula_clarity in {"vague", "not_specified"}:
        return "low"
    if len(hits.get(branch, [])) >= 2:
        return "medium"
    return "low"


def _reason_ko(branch: str, hits: dict[str, list[str]], paper: dict[str, Any], management_lane: str | None = None) -> str:
    if paper.get("is_retracted") is True:
        return "retracted flag가 있어 보수적으로 reject_log 및 수동 검토 대상으로 표시했습니다."
    if management_lane == "backtest_methodology" and branch == "diagnostic":
        return "backtest_methodology lane으로 수집되어 score 후보가 아닌 백테스트 설계/검증 diagnostic backlog로 분리했습니다."
    if branch == "hybrid":
        return "technical keyword와 valuation/fundamental keyword가 함께 감지되어 hybrid_split_required로 분리했습니다."
    if branch == "valuation":
        return "point-in-time fundamentals가 필요한 valuation 후보이므로 별도 valuation agent handoff가 필요합니다."
    if branch == "diagnostic":
        return "방법론/검증/편향 관련 키워드가 감지되어 alpha signal이 아닌 diagnostic backlog로 분류했습니다."
    if branch == "technical":
        return "일간 OHLCV 또는 가격-거래량 기반 technical candidate로만 분류했습니다. score 채택은 수행하지 않았습니다."
    return "MVP technical ranking scope와 맞지 않거나 근거가 부족하여 reject_log로 분류했습니다."


def _idea_summary_ko(paper: dict[str, Any], branch: str) -> str:
    title = paper.get("title") or "제목 없음"
    return f"{title} 문헌을 {branch} research_branch 후보로 보수적으로 분류했습니다. 논문 claim은 검증된 alpha가 아닙니다."


def _signal_family(text: str, config: dict[str, Any]) -> str | None:
    for family in config.get("branches", {}).get("technical", {}).get("signal_families", []):
        if family.replace("_", " ") in text:
            return family
    if "momentum" in text or "relative strength" in text:
        return "momentum"
    if "reversal" in text or "mean reversion" in text:
        return "mean_reversion"
    if "breakout" in text:
        return "breakout"
    if "volatility" in text or "liquidity" in text or "volume" in text:
        return "volatility_liquidity"
    return None


def _required_inputs(branch: str, hits: dict[str, list[str]]) -> list[str]:
    if branch == "valuation":
        return ["point_in_time_fundamentals", "daily_market_cap_or_price"]
    if branch == "hybrid":
        return ["daily_ohlcv", "point_in_time_fundamentals"]
    if branch == "technical":
        return ["daily_ohlcv"]
    if branch == "diagnostic":
        return ["research_outputs", "score_diagnostics"]
    return []


def _unavailable_inputs(branch: str) -> list[str]:
    if branch in {"valuation", "hybrid"}:
        return ["validated_point_in_time_fundamentals"]
    return []


def _implementation_readiness(formula_clarity: str, branch: str) -> int:
    if branch in {"valuation", "hybrid", "out_of_scope"}:
        return 0
    return {"exact": 3, "partial": 2, "vague": 1, "not_specified": 0}.get(formula_clarity, 0)
