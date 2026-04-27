---
name: quant-candidate-ml-gate
description: Use for master_mvp post-MVP v0.2 candidate ML probability gate work: prob_up_1d_candidate, candidate-only predictive probability outputs, feature table scope checks, label-separated training/evaluation checks, leakage checks, and repeatable gate contract validation. Do not use for production ranking activation, report behavior changes, final_composite_score replacement, valuation/fundamental scoring, data-ingestion expansion, or trading recommendation work.
---

# Quant Candidate ML Gate

## Purpose

Keep the candidate ML probability gate repeatable without embedding the workflow
in every prompt. This skill is the reusable procedure for the approved
candidate-only `prob_up_1d_candidate` route.

## Loading Process

Read in order:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this `SKILL.md`
4. affected subproject `AGENTS.md`
5. one active packet
6. one domain stub only when needed
7. targeted files

Treat the user prompt as this gate's local goal and requested outputs only. Do
not infer new reusable policy, new production behavior, or broader roadmap
approval from prompt wording.

## Use When

Use this skill for:

- `prob_up_1d_candidate` candidate probability output work
- feature table changes needed for that candidate output
- label-separated training/evaluation pipeline checks
- leakage and future-data checks for candidate ML
- docs/config/tests that preserve candidate-only semantics
- repeatable contract validation for this gate

## Do Not Use When

Do not use this skill to authorize or implement:

- production ranking activation
- report behavior changes
- `final_composite_score` replacement
- `technical_composite_score` or final score semantic changes
- valuation/fundamental scoring
- financial/fundamental fields in technical or final composite scores
- backtest metrics as model features
- backtest feedback into scoring, ranking, or model construction
- new market-data ingestion
- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe expansion
- trading recommendations, buy/sell/hold, proven-alpha, or expected-return
  wording

## Gate Contract

Allowed scope:

- `prob_up_1d_candidate` candidate probability output
- feature table construction needed for that candidate output
- label-separated training/evaluation pipeline
- validation tests and contract checks
- docs or config that preserve candidate-only semantics

Require explicit separation between:

- feature observation time
- label horizon
- training split
- evaluation split
- candidate inference output

Block or flag:

- future data use
- lookahead labels/features
- leakage through cache, report, or generated output reuse
- target leakage through backtest result fields
- silent score redefinition after validation

## Workflow

1. Classify the request as `planning/read-only`, `narrow edit`, or
   `Step/gate closure`.
2. Confirm the requested output is candidate-only and names or maps to
   `prob_up_1d_candidate`.
3. Run the contract validator before edits for gate-level, docs, policy, or
   config work, and after edits when files changed:

   ```bash
   bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh
   ```

4. Read affected subproject instructions. Use a separate role worktree/branch
   for implementation, review, audit, research, chart runtime, or integration
   work required by Step 15+ policy.
5. Inspect only targeted files. Do not read archives or generated outputs unless
   the prompt names a conflict, regression, provenance, or release-evidence
   need.
6. Keep implementation config-first when changing windows, weights, thresholds,
   paths, or toggles.
7. Route review through existing review gate rules if the change touches code,
   tests, config, schemas, generated-output boundaries, cross-project handoffs,
   or Step/gate closure.

## Script

Use the script as a tiny deterministic CLI:

```bash
bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh
```

Expected stdout:

```text
PASS: quant candidate ML gate contract is present
```

The script exits non-zero and prints `FAIL: ...` when required files, routing
paths, frontmatter, or candidate-only contract text are missing.

## Output

For gate planning or review, answer in Korean using this compact shape:

```yaml
gate: quant_candidate_ml
task_class: planning/read-only | narrow edit | Step/gate closure
scope: candidate_only | blocked | needs_root_approval
allowed_outputs:
  - "<current deliverable>"
blocked_outputs:
  - "<none or forbidden scope>"
contract_validation: pass | fail | not_run
targeted_checks:
  - "<command or file check>"
remaining_risks:
  - "<none or risk>"
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```

For implementation handoff, include changed files, validation seen,
intentionally unchanged surfaces, and whether review/audit is required.
