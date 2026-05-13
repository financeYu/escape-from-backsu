# v1.0-rc LayerRegistry contract

Status: Phase 5 contract for pre-freeze readiness.

## Purpose

`LayerRegistry` is an extension mechanism for candidate-only and diagnostic
layers. It records layer status, category, adapter references, input/output
contracts, allowed modes, blocked modes, and activation flags so future layers
can be registered without rewriting core scoring modules.

Registration is not activation approval. Phase 5 does not create production
ranking replacement, trading output, valuation/fundamental active scoring, or
futures/index/macro/regime active scoring.

## Config

Canonical config:

- `config/layer_registry.toml`

Fixture entries include:

- active technical candidate layer
- active statistical candidate layer
- diagnostic-only data quality layer
- candidate-only valuation placeholder
- inactive futures/macro reference placeholder

## Status semantics

- `active`: may participate only in currently approved evidence/candidate-only
  pathways and does not imply production ranking or live execution.
- `inactive`: registered but unavailable for computation.
- `candidate_only`: may produce candidate artifacts or evidence inputs only
  when separately allowed.
- `diagnostic_only`: may produce diagnostics or review context only.
- `diagnostic_reference`: read-only reference layer.

## LayerAdapter

`LayerAdapter` is a minimal interface:

- `layer_id`
- `validate_inputs(...)`
- `build_candidate_output(...)`
- `build_diagnostic_output(...)`
- `describe_contract(...)`

Phase 5 provides the interface and non-computing placeholder adapter only. It
does not implement valuation/fundamental scoring adapters or futures/index
scoring adapters.

## WeightConfig integration

`WeightConfig` active weights may reference only registry layers that are:

- `layer_status = "active"`
- `layer_category` in `technical` or `statistical`
- `scoring_role = "candidate_evidence_input"`
- `ranking_role = "none"`
- `production_enabled = false`
- `live_execution_enabled = false`

Inactive, diagnostic-only, diagnostic-reference, valuation/fundamental, and
futures/index/macro/regime placeholder layers cannot be used as active weights.

## Boundaries

Valuation/fundamental layers must keep
`valuation_fundamental_active_scoring_enabled = false`.

Futures, index, macro, and regime layers must not become active scoring layers
in Phase 5.

Diagnostic/reference layers must not claim ranking, adoption, recommendation,
or trading roles.

Phase 6+ may consume allowed layer outputs as evidence inputs only after a
separate explicit approval.
