# v0.3 AdoptionCandidate Selector Gate

Status: active selector/adoption evidence gate.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Evaluation input: `docs/extension/v0_3_evaluation_evidence_contract.md`.
Activation gate: `docs/extension/v0_3_production_activation_decision_gate.md`.
Owner lane: ML/evaluator selector with root adoption semantics review.

This gate defines how multiple `StrategyCandidate` records and their
ResearchEvidence/EvaluationEvidence are compared to produce an
`AdoptionCandidate`. The output is candidate adoption evidence only. It may
identify a review-preferred candidate, but it is not operational strategy
adoption and not production activation.

## Adoption Semantics

`AdoptionCandidate` means:

- enough evidence exists to request human/root review
- a selector/evaluator found the candidate reviewable relative to the current
  candidate cohort
- limitations and required reviews are explicit
- activation remains blocked until a separate production activation decision
  gate is approved

`AdoptionCandidate` does not mean:

- the strategy is guaranteed to be superior in the future
- the strategy is adopted for operations
- live or batch trading can run
- automatic production activation can occur

## Selector Input Allowlist

The selector may consume only compact, candidate-only evidence summaries:

- hypothesis metadata:
  - `strategy_hypothesis_id`
  - source/evidence/provenance/license summary
  - usage boundary
  - hypothesis statement
  - evaluation question
  - duplicate and limitation notes
- registry metadata:
  - `candidate_id`
  - `hypothesis_id`
  - `version`
  - `owner`
  - `status`
  - `dependency`
  - `blocked_by`
  - required data and universe boundary summaries
  - conceptual signal/entry/exit/risk rule summaries
- evaluation evidence summary:
  - `evaluation_id`
  - evaluation window and universe
  - assumptions and transaction-cost assumption
  - historical performance metric summaries
  - risk metric summaries
  - failure flags
  - no-lookahead, point-in-time, generated-output, and no-feedback checks
  - limitations and invalidation notes

Blocked selector inputs:

- raw backtest metric tables as runtime model features
- live market data feeds
- runtime report content
- future labels or lookahead fields

## Selector Output Schema

Required output fields:

- `adoption_candidate_id`: stable ID, for example
  `ac_v0_3_YYYYMMDD_slug`.
- `candidate_id`: selected StrategyCandidate ID.
- `candidate_version`: selected StrategyCandidate version.
- `selector_run_id`: identifier for the selector review packet.
- `selector_input_refs`: paths to allowlisted input summaries.
- `selector_score_candidate`: candidate-only review score or ordinal bucket.
- `relative_review_rank`: optional candidate-only review ordering within the
  evaluated cohort.
- `confidence`: one of `low`, `medium`, or `high`; confidence is review
  confidence, not expected performance.
- `reason_codes`: controlled list explaining why the candidate is reviewable.
- `limitations`: unresolved limitations, caveats, and evidence gaps.
- `required_review`: required human/root/subproject reviews before any next
  state.
- `status`: one of `proposed`, `review_required`, `rejected`, or
  `activation_blocked`.
- `no_feedback_check`: confirmation that selector output does not feed
  automatic production activation.
- `activation_gate_ref`: always
  `docs/extension/v0_3_production_activation_decision_gate.md`.
- `production_boundary_check`: confirmation that automatic production
  activation claims are absent.

Optional output fields:

- `alternative_candidate_ids`
- `tie_break_notes`
- `manual_review_notes`
- `rejection_reason`
- `activation_blocker_ids`

## Adoption Status Values

`proposed`:
Candidate has selector evidence worth review. It is not adopted.

`review_required`:
Candidate cannot move forward until named reviews are complete.

`rejected`:
Candidate is not suitable for adoption review or activation route request.

`activation_blocked`:
Candidate may have review evidence, but production activation is explicitly
blocked pending a separate activation decision gate.

Allowed transitions:

- `proposed -> review_required`
- `proposed -> rejected`
- `proposed -> activation_blocked`
- `review_required -> proposed`
- `review_required -> rejected`
- `review_required -> activation_blocked`
- `activation_blocked -> review_required`
- `activation_blocked -> rejected`

Blocked transitions:

- any adoption status -> production activation
- any adoption status -> operational strategy adoption

## Reason Codes

Suggested `reason_codes`:

- `evidence_complete_enough_for_review`
- `evaluation_window_documented`
- `historical_performance_summary_documented`
- `risk_metrics_documented`
- `limitations_explicit`
- `no_feedback_boundary_passed`
- `point_in_time_review_present`
- `no_lookahead_review_present`
- `requires_more_evidence`
- `blocked_by_license`
- `blocked_by_data_availability`
- `blocked_by_scope_boundary`
- `invalidated_by_failure_flags`

Reason codes must describe review status only. They must not encode a future
performance promise, trading attractiveness, or production readiness.

## Adoption Gate vs Activation Gate

Adoption gate:

- compares allowlisted evidence summaries
- may identify review-preferred candidates within the current evidence cohort
- creates an `AdoptionCandidate`
- records limitations and required reviews
- may request a future activation decision review
- remains candidate-only and evidence-only

Activation gate:

- is a separate root-approved production decision process
- must verify safety and release boundaries
- may require `quant-candidate-ml-gate`, `quant-subproject-audit-gate`, and
  `quant-review-gate`
- is the only place where production activation could be considered

The adoption gate must never silently become the activation gate.

## Output Artifact Paths

Proposed adoption outputs:

- `docs/extension/v0_3/adoption_candidates/*.md`
- `docs/extension/v0_3/selector_review_packets/*.md`
- `docs/extension/v0_3/adoption_rejection_log.md`

Proposed selector validation paths:

- `Quant_mvp/tests/fixtures/v0_3_adoption_candidate_minimal.toml`
- `Quant_mvp/tests/test_v0_3_adoption_candidate_schema.py`
- `Quant_mvp/tests/test_v0_3_selector_input_allowlist.py`
- `Quant_mvp/tests/test_v0_3_activation_boundary.py`

These paths are active v0.3 boundaries. Approved owner-lane tasks may implement
or run selector/evaluator logic that stays inside these boundaries. This gate
does not authorize production activation.

## Minimal Fixture Proposal

```toml
[[adoption_candidate]]
adoption_candidate_id = "ac_v0_3_20260428_example"
candidate_id = "sc_v0_3_20260428_example"
candidate_version = "0.1.0"
selector_run_id = "selector_v0_3_contract_only_example"
selector_input_refs = [
  "docs/extension/v0_3/strategy_hypotheses/example.md",
  "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
  "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/example.md",
]
selector_score_candidate = "review_bucket_only"
relative_review_rank = "candidate_review_order_only"
confidence = "low"
reason_codes = ["evidence_complete_enough_for_review", "historical_performance_summary_documented", "limitations_explicit"]
limitations = ["contract_only_fixture", "no_runtime_activation"]
required_review = ["root_governance_review", "activation_gate_required"]
status = "activation_blocked"
no_feedback_check = "must_not_trigger_auto_activation"
activation_gate_ref = "docs/extension/v0_3_production_activation_decision_gate.md"
production_boundary_check = "no_automatic_production_activation_claim"
```

## Validation Proposal

Minimum validation should check:

- AdoptionCandidate records have all required fields.
- `status` is one of `proposed`, `review_required`, `rejected`, or
  `activation_blocked`.
- `selector_input_refs` point only to allowlisted hypothesis metadata, registry
  metadata, and evaluation evidence summaries.
- Selector outputs do not include live trading paths or production activation
  fields.
- `selector_score_candidate` is candidate-only.
- `relative_review_rank`, when present, is candidate-only.
- `confidence` is review confidence only.
- `required_review` includes the production activation decision gate before any
  activation request.
- Automatic production activation claims are absent.

Suggested later command shape:

```powershell
python -m pytest Quant_mvp/tests/test_v0_3_adoption_candidate_schema.py Quant_mvp/tests/test_v0_3_selector_input_allowlist.py Quant_mvp/tests/test_v0_3_activation_boundary.py
```

## Production Activation Pre-Blockers

Before production activation may even be requested, all of these must be true:

- AdoptionCandidate is not `rejected`.
- Status is `activation_blocked` with explicit blockers, not implicitly active.
- Activation gate document is referenced.
- Required reviews are named.
- No automatic production activation feedback exists.
- Root explicitly opens a later production activation decision task.
