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
DIAGNOSTIC_MANAGEMENT_LANES = {
    "backtest_methodology",
    "methodology_diagnostics",
    "diagnostic_methodology",
    "technical_diagnostics",
    "market_context",
}
REGIONAL_CONTEXT_QUERY_SETS = {
    "korea_kospi_context",
    "korea_kospi_expanded",
    "asia_pacific_equity_context",
    "emerging_market_equity_anomalies",
}


def classify_paper(
    paper: dict[str, Any],
    classification_config: dict[str, Any],
    policy_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = _paper_text(paper)
    management_lane = _management_lane(paper)
    branch_hint = _branch_hint(paper)
    formula_clarity = _formula_clarity(paper)
    branch_hits = {
        branch: _keyword_hits(text, classification_config.get("branches", {}).get(branch, {}).get("keywords", []))
        for branch in ["technical", "valuation", "diagnostic", "out_of_scope"]
    }
    required_input_boundary = _required_input_boundary(paper, text, classification_config)
    forbidden_language_hits = _forbidden_valuation_language_hits(text, classification_config)
    branch, rule_names = _select_research_branch(
        paper=paper,
        classification_config=classification_config,
        management_lane=management_lane,
        branch_hint=branch_hint,
        formula_clarity=formula_clarity,
        branch_hits=branch_hits,
        required_input_boundary=required_input_boundary,
    )

    language_guardrail_violation = _language_guardrail_violation(
        forbidden_language_hits=forbidden_language_hits,
        required_input_boundary=required_input_boundary,
        branch_hits=branch_hits,
    )
    branch, route, manual_review = _route_and_review(
        paper=paper,
        classification_config=classification_config,
        policy_config=policy_config,
        branch=branch,
        rule_names=rule_names,
        formula_clarity=formula_clarity,
        language_guardrail_violation=language_guardrail_violation,
    )

    classification_reason_ko = _reason_ko(branch, branch_hits, paper, management_lane)
    if language_guardrail_violation:
        classification_reason_ko = "price-only technical evidence에 valuation language가 감지되어 reject_log로 분리했습니다."
    classification = _classification_payload(
        paper, text, classification_config, branch, route, manual_review, management_lane, branch_hint,
        formula_clarity, branch_hits, rule_names, language_guardrail_violation, classification_reason_ko,
    )
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
    if classification["research_branch"] == "technical" and classification["candidate_idea"].get("point_in_time_fundamentals_required"):
        raise ValueError("Technical candidates must not require point-in-time fundamentals.")
    if classification.get("paper_reported_backtest_treatment") != "diagnostic_note_only":
        raise ValueError("Paper-reported backtests must remain diagnostic metadata only.")


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


def _select_research_branch(
    *,
    paper: dict[str, Any],
    classification_config: dict[str, Any],
    management_lane: str | None,
    branch_hint: str | None,
    formula_clarity: str,
    branch_hits: dict[str, list[str]],
    required_input_boundary: str | None,
) -> tuple[str, list[str]]:
    if branch_hits["out_of_scope"]:
        return "out_of_scope", ["classify_out_of_scope_keywords"]
    if required_input_boundary == "hybrid":
        return "hybrid", ["classify_required_inputs_boundary"]
    if required_input_boundary == "valuation":
        return "valuation", ["classify_required_inputs_boundary"]
    if branch_hint == "hybrid":
        return "hybrid", ["classify_hybrid_technical_valuation_split"]
    if management_lane in DIAGNOSTIC_MANAGEMENT_LANES or branch_hint == "diagnostic":
        return "diagnostic", ["classify_methodology_diagnostic"]
    if branch_hits["diagnostic"] and not branch_hits["technical"] and not branch_hits["valuation"]:
        return "diagnostic", ["classify_methodology_diagnostic"]
    if _market_context_without_formula(paper, formula_clarity) and not branch_hits["valuation"]:
        return "diagnostic", ["classify_market_context_transfer_risk"]
    if branch_hits["technical"] and branch_hits["valuation"]:
        return "hybrid", ["classify_hybrid_technical_valuation_split"]
    if branch_hits["valuation"]:
        return "valuation", ["classify_required_inputs_boundary"]
    if branch_hits["technical"]:
        return "technical", ["classify_ohlcv_compatibility"]
    if branch_hits["diagnostic"]:
        return "diagnostic", ["classify_methodology_diagnostic"]
    fallback = classification_config.get("fallback", {})
    return fallback.get("research_branch", "out_of_scope"), ["classify_fallback_low_information"]


def _route_and_review(
    *,
    paper: dict[str, Any],
    classification_config: dict[str, Any],
    policy_config: dict[str, Any] | None,
    branch: str,
    rule_names: list[str],
    formula_clarity: str,
    language_guardrail_violation: bool,
) -> tuple[str, str, bool]:
    if language_guardrail_violation:
        branch = "out_of_scope"
        rule_names.append("classify_forbidden_valuation_language")

    route = classification_config.get("routing", {}).get(branch, "reject_log")
    manual_review = _manual_review_required(branch, paper, policy_config)
    if formula_clarity in {"vague", "not_specified"}:
        manual_review = True
    if _market_context_without_formula(paper, formula_clarity):
        manual_review = True
    if language_guardrail_violation:
        manual_review = True
        route = "reject_log"
    if paper.get("is_retracted") is True:
        manual_review = True
        route = "reject_log"
    return branch, route, manual_review


def _classification_payload(
    paper: dict[str, Any],
    text: str,
    classification_config: dict[str, Any],
    branch: str,
    route: str,
    manual_review: bool,
    management_lane: str | None,
    branch_hint: str | None,
    formula_clarity: str,
    branch_hits: dict[str, list[str]],
    rule_names: list[str],
    language_guardrail_violation: bool,
    classification_reason_ko: str,
) -> dict[str, Any]:
    required_inputs = _required_inputs(branch, branch_hits, paper, classification_config)
    paper_reported_backtest_present = _paper_reported_backtest_present(text)
    return {
        "research_branch": branch,
        "downstream_route": route,
        "main_score_branch_candidate": _main_score_branch(branch),
        "classification_confidence": _confidence(branch, paper, formula_clarity, branch_hits),
        "manual_review_required": manual_review,
        "classification_reason_ko": classification_reason_ko,
        "management_lane": management_lane,
        "branch_hint": branch_hint,
        "source_query_sets": list(paper.get("research_query_sets", [])),
        "rule_names": rule_names,
        "guardrail_violations": ["language_guardrail_violation"] if language_guardrail_violation else [],
        "manual_review_priority": _manual_review_priority(branch, manual_review, language_guardrail_violation, formula_clarity),
        "paper_claim_type": "paper_reported_backtest" if paper_reported_backtest_present else "paper_claim_only",
        "paper_reported_backtest_present": paper_reported_backtest_present,
        "paper_reported_backtest_treatment": "diagnostic_note_only",
        "candidate_idea": _candidate_idea(
            paper=paper,
            text=text,
            branch=branch,
            branch_hits=branch_hits,
            management_lane=management_lane,
            classification_config=classification_config,
            formula_clarity=formula_clarity,
            required_inputs=required_inputs,
            unavailable_inputs=_unavailable_inputs(branch),
            ohlcv_compatible=_ohlcv_compatible(branch, required_inputs, text),
            daily_frequency_compatible=_daily_frequency_compatible(text),
        ),
    }


def _candidate_idea(
    *,
    paper: dict[str, Any],
    text: str,
    branch: str,
    branch_hits: dict[str, list[str]],
    management_lane: str | None,
    classification_config: dict[str, Any],
    formula_clarity: str,
    required_inputs: list[str],
    unavailable_inputs: list[str],
    ohlcv_compatible: bool,
    daily_frequency_compatible: bool,
) -> dict[str, Any]:
    return {
        "candidate_name": paper.get("title"),
        "idea_summary_ko": _idea_summary_ko(paper, branch),
        "idea_summary_en": paper.get("abstract"),
        "signal_family_candidate": None if management_lane == "backtest_methodology" else _signal_family(text, classification_config),
        "required_inputs": required_inputs,
        "unavailable_inputs": unavailable_inputs,
        "ohlcv_compatible": ohlcv_compatible,
        "daily_frequency_compatible": daily_frequency_compatible,
        "point_in_time_fundamentals_required": branch in {"valuation", "hybrid"},
        "valuation_content_present": branch in {"valuation", "hybrid"} or bool(branch_hits["valuation"]),
        "hybrid_split_required": branch == "hybrid",
        "technical_portion_summary": _technical_portion_summary(branch, paper),
        "valuation_portion_summary": _valuation_portion_summary(branch, paper),
        "universe_market": _universe_market(paper, text),
        "universe_region": _universe_region(paper, text),
        "universe_asset_class": _universe_asset_class(text),
        "universe_frequency": _universe_frequency(text),
        "universe_mismatch_risk": _universe_mismatch_risk(paper, text),
        "transfer_assumption_required": _transfer_assumption_required(paper, text),
        "formula_clarity": formula_clarity,
        "implementation_readiness": _implementation_readiness(formula_clarity, branch),
    }


def _manual_review_required(branch: str, paper: dict[str, Any], policy_config: dict[str, Any] | None) -> bool:
    guardrails = (policy_config or {}).get("guardrails", {})
    if branch == "hybrid" and guardrails.get("require_manual_review_for_hybrid", True):
        return True
    if branch in {"valuation", "out_of_scope"}:
        return True
    if paper.get("is_retracted") is True:
        return True
    return False


def _branch_hint(paper: dict[str, Any]) -> str | None:
    hints: list[str] = []
    hint = paper.get("research_branch_hint")
    if hint:
        hints.append(str(hint))
    for value in paper.get("research_branch_hints") or []:
        text = str(value)
        if text not in hints:
            hints.append(text)
    if "hybrid" in hints:
        return "hybrid"
    if "valuation" in hints:
        return "valuation"
    if "diagnostic" in hints:
        return "diagnostic"
    if "technical" in hints:
        return "technical"
    return next(iter(hints), None)


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
    for lane in lanes:
        if lane in DIAGNOSTIC_MANAGEMENT_LANES:
            return lane
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
    if "language_guardrail_violation" in paper.get("guardrail_violations", []):
        return "price-only technical evidence에 valuation language가 감지되어 reject_log로 분리했습니다."
    if branch == "hybrid":
        return "technical keyword와 valuation/fundamental keyword가 함께 감지되어 hybrid_split_required로 분리했습니다."
    if branch == "valuation":
        return "point-in-time fundamentals가 필요한 valuation 후보이므로 valuation review skill handoff가 필요합니다."
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


def _required_inputs(
    branch: str,
    hits: dict[str, list[str]],
    paper: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    explicit = _explicit_required_inputs(paper)
    if explicit:
        return explicit
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


def _explicit_required_inputs(paper: dict[str, Any]) -> list[str]:
    values = paper.get("required_inputs") or paper.get("candidate_required_inputs") or []
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values if str(value).strip()]


def _required_input_boundary(paper: dict[str, Any], text: str, config: dict[str, Any]) -> str | None:
    explicit_inputs = " ".join(_explicit_required_inputs(paper))
    valuation_terms = config.get("rules", {}).get("valuation_required_input_terms", [])
    required_text = normalize_title(f"{explicit_inputs} {text}")
    valuation_hits = _keyword_hits(required_text, valuation_terms)
    if not valuation_hits:
        return None
    technical_hits = _keyword_hits(required_text, config.get("branches", {}).get("technical", {}).get("keywords", []))
    return "hybrid" if technical_hits else "valuation"


def _forbidden_valuation_language_hits(text: str, config: dict[str, Any]) -> list[str]:
    return _keyword_hits(text, config.get("rules", {}).get("forbidden_price_only_valuation_language", []))


def _language_guardrail_violation(
    *,
    forbidden_language_hits: list[str],
    required_input_boundary: str | None,
    branch_hits: dict[str, list[str]],
) -> bool:
    return bool(forbidden_language_hits and required_input_boundary is None and branch_hits.get("technical"))


def _market_context_without_formula(paper: dict[str, Any], formula_clarity: str) -> bool:
    query_sets = set(paper.get("research_query_sets") or [])
    query_set = paper.get("research_query_set")
    if query_set:
        query_sets.add(str(query_set))
    return bool(query_sets & REGIONAL_CONTEXT_QUERY_SETS and formula_clarity in {"vague", "not_specified"})


def _paper_reported_backtest_present(text: str) -> bool:
    return bool(
        _keyword_hits(
            text,
            [
                "backtest",
                "backtesting",
                "out of sample",
                "out-of-sample",
                "walk forward",
                "strategy performance",
                "sharpe ratio",
                "alpha",
            ],
        )
    )


def _ohlcv_compatible(branch: str, required_inputs: list[str], text: str) -> bool:
    if branch != "technical":
        return False
    if any("fundamental" in normalize_title(value) for value in required_inputs):
        return False
    return not any(term in text for term in ["intraday", "tick data", "order book"])


def _daily_frequency_compatible(text: str) -> bool:
    return not any(term in text for term in ["intraday", "tick data", "high frequency", "order book"])


def _technical_portion_summary(branch: str, paper: dict[str, Any]) -> str | None:
    if branch not in {"technical", "hybrid"}:
        return None
    return f"{paper.get('title') or '제목 없음'} 중 daily OHLCV 또는 가격-거래량 기반 부분만 technical portion 후보입니다."


def _valuation_portion_summary(branch: str, paper: dict[str, Any]) -> str | None:
    if branch not in {"valuation", "hybrid"}:
        return None
    return "fundamental/valuation portion은 point-in-time 검증 전까지 technical 후보로 직접 전달하지 않습니다."


def _universe_market(paper: dict[str, Any], text: str) -> str | None:
    if "kospi" in text or "korean stock" in text:
        return "KOSPI/Korean equity"
    if "asia pacific" in text or "apac" in text:
        return "Asia-Pacific equity"
    if "emerging market" in text:
        return "emerging market equity"
    return paper.get("universe_market")


def _universe_region(paper: dict[str, Any], text: str) -> str | None:
    if "korea" in text or "korean" in text or "kospi" in text:
        return "Korea"
    if "asia pacific" in text or "apac" in text:
        return "Asia-Pacific"
    if "emerging market" in text:
        return "Emerging markets"
    return paper.get("universe_region")


def _universe_asset_class(text: str) -> str:
    if "option" in text:
        return "options"
    if "future" in text:
        return "futures"
    if "crypto" in text:
        return "crypto"
    return "equity"


def _universe_frequency(text: str) -> str:
    if "intraday" in text:
        return "intraday"
    if "tick data" in text:
        return "tick"
    return "daily_or_unspecified"


def _universe_mismatch_risk(paper: dict[str, Any], text: str) -> bool:
    query_sets = set(paper.get("research_query_sets") or [])
    return bool(query_sets & {"asia_pacific_equity_context", "emerging_market_equity_anomalies"}) or any(
        term in text for term in ["emerging market", "asia pacific", "apac"]
    )


def _transfer_assumption_required(paper: dict[str, Any], text: str) -> bool:
    return _universe_mismatch_risk(paper, text) or _market_context_without_formula(paper, _formula_clarity(paper))


def _manual_review_priority(
    branch: str,
    manual_review: bool,
    language_guardrail_violation: bool,
    formula_clarity: str,
) -> str:
    if language_guardrail_violation or branch in {"hybrid", "valuation"}:
        return "high"
    if manual_review or formula_clarity in {"vague", "not_specified"}:
        return "medium"
    return "low"
