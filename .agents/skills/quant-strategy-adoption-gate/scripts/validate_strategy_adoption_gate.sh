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
  'active v0\.3 strategy-selection/adoption' \
  'Archived v0\.1/v0\.2 material is reference-only' \
  'root_hard_stops\.md.*roadmap_status\.md|roadmap_status\.md.*root_hard_stops\.md' \
  'score-runtime-semantics-gate' \
  'does not authorize.*production ranking activation|production ranking activation.*does not authorize' \
  'final_composite_score' \
  'trading recommendations' \
  'data-ingestion expansion' \
  'universe expansion'

require_grep 'The active route is post-MVP `v0\.3 research-to-strategy adoption route`' "docs/root_hard_stops.md"
require_grep 'v0\.1 and v0\.2 are archived reference states' "docs/root_hard_stops.md"
require_grep 'v0\.2 `prob_up_1d_candidate` remains an archived/supporting compatibility' "docs/root_hard_stops.md"
require_grep 'docs/roadmap_archive/v0_1_v0_2_archive\.md' "docs/root_hard_stops.md"
require_grep '## Direction Lock' "docs/root_hard_stops.md"
require_grep 'collect research, papers, and strategy ideas' "docs/root_hard_stops.md"
require_grep 'backtest or simulate each strategy candidate in an evidence-only lane' "docs/root_hard_stops.md"
require_grep 'machine learning or evaluation algorithms' "docs/root_hard_stops.md"
require_grep 'ResearchHypothesis' "docs/root_hard_stops.md"
require_grep 'StrategyHypothesis' "docs/root_hard_stops.md"
require_grep 'StrategyCandidate' "docs/root_hard_stops.md"
require_grep 'EvaluationEvidence' "docs/root_hard_stops.md"
require_grep 'AdoptionCandidate' "docs/root_hard_stops.md"
require_grep 'Post-MVP `v0\.3 research-to-strategy adoption route` is ACTIVE' "docs/roadmap_status.md"
require_grep 'v0\.1 is archived as a frozen historical baseline reference' "docs/roadmap_status.md"
require_grep 'v0\.2 is archived as a supporting probability compatibility reference' "docs/roadmap_status.md"
require_grep 'Direction lock:' "docs/roadmap_status.md"
require_grep 'state = "active_candidate_evidence_route"' "docs/context/EXTENSION_REGISTRY.toml"
require_grep 'state = "archived_supporting_compatibility_reference"' "docs/context/EXTENSION_REGISTRY.toml"
require_file "docs/roadmap_archive/v0_1_v0_2_archive.md"
require_grep '## Product Goal Anchor' "$SKILL_FILE"
require_grep '## Direction-Lock Procedure' "$SKILL_FILE"
require_grep 'evidence-preferred' "$SKILL_FILE"
require_grep 'next_v0_3_artifact' "$SKILL_FILE"

if grep -Eq 'v0\.3 production activation is active|active production v0\.3 route|v0\.3 production implementation scope is open' "$SKILL_FILE" "AGENTS.md"; then
  fail "v0.3 production activation must remain blocked unless root authority opens it"
fi

printf '%s\n' "PASS: quant strategy adoption gate contract is present"
