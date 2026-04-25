# WORKSPACE_MANIFEST

workspace_id: step15_worker_b_validation
branch: step15-worker-b-validation
task_type: step_implementation_validation_support
active_step: Step 15 Latest Ranking Output
owner_or_worker: Worker B
created_from_commit: 8de10055e4989da603cd143f0b744114024aaeda

## Purpose

Add Step 15 verification, focused tests, and guardrail checks for latest ranking output without implementing ranking generation or modifying Worker A core implementation files.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- src/validation/
- tests/validation/
- small Step 15 test fixtures colocated with dedicated validation tests, if needed

## Read-Only Paths

- AGENTS.md
- README.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/workspace_parallel_work_policy.md
- docs/step13_technical_selection_reviewer.md
- docs/step14_adoption_synthesis.md
- docs/step11_composite_score_design.md
- src/selection/
- src/composite/
- src/scores/
- Worker A worktree and branch
- roadmap completion/status files

## Forbidden Actions

- edit Worker A core implementation files
- implement ranking generation
- implement backtesting
- implement valuation or fundamental scoring
- allow financial/fundamental data into technical_composite_score or final_composite_score
- validate with future returns, alpha performance, Sharpe, MDD, win rate, or realized outcome metrics
- expand Step 15 into Step 16 or later
- weaken existing guardrails
- mark roadmap items complete
- generate runtime latest ranking outputs

## Expected Output

- Step 15 validation/checking helpers
- dedicated Step 15 validation tests with minimal in-test fixtures
- explicit hard-stop and forbidden-column coverage
- Korean Worker B handoff summary

## Required Validation

- focused pytest for Step 15 validation assets
- compatibility pytest for existing Step 13/14 selection and Step 11/12/13/14 guardrail-adjacent tests where practical
- git status review to confirm no roadmap/status or Worker A core files were modified

## Handoff Notes

Worker B owns validation/checking assets only. Any failure caused by missing or incompatible Step 15 core implementation should be reported as Worker A integration risk rather than fixed in this branch.
