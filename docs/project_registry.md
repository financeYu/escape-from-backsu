# Master Project Registry

## Purpose

This registry defines the projects managed by the master agent, why each exists, and where responsibility begins and ends.

The goal is not to create more bureaucracy. The goal is to keep research,
quant design, valuation review, and executable scanner work from stepping on
each other as the repository moves to Git-based collaboration.

Post-MVP operating model: `Quant_mvp` is the product umbrella for the
KOSPI200 technical quant system. Research ingestion now lives inside
`Quant_mvp/research_mvp`, while `chart_mvp` remains a separate downstream
scanner/runtime subproject.

---

## Project map

| ID | Project | Path | Primary responsibility | Reason |
| --- | --- | --- | --- | --- |
| P0 | Master Governance | `.` | Repository policy, Git hygiene, project routing, cross-project handoffs | Keeps the workspace coherent and prevents every subproject from inventing its own process |
| P1 | Research Evidence | `Quant_mvp/research_mvp` | Upstream research/evidence lane for the Quant product umbrella: source policy, paper metadata, discovery imports, metadata adapters, EvidenceCards, source-health reports | Prevents paper claims from becoming adopted scores while giving Quant an explicit intake stream |
| P2 | Quant Score Governance | `Quant_mvp` | Quant product umbrella, score taxonomy, technical review, research intake contract, config-first scoring policy, and handoff coordination | Ensures formulas, windows, thresholds, and adoption decisions are explicit before implementation |
| P3 | Scanner Runtime | `chart_mvp` | Downstream scanner/runtime lane for the Quant product umbrella: KOSPI200 data fetching, caching, indicators, ranking output, charts, CLI/GUI | Keeps runnable code and generated runtime artifacts separate from research/design documents while implementing only reviewed Quant specs |
| P4 | Valuation Review | `.agents/skills/valuation_review` | Point-in-time fundamental availability and valuation verdicts | Prevents price-only signals from being mislabeled as valuation evidence |
| P5 | Ops and Reproducibility | root plus affected project | Ignore rules, dependency setup, CI, data/output path policy | Makes the repo cloneable, testable, and reviewable on machines other than the original local PC |
| P6 | Specialist Review and Final Validation | `review_mvp`, root workspace | High-risk code review, minimal safe repair guidance, final conflict/error checks | Gives the master agent a specialist checkpoint for correctness, security, reliability, and cross-project integration risk without making every local change wait on `review_mvp` |
| P7 | Scope Compliance Audit | `Quant_mvp/AGENTS.md` process + `.agents/skills/quant-subproject-audit-gate` | Instruction compliance, roadmap-order checks, worker scope containment, terminology and evidence-strength audit | Lets a strict watchdog stop scope creep before worker changes are treated as normal project progress |
| P8 | Backtest MVP | `Quant_mvp/backtest_mvp` | Evaluation-only conservative backtest contracts, config, runner, and generated-output boundary | Keeps realized-return evaluation subordinate to Quant governance and prevents backtest feedback from becoming score or ranking input |

---

## Handoff rules

Research to quant:

- Input: paper metadata, abstracts, local discovery seeds, EvidenceCards
- Owner: `Quant_mvp/research_mvp`
- Quant consumer contract: `Quant_mvp/config/research_intake.toml`
- Output: candidate cards routed to `technical_score_architect`, `valuation_agent_handoff`, `hybrid_split_required`, `diagnostic_backlog`, or `reject_log`
- Boundary: `Quant_mvp/research_mvp/AGENTS.md` is the canonical
  source-policy owner.
- Umbrella rule: Research is an upstream lane under the Quant product line, but
  it does not define scores, adopt scores, run backtests, or issue valuation
  verdicts.

Quant to scanner:

- Input: adopted or provisional technical score definitions
- Owner: `Quant_mvp`
- Output: implementation-ready score specs, config changes, tests expected
- Contract: scanner work starts from an explicit Quant-owned spec or user/root
  assignment; EvidenceCards alone are not implementation authorization.

Scanner to master:

- Input: implementation change, tests, runtime behavior notes
- Owner: `chart_mvp`
- Output: code diff, test result, and any generated artifacts kept out of Git unless promoted to fixtures
- Umbrella rule: Scanner runtime is a downstream lane under the Quant product
  line, but chart caches, generated reports, images, and local data remain
  runtime artifacts, not Quant source-controlled state.

Subproject to master:

- Input: project-local change after local first review
- Owner: responsible subproject
- Output: master-up summary using `docs/master_up_template.md`, local evidence, unresolved risk summary, and `review_mvp` request status

Root-agent conflict stop:

- Input: detected overlap with root-owned policy, root/master active work, protected concurrent work, or dirty files that cannot be separated
- Owner: responsible worker stops and reports; root/master decides resume ownership
- Output: `NEEDS_ROOT_DECISION` report using `docs/root_agent_conflict_process.md`, followed by a documented resume decision before further edits
- Invocation: required before continuing when a stop trigger is found

Worker to scope watchdog:

- Input: worker scope declaration, active roadmap Step, intended files, changed files, evidence, generated-output status, and unresolved risks
- Owner: `.agents/skills/quant-subproject-audit-gate/SKILL.md` for audit verdict; `Quant_mvp/AGENTS.md` for the Quant-side trigger process; responsible worker for fixes or clarifications
- Output: `PASS`, `WARNING`, `BLOCKING_ISSUE`, or `NEEDS_CLARIFICATION`
- Invocation: required by `docs/scope_audit_process.md` when a worker touches roadmap-gated behavior, score/normalization/diagnostic/selection/composite/ranking/backtest/valuation semantics, schema/config/generated-output boundaries, cross-project handoffs, or root-boundary requests

Valuation handoff:

- Input: valuation or fundamental candidate
- Owner: `.agents/skills/valuation_review/SKILL.md`
- Output: `valuation_status`, `valuation_verdict`, point-in-time caveats, and blocked/rejected reasons

Backtest MVP handoff:

- Input: frozen technical ranking snapshots and OHLCV price inputs
- Owner: `Quant_mvp/backtest_mvp`
- Output: evaluation-only result objects and generated artifacts under `reports/backtest/generated/`
- Boundary: realized returns and backtest metrics must not feed upstream score, adoption, ranking, report, valuation, or data-ingestion behavior

Code-review handoff:

- Input: changed files, implementation notes, failing tests, suspected bug, high-risk change, cross-project change, or unresolved local risk
- Owner: `review_mvp`
- Output: findings ordered by severity, minimal fix guidance, false-positive notes, and final validation status
- Invocation: optional specialist path, not the default bottleneck for every local change

Final master checkpoint:

- Input: master-up summary, project-specific test results, and any required specialist review findings
- Owner: root master agent
- Output: concise summary of cross-project consistency, Cross-Step Conflict Checkpoint status, roadmap/order status, Git hygiene, generated-output boundaries, unresolved risks, and recommended next actions

Cross-step conflict checkpoint:

- Input: compact review packet from `scripts/build_review_packet.py`, current diff or changed-file manifest, active roadmap status, master-up summary, and relevant handoff documents
- Owner: root master agent; affected subproject supplies local evidence
- Output: `PASS`, `WARNING`, `BLOCKING_ISSUE`, or `NEEDS_CLARIFICATION` for roadmap/order, hard stops, score/composite boundary, valuation boundary, diagnostics boundary, handoff consistency, generated-output boundary, and dirty worktree isolation
- Invocation: required when an important in-Step stage ends and before Step-end code review

---

## Boundary decisions

1. `Quant_mvp/research_mvp` is the canonical research-ingestion location.
2. `chart_mvp/data` and `chart_mvp/outputs` are runtime artifacts, not source-controlled project state.
3. Research ingestion does not adopt scores.
4. Quant owns research ingestion through `Quant_mvp/research_mvp`; the
   score-governance lane consumes research via `research_intake.toml`.
5. Quant score review does not fetch live chart data.
6. Chart runtime does not decide valuation status.
7. The master agent coordinates ownership but does not overrule specialized agent boundaries.
8. `review_mvp` handles specialist code-level review, not ordinary local first review, quant score adoption, or valuation verdicts.
9. `Quant_mvp/backtest_mvp` is the canonical backtest owner; `src.backtest` is a legacy compatibility facade.
9. `chart_mvp` remains physically separate from `Quant_mvp`; scanner runtime
   migration still requires a dedicated post-MVP migration step, path/import
   review, and conflict checkpoint.
10. `docs/contracts/quant_umbrella_handoff_contract.md` records the compact
    handoff contract for the research -> Quant -> chart flow.

---

## Recommended Git workflow

Use small changes grouped by responsibility:

- `master`: root docs, ignore rules, CI, project routing
- `research`: research-ingestion specs and EvidenceCard schema work
- `quant`: score definitions, config, review docs
- `chart`: runnable scanner code and tests
- `valuation`: point-in-time fundamental review docs and rules
- `review`: specialist review tooling, optional final validation checks, minimal bug-fix guidance

Each change should answer:

- Which project owns this?
- Which downstream project consumes it?
- Are generated outputs excluded from Git?
- What verification was run?
- Was a complete master-up summary supplied?
- Was Root-Agent Conflict Stop triggered, and if so what resume decision was recorded?
- Was watchdog audit required, and if so what was the verdict?
- Are unrelated dirty files separated from the owned change set?
- Is `review_mvp` required, optional, or not needed?
