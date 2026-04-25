# review_mvp Policy

## review_mvp specialist review role

`review_mvp` is a specialist review project, not the default mandatory review bottleneck.

`review_mvp` is invoked only for:

- high-risk changes
- cross-project changes
- changes affecting schema, validation severity, score definitions, normalization, ranking, composite logic, or backtest design
- changes near Step-end gate decisions
- changes with unresolved risks after subproject local review
- master-requested independent review

For Step-end closure, `review_mvp` is required when the Step change touches code, tests, config, schemas, generated-output boundaries, cross-project handoffs, or roadmap-gated behavior. Narrow docs-only governance changes may use master code review unless the master or user explicitly requests specialist review.

`review_mvp` must focus on:

- hard stop violations
- roadmap/order violations
- lookahead/future-data risk
- config-first violations
- generated-output/source-control boundary
- score redefinition risk
- technical/fundamental boundary violations
- diagnostics being treated as alpha signals
- handoff quality and evidence quality

`review_mvp` must not:

- become the default reviewer for every small local change
- rewrite local implementation unless explicitly asked
- invent new scores
- implement scores before allowed roadmap step
- run or design backtests before allowed roadmap step
- introduce valuation/fundamental scoring before allowed roadmap step

## Review length policy

Default review output is findings-first and compact.

- Report only concrete findings, missing evidence, and required follow-up.
- Do not restate passed checklist items unless the user requests a full gate record.
- Keep normal reviews to at most 5 findings, ordered by blocking risk.
- Keep each finding to path, line when available, impact, and required fix.
- Use `No blocking findings` when the review has no required fixes.
- Move broad background, repeated policy text, and completed-step history out of the response.

Use the full checklist format only for Step-end, explicit specialist review, or a user-requested full gate record. Even in full format, passed items should use `PASS` plus a short reason instead of long explanations.

## Review modes

Use the narrowest mode that satisfies the request:

| Mode | When to use | Output cap |
| --- | --- | --- |
| `quick` | narrow local change, no review_mvp trigger | up to 3 findings |
| `normal` | ordinary master or subproject review | up to 5 findings |
| `step-end` | Step closure or required Cross-Step Conflict Checkpoint | full gate summary, passed items short |
| `specialist` | explicit `review_mvp` trigger or unresolved high-risk issue | focused full review of triggered risks |

## review_mvp output format

Default compact format:

```text
[Review]
- mode: quick / normal / step-end / specialist
- scope:
- verdict: ACCEPT / HOLD / REJECT

[Findings]
- blocking:
- warnings:
- missing evidence:

[Required follow-up]
- ...
```

Full gate format:

```text
[review_mvp 판정 대상]
- source subproject:
- master request reason:
- changed files:

[전문 리뷰 초점]
- high-risk area:
- cross-project impact:
- roadmap gate impact:

[Hard Stop 점검]
- score implementation:
- Research Tester score implementation:
- backtest:
- valuation/fundamental scoring:
- financial data into technical_composite_score:
- financial data into final_composite_score:
- lookahead/future data:
- diagnostics as alpha signal:

[Evidence 검토]
- provided evidence:
- missing evidence:
- reproducibility:

[리스크]
- blocking:
- non-blocking:
- unknown:

[판정]
ACCEPT / HOLD / REJECT

[Master에 전달할 요약]
- ...
```
