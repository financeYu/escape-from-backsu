from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "context" / "check_context_conflicts.py"
SPEC = importlib.util.spec_from_file_location("check_context_conflicts", SCRIPT_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_conflict_checker_catches_forbidden_wording(tmp_path: Path) -> None:
    context_dir = tmp_path / "docs/context"
    context_dir.mkdir(parents=True)
    (context_dir / "bad.md").write_text(
        "\n".join(
            [
                "valuation data is allowed inside technical_composite_score.",
                "diagnostics are alpha signals.",
                "generated report output can feed upstream score construction.",
                "future returns can be used as score inputs.",
                "Step 20 final Done validation complete.",
            ]
        ),
        encoding="utf-8",
    )

    findings = module.check_conflicts(tmp_path)
    codes = {finding.code for finding in findings}

    assert "valuation_in_technical_composite" in codes
    assert "diagnostics_as_alpha" in codes
    assert "generated_output_feedback" in codes
    assert "future_returns_as_inputs" in codes
    assert "step20_final_validation_claimed_complete" in codes


def test_conflict_checker_ignores_negated_guardrails(tmp_path: Path) -> None:
    context_dir = tmp_path / "docs/context"
    context_dir.mkdir(parents=True)
    (context_dir / "safe.md").write_text(
        "\n".join(
            [
                "Financial data must not enter technical_composite_score.",
                "Diagnostics are not alpha signals.",
                "Generated report output must not feed upstream score construction.",
                "Do not use future returns as score inputs.",
                "Step 20 final Done validation is not complete.",
            ]
        ),
        encoding="utf-8",
    )

    findings = module.check_conflicts(tmp_path)

    assert findings == ()


def test_conflict_checker_ignores_risk_condition_wording(tmp_path: Path) -> None:
    context_dir = tmp_path / "docs/context"
    context_dir.mkdir(parents=True)
    (context_dir / "safe.md").write_text(
        "- financial data may have entered `technical_composite_score` or `final_composite_score`",
        encoding="utf-8",
    )

    findings = module.check_conflicts(tmp_path)

    assert findings == ()


def test_conflict_checker_allows_step20_complete_after_roadmap_closure(tmp_path: Path) -> None:
    context_dir = tmp_path / "docs/context"
    context_dir.mkdir(parents=True)
    (tmp_path / "docs/roadmap_status.md").write_text(
        "| Step | Status |\n| --- | --- |\n| Step 20 | COMPLETE |\n",
        encoding="utf-8",
    )
    (context_dir / "current_context.md").write_text(
        "Step 20 = COMPLETE / KOSPI200 MVP final validation closed.",
        encoding="utf-8",
    )

    findings = module.check_conflicts(tmp_path)

    assert findings == ()
