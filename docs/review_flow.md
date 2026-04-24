# Review Flow

## Default flow

```text
subproject local change
-> subproject local first review
-> master-up summary
-> master integration review
-> optional review_mvp specialist review
-> final master decision
```

## Non-default flow

`review_mvp` can be called before master only when:

- the subproject already knows the change is high-risk
- the change crosses subproject boundaries
- the change touches roadmap-gated areas
- the subproject cannot resolve a risk locally

## Required master-up summary

Use `docs/master_up_template.md`.

The summary must make clear:

1. what was validated
2. what remains risky
3. what changed
4. what was intentionally not changed
5. which files are owned by this change and which dirty files are unrelated
6. whether `review_mvp` is requested or not

## Decision meanings

ACCEPT:

- local review complete
- evidence sufficient
- no hard stop violation
- no unresolved cross-project risk

HOLD:

- direction is acceptable but evidence, handoff, docs, or local check is incomplete

REJECT:

- hard stop violation
- roadmap/order violation
- unresolved high-risk issue
- missing or misleading evidence
