# v0.2 Score Revision Approval Packet Draft

Status: draft approval packet only. This document does not approve
implementation, modify MVP v0.1, or activate score, ranking, report, backtest,
valuation, or data-ingestion behavior.

## Purpose

This packet drafts the approval requirements for a future `v0.2` score revision
line. It exists to decide whether a separately approved post-MVP implementation
Step may be opened later.

The frozen MVP v0.1 baseline remains unchanged:

- KOSPI200-only.
- Technical-only.
- Existing `technical_composite_score` and `final_composite_score` semantics
  remain unchanged.
- Backtest output remains evaluation-only and must not feed scoring or ranking.
- Valuation or fundamental data must not enter technical or final composite
  scoring.

## Candidate Scope

The future `v0.2` score revision may only be considered after a concrete
proposal defines:

- candidate score names
- score family and branch
- intended technical purpose
- raw input features
- formula design path
- normalization candidates
- minimum history requirements
- warmup and invalid-row behavior
- expected overlap with existing MVP v0.1 scores
- failure modes and rejection criteria
- implementation owner and validation profile

Allowed score branches for proposal review:

- `technical`
- `diagnostic`
- `out_of_scope`

No candidate score is adopted by this draft. No production field, report, or
ranking behavior changes are authorized by this packet.

## Hard Boundaries

The future score revision must not:

- silently redefine existing MVP v0.1 scores
- use future returns or post-decision values as score inputs
- use diagnostics as ranking signals without explicit adoption review
- introduce valuation or fundamental data into technical or final composite
  scoring
- introduce new market data ingestion
- activate new markets, asset classes, or multi-universe ranking
- connect backtest output to scoring, ranking, adoption, or optimization
- introduce trading recommendation language
- change report ordering or interpretation without a separately approved report
  contract

## Required Architecture Review

Before implementation approval, the Score Architect must produce a candidate
score specification covering:

- `score_name`
- `score_family`
- `score_branch`
- `purpose`
- `market_regime_where_it_helps`
- `raw_input_features`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `expected_overlap_risk`
- `failure_modes`
- `data_requirements`
- `notes_on_interpretability`

Any ambiguous formula, timing rule, data requirement, or branch classification
must be resolved before code work starts.

## Required Testing And Diagnostics Plan

Before implementation approval, the Research Tester plan must define:

- raw score output schema
- normalized score output schema
- cross-sectional normalization behavior
- time-series normalization behavior
- NaN, warmup, and insufficient-history handling
- outlier handling
- coverage diagnostics
- rank stability diagnostics
- turnover proxy diagnostics
- score correlation and redundancy diagnostics
- generated-output boundary

The plan must state which checks are required before any candidate can move to
technical selection review.

## Required Technical Selection Review

Before adoption can be considered, the Technical Selection Reviewer must review
each implemented candidate for:

- technical relevance
- technical distinctiveness
- technical stability
- technical complexity cost
- regime fit
- redundancy risk
- implementation clarity
- data sufficiency

Allowed review outcomes:

- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

This draft does not assign any of these outcomes. It only defines the approval
path needed before outcomes may be assigned.

## Timing And No-Lookahead Contract

Every future implementation request must define:

- decision timestamp or decision date
- source data availability timing
- feature construction timing
- normalization population timing
- report generation timing
- evaluation label timing when evaluation is performed

No-lookahead requirements:

- Scores must be computable using only information available at the decision
  time.
- Cross-sectional normalization must use only the eligible same-date population
  available at that time.
- Time-series normalization must use only prior and current eligible values.
- Evaluation labels must remain separate from scoring and ranking inputs.
- Rows with unresolved timing or availability ambiguity must be excluded or
  marked non-evaluable.

## Backtest And Evaluation Boundary

Backtest or simulation output for `v0.2` score candidates is evaluation-only.
It may support diagnostics, leakage review, stability review, and candidate
comparison, but it must not feed upstream scoring, ranking, adoption, or
parameter optimization.

Any evaluation report must state:

- candidate-only status
- data window and eligibility rules
- timing assumptions
- leakage checks
- limitations
- generated-output boundary
- no production adoption unless a later approval explicitly grants it

## Schema And Lineage Freeze Before Implementation

Implementation approval requires frozen draft contracts for:

- score specification schema
- raw feature lineage
- normalized score lineage
- composite handoff boundary
- diagnostic output schema
- generated-output and source-control policy
- config ownership for windows, thresholds, weights, toggles, and branches
- validation profile and required tests
- rollback or deactivation rule

Any later change to score meaning, formula, input lineage, normalization
semantics, adoption state, or ranking use must trigger a new approval review.

## Review And Audit Gate Checklist

Before implementation begins, the future approval request must pass:

- root/master scope confirmation
- correct post-MVP version or Step assignment
- correct role branch/worktree and workspace manifest
- scope watchdog review when score, ranking, composite, report, backtest, or
  generated-output boundaries are touched
- architecture review
- testing and diagnostics plan review
- technical selection review plan
- no-lookahead review
- generated-output and cache boundary review
- valuation/fundamental hard-stop review
- backtest feedback hard-stop review
- cross-step conflict checkpoint
- `review_mvp` specialist review when code, tests, config, schemas,
  generated-output boundaries, or cross-project handoffs are included

## Remaining Risks And Blockers

Implementation cannot begin until these are resolved:

- no approved post-MVP score revision Step exists
- no candidate score list is frozen
- no score specification schema is approved
- no normalization and composite handoff contract is approved
- no timing and no-lookahead contract is approved
- no diagnostics and redundancy plan is approved
- no generated-output boundary is approved
- no validation profile is approved
- no review/audit route is completed

## Approval Verdict

`v0.2` score revision status: not approved for implementation.

This packet is a draft only. It may be used to prepare a future approval
request, but it does not authorize implementation, score adoption, ranking
changes, report changes, backtest feedback loops, valuation activation, or data
ingestion changes.
