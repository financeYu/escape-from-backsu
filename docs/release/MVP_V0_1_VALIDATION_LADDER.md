# MVP v0.1 Validation Ladder

Use the smallest tier that matches the risk of the change. Keep results compact:
`PASS`, `FAIL`, or `NOT RUN`, plus the command and shortest useful reason.

## Tier 1: Context / Guardrail Smoke

- Purpose: verify compact context docs, archive routing, and forbidden wording
  guardrails.
- Example command:

```powershell
python -m pytest -q tests/context
```

- When to run: context, release, routing, or pre-freeze documentation changes.
- Failure means: stop and fix context scope, archive routing, line limits, or
  forbidden release wording before broader validation.

Also run:

```powershell
python scripts/context/check_context_staleness.py
python scripts/context/check_context_conflicts.py
```

## Tier 2: Scanner / Reports / Validation Focused Tests

- Purpose: verify the main scanner, report, and guardrail surfaces affected by
  MVP release boundaries.
- Example command:

```powershell
python -m pytest -q tests/scanner tests/reports tests/validation
```

- When to run: contract, ranking/report interpretation, or guardrail-adjacent
  changes after Tier 1 passes.
- Failure means: the MVP boundary or user-facing explanation surface may be
  inconsistent; do not freeze until investigated.

## Tier 3: Integration Tests

- Purpose: verify cross-surface contracts at integration boundaries.
- Example command:

```powershell
python -m pytest -q tests/integration
```

- When to run: release/freeze verification, cross-project handoff review, or
  changes touching more than one validation surface.
- Failure means: a contract handoff may be broken; run targeted investigation
  before any freeze decision.

## Tier 4: Full Test Suite

- Purpose: confirm broad repository behavior after focused tiers pass.
- Example command:

```powershell
python -m pytest -q
```

- When to run: final freeze gate, broad integration review, or after required
  fixes that touched shared behavior.
- Failure means: MVP v0.1 is not ready for final freeze until the failing area is
  triaged, fixed, or explicitly downgraded with evidence.

## Compact Result Format

- `Tier 1: PASS - tests/context and context checkers passed.`
- `Tier 2: NOT RUN - docs-only patch after Tier 1; no scanner/report behavior touched.`
- `Tier 3: NOT RUN - no integration surface touched.`
- `Tier 4: NOT RUN - focused context validation sufficient for this patch.`
