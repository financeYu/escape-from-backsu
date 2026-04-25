# Master-up Template

Use this template when a subproject asks master for integration review.

Master-up summary must prioritize:

1. what was validated
2. what remains risky
3. what changed
4. what was intentionally not changed
5. which files are owned by this change and which dirty files are unrelated
6. whether watchdog audit was required and the final watchdog verdict
7. whether Cross-Step Conflict Checkpoint was required and the final verdict
8. whether Root-Agent Conflict Stop was triggered and the resume decision
9. whether `review_mvp` is requested or not
10. whether the change is ready for the Step-end code review / fix / commit gate

```text
[Subproject]
- name:
- responsible scope:

[Change summary]
- changed files:
- purpose:
- local owner:

[Git isolation]
- owned change files:
- unrelated dirty files:
- generated outputs excluded:
- mixed-change files requiring hunk-level staging:

[Root-Agent Conflict Stop]
- triggered / not triggered:
- stop trigger:
- conflicting root area or protected work:
- report location or summary:
- resume decision:
- unresolved risk:

[Local review completed]
- worker scope declaration:
- watchdog audit required:
- watchdog verdict:
- watchdog unresolved warnings:
- scope compliance:
- local tests/checks:
- generated-output/cache boundary:
- config-first compliance:
- hard stop check:

[Evidence]
- commands run:
- outputs checked:
- docs updated:

[What did not change]
- No score implementation unless current roadmap step allows it
- No backtest unless current roadmap step allows it
- No valuation/fundamental scoring unless current roadmap step allows it
- No financial data merge into technical_composite_score
- No financial data merge into final_composite_score

[Remaining risks]
- unresolved:
- unknown:
- inference:

[Scope watchdog audit]
- required / optional / not needed:
- verdict: PASS / WARNING / BLOCKING_ISSUE / NEEDS_CLARIFICATION / not run
- reason:
- blocking findings:
- warnings carried to master:

[Cross-Step Conflict Checkpoint]
- required / optional / not needed:
- trigger:
- review packet:
- verdict: PASS / WARNING / BLOCKING_ISSUE / NEEDS_CLARIFICATION / not run
- roadmap/order:
- hard stops:
- score/composite boundary:
- valuation boundary:
- diagnostics boundary:
- handoff consistency:
- generated-output boundary:
- dirty worktree isolation:
- warnings carried to master:
- blocking findings:

[review_mvp request]
- required / optional / not needed
- reason:

[Step-end gate readiness]
- integration validation evidence ready:
- cross-step conflict checkpoint ready:
- code review owner:
- expected fix owner:
- validation rerun plan:
- commit scope:

[Master decision requested]
- ACCEPT / HOLD / REJECT
```
