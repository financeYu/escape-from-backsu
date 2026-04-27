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

require_absent() {
  [ ! -e "$1" ] || fail "removed Quant-local valuation agent path still exists: $1"
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

SKILL_REL=".agents/skills/valuation_review"
SKILL_FILE="$SKILL_REL/SKILL.md"
EXAMPLE_FILE="$SKILL_REL/references/valuation_scores.example.toml"
SCRIPT_FILE="$SKILL_REL/scripts/validate_valuation_review_gate.sh"
ROOT_ROUTER="AGENTS.md"
QUANT_ROUTER="Quant_mvp/AGENTS.md"
QUANT_CONFIG_README="Quant_mvp/config/README.md"
QUANT_GLOBAL_CONFIG="Quant_mvp/config/global.toml"

require_file "$ROOT_ROUTER"
require_file "$QUANT_ROUTER"
require_file "$SKILL_FILE"
require_file "$EXAMPLE_FILE"
require_file "$SCRIPT_FILE"

LEGACY_AGENT_DIR="$(printf '%s/%s/%s' 'Quant_mvp' 'agents' 'valuation')"
require_absent "$LEGACY_AGENT_DIR/AGENTS.md"
require_absent "$LEGACY_AGENT_DIR/valuation_scores.example.toml"

require_patterns "$SKILL_FILE" \
  '^name: master-mvp-valuation-review$' \
  'canonical valuation/fundamental review gate' \
  'removed Quant-local valuation agent document' \
  'valuation_agent_handoff' \
  'point-in-time' \
  'valuation_status' \
  'valuation_verdict' \
  'blocked_by_data' \
  'technical_composite_score' \
  'final_composite_score' \
  'buy/sell/hold|target prices|expected return' \
  'Extensibility Notes'

require_grep '\.agents/skills/valuation_review/SKILL\.md' "$QUANT_ROUTER"
require_grep '\.agents/skills/valuation_review/references/valuation_scores\.example\.toml' "$QUANT_CONFIG_README"
require_grep 'valuation_review_skill_path' "$QUANT_GLOBAL_CONFIG"

printf '%s\n' "PASS: valuation review skill gate contract is present"
