"""Shared field and column matching helpers for validation guardrails."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import re

import pandas as pd

from src.validation.common import column_names

ColumnPredicate = Callable[[str], bool]
TokenGetter = Callable[[str], Iterable[str]]


def underscore_tokens(value: str) -> tuple[str, ...]:
    """Split a normalized identifier on underscores only."""

    return tuple(value.split("_"))


def identifier_tokens(value: str) -> tuple[str, ...]:
    """Split a normalized identifier on any non-alphanumeric separator."""

    return tuple(token for token in re.split(r"[^a-z0-9]+", value) if token)


def find_forbidden_columns_by_rules(
    columns: pd.DataFrame | Iterable[str],
    *,
    exact: Iterable[str] = (),
    prefixes: tuple[str, ...] = (),
    suffixes: tuple[str, ...] = (),
    substrings: Iterable[str] = (),
    tokens: Iterable[str] = (),
    token_getter: TokenGetter = underscore_tokens,
    extra_predicates: Iterable[ColumnPredicate] = (),
) -> list[str]:
    """Return columns whose normalized names match any supplied rule."""

    exact_set = frozenset(exact)
    substring_tuple = tuple(substrings)
    token_set = frozenset(tokens)
    predicates = tuple(extra_predicates)

    forbidden: set[str] = set()
    for column in column_names(columns):
        normalized = column.lower()
        column_tokens = set(token_getter(normalized)) if token_set else set()
        if (
            normalized in exact_set
            or normalized.startswith(prefixes)
            or normalized.endswith(suffixes)
            or any(term in normalized for term in substring_tuple)
            or bool(column_tokens.intersection(token_set))
            or any(predicate(normalized) for predicate in predicates)
        ):
            forbidden.add(column)
    return sorted(forbidden)


def normalize_field_ref(value: str) -> str:
    """Normalize a field reference while preserving basename semantics."""

    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return normalized.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]


def find_forbidden_field_refs(
    values: Iterable[str],
    forbidden_fields: Iterable[str],
    *,
    match_mode: str = "exact_or_suffix",
) -> list[str]:
    """Return field refs matching exact/suffix or exact/contains forbidden rules."""

    fields = frozenset(forbidden_fields)
    found: set[str] = set()
    for value in values:
        normalized = normalize_field_ref(value)
        if normalized in fields:
            found.add(value)
            continue
        if match_mode == "exact_or_suffix":
            if any(normalized.endswith(f"_{field}") for field in fields):
                found.add(value)
            continue
        if match_mode == "exact_or_contains":
            if any(field in normalized for field in fields):
                found.add(value)
            continue
        raise ValueError(f"unsupported forbidden field ref match mode: {match_mode}")
    return sorted(found)


__all__ = (
    "find_forbidden_columns_by_rules",
    "find_forbidden_field_refs",
    "identifier_tokens",
    "normalize_field_ref",
    "underscore_tokens",
)
