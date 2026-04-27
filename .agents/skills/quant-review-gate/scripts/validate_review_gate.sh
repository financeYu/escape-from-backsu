#!/usr/bin/env sh
set -eu

ROOT="${1:-.}"
cd "$ROOT"

fail() {
  printf '%s\n' "FAIL: $*" >&2
  exit 1
}

require_file() {
  [ -f "$1" ] || fail "missing required file: $1"
}

require_grep() {
  pattern="$1"
  file="$2"
  grep -Eq "$pattern" "$file" || fail "missing pattern in $file: $pattern"
}

SKILL_FILE=".agents/skills/quant-review-gate/SKILL.md"
SCRIPT_FILE=".agents/skills/quant-review-gate/scripts/validate_review_gate.sh"

require_file "AGENTS.md"
require_file "Quant_mvp/AGENTS.md"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"

require_grep '^name: quant-review-gate$' "$SKILL_FILE"
require_grep '^description: .*completion' "$SKILL_FILE"
require_grep 'current task' "$SKILL_FILE"
require_grep 'allowed scope' "$SKILL_FILE"
require_grep 'forbidden scope' "$SKILL_FILE"
require_grep 'required output' "$SKILL_FILE"
require_grep 'validation commands' "$SKILL_FILE"
require_grep 'Korean final report format' "$SKILL_FILE"
require_grep 'PASS' "$SKILL_FILE"
require_grep 'NEEDS FIX' "$SKILL_FILE"
require_grep 'changed files' "$SKILL_FILE"
require_grep 'validation_evidence|validation evidence' "$SKILL_FILE"
require_grep 'remaining_risk|remaining risk' "$SKILL_FILE"
require_grep 'worktree status' "$SKILL_FILE"
require_grep 'production ranking' "$SKILL_FILE"
require_grep 'report behavior' "$SKILL_FILE"
require_grep 'technical_composite_score' "$SKILL_FILE"
require_grep 'final_composite_score' "$SKILL_FILE"
require_grep 'buy/sell/hold|proven-alpha|expected-return|profitability' "$SKILL_FILE"
require_grep 'git fetch' "$SKILL_FILE"
require_grep 'git pull' "$SKILL_FILE"
require_grep 'git push' "$SKILL_FILE"

require_grep '\.agents/skills/quant-review-gate/SKILL\.md' "AGENTS.md"
require_grep 'matching skill gate|Codex skill gate' "AGENTS.md"
require_grep 'current task' "AGENTS.md"
require_grep 'allowed scope' "AGENTS.md"
require_grep 'forbidden scope' "AGENTS.md"
require_grep 'Korean final report format' "AGENTS.md"
require_grep '\.agents/skills/quant-review-gate/SKILL\.md' "Quant_mvp/AGENTS.md"

printf '%s\n' "PASS: quant review gate contract is present"
