# Review Gate

This file defines the Review Gate as a lightweight dispatcher. It decides
whether a review skill must be invoked; it does not perform technical,
valuation, adoption, backtest, or code review itself.

## Inputs

The gate may inspect only:

- current task summary
- `git diff --name-only`
- relevant changed file paths
- validation or test result summary, when available
- explicit user request
- risky wording in changed docs or generated reports

Do not load archive/history files, full validation logs, market data, caches,
generated chart images, or old Step details for ordinary gate decisions.

During active work, prefer local Git operations only: file inspection, edits,
`git diff`, focused local validation, and status checks. Do not run `git fetch`,
`git pull`, or `git push` during the gate unless the root/master explicitly
instructs it or the task is in its final publication stage.

## Output Vocabulary

The gate must output exactly one of:

- `review_not_required`
- `light_policy_check_only`
- `technical_review_required`
- `valuation_review_required`
- `adoption_review_required`
- `full_review_required`

Required output shape:

```text
gate_result: <one vocabulary value>
reason: <one short sentence>
next_skills: <exact skill document paths, policy anchor, or none>
review_mvp_required: <true or false>
minimum_validation_profile: <short profile name>
```

Use `next_skills: none` only for `review_not_required`. Use
`next_skills: docs/context/CODEX_REVIEW_GATE_POLICY.md#light-policy-check` for
`light_policy_check_only`. For `full_review_required`, list the exact next
skill paths in the order they should be called. Do not write a vague value such
as `all reviewers` or `specialist review`.

## Dispatch Rules

Return `review_not_required` when the task is docs/context-only, does not touch
score, ranking, report, backtest, valuation, generated-output boundary, schema,
guardrail, or user-facing claim semantics, and focused checks are clean.

Return `light_policy_check_only` when the change is a policy, routing, context,
or README update that references guardrails but does not alter domain logic,
schemas, defaults, outputs, or reviewer decisions.

Return `technical_review_required` when changed files or text touch technical
score definitions, technical score candidates, normalization, diagnostics,
technical usefulness claims, redundancy, stability, regime fit, or possible
misuse of technical outputs as ranking, composite, backtest, advice, or alpha.
Next skill: `.agents/skills/technical_review/SKILL.md`.

Return `valuation_review_required` when changed files or text touch valuation,
fundamental, PER, PBR, ROE, quality, profitability, accounting, revision,
point-in-time financial data, filing/availability dates, valuation claims, or
cheap/undervalued language. Next skill:
`.agents/skills/valuation_review/SKILL.md`.

Return `adoption_review_required` when changed files or text touch score
adoption, downgrade, reject/defer decisions, composite membership, weight
selection, ranking semantics, or score-to-production handoff. Next skill:
`.agents/skills/technical_review/SKILL.md`.

Return `full_review_required` when more than one specialized review is triggered,
when validation fails in a way that may indicate schema mismatch or guardrail
breach, when user explicitly requests full review, or when forbidden investment
claim wording appears in changed docs or generated reports. The `next_skills`
field must name the exact relevant path or paths, usually
`.agents/skills/technical_review/SKILL.md`,
`.agents/skills/valuation_review/SKILL.md`, or both. Add
`.agents/skills/review_mvp_specialist/SKILL.md` only when code, schema,
generated-output boundary, or integration-risk review is required by root
policy.

## Non-Review Limits

The gate must not:

- decide whether a score is useful, adopted, deferred, or rejected
- evaluate valuation support or point-in-time safety beyond routing
- inspect performance tables to judge alpha
- change formulas, weights, thresholds, ranking, reports, or backtests
- expand the KOSPI200-only technical MVP baseline
- activate valuation or fundamental scoring
- turn risky wording into corrected investment claims

If the gate needs more than a compact path-and-summary check, it should stop and
route to the relevant skill instead of extending its own analysis.
