---
name: master-mvp-review-mvp-specialist
description: Project-local Codex skill for conditional review_mvp specialist code and final-validation review. Use only when Review Gate sets review_mvp_required true or master/root explicitly requests review_mvp specialist review.
---

# review_mvp Specialist

## Skill Name

review_mvp Specialist

## Purpose

Invoke `review_mvp` as a specialist code-review and final-validation support
path only when local policy requires it. This skill must not become the default
review bottleneck for ordinary local changes.

## When To Use

Use only when:

- `.agents/skills/review_gate/SKILL.md` outputs
  `review_mvp_required: true`
- master/root explicitly requests `review_mvp`
- Step-end or final-validation policy requires specialist review
- unresolved local-review risk needs independent code/final-validation review

## When Not To Use

Do not use for:

- ordinary docs/context-only changes
- local subproject changes with clean local review and no high-risk trigger
- technical score selection review
- valuation/fundamental review
- GitHub PR review automation
- GitHub review trigger wording

## Required Inputs

Use the narrowest available inputs:

- Review Gate output
- master/root request reason
- changed file list from `git diff --name-only`
- source subproject local review summary, when available
- focused validation/test summary, when available
- unresolved risk or finding that triggered specialist review

## Allowed File/Tool Scope

Inspection scope follows `docs/review_mvp_policy.md` and `review_mvp/AGENTS.md`.

Modification outside `review_mvp/` is allowed only when all are true:

- master/root or the source subproject explicitly assigns a repair
- the repair is the narrowest fix for a concrete review finding
- target files are allowed by the active `WORKSPACE_MANIFEST.md` or a documented
  root/master resume decision
- affected subproject `AGENTS.md`, tests/checks, generated-output policy, and
  root-boundary rules are followed

Otherwise, report findings and route fixes to the responsible subproject.

## Procedure

1. Confirm `review_mvp_required: true` or explicit master/root request.
2. Identify scope, source subproject, changed paths, and trigger reason.
3. Choose the narrowest review mode from `docs/review_mvp_policy.md`.
4. Run `review_mvp` commands only when the scope justifies them.
5. Report concrete findings first, ordered by blocking risk.
6. Do not perform technical selection or valuation review.
7. Do not repair outside `review_mvp/` unless explicitly assigned and allowed.

## Output Schema

```yaml
review_mvp_status: accept | hold | reject
mode: quick | normal | step-end | specialist
scope:
  - "<path or material>"
trigger_reason: "<short Korean summary>"
findings:
  blocking:
    - "<none or finding>"
  warnings:
    - "<none or finding>"
missing_evidence:
  - "<none or evidence gap>"
required_follow_up:
  - "<none or focused action>"
validation_seen: "<command/result summary or unavailable>"
```

## Validation Expectations

For `review_mvp` internal changes, run from `review_mvp/` and target only that
subproject:

```powershell
python review.py . --format markdown
python -m unittest discover -s tests -v
```

For explicit root/master final-validation or cross-project review only:

```powershell
python review_mvp/review.py . --exclude-dir data --exclude-dir outputs --exclude-dir __pycache__ --exclude-dir samples --format markdown
python -m unittest discover -s review_mvp/tests -v
```

Use the smallest validation profile that matches the trigger.

## Escalation Conditions

Escalate or hold when:

- master-up evidence is missing
- root-agent conflict stop is unresolved
- hard-stop, roadmap/order, generated-output, schema, ranking, report,
  backtest, or valuation boundary risk is unresolved
- a required repair would cross project boundaries without explicit assignment
- technical or valuation review is required but has not been performed

## Optional Resources Or Scripts

- `docs/review_mvp_policy.md`
- `review_mvp/AGENTS.md`
- `review_mvp/README.md`
- `review_mvp/review.py`
- `review_mvp/tests`
