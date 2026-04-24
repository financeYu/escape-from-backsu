"""DataFrame normalization helpers."""

from __future__ import annotations

import pandas as pd

from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN, PRICE_COLUMNS


def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove empty rows and convert columns to analysis-friendly types."""

    if df.empty:
        raise ValueError("Input DataFrame is empty.")

    cleaned = df.dropna(how="any").copy()

    required_columns = [DATE_COLUMN, *PRICE_COLUMNS]
    missing_columns = [column for column in required_columns if column not in cleaned.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    cleaned[DATE_COLUMN] = pd.to_datetime(cleaned[DATE_COLUMN], errors="coerce")

    for column in PRICE_COLUMNS:
        cleaned[column] = (
            cleaned[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(r"[^\d.\-]", "", regex=True)
            .str.strip()
        )
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=[DATE_COLUMN, *PRICE_COLUMNS])
    cleaned = cleaned.sort_values(DATE_COLUMN, ascending=True).reset_index(drop=True)

    if cleaned.empty:
        raise ValueError("No valid rows remain after cleaning.")

    if CLOSE_COLUMN not in cleaned.columns:
        raise ValueError(f"The DataFrame does not contain the '{CLOSE_COLUMN}' column.")

    return cleaned

