# v0.3 StrategyCandidate Registry Contract

Status: active candidate registry contract.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Upstream intake: `docs/extension/v0_3_strategy_hypothesis_intake_contract.md`.
Owner lane: Quant_mvp governance with root boundary review.

This contract defines how a `StrategyHypothesis` is registered as a
`StrategyCandidate`. Registration means the idea is structured enough for
candidate-only backtest/simulation evaluation. It is not an adoption decision,
and not a production signal.

## Architecture Routing

StrategyCandidate registry work must pass through the active root architecture
chain before Quant governance execution or validation begins:

`agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor -> agent-worker-pool -> agent-reporter`

The default domain compatibility target is `quant-strategy-adoption-gate`.
Completion acceptance requires `quant-review-gate`. The supervisor handoff must
lock allowed scope, forbidden scope, required output, validation commands, and
Korean final report format before registry files, fixtures, or schema checks are
created or updated.

## Registry Boundary

Allowed:

- define candidate identity, lineage, ownership, and status
- define required data, universe, conceptual signal, entry/exit, risk rule, and
  evaluation criteria fields
- define dependencies and blockers
- create or maintain candidate-only registry fixtures and schema validation
  checks in the approved owner lane

Blocked:

- live or batch trading signal operation
- implementation of entry/exit/risk logic
- backtest execution or historical result recording inside the registry artifact
- automatic adoption from backtest results
- automatic production activation from backtest results

## Proposed Registry Path

The candidate registry is a Quant_mvp-owned config artifact for v0.3:

- `Quant_mvp/config/v0_3_strategy_candidate_registry.toml`

The schema and validation support may live at:

- `docs/extension/v0_3_strategy_candidate_registry_contract.md`
- `Quant_mvp/tests/fixtures/v0_3_strategy_candidate_registry_minimal.toml`
- `Quant_mvp/tests/test_v0_3_strategy_candidate_registry_schema.py`

This contract authorizes candidate registry structure and validation work in the
approved owner lane. It does not authorize production runtime changes.

## StrategyCandidate Schema

Required identity and ownership fields:

- `candidate_id`: stable candidate ID, for example `sc_v0_3_YYYYMMDD_slug`.
- `hypothesis_id`: upstream `StrategyHypothesis` ID.
- `version`: semantic candidate contract version, for example `0.1.0`.
- `owner`: owning lane or responsible subproject, for example
  `quant_governance`.
- `status`: one of `draft`, `registered`, `evaluable`, `blocked`, or `retired`.
- `created_at`: local date or timestamp.
- `updated_at`: local date or timestamp.
- `registry_source`: path to the registry artifact that owns the record.

Required lineage and dependency fields:

- `source_refs`: upstream hypothesis, research, or EvidenceCard references.
- `dependency`: list of required contracts, data families, or gate approvals.
- `blocked_by`: list of unresolved blockers; empty only when status is
  `registered` or `evaluable`.
- `scope_boundary_ref`: route or hard-stop document path.
- `v0_2_boundary_check`: confirmation that `prob_up_1d_candidate` is not
  replaced, reinterpreted, or used as an automatic selector.

Required candidate structure fields:

- `required_data`: required data families and availability assumptions.
- `universe`: permitted universe boundary; default remains KOSPI200 unless a
  later root-approved route opens another universe.
- `signal`: conceptual signal description, not executable implementation.
- `entry_exit`: conceptual entry/exit review description, not live operation
  logic.
- `risk_rule`: conceptual risk boundary, not sizing or execution code.
- `evaluation_criteria`: predeclared criteria a later historical evaluation
  contract may inspect.
- `evaluation_artifact_plan`: proposed later output path for evaluation
  evidence.
- `no_feedback_boundary`: explicit statement that evaluation metrics must not
  trigger automatic production activation.
- `production_boundary_check`: confirmation that automatic production
  activation claims are absent.

Optional fields:

- `related_candidate_ids`
- `duplicate_of`
- `retirement_reason`
- `review_notes`
- `data_availability_questions`
- `license_questions`

## Status Values

`draft`:
Candidate record is incomplete. It must not be evaluated or registered as ready.

`registered`:
Candidate record has required identity, lineage, and boundary fields. It has no
runtime effect and no evaluation result.

`evaluable`:
Candidate record has a complete evaluation criteria section and no unresolved
schema blockers. This status means a separate approved backtest/simulation
task may evaluate the candidate; the registry status does not run that
evaluation by itself.

`blocked`:
Candidate cannot proceed because data, license, universe, leakage, ownership,
or hard-stop issues remain unresolved.

`retired`:
Candidate is no longer eligible for evaluation or adoption review. Retirement
does not imply the candidate failed a performance test.

Allowed transitions:

- `draft -> registered`
- `draft -> blocked`
- `registered -> evaluable`
- `registered -> blocked`
- `registered -> retired`
- `evaluable -> blocked`
- `evaluable -> retired`
- `blocked -> draft`
- `blocked -> retired`

Blocked transitions:

- any status -> production activation
- any status -> automatic adoption

## Candidate-Only Boundary

StrategyCandidate registry records must stay separate from v0.1 and v0.2:

- Do not use backtest or evaluation metrics as automatic production activation
  triggers.
- Do not reinterpret `prob_up_1d_candidate` as a strategy selector without a
  later candidate ML gate approval.
- Route any probability-sidecar, feature-table, label, training/evaluation, or
  leakage work through `.agents/skills/quant-candidate-ml-gate/SKILL.md`.

## Minimal Fixture Proposal

A minimal TOML fixture should contain one candidate with all required fields and
no runtime behavior:

```toml
[[strategy_candidate]]
candidate_id = "sc_v0_3_20260428_example"
hypothesis_id = "sh_v0_3_20260428_example"
version = "0.1.0"
owner = "quant_governance"
status = "draft"
created_at = "2026-04-28"
updated_at = "2026-04-28"
registry_source = "Quant_mvp/config/v0_3_strategy_candidate_registry.toml"
source_refs = ["docs/extension/v0_3/strategy_hypotheses/example.md"]
dependency = ["docs/extension/v0_3_strategy_candidate_registry_contract.md"]
blocked_by = ["not_yet_reviewed"]
scope_boundary_ref = "docs/extension/v0_3_research_to_strategy_adoption_route.md"
v0_2_boundary_check = "no_prob_up_1d_reinterpretation"
required_data = ["daily_ohlcv_candidate_review_only"]
universe = "KOSPI200_candidate_only"
signal = "conceptual_signal_description_only"
entry_exit = "conceptual_entry_exit_review_only"
risk_rule = "conceptual_risk_boundary_only"
evaluation_criteria = ["later_approved_historical_evaluation_contract_required"]
evaluation_artifact_plan = "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/example.md"
no_feedback_boundary = "evaluation_metrics_must_not_trigger_auto_activation"
production_boundary_check = "no_automatic_production_activation_claim"
```

## Schema Validation Proposal

Minimum validation should check:

- registry TOML parses
- every record has required identity, lineage, candidate structure, boundary,
  and claim-check fields
- `status` is one of `draft`, `registered`, `evaluable`, `blocked`, `retired`
- `candidate_id` and `(candidate_id, version)` are unique
- `hypothesis_id` is present and non-empty
- `blocked_by` is non-empty when status is `draft` or `blocked`
- `blocked_by` is empty when status is `registered` or `evaluable`
- forbidden status jumps are not represented as registry states
- production-boundary wording is absent except inside explicit blocked-policy
  or boundary-check fields
- no field changes `prob_up_1d_candidate` semantics

Suggested command shape for Quant_mvp-owned validation:

```powershell
python -m pytest Quant_mvp/tests/test_v0_3_strategy_candidate_registry_schema.py
```

## Evaluable Candidate Conditions

A candidate may be marked `evaluable` only when:

- upstream `StrategyHypothesis` has `candidate_spec_ready` status
- required data families are named and still candidate-only
- universe boundary is explicit and does not expand active runtime scope
- signal, entry/exit, and risk rule are conceptual and non-runtime
- evaluation criteria are declared before any evaluation run
- dependency and blocker fields are resolved
- v0.1 and v0.2 boundary checks pass
- no adoption decision or production connection is present
