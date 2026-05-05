# v0.3 StrategyHypothesis Intake Contract

Status: active research intake contract.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Owner lane: Research intake with root governance review.

This contract defines how research, papers, and market ideas are collected and
converted into `StrategyHypothesis` records for v0.3. This stage organizes
ideas and evidence so they can become quant strategy candidates. It is not a
profitability claim, not an adoption decision, and not an evaluation result.

Fixed disclaimer for every produced hypothesis:

> This is not a profitability claim, not an adoption decision, and not an
> evaluation result. It is a pre-evaluation StrategyHypothesis intake artifact.

Machine-checkable fixed disclaimer:
`This is not a profitability claim, not an adoption decision, and not an evaluation result. It is a pre-evaluation StrategyHypothesis intake artifact.`

## Architecture Routing

StrategyHypothesis intake work must pass through the active root architecture
chain before research-lane execution or validation begins:

`agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor -> agent-worker-pool -> agent-reporter`

The default domain compatibility target is `quant-strategy-adoption-gate`.
Completion acceptance requires `quant-review-gate`. The supervisor handoff must
lock allowed scope, forbidden scope, required output, validation commands, and
Korean final report format before any intake artifact is created or updated.

## Intake Boundary

Allowed:

- summarize a research idea
- collect paper-derived strategy ideas, research notes, EvidenceCard-linked
  ideas, and manual strategy observations
- map source, evidence, provenance, license, and usage boundary
- state a testable hypothesis in non-runtime language
- mark duplication, scope, and evidence limitations

Blocked:

- StrategyCandidate registration
- signal, entry, exit, sizing, or execution implementation
- backtest execution or simulation result claims
- superior-strategy judgment
- automatic production activation

## Input and Output Paths

Proposed input paths:

- `Quant_mvp/research_mvp/docs/evidence_cards/`
- `Quant_mvp/research_mvp/docs/research_notes/`
- `docs/extension/v0_3/research_hypotheses/*.md`

Proposed output paths:

- `docs/extension/v0_3/strategy_hypotheses/*.md`
- `docs/extension/v0_3/intake_dedupe_index.md`
- `docs/extension/v0_3/intake_rejection_log.md`

These are active v0.3 intake boundaries. They authorize source and idea intake
for candidate evidence work only. They do not authorize StrategyCandidate
registration, backtest execution, selector/evaluator output, or production
runtime changes by themselves.

## StrategyHypothesis Schema

Required fields:

- `strategy_hypothesis_id`: stable ID, for example `sh_v0_3_YYYYMMDD_slug`.
- `status`: one of `draft`, `scope_checked`, `candidate_spec_ready`, `rejected`,
  or `duplicate`.
- `created_at`: local date or timestamp.
- `owner_lane`: `research`, `quant_strategy`, or `mixed`.
- `source_idea_title`: short source idea title.
- `source_type`: one of `paper`, `research_note`, `market_observation`,
  `evidence_card`, or `manual_idea`.
- `source_refs`: local paths or external citations sufficient to locate the
  source without embedding full source text.
- `evidence_refs`: EvidenceCard IDs or paths when available.
- `provenance`: source origin, author/source name when available, retrieval or
  observation date, and custody note.
- `license_status`: one of `open`, `restricted`, `unknown`,
  `internal_note_only`, or `needs_review`.
- `usage_boundary`: allowed use and blocked use for this hypothesis.
- `research_idea_summary`: concise neutral summary of the idea.
- `hypothesis_statement`: testable pre-evaluation statement without profit,
  adoption, or superiority language.
- `observable_inputs`: conceptual observable inputs, not implementation fields.
- `evaluation_question`: what a later historical evaluation contract would ask.
- `scope_boundaries`: universe, data, activation, and baseline limitations.
- `v0_1_boundary_check`: confirmation that the frozen MVP v0.1 baseline is not
  changed.
- `v0_2_boundary_check`: confirmation that `prob_up_1d_candidate` is not
  replaced, reinterpreted, or used as a selector without a later approved gate.
- `duplicate_check`: normalized key and nearest known related hypotheses.
- `production_boundary_check`: confirmation that automatic production
  activation wording is absent except when quoted as a blocked phrase.
- `next_allowed_step`: one of `revise`, `reject`, or
  `request_strategy_candidate_registration`.
- `fixed_disclaimer`: exact disclaimer from the top of this document.

Optional fields:

- `related_hypothesis_ids`
- `research_limitations`
- `data_availability_questions`
- `license_questions`
- `review_notes`

## Source, Evidence, Provenance, License, Usage Fields

`source_refs` must identify where the idea came from. Use paths or citations;
do not paste long paper text into the hypothesis.

`evidence_refs` must point to EvidenceCards or research packets when present.
Absence of EvidenceCard support must be recorded as a limitation, not silently
filled with assumptions.

`provenance` must separate:

- who or what produced the source
- when the source was observed or retrieved
- where the local custody record lives, if any
- whether the source is direct, derived, or manually summarized

`license_status` must be explicit. `unknown` or `needs_review` may proceed only
as an intake limitation and must not become implementation permission.

`usage_boundary` must state:

- allowed use: hypothesis drafting and later contract review
- blocked use: model feature input, ranking input, report content, live signal,
  or adoption decision

## Research Idea to Hypothesis Rules

1. Extract only the neutral mechanism or market observation.
2. Convert claims into a testable question, not an expected outcome.
3. Replace performance language with evaluation-neutral wording.
4. Keep feature, signal, entry, exit, and execution details conceptual.
5. Record source limitations and license status before scope advancement.
6. Check v0.1 and v0.2 boundaries before `candidate_spec_ready`.
7. Assign `rejected` if the idea requires forbidden runtime changes, forbidden
   data ingestion, universe expansion, automatic production activation, or live
   trading.
8. Assign `duplicate` if the normalized hypothesis key matches an existing
   active or rejected hypothesis above the duplicate threshold.

Examples of permitted conversions:

| Research idea wording | StrategyHypothesis wording |
| --- | --- |
| "Paper reports momentum anomaly." | "Evaluate whether a momentum-conditioned candidate has historically distinct behavior under a later approved evaluation contract." |
| "Market commentary says reversal after sharp drops." | "Evaluate whether a reversal-condition candidate is historically measurable under a later approved evaluation contract." |
| "A factor may improve returns." | "Evaluate whether the factor definition is measurable and reviewable as a candidate-only hypothesis." |

## Duplicate Prevention

Each hypothesis must compute or record a normalized duplicate key using:

- source mechanism
- observable condition family
- intended evaluation question
- universe boundary
- required data family
- blocked runtime dependency, if any

Treat a new hypothesis as duplicate when it has the same mechanism and
evaluation question as an existing hypothesis, even if the source title or
wording differs.

Treat a new hypothesis as related, not duplicate, when:

- the mechanism is different
- the evaluation question is materially different
- the required data family differs
- one hypothesis is a broader parent and the other is a narrower child

The dedupe index should record:

- `normalized_key`
- `hypothesis_id`
- `status`
- `source_refs`
- `related_hypothesis_ids`
- `duplicate_of`, when applicable
- `dedupe_reason`

## Fixed Wording Policy

Allowed wording:

- `hypothesis`
- `candidate-only`
- `pre-evaluation`
- `historical evaluation question`
- `requires later approved evaluation`
- `not an adoption decision`
- `not a profitability claim`
- `not an evaluation result`

Production-scope wording blocked by this intake contract:

- `adopted`
- `production-ready`

Production-scope phrases may appear only inside blocked-wording policy,
validation, or rejection notes.

## Exit Criteria

A StrategyHypothesis intake artifact may exit this stage only when:

- schema-required fields are present
- source/evidence/provenance/license/usage boundary are explicit
- duplicate check is recorded
- fixed disclaimer is present exactly
- v0.1 and v0.2 boundaries are checked
- no StrategyCandidate registration occurred inside the intake artifact
- no backtest, ML selector, signal, entry, exit, or production activation was
  implemented or triggered
