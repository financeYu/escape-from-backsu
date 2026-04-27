#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SKILL_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
DEFAULT_ROOT="$(CDPATH= cd -- "$SKILL_DIR/../../.." && pwd)"

ROOT="${1:-$DEFAULT_ROOT}"
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

require_patterns() {
  file="$1"
  shift
  for pattern in "$@"; do
    require_grep "$pattern" "$file"
  done
}

SKILL_REL=".agents/skills/quant-subproject-audit-gate"
SKILL_FILE="$SKILL_REL/SKILL.md"
SCRIPT_FILE="$SKILL_REL/scripts/validate_subproject_audit_gate.sh"
ROOT_ROUTER="AGENTS.md"
QUANT_ROUTER="Quant_mvp/AGENTS.md"
SCOPE_PROCESS="docs/scope_audit_process.md"

require_file "$ROOT_ROUTER"
require_file "$QUANT_ROUTER"
require_file "$SCOPE_PROCESS"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"

require_patterns "$SKILL_FILE" \
  '^name: quant-subproject-audit-gate$' \
  '^description: .*Quant_mvp subproject-wide audit' \
  'root/master-managed Codex skill gate' \
  'audit verdict and validation evidence are separate parts' \
  'Part 1: Audit' \
  'Part 2: Validation' \
  'Extensibility Notes' \
  'Quant_mvp/AGENTS\.md' \
  'subproject-wide audit means path and' \
  'Quant_mvp/\*\*' \
  'PASS' \
  'WARNING' \
  'BLOCKING_ISSUE' \
  'NEEDS_CLARIFICATION' \
  'validation_result: PASS \| FAIL \| NOT_RUN' \
  'technical_composite_score|final_composite_score' \
  'trading|proven-alpha|expected-return|profitability' \
  'git fetch' \
  'git pull' \
  'git push'

require_grep '\.agents/skills/quant-subproject-audit-gate/SKILL\.md' "$ROOT_ROUTER"
require_grep '\.agents/skills/quant-subproject-audit-gate/SKILL\.md' "$QUANT_ROUTER"
require_grep '\.agents/skills/quant-subproject-audit-gate/SKILL\.md' "$SCOPE_PROCESS"
require_grep 'audit.*validation|validation.*audit|감사.*밸리데이션|밸리데이션.*감사' "$SCOPE_PROCESS"

printf '%s\n' "PASS: quant subproject audit gate contract is present"
