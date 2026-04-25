"""Step 18 valuation/fundamental candidate contracts.

The contracts here describe candidate explanatory data only. They intentionally
do not define active valuation scores, production ranking columns, or backtest
inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricCategory(str, Enum):
    """Allowed Step 18 candidate metric categories."""

    VALUATION = "valuation"
    PROFITABILITY = "profitability"
    GROWTH = "growth"
    LEVERAGE = "leverage"
    QUALITY = "quality"
    DIAGNOSTIC = "diagnostic"


STEP18_CANDIDATE_SCHEMA_COLUMNS: tuple[str, ...] = (
    "symbol",
    "company_name",
    "metric_name",
    "metric_value",
    "metric_unit",
    "metric_category",
    "fiscal_period",
    "report_date",
    "available_date",
    "source",
    "quality_flags",
)

STEP18_OPTIONAL_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "name",
    "as_of_date",
    "universe_date",
    "notes",
    "filing_date",
    "source_report_id",
    "source_vendor",
    "collected_at",
)


@dataclass(frozen=True)
class ValuationCandidateRecord:
    """One Step 18 candidate valuation/fundamental metric observation."""

    symbol: str
    company_name: str
    metric_name: str
    metric_value: float
    metric_unit: str
    metric_category: str
    fiscal_period: str
    report_date: str
    available_date: str
    source: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    universe_date: str | None = None
    notes: str | None = None
    filing_date: str | None = None
    source_report_id: str | None = None
    source_vendor: str | None = None
    collected_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a DataFrame/report friendly dictionary."""

        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "metric_category": self.metric_category,
            "fiscal_period": self.fiscal_period,
            "report_date": self.report_date,
            "available_date": self.available_date,
            "source": self.source,
            "quality_flags": self.quality_flags,
            "universe_date": self.universe_date,
            "notes": self.notes,
            "filing_date": self.filing_date,
            "source_report_id": self.source_report_id,
            "source_vendor": self.source_vendor,
            "collected_at": self.collected_at,
        }


__all__ = (
    "STEP18_CANDIDATE_SCHEMA_COLUMNS",
    "STEP18_OPTIONAL_CANDIDATE_COLUMNS",
    "MetricCategory",
    "ValuationCandidateRecord",
)
