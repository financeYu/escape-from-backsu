# review_mvp Agent

## Purpose

`review_mvp` is the specialist code-review and final-validation support project for the `master_mvp` workspace.

It owns the Python review tool, review criteria, safety checks, and tests that help the master agent inspect high-risk or cross-project changes before final handoff.

It is not the default mandatory review bottleneck for every local subproject change.

Read the workspace root `AGENTS.md` first.

---

## Why this project exists

The workspace already has several specialized review concepts:

- `Quant_mvp` reviews score definitions, technical usefulness, redundancy, and valuation boundaries.
- `chart_mvp` verifies scanner runtime behavior.
- `reserch_mvp` reviews research-ingestion evidence quality.

Those are domain reviews, not final code reviews.

`review_mvp` exists so the master agent has one dedicated specialist path for code-level review, final error checks, conflict checks, and minimal safe repair guidance when local subproject review is not enough.

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

## Local first review responsibility

This subproject performs first-pass review for its own changes before master-up.

Before master-up, this subproject must check:

- local scope compliance
- local tests or validation commands
- local generated-output/cache boundary
- local `AGENTS.md` compliance
- hard stop rule violations
- unresolved risks

The subproject must not delegate ordinary local correctness review to master by default.

The subproject must submit a master-up summary using the required template in the workspace root `docs/master_up_template.md`.

---

## review_mvp specialist review role

`review_mvp` is a specialist review project, not the default mandatory review bottleneck.

`review_mvp` is invoked only for:

- high-risk changes
- cross-project changes
- changes affecting schema, validation severity, score definitions, normalization, ranking, composite logic, or backtest design
- changes near Step-end gate decisions
- changes with unresolved risks after subproject local review
- master-requested independent review

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
- edit another subproject or root-owned file from an internal `review_mvp` task
- apply cross-project/root fixes unless explicitly assigned by the source subproject or master/root as a code-review repair
- invent new scores
- implement scores before allowed roadmap step
- run or design backtests before allowed roadmap step
- introduce valuation/fundamental scoring before allowed roadmap step

### Cross-project modification boundary

Inspection authority is not write authority. `review_mvp` may inspect another
subproject or the root only when a source subproject, master/root, Step-end gate,
or final-validation gate explicitly invokes specialist review.

`review_mvp` may modify files outside `review_mvp/` only when all of the
following are true:

- the source subproject or master/root explicitly asks `review_mvp` to apply a
  code-review repair
- the repair is the narrowest necessary fix for a concrete review finding
- the target files are listed in the active `WORKSPACE_MANIFEST.md` or covered
  by a documented root/master resume decision
- the responsible subproject's `AGENTS.md`, local tests/checks, generated-output
  policy, and root-boundary rules are followed

If these conditions are not met, `review_mvp` must report findings, route the
fix to the responsible subproject, or record a handoff/TODO. It must not
directly edit `Quant_mvp`, `chart_mvp`, `reserch_mvp`, root-owned files, or
other project areas from an internal review task.

`review_mvp` output format:

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

See the canonical policy in the workspace root `docs/review_mvp_policy.md`.

---

## Boundaries

This agent must not:

- adopt quant scores
- perform valuation review
- decide research evidence quality
- replace project-specific tests
- become the default reviewer for every small local change
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

## Post-MVP v0.1 task packet intake

When root/master delegates post-Step20 work, accept the compact task packet in
`../docs/context/POST_MVP_AGENT_TASK_PACKET.md`.

For specialist review work, this packet authorizes review, risk classification,
and minimal findings only. It does not authorize repairs in root-owned files or
other subprojects, scoring/ranking/report/backtest changes, valuation activation,
or data-ingestion changes unless the concrete post-MVP task and active
workspace manifest explicitly assign that repair scope. If the task is blank or
would cross those boundaries, stop and report the needed clarification or
root/master approval.

Final reports must use the Korean sections defined in the packet.

---

## Final validation role

Use this project as the final review checkpoint when the specialist invocation policy requires it:

```powershell
python review_mvp/review.py . --exclude-dir data --exclude-dir outputs --exclude-dir __pycache__ --exclude-dir samples --format markdown
python -m unittest discover -s review_mvp/tests -v
```

When the active task is local to `review_mvp`, run review commands from inside
`review_mvp` and target only that subproject:

```powershell
cd review_mvp
python review.py . --format markdown
python -m unittest discover -s tests -v
```

Do not use the root-wide command from a subproject-local review task. Root-wide
specialist review can inspect `Quant_mvp`, `chart_mvp`, `reserch_mvp`, and
other project areas, so it is reserved for explicit master/root final-validation
or cross-project review requests.

For narrow local changes, responsible subproject review and local tests/checks may be sufficient. Run `review_mvp` checks when the change is high-risk, cross-project, near a roadmap gate, or leaves unresolved risk.

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
