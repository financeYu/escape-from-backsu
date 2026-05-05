from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL = ROOT / ".agents/skills/gpt-context-refresh/SKILL.md"
RULES = ROOT / "docs/context/GPT_CONTEXT_GENERATION_RULES.md"


REQUIRED_SKILL_PHRASES = (
    "v0.3 research-to-strategy adoption is the active route",
    "Refresh GPT-facing local context artifacts only after an explicit user request",
    "docs/context/gpt/",
    "scripts\\context\\refresh_gpt_references.py --user-requested --request",
    "fetch=false",
    "push=false",
    "commit=false",
)

REQUIRED_RULE_PHRASES = (
    "Default GPT input = one generated brief only",
    "at most 3 confirmed context facts",
    "Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.",
    "GPT-facing output refresh commands require `--user-requested`",
)


def validate() -> list[str]:
    errors: list[str] = []
    skill_text = _read(SKILL)
    rules_text = _read(RULES)

    for phrase in REQUIRED_SKILL_PHRASES:
        if phrase not in skill_text:
            errors.append(f"missing skill phrase: {phrase}")
    for phrase in REQUIRED_RULE_PHRASES:
        if phrase not in rules_text:
            errors.append(f"missing rules phrase: {phrase}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate GPT context refresh skill controls.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files.")
    parser.parse_args(argv)

    errors = validate()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("gpt_context_refresh_validation=PASS")
    return 0


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
