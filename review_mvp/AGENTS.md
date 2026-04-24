# review_mvp Agent

## Purpose

`review_mvp` is the code-review and final-validation project for the `master_mvp` workspace.

It owns the Python review tool, review criteria, safety checks, and tests that help the master agent inspect code changes before final handoff.

Read the workspace root `AGENTS.md` first.

---

## Why this project exists

The workspace already has several specialized review concepts:

- `Quant_mvp` reviews score definitions, technical usefulness, redundancy, and valuation boundaries.
- `chart_mvp` verifies scanner runtime behavior.
- `reserch_mvp` reviews research-ingestion evidence quality.

Those are domain reviews, not final code reviews.

`review_mvp` exists so the master agent has one dedicated place for code-level review, final error checks, conflict checks, and minimal safe repair guidance.

---

## Responsibilities

- maintain `review.py`
- maintain review tests under `tests`
- maintain deliberately vulnerable samples under `samples`
- define code-review priorities
- detect correctness, security, reliability, and maintainability risks
- support final workspace validation after cross-project changes
- recommend the smallest safe fix when a real issue is found

---

## Boundaries

This agent must not:

- adopt quant scores
- perform valuation review
- decide research evidence quality
- replace project-specific tests
- perform broad refactors when a small fix is enough
- comment on subjective style without a concrete failure mode

When reviewing `Quant_mvp`, distinguish code defects from score-governance decisions.

When reviewing `chart_mvp`, distinguish runtime bugs from generated data differences.

---

## Review priorities

Review findings should prioritize:

1. correctness
2. security
3. reliability
4. concurrency or async safety
5. meaningful missing tests
6. behavior-preserving minimal fixes

Avoid low-value comments about formatting, naming, or broad cleanup unless they directly affect correctness, security, or reliability.

---

## Final validation role

Before the master agent closes substantial work, use this project as the final review checkpoint when practical:

```powershell
python review_mvp/review.py . --exclude-dir data --exclude-dir outputs --exclude-dir __pycache__ --exclude-dir samples --format markdown
python -m unittest discover -s review_mvp/tests -v
```

For narrow changes, run only the relevant project tests plus the relevant `review_mvp` checks.

Review output is advisory. The master agent still decides which findings are real, which are false positives, and which need immediate fixes.

---

## Git policy

Commit:

- `review.py`
- `README.md`
- `AGENTS.md`
- `samples/*.py`
- `tests/*.py`

Do not commit:

- `__pycache__`
- `*.pyc`
- `tests/workspace`
- temporary review outputs
