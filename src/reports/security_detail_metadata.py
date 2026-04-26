"""Step 16 security detail report metadata helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import math
from typing import Any

import numpy as np
import pandas as pd

from src.composite.contracts import CompositeInputSpec


SOURCE_ADOPTION_METADATA_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "adoption_state",
    "source_review_status",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "manual_review_required",
    "limitations",
)


def coerce_optional_metadata_frame(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]] | None,
) -> pd.DataFrame | None:
    if rows is None:
        return None
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(list(rows))


def merge_security_detail_metadata(
    metadata_frames: Sequence[pd.DataFrame | None],
    *,
    registry: Sequence[CompositeInputSpec],
) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {
        spec.score_name: {
            "score_name": spec.score_name,
            "family": spec.family,
            "branch": spec.branch,
            "role": spec.role.value,
            "eligibility": spec.eligibility.value,
            "normalized_score_column": spec.normalized_column,
        }
        for spec in registry
    }
    for frame in metadata_frames:
        if frame is None or frame.empty:
            continue
        if "score_name" not in frame.columns:
            raise ValueError("Step 16 metadata tables must include score_name.")
        for _, row in frame.iterrows():
            score_name = str(row["score_name"])
            target = metadata.setdefault(score_name, {"score_name": score_name})
            for column, value in row.items():
                if is_present(value):
                    target[str(column)] = safe_scalar(value)
    return metadata


def source_adoption_metadata(
    metadata_by_score: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for score_name in sorted(metadata_by_score):
        metadata = metadata_by_score[score_name]
        if "adoption_state" not in metadata and "source_review_status" not in metadata:
            continue
        row = {
            column: metadata[column]
            for column in SOURCE_ADOPTION_METADATA_COLUMNS
            if column in metadata and is_present(metadata[column])
        }
        if row:
            rows.append(row)
    return tuple(rows)


def safe_float(value: object) -> float | None:
    if not is_present(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def safe_int(value: object) -> int | None:
    if not is_present(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed)


def safe_scalar(value: object) -> Any:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return safe_float(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def is_present(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return True
    if isinstance(missing, (bool, np.bool_)):
        return not bool(missing)
    return True


__all__ = (
    "SOURCE_ADOPTION_METADATA_COLUMNS",
    "coerce_optional_metadata_frame",
    "is_present",
    "merge_security_detail_metadata",
    "safe_float",
    "safe_int",
    "safe_scalar",
    "source_adoption_metadata",
)
