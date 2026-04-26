from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.valuation import (  # noqa: E402
    MetricCategory,
    build_step18_candidate_report,
    load_metric_registry,
    validate_candidate_records,
)
from src.validation.step18_valuation_fundamental_guardrails import (  # noqa: E402
    validate_step18_candidate_report_text,
)


def candidate_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "ticker": "005930",
        "company_name": "Samsung Electronics",
        "metric": "per",
        "value": 12.5,
        "metric_unit": "ratio",
        "metric_category": MetricCategory.VALUATION.value,
        "period": "2025Q4",
        "report_date": "2026-03-15",
        "availability_date": "2026-03-31",
        "source": "synthetic_fixture",
        "universe_date": "2026-04-01",
        "quality_flags": ("synthetic", "candidate_only"),
        "notes": "Synthetic Step 18 fixture.",
        "filing_date": "2026-03-20",
        "source_report_id": "SYN-2025Q4-005930",
        "source_vendor": "synthetic",
        "collected_at": "2026-04-01",
    }
    record.update(overrides)
    return record


def test_metric_registry_loads_as_candidate_only_config() -> None:
    registry = load_metric_registry(PROJECT_ROOT / "config" / "valuation_fundamental_metrics.toml")

    names = {spec.metric_name for spec in registry}
    assert {"per", "pbr", "roe", "debt_to_equity", "eps_growth_yoy"}.issubset(names)
    assert "ev_ebitda" not in names
    assert all(spec.candidate_only for spec in registry)


def test_candidate_records_can_be_parsed_and_validated() -> None:
    records = validate_candidate_records([candidate_record()], evaluation_date="2026-04-01")

    assert len(records) == 1
    (record,) = records
    assert record.ticker == "005930"
    assert record.metric == "per"
    assert record.availability_date == "2026-03-31"


def test_legacy_aliases_are_allowed_but_stored_as_canonical_fields() -> None:
    record = candidate_record(
        ticker=None,
        symbol="005930",
        metric=None,
        metric_name="per",
        value=None,
        metric_value=12.5,
        period=None,
        fiscal_period="2025Q4",
        availability_date=None,
        as_of_date="2026-03-31",
    )
    for field in ("ticker", "metric", "value", "period", "availability_date"):
        record.pop(field)

    parsed = validate_candidate_records([record], evaluation_date="2026-04-01")

    (parsed_record,) = parsed
    assert parsed_record.ticker == "005930"
    assert parsed_record.metric == "per"
    assert parsed_record.value == 12.5
    assert parsed_record.period == "2025Q4"
    assert parsed_record.availability_date == "2026-03-31"


def test_future_available_date_is_rejected_for_earlier_evaluation() -> None:
    with pytest.raises(ValueError, match="not available for evaluation_date"):
        validate_candidate_records(
            [candidate_record(availability_date="2026-04-10")],
            evaluation_date="2026-04-01",
        )


def test_missing_available_date_or_as_of_date_is_rejected() -> None:
    record = candidate_record()
    record.pop("availability_date")

    with pytest.raises(ValueError, match="availability_date/available_date/as_of_date"):
        validate_candidate_records([record], evaluation_date="2026-04-01")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("metric", "ev_ebitda", "outside the allowed registry"),
        ("metric_category", "quality", "metric_category does not match registry"),
        ("metric_unit", "percent", "metric_unit does not match registry"),
        ("value", "not_numeric", "value/metric_value must be numeric"),
        ("value", math.inf, "value/metric_value must be finite"),
    ),
)
def test_invalid_metric_contract_values_are_rejected(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_candidate_records([candidate_record(**{field: value})], evaluation_date="2026-04-01")


@pytest.mark.parametrize(
    "unsafe_payload",
    (
        {"quality_flags": ("future_filled",)},
        {"quality_flags": "synthetic|cross_sectional_imputed"},
        {"imputation_method": "peer_fill"},
        {"filled_from_future": True},
    ),
)
def test_unsafe_imputation_is_rejected(unsafe_payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="unsafe imputation"):
        validate_candidate_records([candidate_record(**unsafe_payload)], evaluation_date="2026-04-01")


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("filing_date", "filing_date"),
        ("source_vendor", "source_vendor"),
        ("collected_at", "collected_at"),
    ),
)
def test_required_point_in_time_metadata_is_rejected_when_missing(
    field: str,
    message: str,
) -> None:
    record = candidate_record()
    record.pop(field)

    with pytest.raises(ValueError, match=message):
        validate_candidate_records([record], evaluation_date="2026-04-01")


def test_disclosure_id_can_satisfy_source_identifier_requirement() -> None:
    record = candidate_record(disclosure_id="DISC-2025Q4-005930")
    record.pop("source_report_id")

    parsed = validate_candidate_records([record], evaluation_date="2026-04-01")

    (parsed_record,) = parsed
    assert parsed_record.disclosure_id == "DISC-2025Q4-005930"
    assert parsed_record.source_report_id is None


def test_missing_source_identifier_is_rejected() -> None:
    record = candidate_record()
    record.pop("source_report_id")

    with pytest.raises(ValueError, match="source_report_id or disclosure_id"):
        validate_candidate_records([record], evaluation_date="2026-04-01")


def test_reporting_lag_and_stale_candidate_policies_are_enforced() -> None:
    with pytest.raises(ValueError, match="availability_date cannot be before filing_date"):
        validate_candidate_records(
            [candidate_record(filing_date="2026-04-01", availability_date="2026-03-31")],
            evaluation_date="2026-04-01",
        )

    with pytest.raises(ValueError, match="reporting lag exceeds policy"):
        validate_candidate_records(
            [candidate_record(filing_date="2025-01-01", availability_date="2025-06-01")],
            evaluation_date="2025-06-01",
        )

    with pytest.raises(ValueError, match="availability_date is stale"):
        validate_candidate_records(
            [candidate_record(availability_date="2024-01-01", filing_date="2023-12-20")],
            evaluation_date="2026-04-01",
        )


def test_candidate_report_has_required_boundary_notices() -> None:
    report = build_step18_candidate_report([candidate_record()], evaluation_date="2026-04-01")

    validate_step18_candidate_report_text(report)
    assert "not activated in final ranking" in report
    assert "not validated alpha signals" in report
