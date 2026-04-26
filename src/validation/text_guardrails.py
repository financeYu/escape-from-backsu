"""Shared text matching helpers for validation guardrails."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import re

AllowedMatchPredicate = Callable[[str, re.Match[str], str], bool]


def contains_forbidden_term(lowered: str, term: str) -> bool:
    """Return whether a lowercased text contains a term as phrase or token."""

    normalized_term = term.lower()
    if " " in normalized_term or "-" in normalized_term or "_" in normalized_term:
        return normalized_term in lowered
    return (
        re.search(rf"(?<![A-Za-z0-9_]){re.escape(normalized_term)}(?![A-Za-z0-9_])", lowered)
        is not None
    )


def find_forbidden_terms(text: str, terms: set[str] | frozenset[str]) -> list[str]:
    """Return forbidden term labels found in text."""

    lowered = text.lower()
    return [term for term in sorted(terms) if contains_forbidden_term(lowered, term)]


def contains_forbidden_pattern(
    lowered: str,
    pattern: str,
    *,
    label: str = "",
    flags: int = re.IGNORECASE | re.DOTALL,
    is_allowed_match: AllowedMatchPredicate | None = None,
) -> bool:
    """Return whether a regex pattern has a non-negated forbidden match."""

    for match in re.finditer(pattern, lowered, flags=flags):
        if is_allowed_match is not None and is_allowed_match(lowered, match, label):
            continue
        return True
    return False


def find_forbidden_pattern_labels(
    text: str,
    patterns: Mapping[str, str],
    *,
    flags: int = re.IGNORECASE | re.DOTALL,
    is_allowed_match: AllowedMatchPredicate | None = None,
) -> list[str]:
    """Return labels whose regex patterns have non-negated forbidden matches."""

    lowered = text.lower()
    forbidden: list[str] = []
    for label, pattern in patterns.items():
        if contains_forbidden_pattern(
            lowered,
            pattern,
            label=label,
            flags=flags,
            is_allowed_match=is_allowed_match,
        ):
            forbidden.append(label)
    return sorted(forbidden)


__all__ = (
    "contains_forbidden_pattern",
    "contains_forbidden_term",
    "find_forbidden_pattern_labels",
    "find_forbidden_terms",
)
