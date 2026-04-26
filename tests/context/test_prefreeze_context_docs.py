from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


LINE_LIMITS = {
    "docs/context/MVP_V0_1_BASELINE.md": 80,
    "docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md": 120,
    "docs/release/MVP_V0_1_QUICKSTART.md": 120,
    "docs/release/MVP_V0_1_VALIDATION_LADDER.md": 120,
}


def test_prefreeze_docs_stay_under_line_limits() -> None:
    for rel_path, limit in LINE_LIMITS.items():
        lines = _read(rel_path).splitlines()

        assert len(lines) <= limit, rel_path


def test_context_budget_policy_defines_default_context_shape() -> None:
    text = _read("docs/context/CONTEXT_BUDGET_POLICY.md")

    assert "docs/context/MVP_V0_1_BASELINE.md" in text
    assert "exactly one active packet" in text
    assert "docs/context/CONTEXT_ROUTING_INDEX.md" in text


def test_context_budget_policy_marks_completed_history_archive_only() -> None:
    text = _read("docs/context/CONTEXT_BUDGET_POLICY.md")

    assert "Completed Step 1-20 history is archive-only" in text
    assert "Full validation logs are archive-only" in text
    assert "Score catalog dumps are not default context" in text


def test_routing_index_does_not_embed_long_step_history() -> None:
    text = _read("docs/context/CONTEXT_ROUTING_INDEX.md")

    assert "| Step 1 |" not in text
    assert "Compact Step History" not in text
    assert "Step 01 To Step 20 History" not in text


def test_release_docs_do_not_contain_forbidden_claim_language() -> None:
    release_paths = [
        "docs/release/MVP_V0_1_QUICKSTART.md",
        "docs/release/MVP_V0_1_VALIDATION_LADDER.md",
    ]
    forbidden_phrases = (
        "buy recommendation",
        "sell recommendation",
        "hold recommendation",
        "proven alpha",
        "market beating",
        "guaranteed return",
        "expected return signal",
        "target price support",
        "undervalued opportunity",
    )

    for rel_path in release_paths:
        text = _read(rel_path).lower()
        for phrase in forbidden_phrases:
            assert phrase not in text, f"{phrase!r} found in {rel_path}"


def test_no_default_context_route_points_to_archive_history() -> None:
    budget = _section(
        _read("docs/context/CONTEXT_BUDGET_POLICY.md"),
        "## Default Prompt Context",
        "## Archive-Only Context",
    )
    routing_default = _section(
        _read("docs/context/CONTEXT_ROUTING_INDEX.md"),
        "## Default Prompt Context",
        "## Routes",
    )

    default_text = f"{budget}\n{routing_default}"

    assert "docs/context/archive" not in default_text
    assert "docs/roadmap_archive" not in default_text


def test_active_prefreeze_packet_states_no_quant_logic_change() -> None:
    text = _read("docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md").lower()

    assert "does not change quant logic" in text


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]
