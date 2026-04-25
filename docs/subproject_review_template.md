# Subproject Review Template

Use this checklist before sending a change to master-up.

The responsible subproject performs first-pass review for its own changes. It should not delegate ordinary local correctness review to master by default.

## Local First Checklist

- worker scope declaration recorded
- root-agent conflict stop trigger decision recorded
- root-agent conflict stop report and resume decision recorded when triggered
- watchdog audit trigger decision recorded
- watchdog audit verdict and unresolved warnings recorded when required
- local scope compliance
- local tests or validation commands
- local generated-output/cache boundary
- local `AGENTS.md` compliance
- config-first compliance where behavior is configurable
- hard stop rule violations
- Cross-Step Conflict Checkpoint trigger decision and verdict when an important in-Step stage ended
- unresolved risks
- whether `review_mvp` is required, optional, or not needed
- Step-end code review / fix / validation rerun / commit readiness
- owned change files are separated from unrelated dirty files
- mixed-change files are marked for hunk-level staging before commit

## Evidence Expectations

Record the commands, outputs, docs, and files checked. If a command was not run, state why.

For generated outputs, confirm whether they were intentionally excluded from source control or promoted to a small fixture with an explanation.

For watchdog-triggered changes, include the watchdog audit request package and final verdict from `Quant_mvp/agents/audit/AGENTS.md`.

If watchdog audit is marked not needed, state why the change did not touch any required trigger in `docs/scope_audit_process.md`.

If root-agent conflict stop is triggered, stop work and report with `docs/root_agent_conflict_process.md` before any further edits, staging, commit, cleanup, reset, or broad repair action.

When an important in-Step stage ends, include the Cross-Step Conflict Checkpoint from `docs/cross_step_conflict_check.md`. Generate `docs/current_review_packet.md` with `scripts/build_review_packet.py` and attach the packet path in the master-up summary.

## Required Master-up Summary

Submit the final handoff with `docs/master_up_template.md`.
