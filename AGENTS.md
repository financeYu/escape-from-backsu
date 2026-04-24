# Master Project Agent

## Default Project References

Before starting any task, read `docs/project_checklist.md` and `docs/roadmap_status.md`.

Reference authority:

- `AGENTS.md` controls global behavior and safety rules.
- `docs/project_checklist.md` controls roadmap order.
- `docs/roadmap_status.md` controls current step status.
- The user's latest explicit instruction wins if there is a conflict.

At the end of every Step, report one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`

## Purpose

This workspace uses a master agent to coordinate the projects under `master_mvp`.

The master agent is responsible for repository-level direction, Git hygiene, cross-project handoffs, and project boundary control. It does not replace the more specialized agents inside each project.

Subprojects:

- `reserch_mvp`: research-ingestion specification and upstream evidence workflow
- `Quant_mvp`: quant score design, technical-review governance, valuation boundary, and config policy
- `chart_mvp`: executable KOSPI200 scanner, data cache, chart rendering, CLI, GUI, and tests
- `review_mvp`: code-review tooling, minimal repair policy, and final workspace validation

The directory name `reserch_mvp` is intentionally preserved for now to avoid breaking existing paths. Rename it only through an explicit migration.

---

## Why this master agent exists

The projects now have different responsibilities and different failure modes.

A master agent is needed because:

1. Research, quant design, valuation review, and scanner runtime should not collapse into one generic workflow.
2. Git history is easier to review when repository-level policy, subproject design, and runtime output are separated.
3. Research evidence should flow into score design before code implementation.
4. Valuation logic requires point-in-time data rules and must stay separated from price-only technical signals.
5. `chart_mvp` produces runtime caches and chart outputs that should not be confused with source-controlled project state.
6. Cross-project changes need one place to decide ownership, handoff format, and verification expectations.
7. Final code review should be separated from domain review so runtime bugs, merge conflicts, and security issues are checked consistently.

---

## Operating model

Before changing files, classify the request into one of these work types:

- `master_governance`: repository structure, Git policy, CI, project registry, release notes
- `research_ingestion`: papers, metadata sources, EvidenceCards, Google Scholar discovery imports
- `score_design`: score taxonomy, formulas, branches, config, technical review
- `scanner_runtime`: data fetching, cache behavior, indicators, chart rendering, CLI, GUI
- `valuation_review`: point-in-time fundamental review, valuation score availability, valuation verdicts
- `code_review`: correctness, security, reliability, minimal repair, changed-file review
- `final_validation`: cross-project conflict checks, generated-output checks, tests, review summaries
- `cross_project`: any change touching more than one subproject

Then route work to the narrowest responsible project.

---

## Routing table

| Request type | Primary project | Required references |
| --- | --- | --- |
| Git layout, ignore rules, CI, release process | root workspace | `AGENTS.md`, `docs/project_registry.md` |
| Research source collection or paper evidence | `reserch_mvp`, `Quant_mvp/agents/research` | `reserch_mvp/AGENTS.md`, `Quant_mvp/agents/research/AGENTS.md` |
| Technical score definition or adoption review | `Quant_mvp` | `Quant_mvp/AGENTS.md`, `Quant_mvp/config/*.toml` |
| Valuation or fundamental score review | `Quant_mvp/agents/valuation` | `Quant_mvp/agents/valuation/AGENTS.md` |
| Runnable scanner, data cache, charts, GUI | `chart_mvp` | `chart_mvp/AGENTS.md`, `chart_mvp/README.md` |
| Code review, bug-risk review, minimal repair guidance | `review_mvp` | `review_mvp/AGENTS.md`, `review_mvp/README.md` |
| Final error, conflict, and integration check | root workspace plus `review_mvp` | `AGENTS.md`, `docs/project_registry.md`, `review_mvp/AGENTS.md` |
| Data-path or output-path policy | root plus affected project | root `.gitignore`, affected project `AGENTS.md` |

When a request spans projects, write or update the handoff artifact before implementing downstream runtime behavior.

Do not confuse `Quant_mvp`'s Technical Selection Reviewer with `review_mvp`.
The former reviews technical score adoption. The latter reviews code changes and final integration risks.

---

## Cross-project handoff flow

Preferred flow:

```text
research evidence
  -> Quant_mvp score architecture / review
  -> chart_mvp implementation
  -> chart_mvp tests and runtime outputs
  -> root-level Git / release summary
```

Valuation flow:

```text
research or user request
  -> Quant_mvp/agents/valuation review
  -> explicit availability verdict
  -> optional integration plan
```

Do not skip directly from paper discovery to scanner implementation unless the user explicitly asks for a prototype and the limitation is documented.

Final validation flow:

```text
project change
  -> project-specific tests or checks
  -> review_mvp code review when practical
  -> master conflict/error summary
```

---

## Repository policy

Source-controlled by default:

- code
- tests
- docs
- config
- small reference fixtures
- project-level agent instructions

Not source-controlled by default:

- generated chart images
- daily price caches
- scan outputs
- local reports generated from current runs
- `__pycache__`
- `*.pyc`
- virtual environments
- `.env` and secrets

If a generated output is needed for review, prefer a small fixture under a test or docs fixture path with an explanation.

---

## Shared engineering rules

- Keep paths relative to the project root or configurable through environment variables.
- Do not hardcode personal machine paths.
- Prefer config changes before code changes when altering windows, weights, thresholds, paths, or score toggles.
- Preserve Korean user-facing progress and status messages unless the user asks otherwise.
- Keep code identifiers, config keys, file paths, and exported column names in English where implementation clarity benefits from it.
- Treat unknowns as unknown.
- Avoid optimistic claims about alpha, robustness, or valuation support without evidence.

---

## Master deliverables

The master project owns:

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `docs/project_registry.md`
- repository-level CI and release notes when added
- final code-review routing and integration-risk summaries

The master project should not own runtime data, score formula adoption decisions, or valuation verdicts.
It does own the final pass that checks whether changes across projects conflict, leave obvious errors, or require follow-up verification.
