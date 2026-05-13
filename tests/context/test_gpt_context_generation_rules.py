from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "context" / "build_context_packet.py"
SPEC = importlib.util.spec_from_file_location("build_context_packet", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_gpt_context_generation_rules_doc_exists() -> None:
    assert (ROOT / "docs/context/GPT_CONTEXT_GENERATION_RULES.md").exists()


def test_gpt_rules_define_required_budget_and_repetition_rules() -> None:
    text = _read("docs/context/GPT_CONTEXT_GENERATION_RULES.md")

    assert "at most 3 confirmed context facts" in text
    assert "Default GPT input = one generated brief only" in text
    assert "Do not paste this document into GPT" in text
    assert ".agents/skills/gpt-context-refresh/SKILL.md" in text
    assert "v0.3 research-to-strategy adoption is the active route" in text
    assert "v1.x staged release development is active" in text
    assert (
        "Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision."
        in text
    )
    assert "Completed Step 1-20 history is archive-only" in text
    assert "Full validation logs are archive-only" in text
    assert "full score catalog" in text.lower()


def test_context_budget_policy_has_gpt_specific_defaults() -> None:
    text = _read("docs/context/CONTEXT_BUDGET_POLICY.md")

    assert "Default GPT input = one generated brief only" in text
    assert "docs/context/gpt/gpt_context_quant.md" in text
    assert "GPT receives the generated brief, not the internal rules files" in text
    assert ".agents/skills/gpt-context-refresh/SKILL.md" in text
    assert "v0.3 research-to-strategy adoption" in text
    assert "v1.x staged release development" in text
    assert "No Step-by-Step roadmap table in GPT default context" in text
    assert "No repeated Step completion summaries" in text
    assert "No pasted old validation logs" in text
    assert "No full score catalog" in text
    assert "Route to file paths instead of embedding file bodies" in text


def test_gpt_routing_index_default_routes_do_not_point_to_archives() -> None:
    table = _section(_read("docs/context/CONTEXT_ROUTING_INDEX.md"), "## Internal GPT Route Map", "## Archive Routes")
    default_route_lines = [
        line
        for line in table.splitlines()
        if line.startswith("|") and "archive/provenance lookup" not in line.lower()
    ]
    default_routes = "\n".join(default_route_lines)

    assert "docs/context/archive" not in default_routes
    assert "docs/roadmap_archive" not in default_routes
    assert "archive/provenance lookup" in table
    assert "on-demand only" in table


def test_generated_sample_gpt_brief_stays_small_and_avoids_history() -> None:
    text = _read("docs/context/generated/sample_gpt_context_brief.md")

    assert "sample only" in text
    assert len(text.splitlines()) <= 80
    assert "GPT_CONTEXT_GENERATION_RULES.md" not in text
    assert "CONTEXT_ROUTING_INDEX.md" not in text
    assert "| Step 1 |" not in text
    assert "Step 01 To Step 20 History" not in text
    assert "Full validation" not in text
    assert "score catalog" not in text.lower()


def test_gpt_context_quant_is_the_submission_brief() -> None:
    text = _read("docs/context/gpt/gpt_context_quant.md")

    assert len(text.splitlines()) <= 80
    assert "GPT Context Quant" in text
    assert "Do not repeat completed Step history" in text
    assert "GPT_CONTEXT_GENERATION_RULES.md" not in text
    assert "CONTEXT_ROUTING_INDEX.md" not in text
    assert "| Step 1 |" not in text


def test_gpt_brief_builder_stays_under_80_lines() -> None:
    text = module.build_gpt_brief(
        module.GptBriefConfig(
            project_root=ROOT,
            request="Create a focused GPT-facing planning brief.",
            output_path=ROOT / "docs/context/generated/test_gpt_brief.md",
        )
    )

    assert len(text.splitlines()) <= 80
    assert text.count("v0.3 research-to-strategy adoption") == 1
    assert text.count("v1.x staged release development") == 1
    assert "v0.2 `prob_up_1d_candidate` is archived/supporting compatibility only" in text
    assert (
        "Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision."
        in text
    )
    assert "| Step 1 |" not in text
    assert "Completed Step 1-20 and v0.1/v0.2 material are archive-only" in text
    assert "GPT_CONTEXT_GENERATION_RULES.md" not in text
    assert "CONTEXT_ROUTING_INDEX.md" not in text
    assert "## Route-Only References" in text


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]
