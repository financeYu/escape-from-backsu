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

SKILL_REL=".agents/skills/quant-research-artifact-review"
SKILL_FILE="$SKILL_REL/SKILL.md"
SCRIPT_FILE="$SKILL_REL/scripts/validate_research_artifact_review.sh"

require_file "docs/root_hard_stops.md"
require_file "docs/roadmap_status.md"
require_file ".agents/skills/quant-strategy-adoption-gate/SKILL.md"
require_file ".agents/skills/quant-review-gate/SKILL.md"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"

require_grep '^name: quant-research-artifact-review$' "$SKILL_FILE"
require_grep '^description: .*ResearchHypothesis.*StrategyHypothesis.*StrategyCandidate' "$SKILL_FILE"
require_grep 'EvaluationEvidence' "$SKILL_FILE"
require_grep 'AdoptionCandidate' "$SKILL_FILE"
require_grep 'review-only|Review active' "$SKILL_FILE"
require_grep 'does not create the next artifact' "$SKILL_FILE"
require_grep 'does not.*run simulations' "$SKILL_FILE"
require_grep 'production activation' "$SKILL_FILE"
require_grep 'live trading' "$SKILL_FILE"
require_grep 'selector/evaluator preference signal|selector claim-leakage' "$SKILL_FILE"
require_grep 'Generated outputs are normally outside default context' "$SKILL_FILE"
require_grep 'ResearchHypothesis -> StrategyHypothesis -> StrategyCandidate ->' "$SKILL_FILE"
require_grep 'paper claim language' "$SKILL_FILE"
require_grep 'no-feedback' "$SKILL_FILE"
require_grep 'ready_for_eval' "$SKILL_FILE"
require_grep 'review-preferred only' "$SKILL_FILE"
require_grep 'gate_result: PASS \| NEEDS FIX' "$SKILL_FILE"
require_grep 'status: COMPLETE \| PARTIALLY COMPLETE \| NEEDS FIX' "$SKILL_FILE"

require_grep 'The active route is post-MVP `v0\.3 research-to-strategy adoption route`' "docs/root_hard_stops.md"
require_grep 'ResearchHypothesis' "docs/root_hard_stops.md"
require_grep 'StrategyHypothesis' "docs/root_hard_stops.md"
require_grep 'StrategyCandidate' "docs/root_hard_stops.md"
require_grep 'EvaluationEvidence' "docs/root_hard_stops.md"
require_grep 'AdoptionCandidate' "docs/root_hard_stops.md"
require_grep 'Post-MVP `v0\.3 research-to-strategy adoption route` is ACTIVE' "docs/roadmap_status.md"

if grep -Eq 'live trading approval is allowed|future performance proof is allowed|production activation is open' "$SKILL_FILE"; then
  fail "skill must not imply production activation or trading approval"
fi

printf '%s\n' "PASS: quant research artifact review skill contract is present"
