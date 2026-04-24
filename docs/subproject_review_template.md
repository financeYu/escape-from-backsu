# Subproject Review Template

Use this checklist before sending a change to master-up.

The responsible subproject performs first-pass review for its own changes. It should not delegate ordinary local correctness review to master by default.

## Local First Checklist

- local scope compliance
- local tests or validation commands
- local generated-output/cache boundary
- local `AGENTS.md` compliance
- config-first compliance where behavior is configurable
- hard stop rule violations
- unresolved risks
- whether `review_mvp` is required, optional, or not needed
- owned change files are separated from unrelated dirty files
- mixed-change files are marked for hunk-level staging before commit

## Evidence Expectations

Record the commands, outputs, docs, and files checked. If a command was not run, state why.

For generated outputs, confirm whether they were intentionally excluded from source control or promoted to a small fixture with an explanation.

## Required Master-up Summary

Submit the final handoff with `docs/master_up_template.md`.
