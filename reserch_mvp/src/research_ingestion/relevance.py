from __future__ import annotations

import re
from typing import Any


DEFAULT_RELEVANCE_POLICY = {
    "min_positive_keyword_hits": 1,
    "reject_on_exclude_keyword": True,
    "manual_review_when_abstract_missing": True,
}


def assess_collection_relevance(
    paper: dict[str, Any],
    query_set: dict[str, Any],
    relevance_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess whether collected metadata should proceed to normalization.

    This is a conservative metadata gate. It does not verify paper claims and it
    does not score research quality.
    """

    policy = {**DEFAULT_RELEVANCE_POLICY, **(relevance_defaults or {})}
    positive_terms = _terms(query_set.get("keywords", []))
    exclude_terms = _terms(query_set.get("exclude_keywords", []))
    text = _paper_text(paper)
    positive_hits = _matching_terms(text, positive_terms)
    exclude_hits = _matching_terms(text, exclude_terms)
    required_group_hits = _required_group_hits(text, query_set.get("required_keyword_groups", []))
    abstract_available = bool((paper.get("abstract") or "").strip())

    if exclude_hits and policy.get("reject_on_exclude_keyword", True):
        return _exclude_keyword_relevance_result(positive_hits, exclude_hits, required_group_hits, abstract_available)

    missing_required_groups = [
        group_name
        for group_name, group_hits in required_group_hits.items()
        if not group_hits
    ]
    if missing_required_groups:
        return _missing_group_relevance_result(
            positive_hits,
            exclude_hits,
            required_group_hits,
            abstract_available,
            missing_required_groups,
        )

    min_hits = int(policy.get("min_positive_keyword_hits", 1))
    if len(positive_hits) < min_hits:
        return _insufficient_keyword_relevance_result(positive_hits, exclude_hits, required_group_hits, abstract_available)

    manual_review = bool(policy.get("manual_review_when_abstract_missing", True) and not abstract_available)
    return _accepted_relevance_result(positive_hits, exclude_hits, required_group_hits, abstract_available, manual_review)


def _exclude_keyword_relevance_result(positive_hits: list[str], exclude_hits: list[str], required_group_hits: dict[str, list[str]], abstract_available: bool) -> dict[str, Any]:
    return {
        "status": "rejected",
        "positive_keyword_hits": positive_hits,
        "exclude_keyword_hits": exclude_hits,
        "required_keyword_group_hits": required_group_hits,
        "abstract_available": abstract_available,
        "manual_review_required": True,
        "reason_ko": "query-set exclude keyword가 metadata/title/abstract에서 감지되어 downstream evidence 생성을 막았습니다.",
    }


def _missing_group_relevance_result(positive_hits: list[str], exclude_hits: list[str], required_group_hits: dict[str, list[str]], abstract_available: bool, missing_required_groups: list[str]) -> dict[str, Any]:
    return {
        "status": "rejected",
        "positive_keyword_hits": positive_hits,
        "exclude_keyword_hits": exclude_hits,
        "required_keyword_group_hits": required_group_hits,
        "abstract_available": abstract_available,
        "manual_review_required": True,
        "reason_ko": (
            "필수 relevance keyword group이 충족되지 않아 제외했습니다: "
            + ", ".join(missing_required_groups)
        ),
    }


def _insufficient_keyword_relevance_result(positive_hits: list[str], exclude_hits: list[str], required_group_hits: dict[str, list[str]], abstract_available: bool) -> dict[str, Any]:
    return {
        "status": "rejected",
        "positive_keyword_hits": positive_hits,
        "exclude_keyword_hits": exclude_hits,
        "required_keyword_group_hits": required_group_hits,
        "abstract_available": abstract_available,
        "manual_review_required": True,
        "reason_ko": "query-set keyword와 충분히 일치하지 않아 metadata relevance gate에서 제외했습니다.",
    }


def _accepted_relevance_result(positive_hits: list[str], exclude_hits: list[str], required_group_hits: dict[str, list[str]], abstract_available: bool, manual_review: bool) -> dict[str, Any]:
    return {
        "status": "accepted",
        "positive_keyword_hits": positive_hits,
        "exclude_keyword_hits": exclude_hits,
        "required_keyword_group_hits": required_group_hits,
        "abstract_available": abstract_available,
        "manual_review_required": manual_review,
        "reason_ko": (
            "abstract가 없어 metadata-only 수집 항목으로 수동 검토가 필요합니다."
            if manual_review
            else "query-set keyword와 metadata/title/abstract가 일치하여 수집 후보로 유지했습니다."
        ),
    }


def apply_collection_relevance_gate(
    papers: list[dict[str, Any]],
    query_set: dict[str, Any],
    relevance_defaults: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for paper in papers:
        assessment = assess_collection_relevance(paper, query_set, relevance_defaults)
        annotated = dict(paper)
        annotated["collection_relevance"] = assessment
        if assessment["manual_review_required"]:
            annotated["manual_review_required"] = True
            notes = list(annotated.get("conflict_notes", []))
            note = assessment["reason_ko"]
            if note not in notes:
                notes.append(note)
            annotated["conflict_notes"] = notes
        if assessment["status"] == "accepted":
            accepted.append(annotated)
        else:
            rejected.append(annotated)
    return accepted, rejected


def _paper_text(paper: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in ["title", "abstract", "venue", "publisher"]:
        value = paper.get(field)
        if value:
            parts.append(str(value))
    for field in ["topics", "fields_of_study", "categories", "source_adapters"]:
        values = paper.get(field) or []
        parts.extend(str(value) for value in values if value)
    return _normalize(" ".join(parts))


def _terms(values: list[Any]) -> list[str]:
    result = []
    for value in values:
        term = _normalize(str(value))
        if term:
            result.append(term)
    return result


def _required_group_hits(text: str, groups: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for index, group in enumerate(groups or []):
        name = str(group.get("name") or f"group_{index + 1}")
        result[name] = _matching_terms(text, _terms(group.get("keywords", [])))
    return result


def _matching_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _contains_term(text, term)]


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    if " " in term:
        return term in text
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))


def _normalize(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9가-힣]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()
