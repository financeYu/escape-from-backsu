# v0.3 Production Activation Decision Gate

Status: blocked separate production approval route.
Parent selector gate: `docs/extension/v0_3_adoption_candidate_selector_gate.md`.

This document separates v0.3 `AdoptionCandidate` evidence from operational
strategy adoption. The active v0.3 route may produce adoption evidence and
historical return/risk/performance summaries, but this document does not
authorize production activation.

## Purpose

Production activation is a future, separate root-approved route. It may be
requested only after candidate evidence exists, but candidate evidence never
activates runtime behavior by itself.

## Required Pre-Conditions

Before any future activation task can be considered:

- Root must explicitly open a production activation task.
- The candidate must have an `AdoptionCandidate` packet.
- The candidate must have EvaluationEvidence with historical return, risk, and
  performance summaries framed as evidence only.
- The packet must list unresolved blockers and required reviews.
- No-feedback checks must pass.
- Generated-output boundaries must be reviewed.
- Runtime score, ranking, and report semantics must be reviewed through
  `score-runtime-semantics-gate` if touched.
- Candidate ML or probability inputs must route through
  `quant-candidate-ml-gate` if touched.
- Subproject-wide audit or scope-watchdog work must route through
  `quant-subproject-audit-gate` when applicable.
- Completion must pass `quant-review-gate`.

## Still Blocked Here

- automatic production activation
- trading recommendations
- buy/sell/hold wording
- expected-return claims
- proven-alpha claims
- production ranking/report changes without explicit runtime semantic approval
- `final_composite_score` replacement without explicit root and semantic gate
  approval
- backtest metrics as direct runtime model features, score weights, ranking
  inputs, or automatic production activation triggers

## Adoption vs Operational Adoption

`AdoptionCandidate` means evidence is organized for review and a candidate may
be review-preferred within the current evidence cohort.

Operational strategy adoption means production behavior would change. That is a
separate approval route and remains blocked until root explicitly opens it.
