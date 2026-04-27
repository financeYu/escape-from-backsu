#!/usr/bin/env sh
set -eu

MODE="${1:-}"
if [ "$MODE" = "--self-check" ]; then
  ROOT="${2:-.}"
else
  ROOT="${1:-.}"
fi
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

SKILL_FILE=".agents/skills/quant-git-finalize/SKILL.md"
SCRIPT_FILE=".agents/skills/quant-git-finalize/scripts/validate_git_finalize.sh"

require_file "AGENTS.md"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"

require_grep '^name: quant-git-finalize$' "$SKILL_FILE"
require_grep '^description: .*local-first Git finalization' "$SKILL_FILE"
require_grep 'review gate.*PASS|review gate `PASS`' "$SKILL_FILE"
require_grep 'inspect changed files|Inspect changed files' "$SKILL_FILE"
require_grep 'required validation' "$SKILL_FILE"
require_grep 'local commit|Create a local commit|create a local commit' "$SKILL_FILE"
require_grep 'push remote only at the final stage|Push remote only at the final stage' "$SKILL_FILE"
require_grep 'commit hash' "$SKILL_FILE"
require_grep 'push result' "$SKILL_FILE"
require_grep 'Do not push if' "$SKILL_FILE"
require_grep 'NEEDS FIX' "$SKILL_FILE"
require_grep 'forbidden scope' "$SKILL_FILE"
require_grep 'validation failed|validation_failed' "$SKILL_FILE"
require_grep 'explicitly confirmed|explicit root|remote-finalization approval' "$SKILL_FILE"
require_grep 'fetch/pull/push cycles|fetch, pull, or push repeatedly' "$SKILL_FILE"
require_grep '\.agents/skills/quant-git-finalize/SKILL\.md' "AGENTS.md"

if [ "$MODE" = "--self-check" ]; then
  printf '%s\n' "PASS: git finalization gate blocks push unless review gate PASS"
else
  printf '%s\n' "PASS: quant git finalization contract is present"
fi
