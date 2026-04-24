# Master Project Registry

## Purpose

This registry defines the projects managed by the master agent, why each exists, and where responsibility begins and ends.

The goal is not to create more bureaucracy. The goal is to keep research, quant design, valuation review, and executable scanner work from stepping on each other as the repository moves to Git-based collaboration.

---

## Project map

| ID | Project | Path | Primary responsibility | Reason |
| --- | --- | --- | --- | --- |
| P0 | Master Governance | `.` | Repository policy, Git hygiene, project routing, cross-project handoffs | Keeps the workspace coherent and prevents every subproject from inventing its own process |
| P1 | Research Evidence | `reserch_mvp`, `Quant_mvp/agents/research` | Source policy, paper metadata, discovery imports, EvidenceCards | Prevents paper claims from becoming adopted scores without review |
| P2 | Quant Score Governance | `Quant_mvp` | Score taxonomy, technical review, config-first scoring policy | Ensures formulas, windows, thresholds, and adoption decisions are explicit before implementation |
| P3 | Scanner Runtime | `chart_mvp` | KOSPI200 data fetching, caching, indicators, ranking output, charts, CLI/GUI | Keeps runnable code and generated runtime artifacts separate from research/design documents |
| P4 | Valuation Review | `Quant_mvp/agents/valuation` | Point-in-time fundamental availability and valuation verdicts | Prevents price-only signals from being mislabeled as valuation evidence |
| P5 | Ops and Reproducibility | root plus affected project | Ignore rules, dependency setup, CI, data/output path policy | Makes the repo cloneable, testable, and reviewable on machines other than the original local PC |
| P6 | Code Review and Final Validation | `review_mvp`, root workspace | Code-level review, minimal safe repair guidance, final conflict/error checks | Gives the master agent one consistent checkpoint for correctness, security, reliability, and cross-project integration risk |

---

## Handoff rules

Research to quant:

- Input: paper metadata, abstracts, local discovery seeds, EvidenceCards
- Owner: `reserch_mvp` and `Quant_mvp/agents/research`
- Output: candidate cards routed to `technical_score_architect`, `valuation_agent_handoff`, `hybrid_split_required`, `diagnostic_backlog`, or `reject_log`

Quant to scanner:

- Input: adopted or provisional technical score definitions
- Owner: `Quant_mvp`
- Output: implementation-ready score specs, config changes, tests expected

Scanner to master:

- Input: implementation change, tests, runtime behavior notes
- Owner: `chart_mvp`
- Output: code diff, test result, and any generated artifacts kept out of Git unless promoted to fixtures

Valuation handoff:

- Input: valuation or fundamental candidate
- Owner: `Quant_mvp/agents/valuation`
- Output: `valuation_status`, `valuation_verdict`, point-in-time caveats, and blocked/rejected reasons

Code-review handoff:

- Input: changed files, implementation notes, failing tests, or suspected bug
- Owner: `review_mvp`
- Output: findings ordered by severity, minimal fix guidance, false-positive notes, and final validation status

Final master checkpoint:

- Input: project-specific test results and review findings
- Owner: root master agent
- Output: concise summary of remaining errors, conflicts, blocked checks, and recommended next actions

---

## Boundary decisions

1. `reserch_mvp` keeps its current misspelled directory name until a dedicated rename migration is requested.
2. `chart_mvp/data` and `chart_mvp/outputs` are runtime artifacts, not source-controlled project state.
3. Research ingestion does not adopt scores.
4. Quant score review does not fetch live chart data.
5. Chart runtime does not decide valuation status.
6. The master agent coordinates ownership but does not overrule specialized agent boundaries.
7. `review_mvp` handles code-level review, not quant score adoption or valuation verdicts.

---

## Recommended Git workflow

Use small changes grouped by responsibility:

- `master`: root docs, ignore rules, CI, project routing
- `research`: research-ingestion specs and EvidenceCard schema work
- `quant`: score definitions, config, review docs
- `chart`: runnable scanner code and tests
- `valuation`: point-in-time fundamental review docs and rules
- `review`: review tooling, final validation checks, minimal bug-fix guidance

Each change should answer:

- Which project owns this?
- Which downstream project consumes it?
- Are generated outputs excluded from Git?
- What verification was run?
