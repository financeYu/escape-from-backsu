# v1.0-rc freeze plan

Status: pre-freeze readiness plan only.

Current readiness state:

- Phase 0: COMPLETE / preflight and scope boundary.
- Phase 1: COMPLETE / next-day / 1D hardcoding audit.
- Phase 2: COMPLETE / HorizonPolicy contract.
- Phase 3: COMPLETE / SimulationRunManifest contract.
- Phase 4: COMPLETE / WeightConfig loop contract.
- Phase 5: COMPLETE / LayerRegistry contract.
- Phase 6: COMPLETE / EvaluationEvidenceV1 contract.
- Phase 7: COMPLETE / ML/rule selector evaluator contract.
- Phase 8: COMPLETE / ManualReviewPacket contract.
- Phase 9: COMPLETE / freeze readiness validation packet.

## Purpose

v1.0-rc prepares the project for a future evidence-only multi-horizon
strategy candidate selector.

Phase 0 through Phase 9 prepare the scope boundary, next-day / 1D hardcoding
audit, HorizonPolicy contract, SimulationRunManifest contract, WeightConfig
loop contract, LayerRegistry contract, EvaluationEvidenceV1 contract,
selector/evaluator contract, ManualReviewPacket contract, and
freeze-readiness validation packet needed for evidence-only manual review.
They do not create final v1.0 release evidence.

Final v1.0 freeze, tag, release, and push are out of scope for this plan.

## Future v1.0 target modules

These modules are the completed evidence-only readiness phases. They are not
production activation modules.

- HorizonPolicy
- SimulationRunManifest
- WeightConfig loop
- LayerRegistry
- EvaluationEvidenceV1
- ML/rule-based AdoptionCandidate selector
- ManualReviewPacket

## Phase map

| phase | scope |
| --- | --- |
| Phase 0 | preflight and scope boundary |
| Phase 1 | next-day / 1D hardcoding audit |
| Phase 2 | HorizonPolicy contract |
| Phase 3 | SimulationRunManifest |
| Phase 4 | WeightConfig loop |
| Phase 5 | LayerRegistry |
| Phase 6 | EvaluationEvidenceV1 |
| Phase 7 | ML selector / evaluator |
| Phase 8 | ManualReviewPacket |
| Phase 9 | v1.0-rc validation packet |

## Explicit non-goals for Phase 0 and Phase 1

- no runtime behavior changes
- no scoring changes
- no ranking changes
- no backtest semantic changes
- no ML model training
- no new market data
- no valuation/futures activation
- no trading output
- no Phase 2+ artifact implementation

## Phase 2 entry conditions

Phase 2 may start only when all of these are true:

- Phase 0 documents exist.
- Phase 1 audit exists.
- All hardcoded next-day / 1D findings are classified.
- No hard-stop violation is present.
- Unresolved findings are documented as manual review items.

## Post-Phase9 boundary

Phase 0 through Phase 9 do not authorize final v1.0 freeze, tag, release,
push, production activation, live execution, valuation/fundamental activation,
futures/options/index activation, or new post-Phase9 modules. Any such work
requires a later explicit task approval and a fresh route-state update.

## Phase 0 and Phase 1 acceptance boundary

Phase 0 and Phase 1 are complete when the pre-freeze scope is explicit, the
compatibility boundary is documented, the hardcoding audit exists, and the
changed documents pass focused local validation. Passing this boundary does
not authorize Phase 2 implementation, final release work, production
activation, remote Git actions, or trading/valuation/futures behavior.
