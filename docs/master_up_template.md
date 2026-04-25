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
11. whether the master-up preflight passed or returned a missing-evidence error
12. which risk-based operating level applies: Level 1, Level 2, or Level 3
13. which branch integration queue state applies
14. which validation layer was run: branch-focused or Step-end
15. where required review/audit fixes must be routed

Before requesting detailed master integration review, run the preflight gate:

```powershell
python scripts/check_master_up_preflight.py --summary <path-to-this-master-up-summary.md>
```

If the preflight fails, the request is `HOLD` until the missing field, missing evidence, or unresolved gate is fixed. Do not ask master to reconstruct missing evidence from the diff or local working tree during active master-up.

Use the operating levels from `docs/workspace_parallel_work_policy.md`. Level 3 master-up must keep the Scope watchdog audit and Cross-Step Conflict Checkpoint marked `required`; it may not mark `review_mvp` as `not needed`.

```text
[Subproject]
- name:
- responsible scope:
- operating level:

[Change summary]
- changed files:
- purpose:
- local owner:

[Git isolation]
- owned change files:
- unrelated dirty files:
- generated outputs excluded:
- mixed-change files requiring hunk-level staging:

[Branch integration queue]
- queue state:
- branch under review:
- previous branch gate:
- next branch blocked:

[Validation layering]
- branch integration validation:
- step-end validation:
- full validation repeated per branch:
- escalation condition:

[Required fix routing]
- required findings owner:
- fix target worktree/branch:
- master direct fixes:
- rerun scope:

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
- required / optional / not needed:
- reason:

[Step-end gate readiness]
- master-up preflight result:
- integration validation evidence ready:
- cross-step conflict checkpoint ready:
- code review owner:
- expected fix owner:
- validation rerun plan:
- commit scope:

[Master decision requested]
- ACCEPT / HOLD / REJECT
```
