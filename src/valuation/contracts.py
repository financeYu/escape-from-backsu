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
    "ticker",
    "company_name",
    "metric",
    "value",
    "metric_unit",
    "metric_category",
    "period",
    "filing_date",
    "availability_date",
    "source_vendor",
    "collected_at",
    "quality_flags",
)

STEP18_CANDIDATE_SOURCE_ID_COLUMNS: tuple[str, ...] = (
    "disclosure_id",
    "source_report_id",
)

STEP18_OPTIONAL_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "symbol",
    "name",
    "metric_name",
    "metric_value",
    "fiscal_period",
    "available_date",
    "as_of_date",
    "report_date",
    "universe_date",
    "source",
    "notes",
    "disclosure_id",
    "source_report_id",
)


@dataclass(frozen=True)
class ValuationCandidateRecord:
    """One Step 18 candidate valuation/fundamental metric observation."""

    ticker: str
    company_name: str
    metric: str
    value: float
    metric_unit: str
    metric_category: str
    period: str
    filing_date: str
    availability_date: str
    source_vendor: str
    collected_at: str
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    disclosure_id: str | None = None
    source_report_id: str | None = None
    report_date: str | None = None
    universe_date: str | None = None
    source: str | None = None
    notes: str | None = None

    @property
    def symbol(self) -> str:
        """Backward-compatible alias for the canonical ticker."""

        return self.ticker

    @property
    def metric_name(self) -> str:
        """Backward-compatible alias for the canonical metric name."""

        return self.metric

    @property
    def metric_value(self) -> float:
        """Backward-compatible alias for the canonical metric value."""

        return self.value

    @property
    def fiscal_period(self) -> str:
        """Backward-compatible alias for the canonical reporting period."""

        return self.period

    @property
    def available_date(self) -> str:
        """Backward-compatible alias for the canonical availability date."""

        return self.availability_date

    def to_dict(self) -> dict[str, Any]:
        """Return a DataFrame/report friendly dictionary."""

        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "metric": self.metric,
            "value": self.value,
            "metric_unit": self.metric_unit,
            "metric_category": self.metric_category,
            "period": self.period,
            "filing_date": self.filing_date,
            "availability_date": self.availability_date,
            "source_vendor": self.source_vendor,
            "collected_at": self.collected_at,
            "quality_flags": self.quality_flags,
            "disclosure_id": self.disclosure_id,
            "source_report_id": self.source_report_id,
            "report_date": self.report_date,
            "universe_date": self.universe_date,
            "source": self.source,
            "notes": self.notes,
        }


__all__ = (
    "STEP18_CANDIDATE_SCHEMA_COLUMNS",
    "STEP18_CANDIDATE_SOURCE_ID_COLUMNS",
    "STEP18_OPTIONAL_CANDIDATE_COLUMNS",
    "MetricCategory",
    "ValuationCandidateRecord",
)
