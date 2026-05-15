# Readiness Reports

This directory is reserved for compact readiness report documentation and
small, explicitly promoted review packets.

Runtime readiness outputs are generated artifacts. They should stay outside
source control unless a later task explicitly promotes a small reference
fixture.

Current contract:

- `docs/extension/v2_0_evidence_readiness_gap_report.md`
- `src/validation/v2_0_evidence_readiness.py`

The v2.0 readiness validator is evidence-only and manual-review-support only.
It checks PIT safety, lineage, coverage, feature/label separation, leakage and
no-lookahead prevention, cost/liquidity readiness, robustness, and forbidden
output boundaries before KOSPI200 strategy candidates can be reviewed as
`AdoptionCandidate` material.
