"""Build v0.3 ResearchHypothesis records from research EvidenceCards.

The generated records structure research ideas for the v0.3 candidate/evidence
route. They are not strategy adoptions, production score inputs, production
ranking inputs, trading recommendations, or future-performance evidence.
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
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/research_hypotheses")
DEFAULT_JSONL_NAME = "v0_3_research_hypotheses.jsonl"
DEFAULT_CSV_NAME = "v0_3_research_hypotheses.csv"
DEFAULT_MANIFEST_NAME = "v0_3_research_hypotheses_manifest.json"

CURRENT_STAGE = "ResearchHypothesis"
RESEARCH_BOUNDARY = (
    "This ResearchHypothesis output is candidate-only research structure. It is "
    "not a production ranking input, not a score input, not a runtime model "
    "feature source, not a trading recommendation, and not an adoption decision."
)

SOURCE_TYPES = {
    "paper",
    "article",
    "market_observation",
    "prior_strategy",
    "user_idea",
    "internal_experiment",
}

NEXT_ACTIONS = {"convert_to_strategy_hypothesis", "needs_more_research", "reject"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
EVIDENCE_QUALITY_LEVELS = {"weak", "moderate", "strong"}
DIFFICULTY_LEVELS = {"low", "medium", "high"}


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

    reasons.extend(str(item) for item in _as_list(_get(card, "classification.guardrail_violations")) if item)
    return sorted(set(reasons))


def _source_type(card: dict[str, Any]) -> str:
    if _get(card, "paper.canonical_paper_id") or _get(card, "paper.title"):
        return "paper"
    seed_type = str(_get(card, "source.seed_origin_type", "")).lower()
    if "strategy" in seed_type:
        return "prior_strategy"
    if "observation" in seed_type:
        return "market_observation"
    return "article"


def _source_reference(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_card_id": _get(card, "evidence_card_id"),
        "canonical_paper_id": _get(card, "paper.canonical_paper_id"),
        "title": _compact_text(_get(card, "paper.title"), limit=300),
        "publication_year": _get(card, "paper.publication_year"),
        "venue": _compact_text(_get(card, "paper.venue"), limit=160),
        "source_run_id": _get(card, "source_run_id"),
        "source_query_set": _get(card, "source.source_query_set"),
    }


def _target_universe(card: dict[str, Any]) -> str:
    region = _get(card, "candidate_idea.universe_region")
    market = _get(card, "candidate_idea.universe_market")
    asset_class = _get(card, "candidate_idea.universe_asset_class") or "equity"
    frequency = _get(card, "candidate_idea.universe_frequency") or "daily_or_unspecified"
    pieces = [str(item) for item in (region, market, asset_class, frequency) if item]
    if not pieces:
        return "daily equity universe; KOSPI200 transfer requires separate review"
    return "; ".join(pieces)


def _mechanism_for_family(family: Any) -> str:
    family_text = str(family or "unspecified").lower()
    if "momentum" in family_text or "trend" in family_text:
        return (
            "가격 추세 또는 정보 반영 지연이 지속되면 최근 가격/거래량 변화가 다음 기간의 "
            "상대적 움직임과 관련될 수 있다는 메커니즘입니다."
        )
    if "mean" in family_text or "reversion" in family_text or "reversal" in family_text:
        return (
            "단기 과잉반응이나 유동성 충격이 정상화되면 극단적 가격 움직임 이후 되돌림 "
            "패턴이 관찰될 수 있다는 메커니즘입니다."
        )
    if "vol" in family_text or "squeeze" in family_text:
        return (
            "변동성 압축과 확장 국면이 위험 선호, 포지션 조정, 거래량 변화와 함께 나타나며 "
            "후속 가격 분포를 바꿀 수 있다는 메커니즘입니다."
        )
    if "volume" in family_text or "flow" in family_text or "liquidity" in family_text:
        return (
            "거래량과 가격 변화의 결합이 수급 불균형이나 유동성 충격을 반영할 수 있다는 "
            "메커니즘입니다."
        )
    if "correlation" in family_text or "serial" in family_text:
        return (
            "상관 구조나 자기상관 구조가 시장 국면별로 달라지면 분산, 추세성, 회귀성에 "
            "대한 진단 신호가 될 수 있다는 메커니즘입니다."
        )
    return (
        "논문 또는 리서치가 제시한 가격, 거래량, 변동성, 구조적 조건이 반복적으로 관찰될 "
        "경우 검증 가능한 후보 신호로 정리할 수 있다는 메커니즘입니다."
    )


def _core_claim(card: dict[str, Any]) -> str:
    family = _get(card, "candidate_idea.signal_family_candidate") or "unspecified"
    branch = _get(card, "classification.research_branch") or "needs_route_review"
    return (
        f"{branch} 분류의 {family} 계열 현상이 사전 정의된 데이터와 검증 규칙 안에서 "
        "반복적으로 관찰되는지 확인할 수 있는 ResearchHypothesis입니다. 논문 또는 "
        "소스의 성과 주장은 별도 재현 전까지 검증 증거로 보지 않습니다."
    )


def _expected_signal(card: dict[str, Any]) -> str:
    family = _get(card, "candidate_idea.signal_family_candidate") or "unspecified"
    formula_clarity = _get(card, "candidate_idea.formula_clarity") or "unknown"
    inputs = ", ".join(str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs"))) or "unknown"
    return (
        f"{family} 계열 후보 신호입니다. 현재 formula_clarity={formula_clarity}, "
        f"required_inputs={inputs}이며, 다음 단계에서 entry/exit/risk rule로 구체화해야 합니다."
    )


def _required_data(card: dict[str, Any], action: str, blocked_reasons: list[str]) -> list[str]:
    required_inputs = [str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs")) if item]
    if required_inputs:
        return required_inputs
    if action == "reject" or "out_of_scope_or_rejected" in blocked_reasons:
        return ["not_applicable_rejected_or_out_of_scope"]
    if "blocked_by_data" in blocked_reasons:
        return ["blocked_required_data_not_available_in_current_scope"]
    return ["required_data_not_specified_needs_research"]


def _assumptions(card: dict[str, Any]) -> list[str]:
    assumptions = [
        "EvidenceCard의 논문 주장은 검증된 성과 증거가 아니라 연구 입력으로만 사용한다.",
        "다음 단계 전에는 신호 정의, 데이터 시점, 평가 기준을 사전 고정해야 한다.",
    ]
    if "daily_ohlcv" in {str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs"))}:
        assumptions.append("일봉 OHLCV 기반 검증이 가능하다는 전제에서만 전략 가설로 변환한다.")
    if _as_bool(_get(card, "candidate_idea.point_in_time_fundamentals_required")):
        assumptions.append("point-in-time fundamentals가 검증되지 않으면 기술 전략 후보로 직접 변환하지 않는다.")
    return assumptions


def _falsification_test(card: dict[str, Any]) -> str:
    if _as_bool(_get(card, "candidate_idea.blocked_by_data")):
        return "필수 데이터가 현재 승인 범위에 없으면 이 ResearchHypothesis는 전략 가설로 전환할 수 없습니다."
    return (
        "사전 정의한 입력 데이터와 기간에서 신호 방향, 적용 가능 커버리지, 비용/편향 진단을 "
        "분리해 확인합니다. out-of-sample 또는 walk-forward 검증에서 신호가 불안정하거나 "
        "거래비용, 생존편향, lookahead 점검 후 설명력이 사라지면 가설을 기각합니다."
    )


def _confidence_level(card: dict[str, Any]) -> str:
    confidence = _get(card, "classification.classification_confidence") or "low"
    return str(confidence) if str(confidence) in CONFIDENCE_LEVELS else "low"


def _evidence_quality(card: dict[str, Any]) -> str:
    status = _get(card, "extraction.evidence_status")
    formula_clarity = _get(card, "candidate_idea.formula_clarity")
    cost_discussed = _as_bool(_get(card, "backtest_context.transaction_costs_discussed"))
    bias_discussed = _as_bool(_get(card, "backtest_context.lookahead_bias_discussed")) and _as_bool(
        _get(card, "backtest_context.survivorship_bias_discussed")
    )
    if status == "open_access_fulltext_supported" and formula_clarity == "exact" and cost_discussed and bias_discussed:
        return "strong"
    if status in {"open_access_fulltext_supported", "abstract_supported"} and formula_clarity in {"exact", "partial"}:
        return "moderate"
    return "weak"


def _implementation_difficulty(card: dict[str, Any], blocked_reasons: list[str]) -> str:
    if {
        "blocked_by_data",
        "intraday_required",
        "order_book_required",
        "alternative_data_required",
        "point_in_time_fundamentals_required",
        "hybrid_split_required",
        "valuation_lane",
    } & set(blocked_reasons):
        return "high"
    readiness = _get(card, "candidate_idea.implementation_readiness", 0)
    try:
        readiness_int = int(readiness)
    except (TypeError, ValueError):
        readiness_int = 0
    if readiness_int >= 2 and _get(card, "candidate_idea.formula_clarity") == "exact":
        return "low"
    return "medium"


def _next_action(card: dict[str, Any], blocked_reasons: list[str]) -> str:
    branch = _get(card, "classification.research_branch")
    route = _get(card, "classification.downstream_route")
    required_inputs = {str(item) for item in _as_list(_get(card, "candidate_idea.required_inputs"))}
    if "out_of_scope_or_rejected" in blocked_reasons or _get(card, "paper.is_retracted") is True:
        return "reject"
    if (
        branch == "technical"
        and route == "technical_score_architect"
        and "daily_ohlcv" in required_inputs
        and not blocked_reasons
    ):
        return "convert_to_strategy_hypothesis"
    return "needs_more_research"


def _reason_for_next_action(action: str, blocked_reasons: list[str]) -> str:
    if action == "convert_to_strategy_hypothesis":
        return (
            "기술 분류, daily_ohlcv 입력, 기본 guardrail이 충족되어 다음 단계에서 entry/exit/risk "
            "rule을 갖춘 StrategyHypothesis로 변환할 수 있습니다."
        )
    if action == "reject":
        return "out_of_scope 또는 기각 경로로 분류되어 현재 v0.3 전략 가설 후보로 넘기지 않습니다."
    if blocked_reasons:
        return f"추가 리서치 또는 분리가 필요합니다. blocker={', '.join(blocked_reasons)}"
    return "전략화 전 신호 정의, 데이터 범위, 검증 기준을 더 구체화해야 합니다."


def _main_risks(card: dict[str, Any], blocked_reasons: list[str]) -> list[str]:
    risks = _risk_flags(card) + blocked_reasons
    if not risks:
        risks.append("insufficient_reproduction_evidence")
    return sorted(set(risks))


def _next_stage_input(
    card: dict[str, Any],
    research_id: str,
    action: str,
    blocked_reasons: list[str],
) -> dict[str, Any] | None:
    if action != "convert_to_strategy_hypothesis":
        return None
    return {
        "next_stage": "StrategyHypothesis",
        "research_id": research_id,
        "candidate_name": _get(card, "candidate_idea.candidate_name"),
        "signal_family_candidate": _get(card, "candidate_idea.signal_family_candidate"),
        "required_data": _required_data(card, action, blocked_reasons),
        "expected_signal": _expected_signal(card),
        "market_mechanism": _mechanism_for_family(_get(card, "candidate_idea.signal_family_candidate")),
        "falsification_test": _falsification_test(card),
        "guardrails": [
            "no_score_adopted",
            "no_backtest_performed_at_research_stage",
            "no_feedback_into_scores_rankings_reports_models_or_auto_adoption",
        ],
    }


def _blocker(action: str, blocked_reasons: list[str]) -> list[str]:
    if action == "convert_to_strategy_hypothesis":
        return []
    return blocked_reasons or ["strategy_definition_not_specific_enough"]


def _minimal_fix(action: str, blocked_reasons: list[str]) -> list[str]:
    if action == "convert_to_strategy_hypothesis":
        return []
    fixes: list[str] = []
    if "hybrid_split_required" in blocked_reasons:
        fixes.append("technical portion과 valuation/fundamental portion을 분리한다.")
    if "point_in_time_fundamentals_required" in blocked_reasons:
        fixes.append("point-in-time fundamentals 사용 가능성과 라이선스를 별도 검토한다.")
    if "blocked_by_data" in blocked_reasons:
        fixes.append("현재 승인된 데이터로 검증 가능한 하위 가설만 남긴다.")
    if "diagnostic_only" in blocked_reasons:
        fixes.append("전략 신호가 아니라 진단/리스크 컨텍스트로 유지한다.")
    if "out_of_scope_or_rejected" in blocked_reasons:
        fixes.append("현재 v0.3 후보 레지스트리에는 포함하지 않는다.")
    if not fixes:
        fixes.append("신호 정의, required_data, falsification_test를 보강한다.")
    return fixes


def evidence_card_to_research_hypothesis_record(card: dict[str, Any]) -> dict[str, Any]:
    blocked_reasons = _blocked_reasons(card)
    action = _next_action(card, blocked_reasons)
    research_id = f"rh:{_get(card, 'evidence_card_id')}"
    hypothesis = {
        "research_id": research_id,
        "title": _compact_text(_get(card, "candidate_idea.candidate_name") or _get(card, "paper.title"), limit=300),
        "source_type": _source_type(card),
        "source_reference": _source_reference(card),
        "core_claim": _core_claim(card),
        "market_mechanism": _mechanism_for_family(_get(card, "candidate_idea.signal_family_candidate")),
        "target_universe": _target_universe(card),
        "expected_signal": _expected_signal(card),
        "required_data": _required_data(card, action, blocked_reasons),
        "assumptions": _assumptions(card),
        "falsification_test": _falsification_test(card),
        "risk_or_failure_modes": _main_risks(card, blocked_reasons),
        "confidence_level": _confidence_level(card),
        "evidence_quality": _evidence_quality(card),
        "implementation_difficulty": _implementation_difficulty(card, blocked_reasons),
        "next_action": action,
        "reason_for_next_action": _reason_for_next_action(action, blocked_reasons),
    }
    record = {
        "schema_version": "v0_3_research_hypothesis_output_0_1",
        "current_stage": CURRENT_STAGE,
        "research_boundary": RESEARCH_BOUNDARY,
        "research_hypothesis": hypothesis,
        "why_this_could_be_a_strategy": (
            "이 가설은 관찰 가능한 시장 메커니즘을 사전 정의된 데이터와 실패 조건으로 "
            "검증할 수 있을 때만 StrategyHypothesis로 전환됩니다."
        ),
        "validation_requirement": (
            "다음 단계에서는 데이터 시점, 입력 컬럼, 신호 계산식, 평가 기간, 비용/편향 점검을 "
            "사전 정의해야 합니다."
        ),
        "main_risks": _main_risks(card, blocked_reasons),
        "next_stage_input": _next_stage_input(card, research_id, action, blocked_reasons),
        "blocker": _blocker(action, blocked_reasons),
        "minimal_fix": _minimal_fix(action, blocked_reasons),
        "no_feedback_check": "research_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }
    validate_research_hypothesis_record(record)
    return record


def validate_research_hypothesis_record(record: dict[str, Any]) -> None:
    if record.get("current_stage") != CURRENT_STAGE:
        raise ValueError("current_stage must be ResearchHypothesis")
    hypothesis = record.get("research_hypothesis")
    if not isinstance(hypothesis, dict):
        raise ValueError("research_hypothesis must be an object")

    required_keys = {
        "research_id",
        "title",
        "source_type",
        "source_reference",
        "core_claim",
        "market_mechanism",
        "target_universe",
        "expected_signal",
        "required_data",
        "assumptions",
        "falsification_test",
        "risk_or_failure_modes",
        "confidence_level",
        "evidence_quality",
        "implementation_difficulty",
        "next_action",
        "reason_for_next_action",
    }
    missing = sorted(required_keys - set(hypothesis))
    if missing:
        raise ValueError(f"research_hypothesis missing keys: {missing}")
    if hypothesis["source_type"] not in SOURCE_TYPES:
        raise ValueError(f"invalid source_type: {hypothesis['source_type']}")
    if hypothesis["confidence_level"] not in CONFIDENCE_LEVELS:
        raise ValueError(f"invalid confidence_level: {hypothesis['confidence_level']}")
    if hypothesis["evidence_quality"] not in EVIDENCE_QUALITY_LEVELS:
        raise ValueError(f"invalid evidence_quality: {hypothesis['evidence_quality']}")
    if hypothesis["implementation_difficulty"] not in DIFFICULTY_LEVELS:
        raise ValueError(f"invalid implementation_difficulty: {hypothesis['implementation_difficulty']}")
    if hypothesis["next_action"] not in NEXT_ACTIONS:
        raise ValueError(f"invalid next_action: {hypothesis['next_action']}")
    if not hypothesis["required_data"]:
        raise ValueError("required_data must not be empty")
    if hypothesis["next_action"] == "convert_to_strategy_hypothesis" and not record.get("next_stage_input"):
        raise ValueError("convert_to_strategy_hypothesis requires next_stage_input")
    if hypothesis["next_action"] != "convert_to_strategy_hypothesis" and not record.get("blocker"):
        raise ValueError("non-convert records require blocker")
    if "trading recommendation" not in str(record.get("research_boundary", "")):
        raise ValueError("research boundary disclaimer is missing")


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
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    hypothesis = record["research_hypothesis"]
    flattened = {
        "schema_version": record["schema_version"],
        "current_stage": record["current_stage"],
        "research_boundary": record["research_boundary"],
        **hypothesis,
        "why_this_could_be_a_strategy": record["why_this_could_be_a_strategy"],
        "validation_requirement": record["validation_requirement"],
        "main_risks": record["main_risks"],
        "next_stage_input": record["next_stage_input"],
        "blocker": record["blocker"],
        "minimal_fix": record["minimal_fix"],
        "no_feedback_check": record["no_feedback_check"],
        "activation_boundary": record["activation_boundary"],
    }
    return flattened


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    flattened = [_flatten_record(record) for record in records]
    fieldnames = list(flattened[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in flattened:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


def build_manifest(records: list[dict[str, Any]], *, source_path: Path, run_id: str) -> dict[str, Any]:
    hypotheses = [record["research_hypothesis"] for record in records]
    action_counts = Counter(str(item.get("next_action")) for item in hypotheses)
    branch_counts = Counter(
        str(item.get("source_reference", {}).get("source_query_set") or "unknown")
        for item in hypotheses
    )
    confidence_counts = Counter(str(item.get("confidence_level")) for item in hypotheses)
    evidence_quality_counts = Counter(str(item.get("evidence_quality")) for item in hypotheses)
    return {
        "schema_version": "v0_3_research_hypotheses_manifest_0_1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": str(source_path),
        "record_count": len(records),
        "next_action_counts": dict(sorted(action_counts.items())),
        "source_query_set_counts": dict(sorted(branch_counts.items())),
        "confidence_level_counts": dict(sorted(confidence_counts.items())),
        "evidence_quality_counts": dict(sorted(evidence_quality_counts.items())),
        "research_boundary": RESEARCH_BOUNDARY,
        "no_feedback_check": "research_hypotheses_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_research_hypotheses(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    cards = read_jsonl(input_path)
    records = [evidence_card_to_research_hypothesis_record(card) for card in cards]
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
        default=datetime.now(timezone.utc).strftime("research_hypotheses_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = build_research_hypotheses(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
