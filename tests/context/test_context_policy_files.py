from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CURRENT_CONTEXT_LIMIT = 8_000


def test_current_context_stays_under_size_threshold() -> None:
    text = (ROOT / "docs/context/current_context.md").read_text(encoding="utf-8")

    assert len(text) <= CURRENT_CONTEXT_LIMIT


def test_active_step20_packet_does_not_embed_long_step_history() -> None:
    text = (ROOT / "docs/context/active_step20_packet.md").read_text(encoding="utf-8")

    assert len(text) <= 6_000
    assert "Compact Step History" not in text
    assert "| Step 1 |" not in text
    assert "Step 01 To Step 19 Summary" not in text


def test_archives_are_not_default_required_or_optional_context() -> None:
    text = (ROOT / "docs/context/context_routing.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `"):
            continue
        cells = _split_markdown_row(stripped)
        required_context = cells[1]
        optional_context = cells[2]
        default_context = f"{required_context} {optional_context}"

        assert "docs/context/archive" not in default_context
        assert "docs/roadmap_archive" not in default_context


def test_packets_clearly_say_routing_aids_not_authority_documents() -> None:
    packet_paths = [ROOT / "docs/context/active_step20_packet.md"]
    generated_dir = ROOT / "docs/context/generated"
    if generated_dir.exists():
        packet_paths.extend(sorted(generated_dir.glob("*.md")))

    assert packet_paths
    for path in packet_paths:
        text = path.read_text(encoding="utf-8").lower()
        assert "routing aid" in text or "routing aids" in text
        assert "not an authority document" in text or "not authority documents" in text


def _split_markdown_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]
