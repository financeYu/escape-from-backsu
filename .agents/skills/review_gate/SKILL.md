---
name: master-mvp-review-gate
description: Project-local Codex skill for routing master_mvp review work. Use before deciding whether local technical, valuation, adoption, or review_mvp specialist review is required. This is local routing only, not GitHub pull request automation.
---

# Review Gate

## Skill Name

Review Gate

## Purpose

Route local `master_mvp` tasks to the narrowest required review path. This skill
is a dispatcher only. It must not perform technical, valuation, adoption, code,
backtest, or final-validation review itself.

These are project-local Codex skill instructions under `.agents/skills/`.
They are not globally installed Codex skills and are not GitHub PR review
configuration.

## When To Use

Use this skill before deciding whether to invoke:

- `.agents/skills/technical_review/SKILL.md`
- `.agents/skills/valuation_review/SKILL.md`
- `.agents/skills/review_mvp_specialist/SKILL.md`

Use it when a task changes files, validates a change, reports review status, or
asks whether specialist review is needed.

## When Not To Use

Do not use this skill to:

- perform the review itself
- judge technical usefulness, adoption quality, valuation support, or code
  correctness
- configure automatic GitHub PR review
- require GitHub PR review usage
- use GitHub review trigger wording
- reopen completed Step 1-20 history

## Required Inputs

Inspect only:

- current task summary
- `git diff --name-only`
- relevant changed file paths
- validation or test result summary, if available
- explicit user request
- risky wording in changed docs or generated reports

## Allowed File/Tool Scope

Allowed local tools:

- `git status --short`
- `git diff --name-only`
- `git diff --check`
- targeted `rg`
- focused local validation commands already appropriate for the changed files

Do not run `git fetch`, `git pull`, or `git push` during routing unless
root/master explicitly instructs it or the task is in its final publication
stage.

Do not read archives, full validation logs, market data, caches, generated chart
images, or old Step details unless a named conflict, regression, provenance, or
release-evidence check requires the narrowest lookup.

## Procedure

1. List changed paths with local Git.
2. Read only the relevant changed files or summaries.
3. Check explicit user request for technical, valuation, adoption, full,
   specialist, final, or `review_mvp` review.
4. Check trigger conditions.
5. Check non-trigger conditions.
6. Emit one compact machine-readable decision.
7. Stop. Do not perform the downstream review.

## Trigger Conditions

Return `technical_review_required` when changed paths or text touch technical
score definitions, candidate scores, normalization, diagnostics, usefulness,
redundancy, stability, regime fit, or misuse of technical outputs as ranking,
composite, backtest, advice, or alpha.

Return `valuation_review_required` when changed paths or text touch valuation,
fundamentals, PER, PBR, ROE, quality, profitability, accounting, revision,
filing dates, availability dates, point-in-time financial data, valuation
claims, or cheap/undervalued wording.

Return `adoption_review_required` when changed paths or text touch score
adoption, downgrade, defer, reject decisions, composite membership, score
weights, ranking semantics, or score-to-production handoff.

Return `full_review_required` when more than one specialized review is
triggered, validation fails with schema/contract/boundary risk, forbidden
investment wording appears, the user requests full review, or root policy
requires `review_mvp`.

Set `review_mvp_required: true` only for high-risk code, tests, config, schemas,
generated-output boundaries, cross-project handoffs, roadmap-gated behavior,
Step-end/final-validation gates, unresolved local-review risks, or explicit
master/root `review_mvp` requests.

## Non-Trigger Conditions

Return `review_not_required` or `light_policy_check_only` when all changed files
are docs/context-only, do not alter score, ranking, report, backtest, valuation,
schema, generated-output, roadmap verdict, or guardrail semantics, and focused
checks are clean.

Typo fixes, link-only context routing updates, and reminders that valuation is
unavailable or technical-only are normally non-triggers unless they weaken a
hard stop or introduce risky claims.

## Output Schema

Return YAML:

```yaml
gate_result: review_not_required | light_policy_check_only | technical_review_required | valuation_review_required | adoption_review_required | full_review_required
reason: "<one short Korean sentence>"
next_skills:
  - "none | .agents/skills/technical_review/SKILL.md | .agents/skills/valuation_review/SKILL.md | .agents/skills/review_mvp_specialist/SKILL.md"
review_mvp_required: true | false
minimum_validation_profile: "<focused docs/config/schema/tests/check profile>"
```

Use `next_skills: ["none"]` only for `review_not_required`. For
`light_policy_check_only`, use
`docs/context/CODEX_REVIEW_GATE_POLICY.md#light-policy-check`.

## Validation Expectations

For gate-only documentation work, validate with targeted grep:

- `SKILL.md` files exist
- YAML `name:` and `description:` are present
- gate vocabulary is present
- forbidden wording is listed as prohibited
- GitHub review trigger wording is absent
- GitHub PR review is not required
- review skills are on-demand, not default
- `review_mvp` is conditional on Gate/master/root trigger
- `git diff --check` passes for changed docs

## Escalation Conditions

Escalate to a downstream skill instead of analyzing further when:

- trigger conditions are met
- validation/test failure indicates schema, ranking, report, backtest, PIT, or
  generated-output boundary risk
- changed text includes forbidden investment wording
- the gate needs more than path, summary, and compact wording checks
- root/master asks for specialist or full review

## Optional Resources Or Scripts

- `docs/context/CODEX_REVIEW_GATE_POLICY.md`
- `docs/review_mvp_policy.md`
- `review_mvp/review.py` only when `review_mvp_required: true`
