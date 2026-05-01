#!/usr/bin/env python3
"""Dry-run validator for the quant-work-cycle skill document."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_PHRASES = {
    "scope confirmation": "### 1. Scope Confirmation",
    "implementation": "### 2. Implementation",
    "diff review": "### 3. Diff Review",
    "fix pass": "### 4. Fix Pass",
    "verify pass": "### 5. Verify Pass",
    "commit-ready report": "### 6. Commit-Ready Report",
    "review fail loops": "If diff review returns `FAIL`",
    "verify fail loops": "If verification returns `FAIL`",
    "no commit": "commits, stages",
    "no push": "This workflow never pushes",
    "fetch disabled": "`git fetch`",
    "pull disabled": "`git pull`",
    "push disabled": "`git push`",
    "commit disabled": "`git commit`",
    "stage disabled": "`git add`",
    "changed files": "changed files",
    "validation results": "validation results",
    "recommended commit message": "recommended commit message",
    "blocked validation is not pass": "Routed blockers are useful evidence",
}


def read_skill(path: Path) -> str:
    if path.is_dir():
        path = path / "SKILL.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"missing skill document: {path}") from None


def frontmatter_ok(text: str) -> list[str]:
    failures: list[str] = []
    todo_marker = "TO" + "DO"
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return ["missing YAML frontmatter"]
    frontmatter = match.group(1)
    if "name: quant-work-cycle" not in frontmatter:
        failures.append("frontmatter name is not quant-work-cycle")
    if "description:" not in frontmatter:
        failures.append("frontmatter description is missing")
    if todo_marker in frontmatter:
        failures.append(f"frontmatter still contains {todo_marker}")
    return failures


def validate(text: str) -> dict[str, object]:
    failures = frontmatter_ok(text)
    todo_marker = "TO" + "DO"
    missing = [
        label for label, phrase in REQUIRED_PHRASES.items() if phrase not in text
    ]
    failures.extend(f"missing required phrase: {label}" for label in missing)
    if f"[{todo_marker}" in text or f"{todo_marker}:" in text:
        failures.append(f"document still contains {todo_marker} markers")

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "checked_phrases": sorted(REQUIRED_PHRASES),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate quant-work-cycle SKILL.md workflow controls."
    )
    parser.add_argument(
        "skill_path",
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "SKILL.md",
        type=Path,
        help="Path to SKILL.md or the quant-work-cycle skill directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Document-only check; no Git commands or writes are performed.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    text = read_skill(args.skill_path)
    result = validate(text)
    result["dry_run"] = bool(args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"quant-work-cycle validation: {result['status']}")
        print(f"dry_run: {str(result['dry_run']).lower()}")
        for failure in result["failures"]:
            print(f"- {failure}")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
