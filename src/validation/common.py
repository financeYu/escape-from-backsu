"""Shared lightweight helpers for validation guardrails."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd


def column_names(columns: pd.DataFrame | Iterable[str]) -> tuple[str, ...]:
    """Return string column names from a frame or iterable."""

    if isinstance(columns, pd.DataFrame):
        return tuple(str(column) for column in columns.columns)
    return tuple(str(column) for column in columns)


def coerce_frame(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Copy or coerce structured validation input into a DataFrame."""

    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, Mapping):
        return pd.DataFrame([dict(data)])
    return pd.DataFrame(list(data))


def collect_text(value: object, parts: list[str], *, include_mapping_keys: bool = True) -> None:
    """Collect nested string content from mappings and simple sequences."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if include_mapping_keys:
                parts.append(str(key))
            collect_text(child, parts, include_mapping_keys=include_mapping_keys)
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            collect_text(child, parts, include_mapping_keys=include_mapping_keys)
        return
    if isinstance(value, str):
        parts.append(value)


def extract_text_from_frame(frame: pd.DataFrame, *, include_mapping_keys: bool = True) -> str:
    """Return nested text content from all frame records."""

    if frame.empty:
        return ""
    parts: list[str] = []
    for record in frame.to_dict(orient="records"):
        collect_text(record, parts, include_mapping_keys=include_mapping_keys)
    return "\n".join(parts)


def string_tuple(value: Any) -> tuple[str, ...]:
    """Return a tuple of strings for scalar, mapping, and iterable inputs."""

    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return tuple(str(item) for item in value.keys())
    try:
        return tuple(str(item) for item in value)
    except TypeError:
        return (str(value),)


__all__ = (
    "coerce_frame",
    "collect_text",
    "column_names",
    "extract_text_from_frame",
    "string_tuple",
)
