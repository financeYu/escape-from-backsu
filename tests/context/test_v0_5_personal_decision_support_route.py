from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v0_5_route_is_registered_as_contract_only_personal_support() -> None:
    registry = _text("docs/context/EXTENSION_REGISTRY.toml")

    assert "[extension.personal_decision_support_v0_5]" in registry
    assert "active_contract_only_personal_decision_support_route" in registry
    assert "docs/extension/v0_5_personal_decision_support_route.md" in registry
    assert "Quant_mvp/scripts/build_v0_5_personal_decision_support_packets.py" in registry
    assert "Quant_mvp/data/v0_5/personal_decision_support/v0_5_personal_decision_support_manifest.json" in registry
    assert "new market-data ingestion" in registry
    assert "order generation" in registry


def test_v0_5_route_requires_packet_guardrails() -> None:
    route = _text("docs/extension/v0_5_personal_decision_support_route.md")

    for required in (
        "PersonalDecisionSupportPacket",
        "no_order_generation_check",
        "no_position_sizing_check",
        "no_prediction_claim_check",
        "no_production_activation_check",
        "manual_review_checklist",
    ):
        assert required in route


def test_v0_5_route_keeps_runtime_actions_forbidden() -> None:
    route = _text("docs/extension/v0_5_personal_decision_support_route.md")

    forbidden_terms = (
        "`buy`",
        "`sell`",
        "`hold`",
        "`rebalance`",
        "`move_to_cash`",
        "`position_size`",
        "`order`",
    )
    for term in forbidden_terms:
        assert term in route
    assert "The route must not answer with an instruction to transact." in route


def test_v0_5_gap_assessment_records_current_limitations() -> None:
    assessment = _text("docs/extension/v0_5_pre_entry_gap_assessment.md")

    for expected in (
        "candidate-level metric rows: 62",
        "null-label rows: 636",
        "missing EvaluationEvidence rows: 616",
        "needs-more-evidence rows: 20",
        "full validation was interrupted",
    ):
        assert expected in assessment
