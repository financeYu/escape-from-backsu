# Master-up Template

Use this template when a subproject asks master for integration review.

Master-up summary must prioritize:

1. what was validated
2. what remains risky
3. what changed
4. what was intentionally not changed
5. which files are owned by this change and which dirty files are unrelated
6. whether `review_mvp` is requested or not

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

[Local review completed]
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

[review_mvp request]
- required / optional / not needed
- reason:

[Master decision requested]
- ACCEPT / HOLD / REJECT
```
