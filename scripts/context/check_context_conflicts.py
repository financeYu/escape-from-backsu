from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SCAN_ROOTS = (Path("docs/context"),)
NEGATION_MARKERS = (
    "must not",
    " are not ",
    " is not ",
    "do not",
    "does not",
    "not allowed",
    "never",
    "forbidden",
    "reject",
    "rejects",
    "must never",
    "must stay out",
    "without",
    "금지",
    "허용하지",
)


@dataclass(frozen=True)
class ConflictRule:
    code: str
    pattern: re.Pattern[str]
    message: str


@dataclass(frozen=True)
class ConflictFinding:
    path: Path
    line_number: int
    code: str
    message: str
    line: str


RULES = (
    ConflictRule(
        code="valuation_in_technical_composite",
        pattern=re.compile(
            r"\b(valuation|fundamental|financial)\b.{0,100}\b(allowed|may|can|should|inside|enter|used)\b"
            r".{0,100}\b(technical_composite_score|final_composite_score)\b",
            flags=re.IGNORECASE,
        ),
        message="valuation/fundamental data appears allowed inside technical or final composite scoring.",
    ),
    ConflictRule(
        code="diagnostics_as_alpha",
        pattern=re.compile(
            r"\bdiagnostics?\b.{0,80}\b(are|is|as|provide|become)\b.{0,80}\b(alpha signal|alpha signals|stock-selection score)\b",
            flags=re.IGNORECASE,
        ),
        message="diagnostics appear described as alpha or stock-selection signals.",
    ),
    ConflictRule(
        code="generated_output_feedback",
        pattern=re.compile(
            r"\bgenerated report output\b.{0,80}\b(can|may|should|allowed)\b.{0,80}\bfeed\b.{0,80}\bupstream\b",
            flags=re.IGNORECASE,
        ),
        message="generated report output appears allowed to feed upstream construction.",
    ),
    ConflictRule(
        code="future_returns_as_inputs",
        pattern=re.compile(
            r"\bfuture returns?\b.{0,80}\b(can|may|should|allowed)\b.{0,80}\bscore inputs?\b",
            flags=re.IGNORECASE,
        ),
        message="future returns appear allowed as score inputs.",
    ),
    ConflictRule(
        code="step19_already_implemented",
        pattern=re.compile(
            r"\bStep 19\b.{0,80}\b(already implemented|implemented automatic execution)\b|"
            r"\bStep 19\b\s*=\s*COMPLETE\b|"
            r"\bautomatic execution pipeline\b.{0,80}\b(has been implemented|is implemented)\b",
            flags=re.IGNORECASE,
        ),
        message="Step 19 automatic execution appears claimed as already implemented.",
    ),
)


def check_conflicts(project_root: Path, scan_roots: tuple[Path, ...] = DEFAULT_SCAN_ROOTS) -> tuple[ConflictFinding, ...]:
    root = project_root.resolve()
    findings: list[ConflictFinding] = []
    for scan_root in scan_roots:
        resolved = _root_path(root, scan_root)
        paths = [resolved] if resolved.is_file() else sorted(resolved.glob("**/*.md")) if resolved.exists() else []
        for path in paths:
            findings.extend(_check_file(root, path))
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan context docs for suspicious forbidden claims.")
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or directories to scan. Defaults to docs/context.",
    )
    args = parser.parse_args(argv)

    scan_roots = tuple(Path(path) for path in args.paths) if args.paths else DEFAULT_SCAN_ROOTS
    findings = check_conflicts(Path(args.project_root), scan_roots)
    if not findings:
        print("No context conflict findings.")
        return 0

    root = Path(args.project_root).resolve()
    for finding in findings:
        print(
            f"[{finding.code}] {_display_path(root, finding.path)}:{finding.line_number}: "
            f"{finding.message} :: {finding.line.strip()}"
        )
    return 1


def _check_file(project_root: Path, path: Path) -> list[ConflictFinding]:
    text = path.read_text(encoding="utf-8")
    findings: list[ConflictFinding] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if _is_negated(line):
            continue
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append(
                    ConflictFinding(
                        path=path,
                        line_number=index,
                        code=rule.code,
                        message=rule.message,
                        line=line,
                    )
                )
    return findings


def _is_negated(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in NEGATION_MARKERS)


def _root_path(project_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return project_root / path


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
