# v0.2 Rollback And Deactivation Rule

Status: frozen rollback/deactivation rule for the post-MVP `v0.2 predictive
probability score route`.

## Required Deactivation Controls

Implementation must include a config-owned disable path before adoption:

- disable probability model scoring
- stop generated probability output creation
- preserve old MVP v0.1 outputs unchanged
- mark candidate route inactive in user-visible status

## Rollback Requirements

Rollback must not:

- rewrite MVP v0.1 release evidence
- alter old score formulas
- alter production ranking
- delete source-controlled contracts
- hide failed validation evidence

Rollback must:

- record reason
- record affected model and feature-set version
- clean or quarantine generated runtime outputs according to generated-output
  policy
- leave a master-up risk note if adoption was under review
