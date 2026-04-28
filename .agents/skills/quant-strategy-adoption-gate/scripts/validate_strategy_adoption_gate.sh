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

SKILL_REL=".agents/skills/quant-strategy-adoption-gate"
SKILL_FILE="$SKILL_REL/SKILL.md"
SCRIPT_FILE="$SKILL_REL/scripts/validate_strategy_adoption_gate.sh"

require_file "AGENTS.md"
require_file "docs/root_hard_stops.md"
require_file "docs/roadmap_status.md"
require_file ".agents/skills/quant-candidate-ml-gate/SKILL.md"
require_file ".agents/skills/quant-review-gate/SKILL.md"
require_file ".agents/skills/quant-subproject-audit-gate/SKILL.md"
require_file ".agents/skills/score-runtime-semantics-gate/SKILL.md"
require_file "$SKILL_FILE"
require_file "$SCRIPT_FILE"

require_patterns "$SKILL_FILE" \
  '^name: quant-strategy-adoption-gate$' \
  '^description: .*v0\.3.*strategy-selection/adoption' \
  'proposal/candidate-only' \
  'root_hard_stops\.md.*roadmap_status\.md|roadmap_status\.md.*root_hard_stops\.md' \
  'does not activate|does not authorize' \
  'production ranking' \
  'report behavior' \
  'final_composite_score' \
  'trading recommendations|buy/sell/hold' \
  'valuation/fundamental scoring' \
  'data-ingestion expansion|market-data ingestion' \
  'universe expansion' \
  'quant-candidate-ml-gate/SKILL\.md' \
  'score-runtime-semantics-gate/SKILL\.md' \
  'quant-subproject-audit-gate/SKILL\.md' \
  'quant-review-gate/SKILL\.md'

require_patterns "AGENTS.md" \
  'quant-strategy-adoption-gate/SKILL\.md' \
  'proposal/candidate-only' \
  'root_hard_stops\.md.*roadmap_status\.md|roadmap_status\.md.*root_hard_stops\.md' \
  'score-runtime-semantics-gate' \
  'does not authorize.*production ranking activation|production ranking activation.*does not authorize' \
  'final_composite_score' \
  'trading recommendations' \
  'data-ingestion expansion' \
  'universe expansion'

require_grep 'The active route is post-MVP `v0\.2 predictive probability score route`' "docs/root_hard_stops.md"
require_grep 'The only approved active candidate ML output is `prob_up_1d_candidate`' "docs/root_hard_stops.md"

if grep -Eq 'v0\.3 (is )?active|active v0\.3 route|active route.*v0\.3|v0\.3 implementation scope is open' "$SKILL_FILE" "AGENTS.md"; then
  fail "v0.3 must remain proposal/candidate-only unless root authority opens it"
fi

printf '%s\n' "PASS: quant strategy adoption gate contract is present"
