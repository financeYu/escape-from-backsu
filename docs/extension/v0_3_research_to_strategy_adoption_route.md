# v0.3 Research-to-Strategy Adoption Route

Status: active candidate/evidence route.
Route key: `strategy_adoption_v0_3`.
Route name: `Research-to-Strategy Adoption Pipeline`.

v0.3 is the product route for turning research ideas into reviewable quant
strategy candidates, evaluating them historically, selecting review-preferred
candidates, and recording what historical return/risk/performance evidence is
available.

## Product Goal

- Collect research, papers, and strategy ideas.
- Structure those ideas as quant strategy candidates.
- Backtest or simulate each strategy candidate in an evidence-only lane.
- Use machine learning or evaluation algorithms to select review-preferred
  candidates.
- Check what historical return, risk, and performance characteristics may be
  supported by the adopted-candidate evidence.

This route is about evidence, comparison, and adoption review. It is not live
trading, not a brokerage connection, not a production ranking/report route, not
a final score replacement, and not a future-performance guarantee.

## Route Flow

`research -> strategy hypothesis -> candidate registry -> backtest/simulation evidence -> selector/evaluator review -> adoption evidence`

Entity flow:

`ResearchHypothesis -> StrategyHypothesis -> StrategyCandidate -> EvaluationEvidence -> AdoptionCandidate`

## Authority Boundary

Root/master owns:

- this active route scope
- authority boundaries
- route registration
- cross-subproject handoff shape
- approval gate ordering
- final review-gate acceptance

Owner lanes:

- Research lane: source intake, EvidenceCard linkage, provenance/license notes,
  and `ResearchHypothesis` drafting.
- Quant strategy/governance lane: `StrategyHypothesis`,
  `StrategyCandidate`, registry fields, schemas, and scope boundaries.
- Backtest/simulation lane: approved candidate-only historical evaluation runs
  and `EvaluationEvidence` output.
- ML/evaluator lane: selector or evaluator algorithms that consume allowlisted
  evidence summaries and emit `AdoptionCandidate` review packets.
- Root governance: adoption evidence review, activation boundaries, and
  cross-lane conflict checks.

## Entity State Flow

### ResearchHypothesis

Purpose: capture a research-grounded idea without making an adoption claim.

States:

- `draft`: initial research note or EvidenceCard-derived idea.
- `evidence_mapped`: source, license, evidence level, and limitations recorded.
- `strategy_hypothesis_ready`: sufficient to propose a strategy hypothesis.
- `rejected`: unsuitable, duplicated, unlicensed, or out of route scope.

Allowed inputs:

- Research EvidenceCards.
- Papers, research notes, and strategy ideas with source/provenance metadata.
- License/status notes.
- Non-runtime research summaries.

Allowed outputs:

- Research hypothesis packet.
- Evidence limitation notes.
- Source/provenance/license mapping.

### StrategyHypothesis

Purpose: translate research evidence into a testable strategy idea without
runtime activation.

States:

- `draft`: plain-language hypothesis with intended observable conditions.
- `scope_checked`: universe, data, score, report, and baseline boundaries
  checked.
- `candidate_spec_ready`: sufficient to propose a StrategyCandidate.
- `rejected`: violates hard stops or lacks a testable historical evaluation
  path.

Allowed inputs:

- `ResearchHypothesis` packet.
- Existing route boundaries.
- Candidate-only feature or signal descriptions.

Allowed outputs:

- Strategy hypothesis spec.
- Required artifact checklist for candidate registration.
- Predeclared evaluation question.

### StrategyCandidate

Purpose: registry record for a candidate strategy concept.

States:

- `draft`: candidate record is incomplete.
- `registered`: required identity, lineage, and boundary fields are present.
- `evaluable`: evaluation criteria are complete enough to request an approved
  backtest/simulation task.
- `blocked`: unresolved data, license, leakage, ownership, or hard-stop issue.
- `retired`: no longer eligible for evaluation or adoption review.

Allowed inputs:

- `StrategyHypothesis`.
- Candidate registry schema.
- Evaluation eligibility checklist.

Allowed outputs:

- Strategy candidate registry row.
- Candidate evaluation contract stub.
- Candidate-only conceptual signal, entry/exit, risk-rule, and evaluation
  criteria fields.

### EvaluationEvidence

Purpose: collect historical backtest/simulation evidence as review input, not
as live scoring or automatic adoption input.

States:

- `contract_only`: metric definitions and data boundaries documented.
- `ready_for_approved_run`: candidate and evaluation design are ready for an
  approved owner-lane run.
- `evidence_recorded`: historical evidence packet recorded after an approved
  run.
- `invalidated`: leakage, boundary, provenance, or validation failure found.
- `retired`: no longer used as adoption input.

Allowed inputs:

- StrategyCandidate evaluation contract.
- Approved historical backtest/simulation outputs.
- Leakage, no-lookahead, point-in-time, and provenance review notes.

Allowed outputs:

- Historical evaluation evidence packet.
- Evidence-only return/risk/performance summaries.
- Candidate comparison summaries.
- Evaluation limitations and invalidation notes.

### AdoptionCandidate

Purpose: evidence-only adoption review object for deciding whether a strategy
candidate should be rejected, need more evidence, or request a future
production activation decision.

States:

- `proposed`: selector evidence is ready for review.
- `review_required`: review found gaps or unresolved risks.
- `rejected`: not suitable for adoption review.
- `activation_blocked`: evidence may support a later activation request, but
  production activation remains blocked.

Allowed inputs:

- StrategyCandidate registry record.
- EvaluationEvidence packet.
- Allowlisted selector/evaluator summaries.
- Review gate result.

Allowed outputs:

- Adoption evidence packet.
- Selector/evaluator review packet.
- Decision memo limited to candidate status.
- Future activation decision request, if justified.

Blocked outputs:

- production activation
- production ranking/report connection
- trading recommendation language
- automatic score replacement
- automatic model or strategy activation trigger

## Artifact Paths

| Stage | Owner lane | Input artifacts | Output artifacts |
| --- | --- | --- | --- |
| ResearchHypothesis | Research | `Quant_mvp/research_mvp/docs/evidence_cards/`, research notes, source metadata | `docs/extension/v0_3/research_hypotheses/*.md` |
| StrategyHypothesis | Research + Quant governance | `docs/extension/v0_3/research_hypotheses/*.md` | `docs/extension/v0_3/strategy_hypotheses/*.md` |
| StrategyCandidate | Quant strategy/governance | `docs/extension/v0_3/strategy_hypotheses/*.md` | `Quant_mvp/config/v0_3_strategy_candidate_registry.toml` |
| EvaluationEvidence | Backtest/simulation lane | `Quant_mvp/config/v0_3_strategy_candidate_registry.toml` | `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/*.md` |
| Candidate comparison | Backtest/simulation + ML/evaluator | `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/*.md` | `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison/*.md` |
| AdoptionCandidate | ML/evaluator + root governance | candidate comparison and allowlisted evidence summaries | `docs/extension/v0_3/adoption_candidates/*.md` |

Generated reports may live under:

- `Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/`

Generated outputs remain outside default context unless explicitly promoted as
small review fixtures.

## Baseline Boundaries

v0.3 must not invade the frozen v0.1 baseline:

- Do not modify `technical_composite_score`.
- Do not silently redefine MVP v0.1 `final_composite_score`.
- Do not change production ranking or report behavior.
- Do not expand the KOSPI200 universe without later explicit approval.
- Do not add new market-data ingestion assumptions without later explicit
  approval.

v0.3 must not invade the v0.2 `prob_up_1d_candidate` route:

- Do not replace or reinterpret `prob_up_1d_candidate`.
- Do not treat v0.2 probability output as a strategy selector unless a later
  candidate ML gate explicitly approves that input contract.
- Do not feed historical evaluation metrics into v0.2 model features, score
  weights, ranking inputs, or automatic selector triggers.
- Route any probability-sidecar, feature-table, training/evaluation, leakage,
  or label-separated pipeline work through
  `.agents/skills/quant-candidate-ml-gate/SKILL.md`.

## Active Work Order

### Stage 1: Route Activation and Registration

Owner: root/master.

Allowed:

- keep this route active in `docs/root_hard_stops.md`
- keep latest state in `docs/roadmap_status.md`
- register the route in `docs/context/EXTENSION_REGISTRY.toml`
- maintain entity states and artifact handoffs

Gate:

- `quant-strategy-adoption-gate`
- `quant-review-gate`

Exit evidence:

- route registration points to this document
- product goal is explicit
- forbidden production scope remains closed

### Stage 2: Research Intake

Owner: Research lane.

Allowed:

- collect research ideas, paper-derived ideas, market observations, and
  EvidenceCard-linked strategy ideas
- define ResearchHypothesis packet shape
- define StrategyHypothesis intake schema and conversion rules
- map source, evidence, provenance, license, and limitations

Gate:

- `quant-strategy-adoption-gate`
- research owner review when applicable
- `quant-review-gate`

Exit evidence:

- research packet or StrategyHypothesis intake artifact
- no adoption, ranking, report, live trading, or performance-guarantee claims

### Stage 3: Candidate Registry

Owner: Quant strategy/governance lane.

Allowed:

- define StrategyHypothesis and StrategyCandidate schemas
- implement candidate registry fields, fixtures, and validation checks in the
  approved owner lane
- define required data, universe boundary, conceptual signal, entry/exit,
  risk-rule, evaluation criteria, and rejection reasons
- define no-feedback boundaries into scoring/ranking/model features

Gate:

- `quant-strategy-adoption-gate`
- `score-runtime-semantics-gate` if runtime score/ranking/report semantics are
  touched
- `quant-review-gate`

Exit evidence:

- StrategyCandidate registry contract or registry artifact
- explicit confirmation that production runtime is unchanged

### Stage 4: Backtest and Simulation Evidence

Owner: Backtest/simulation lane.

Allowed:

- run approved candidate-only historical backtests or simulations
- emit `EvaluationEvidence`
- emit evidence-only return/risk/performance summaries
- emit evidence-only candidate comparison summaries
- run no-lookahead, point-in-time, generated-output, and no-feedback checks

Gate:

- `quant-strategy-adoption-gate`
- `quant-subproject-audit-gate` for subproject-wide audit/scope-watchdog work
- `quant-review-gate`

Exit evidence:

- EvaluationEvidence packet
- comparison summary, if requested
- no production score, ranking, report, model-feature, or activation feedback

### Stage 5: ML or Evaluation Selector

Owner: ML/evaluator lane with root governance review.

Allowed:

- implement or run candidate-only selector/evaluator logic in the approved lane
- consume allowlisted hypothesis, registry, and EvaluationEvidence summaries
- emit `AdoptionCandidate` review packets
- compare candidates for review preference and evidence completeness

Gate:

- `quant-strategy-adoption-gate`
- `quant-candidate-ml-gate` if `prob_up_1d_candidate` inputs are used
- `score-runtime-semantics-gate` if runtime score/ranking/report semantics are
  touched
- `quant-review-gate`

Exit evidence:

- AdoptionCandidate selector/evaluator packet
- limitations, confidence, reason codes, and required review
- no automatic production activation

### Stage 6: Adoption Evidence Review

Owner: root governance with affected owner lanes.

Allowed:

- review historical return/risk/performance evidence
- classify candidates as `proposed`, `review_required`, `rejected`, or
  `activation_blocked`
- request a future production activation decision route if evidence justifies
  review

Gate:

- `quant-strategy-adoption-gate`
- `quant-review-gate`
- later activation-specific gates only if root explicitly opens activation work

Exit evidence:

- adoption review packet
- remaining blockers
- explicit activation boundary

## Closed Scope

- live trading
- brokerage integration
- order generation
- production ranking or report connection
- `technical_composite_score` changes
- `final_composite_score` replacement or silent redefinition
- valuation/fundamental scoring activation
- data-ingestion expansion without later approval
- universe expansion without later approval
- backtest metrics as production score weights, production ranking inputs,
  runtime model features, or automatic production activation triggers
- trading recommendations
- buy/sell/hold wording
- expected-return promises
- proven-alpha claims
- profitability-proof wording
- future-performance guarantees
