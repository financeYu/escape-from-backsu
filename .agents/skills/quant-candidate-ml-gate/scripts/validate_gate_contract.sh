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

SKILL_DIR=".agents/skills/quant-candidate-ml-gate"
SKILL_FILE="$SKILL_DIR/SKILL.md"
SCRIPT_FILE="$SKILL_DIR/scripts/validate_gate_contract.sh"
META_FILE="$SKILL_DIR/agents/openai.yaml"

require_file "AGENTS.md"
require_file "docs/root_hard_stops.md"
require_file "docs/roadmap_status.md"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"
require_file "$META_FILE"

rule_count="$(grep -Ec '^[0-9]+\.' AGENTS.md)"
[ "$rule_count" -eq 10 ] || fail "AGENTS.md must contain exactly 10 numbered router rules; found $rule_count"

require_grep 'root_hard_stops\.md' "AGENTS.md"
require_grep 'roadmap_status\.md' "AGENTS.md"
require_grep '\.agents/skills/quant-candidate-ml-gate/SKILL\.md' "AGENTS.md"
require_grep 'user prompt.*local goal|gate.*local goal|goal/output' "AGENTS.md"

require_grep 'current project authority|project authority' "docs/root_hard_stops.md"
require_grep 'prob_up_1d_candidate' "docs/root_hard_stops.md"
require_grep 'candidate-only|candidate ML|candidate probability' "docs/root_hard_stops.md"
require_grep '\.agents/skills/quant-candidate-ml-gate/SKILL\.md' "docs/root_hard_stops.md"
require_grep 'technical_composite_score' "docs/root_hard_stops.md"
require_grep 'final_composite_score' "docs/root_hard_stops.md"
require_grep 'Trading recommendations|trading recommendations|buy/sell/hold' "docs/root_hard_stops.md"

require_grep 'v0\.2 predictive probability score route' "docs/roadmap_status.md"
require_grep 'prob_up_1d_candidate' "docs/roadmap_status.md"
require_grep '\.agents/skills/quant-candidate-ml-gate/SKILL\.md' "docs/roadmap_status.md"

require_grep '^name: quant-candidate-ml-gate$' "$SKILL_FILE"
require_grep '^description: .*prob_up_1d_candidate' "$SKILL_FILE"
require_grep 'Do Not Use When' "$SKILL_FILE"
require_grep 'prob_up_1d_candidate' "$SKILL_FILE"
require_grep 'candidate-only|candidate_only' "$SKILL_FILE"
require_grep 'label-separated' "$SKILL_FILE"
require_grep 'validate_gate_contract\.sh' "$SKILL_FILE"
require_grep 'display_name: "Quant Candidate ML Gate"' "$META_FILE"

printf '%s\n' "PASS: quant candidate ML gate contract is present"
