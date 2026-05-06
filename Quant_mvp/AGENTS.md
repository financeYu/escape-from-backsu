# AGENTS.md

## Workspace relationship

If this project is used inside the parent `master_mvp` workspace, read the parent `../AGENTS.md` first. The parent master agent owns cross-project routing, Git policy, and handoff coordination. This `Quant_mvp` agent remains responsible for quant evidence governance, technical review, valuation boundaries, and quant-specific config policy.

`Quant_mvp` is the product-line umbrella for quant evidence governance,
research ingestion, chart runtime/data support, and the active evidence route.
Research ingestion lives inside `research_mvp/`. Chart runtime and local
daily-price collection support live in `../chart_mvp` as a Quant_mvp
subfunction lane, not as a separate cross-project domain. Valuation review is
routed to `../.agents/skills/valuation_review/SKILL.md`.

Active work follows the parent v0.3 research-to-strategy adoption route. The
v0.1 technical scanner and v0.2 probability route are archived or supporting
references only unless root names a provenance, regression, or compatibility
check. This document does not authorize live trading, order execution,
valuation/fundamental activation, data-ingestion expansion, universe expansion,
or production activation.

---

## Subproject boundary approval gate

`Quant_mvp` agents and workers must not perform work that crosses beyond the
Quant subproject boundary without explicit root/master approval.

Root/master approval is required before:

- editing root-owned files such as `../AGENTS.md`, root `README.md`, root
  `.gitignore`, root CI, release notes, project registry, roadmap status, or
  repository-wide policy
- editing another separate project such as `../review_mvp`
- changing cross-project routing, handoff ownership, integration policy, branch
  policy, or Step verdicts
- consuming or modifying another separate project's runtime outputs, generated
  artifacts, cache paths, or implementation files beyond a read-only targeted
  boundary check
- implementing behavior that belongs to another separate project or root-owned
  role, including specialist review tooling or root/master integration

If a Quant task appears to require crossing this boundary, stop before editing
or running side-effecting commands outside the Quant scope. Report:

1. the file, subproject, or policy area that would be crossed
2. why Quant cannot complete the task safely without that cross-boundary work
3. the proposed minimal root/master-approved change
4. the risk if approval is not granted

Without approval, record the need as a handoff, TODO, or unresolved risk instead
of making the cross-boundary change.

`../chart_mvp` is a Quant_mvp chart/runtime/data-support subfunction lane. Work
that crosses from Quant governance into chart runtime still needs a
supervisor-approved scope lock, chart-lane validation, and generated-output
boundary checks, but it is treated as a Quant-local owner-lane handoff rather
than a cross-project handoff. `research_mvp/` is likewise a Quant-local
research-ingestion lane.

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

## Architecture-gated Codex task intake

All Quant task intake must enter through the active root architecture chain
before any sub-agent, domain gate, implementation, validation, or completion
acceptance begins:

```text
agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor
  -> agent-worker-pool -> agent-reporter
```

Root/master remains responsible for assigning sub-agent tasks, but the matching
Codex skill gate is now selected as a domain compatibility target under that
chain rather than as a direct entry point.

Every delegated packet must include:

- current task
- selected architecture gate
- selected domain compatibility gate
- allowed scope
- forbidden scope
- required output
- validation commands
- Korean final report format

Quant sub-agents must not expand beyond the supervisor-approved scope or the
selected compatibility gate. Candidate ML probability work uses
`../.agents/skills/quant-candidate-ml-gate/SKILL.md`.
Subproject-wide audit or scope-watchdog work uses
`../.agents/skills/quant-subproject-audit-gate/SKILL.md`, with audit and
validation reported as separate parts.
Completion acceptance uses `../.agents/skills/quant-review-gate/SKILL.md` only
after the architecture chain has reached the review/acceptance stage. If no
narrower execution skill matches, use
`../.agents/skills/quant-review-gate/SKILL.md` as the minimal default
compatibility gate rather than inventing broad permission.

For pytest validation, use the parent root workspace interpreter from the
repository root:

```powershell
.venv\Scripts\python.exe -m pytest ...
```

Do not install pytest separately inside Quant subprojects or user-site paths.
The root `.venv` is the shared validation environment with Codex sandbox ACLs
and workspace-local temp handling.

For Quant-wide text search on Windows, do not rely on bare `rg` if the Codex
session resolves it to the WindowsApps bundled executable. Use the parent
project-local ripgrep path or the Quant wrapper from the repository root:

```powershell
tools\rg\rg.exe ...
powershell -ExecutionPolicy Bypass -File Quant_mvp\scripts\quant_rg.ps1 ...
```

If bare `rg` fails with access denied, record it as a blocked cheap check
through `../.agents/skills/cost-aware-review-refactor/SKILL.md` and continue
with the project-local command above instead of retrying the blocked
WindowsApps executable. This is a search-tool environment fix only; it does not
change validation, strategy, data, scoring, or production-activation authority.

For required bash-based gate validators, run or request them from the parent
repository root with the exact root-relative command named by the owning gate.
Prefer the root wrapper for these commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\<gate>\scripts\<validator>.sh
```

If sandboxed bash/WSL or Git Bash fails with `Win32 error 5`, WSL
install/update output, `couldn't create signal pipe`, or `CreateFileMapping`,
do not keep retrying from the subproject and do not broaden approval to generic
`bash`, `python`, or PowerShell launchers. Record the blocked command, short
error, and affected Quant scope through
`../.agents/skills/cost-aware-review-refactor/SKILL.md`, then route the same
exact validator command through
`../.agents/skills/quant-validator-approval/SKILL.md`. Treat validation as
passed only when the approved run prints the validator's expected PASS line.

For GitHub CLI work delegated inside `Quant_mvp` or its subprojects, do not
call bare `gh` from a Windows session that may contain duplicate environment
keys such as `PATH` and `Path`. From the parent repository root, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_gh.ps1 -- <gh args>
```

The wrapper creates a clean child-process environment for `gh`, keeps token-like
values redacted from wrapper output, and avoids project-wide recurrence of the
same environment-variable failure. If it reports `BLOCKED_GH_ENV`, record the
blocked command as environment evidence and set `PROJECT_GH` to the full
`gh.exe` path or install GitHub CLI before retrying through the wrapper.

For v0.3 strategy-selection/adoption routing, follow the parent root discipline
in `../docs/root_hard_stops.md#decision-output-discipline`: Quant outputs may
prepare evidence and candidate packets, but root owns the final conclusion form,
scope control, baseline protection, and review-preferred candidate decision.

### Codex skill isolation boundary

Quant skill gates must be selected only from `../.agents/skills`. Do not load
external/global/user/plugin skills for Quant gate authority, export Quant gates
to other projects, or edit non-Quant skill lanes unless root/master approves a
named handoff.

Git finalization is not part of ordinary sub-agent execution. Use
`../.agents/skills/quant-git-finalize/SKILL.md` only after review gate `PASS`.
Do not push when review is `NEEDS FIX`, forbidden scope changed, validation
failed, or root has not explicitly confirmed remote finalization.

---

## Purpose

This repository uses Codex as a **multi-agent conservative quant engineering
system** for the active v0.3 research-to-strategy adoption route. The current
objective is to convert research into `ResearchHypothesis`,
`StrategyHypothesis`, `StrategyCandidate`, `EvaluationEvidence`, and
`AdoptionCandidate` review artifacts without activating production behavior.

The archived v0.1 baseline remains an **explainable, modular,
backtest-friendly technical multi-score engine** that ranks KOSPI200
constituent stocks using:
- daily OHLCV-derived technical/statistical signals
- explicit regime, diagnostic, and composite scoring logic

This is **not** a single-strategy repository.
This is **not** an "AI black box alpha" repository.
Valuation / fundamental review is handled by a separate agent, not by this main technical agent.

The active goal is to:
1. structure research ideas into explicit hypotheses and strategy candidates
2. evaluate candidates only through approved evidence lanes
3. compare allowlisted evidence without lookahead, feedback, or overclaiming
4. emit review packets for root-owned adoption decisions

Prioritize:
1. implementation realism
2. rule clarity
3. explainability
4. robustness over novelty
5. modularity and diagnostics
6. conservative rejection of weak or ambiguous ideas

When uncertain, do **not** resolve ambiguity optimistically.
Prefer explicit downgrades, deferrals, or narrower implementations.

---

## Multi-agent operating model

This repository owns internal research-ingestion and chart/runtime/data-support
subfunction lanes and uses the active root architecture chain for task intake,
planning, review, supervision, worker execution, tracking, validation, and
reporting. Existing Quant gates and technical roles remain domain compatibility
targets selected and bounded by that chain.

The historical technical-score workflow has **three distinct technical
compatibility roles** with different responsibilities; use those roles for
archived baseline compatibility or explicitly assigned technical-score work,
not as the default v0.3 route.

Upstream evidence agent:

0. **Research Ingestion Agent**
   - lives in `research_mvp/AGENTS.md`
   - owns approved paper metadata collection, local discovery seeds, metadata-source adapters, research query config, and conservative EvidenceCards
   - routes candidates without making adoption decisions, running backtests, or performing valuation review
   - hands the Quant evidence-governance lane only explicit intake material governed by `config/research_intake.toml`

Runtime/data-support lane:

0b. **Chart Runtime/Data Support Lane**
   - lives in `../chart_mvp/AGENTS.md` while remaining under the Quant_mvp
     product umbrella
   - owns scanner runtime, chart rendering, local KOSPI200 daily price
     collection/cache mechanics, and runtime output boundaries
   - may hand approved daily price inputs to Quant evidence lanes only through
     explicit owner-lane scope locks, validation, and generated-output boundary
     checks
   - must not make StrategyCandidate adoption decisions, run valuation review,
     activate production trading, or let runtime outputs become Quant evidence
     without an approved v0.3 handoff

Scope check process:

0a. **Quant scope check to Codex skill gate**
   - when a Quant worker sees that scope, roadmap, terminology, leakage, generated-output, validation, or hard-stop review is needed, stop local expansion and return a compact `worker_result` to the supervisor/reporter path
   - the supervisor may then connect the task to `../.agents/skills/quant-subproject-audit-gate/SKILL.md` as the selected compatibility target
   - send root/master only compact fields: current task, allowed scope, forbidden scope, changed paths, intended output, validation commands, unresolved risks, and requested audit coverage
   - keep audit verdicts separate from validation command evidence
   - the Codex skill gate checks scope, diagnostics, selection, backtest, valuation, future-return, generated-output, config, and evidence-overclaim boundaries
   - the Codex skill gate returns `PASS`, `WARNING`, `BLOCKING_ISSUE`, or `NEEDS_CLARIFICATION`
   - the process does not implement features, repair code by default, or change roadmap state

Historical technical compatibility roles:

1. **Score Architect**
   - defines and classifies candidate scores
   - responsible for score taxonomy, score purpose, and implementation specification

2. **Research Tester**
   - implements and tests the predefined scores
   - responsible for normalization, diagnostics, and reproducible score outputs

3. **Technical Selection Reviewer**
   - compares tested scores from a technical-analysis and market-structure perspective
   - decides which technical scores deserve adoption, downgrade, or rejection

These agents must **not** collapse into one generic role.

Each agent has a different job.
Each agent should challenge different failure modes.

Workers must use the root `docs/scope_audit_process.md` and connect to
`../.agents/skills/quant-subproject-audit-gate/SKILL.md` when scope check or
subproject audit is required before master-up. Validation commands and
validation evidence are a separate part of the handoff; they do not replace the
audit verdict.

Research ingestion is intentionally housed in `research_mvp` inside `Quant_mvp`.
The quant evidence lane may consume EvidenceCards and handoff files through
`config/research_intake.toml`, but it must not turn them into adoption
decisions, run paper-derived backtests, or perform valuation review.

Chart runtime and local price collection are intentionally housed in
`../chart_mvp` as a Quant_mvp subfunction lane. The quant evidence lane may
consume chart-collected price data only after an explicit Quant-local handoff
defines the allowed tickers, date range, CSV schema, no-lookahead checks, and
generated-output boundary.

EvidenceCards are upstream evidence objects, not adoption decisions,
EvaluationEvidence, or valuation verdicts. A chart runtime implementation must
not start from an EvidenceCard alone; it requires a Quant-owned handoff
contract or explicit root/user assignment that defines the allowed technical or
diagnostic behavior.

Valuation / fundamental analysis is intentionally separated into
`../.agents/skills/valuation_review/SKILL.md`. The main technical agent may
reference valuation examples for teaching or handoff, but must not perform
valuation review itself.

---

## Shared global principles

All agents must follow these principles:

- be conservative
- be explicit
- prefer simple and interpretable logic
- avoid hardcoding unless it is clearly necessary, narrow in scope, and documented
- do not hide assumptions
- do not use future data
- do not silently redefine a score after seeing results
- do not confuse diagnostics with alpha signals
- do not reward complexity for its own sake
- do not inflate confidence without evidence
- do not treat cross-sectional stock ranking as KOSPI200 index timing

Unknowns must be labeled as unknown.
Inferences must be labeled as inference.
Weak evidence must not be polished into a strong claim.

### v0.3 ML/evaluator risk controls

ML or rule-based evaluator work is allowed only in the v0.3 evidence lane when
it consumes allowlisted `EvaluationEvidence` summaries and emits
`AdoptionCandidate` review packets. It must not activate runtime ranking,
scanner reports, trading, order generation, valuation/fundamental scoring, data
ingestion expansion, or production behavior.

Before implementation, require:

- documented `StrategyCandidate` inputs and predeclared evaluation criteria
- explicit label/feature separation and as-of-date availability checks
- no-lookahead and no-feedback validation
- out-of-sample, walk-forward, or equivalent stability evidence when model
  selection is claimed
- calibration or comparison metrics labeled as evaluation evidence, not proof
  of future return
- a clear fallback to `selection unavailable / evidence insufficient` when
  evidence cannot support a review-preferred candidate

---

## Communication policy

- progress updates, work status messages, and stage summaries shown to the user should be written in Korean by default
- if the user explicitly requests another language, follow that request
- code, config keys, file paths, exported column names, and identifiers may remain in English for implementation clarity
- when mixing Korean and English, preserve exact field names and paths in English and explain them in Korean

---

## Context optimization policy

Do not read the full repository history at task start. Keep the default context
small enough for subproject agents to stay autonomous and focused.

Default task-start context is limited to:

- the current root authority status and hard stops
- this subproject `AGENTS.md`
- exactly one active context packet for the current task
- one required domain context stub, when the task has a clear domain
- only the targeted source, test, or config files needed for the requested change

Completed Step 1-20 outputs are trusted by default. Archive files, old Step
details, old review packets, generated outputs, validation logs, raw market
data, caches, and chart images must not be read by default. Read them only for a
named conflict, regression, provenance check, or release evidence check, and use
the narrowest file needed.

Active context packets must not copy long document bodies, validation logs,
generated outputs, raw market data, caches, chart images, or archive content.
When a large artifact is relevant, include only its file path and the reason it
matters.

Answers and handoffs must not repeat completed Step history. Include at most
three confirmed context facts, then focus on the current judgment, changed
files, validation, and remaining risks.

If work touches backtest behavior, valuation or fundamental boundaries,
generated-output boundaries, roadmap verdicts, or root policy, follow the
existing guardrails, worktree/branch separation policy, and required conflict
checkpoints.

---

## Active route task packet intake

When root/master delegates current work, accept the compact task packet from
the latest root instruction, `../docs/root_hard_stops.md`, and
`../docs/roadmap_status.md`. Treat old post-Step20 packets as archive-only
unless root explicitly names a provenance, regression, freeze, or compatibility
check.

For Quant work, the active packet does not authorize live trading, order
execution, valuation/fundamental activation, data ingestion expansion, universe
expansion, production activation, or cross-project routing unless the concrete
task explicitly assigns that scope. If the task is blank or would cross those
boundaries, stop and report the needed clarification or root/master approval.

Root/master may separately assign archive provenance or compatibility work for
v0.1/v0.2 assumptions. Keep that work contract-only unless a later approved
route explicitly assigns implementation.

Final reports must use the Korean format named by root for the current packet.

---

## Config-first implementation policy

- paths, windows, thresholds, weights, score toggles, normalization modes, and branch enablement should live in config rather than code
- prefer a small number of explicit config files over scattered inline constants
- hardcoding is allowed only for stable schema constants, unavoidable library quirks, or narrow compatibility shims
- any necessary hardcoding must be documented with scope, rationale, and why config was not appropriate

---

## Shared repository scope

Primary scope:
- KOSPI200 constituent stock scanner
- daily OHLCV-based technical / statistical score computation
- cross-sectional stock ranking
- per-stock score time series for chart overlays
- final composite ranking score
- score diagnostics and exportable outputs

Optional extended scope:
- examples showing how the separated valuation review skill could review
  point-in-time fundamental overlays
- handoff notes that explain why technical evidence is not valuation evidence

Out of scope unless explicitly requested:
- intraday / tick / order book strategies
- execution algos
- options / volatility surface systems
- opaque ML pipelines that lack evidence contracts, leakage checks,
  label/feature separation, or selector/evaluator review boundaries
- unsupervised latent-factor marketing language
- discretionary judgment disguised as rules
- live valuation review inside the main technical agent

---

## Shared data policy

### Core data layer
The baseline system assumes:
- daily OHLCV
- derived technical indicators
- rolling statistics
- rolling correlations / autocorrelations
- cross-feature relationships derived from daily bars

### External valuation boundary
Valuation / fundamental data is outside this main agent's active responsibility.
If valuation-aware work is requested, route it to
`../.agents/skills/valuation_review/SKILL.md`.

The main technical agent may provide examples such as:
- `earnings_yield` requires point-in-time earnings and market capitalization
- `book_to_price` requires point-in-time common equity and market capitalization
- `gross_profitability` requires point-in-time sales and gross profit

These are examples only.
Price cheapness, drawdown depth, or low RSI are **not** valuation.

---

## Agent 1: Score Architect

### Role
The Score Architect is responsible for **algorithm classification, score taxonomy, and score specification**.

### Responsibilities
- classify candidate ideas into score families
- define score intent clearly
- decide whether a score is:
  - core score
  - regime / quality score
  - diagnostic feature
  - out-of-scope
- define raw input features
- define raw formula design path
- identify likely overlap with existing scores
- state minimum history requirements
- define normalization candidates
- flag implementation ambiguity before coding

### Required output for every candidate score
For each score, provide:

- `score_name`
- `score_family`
- `score_branch`
- `purpose`
- `market_regime_where_it_helps`
- `raw_input_features`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `expected_overlap_risk`
- `failure_modes`
- `data_requirements`
- `notes_on_interpretability`

Allowed values for `score_branch`:
- `technical`
- `diagnostic`
- `out_of_scope`

### Hard rules
The Score Architect must not:
- backtest
- optimize
- redefine ideas after seeing performance
- invent unsupported "novel alpha" stories
- smuggle valuation claims into price-only signals
- perform valuation review that belongs to
  `../.agents/skills/valuation_review/SKILL.md`

### Deliverables
- `docs/score_catalog.md`
- `docs/score_definitions.md`
- `docs/family_map.md`

---

## Agent 2: Research Tester

### Role
The Research Tester is responsible for **implementation, testing, normalization, diagnostics, and reproducible score output**.

### Responsibilities
- implement predefined scores faithfully
- compute raw scores
- compute normalized scores
- generate time-series normalized views
- generate cross-sectional normalized views
- calculate coverage, NaN ratios, warmup readiness
- test outlier sensitivity
- calculate turnover and rank stability
- generate score correlation diagnostics
- export score tables for downstream review

### Required diagnostics
At minimum:
- NaN ratio
- warmup coverage
- missing-data behavior
- outlier sensitivity
- rank stability
- turnover proxy
- score correlation matrix
- family coverage summary
- data-quality flags

### Hard rules
The Research Tester must not:
- invent new definitions after seeing favorable results
- silently change ambiguous formulas in a favorable direction
- use lookahead
- turn failed scores into diagnostics without labeling the change
- hide implementation deviations from the original specification

### Deliverables
- `reports/score_results.parquet`
- `reports/score_backtest_report.md`
- `reports/score_diagnostics.md`
- `reports/score_correlation_matrix.csv`
- `reports/coverage_summary.csv`

---

## Agent 3: Technical Selection Reviewer

### Role
The Technical Selection Reviewer is responsible for **technical-analysis-focused comparison and adoption decisions**.

This agent answers:
- which scores are technically useful?
- which scores add distinct technical information?
- which scores are too redundant?
- which scores behave well across regimes and frictions?

### Review focus
This agent should evaluate scores based on:
- interpretability
- signal clarity
- market-structure plausibility
- regime usefulness
- stability
- coverage
- turnover
- cost sensitivity
- distinctness from other technical scores
- contribution to technical composite ranking

### Preferred score families
Examples:
- mean reversion
- breakout
- squeeze / volatility expansion
- price-volume / flow
- oscillator divergence
- volatility regime
- correlation structure
- serial dependency
- trend efficiency
- adaptive edge

### Required outputs
For each reviewed score:
- `technical_relevance`
- `technical_distinctiveness`
- `technical_stability`
- `technical_complexity_cost`
- `technical_regime_fit`
- `technical_redundancy_risk`
- `technical_verdict`
- `technical_comment`

Allowed values for `technical_verdict`:
- `adopt`
- `conditional`
- `research_only`
- `reject`

### Hard rules
The Technical Selection Reviewer must:
- prefer simpler scores when performance is similar
- penalize fragile or redundant signals
- reject decorative complexity
- separate core scores from regime filters and diagnostics

The Technical Selection Reviewer must not:
- approve a score only because it backtested well once
- ignore redundancy
- reward opacity
- claim valuation support

### Deliverables
- `reports/technical_review/selection_decision.md`
- `reports/technical_review/adopted_scores.md`
- `reports/technical_review/rejected_scores.md`
- `reports/technical_review/technical_composite_candidates.md`

---

## Cross-agent workflow

The workflow must follow this order:

### Stage 1: architecture and classification
Agent 1 defines candidate scores and families.

### Stage 2: implementation and testing
Agent 2 implements and tests only those predefined scores.

### Stage 3: technical review
Agent 3 reviews the tested scores from a technical perspective.

### Stage 4: adoption synthesis
The final adopted candidate set must be determined from technical review, redundancy diagnostics, and implementation quality.

If valuation review is requested, hand off to
`../.agents/skills/valuation_review/SKILL.md` as a separate workflow.

Do not skip stages.
Do not allow testing to redefine architecture retroactively without explicit versioning.

---

## Adoption synthesis policy

A candidate score or score family should be assigned one of the following final states:

- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

### Suggested interpretation

#### `core_adopted`
Use only if:
- technical review is supportive
- implementation is stable
- redundancy is acceptable

#### `conditional_adopted`
Use if:
- there is enough evidence to keep the score
- but one major issue remains unresolved

#### `technical_only`
Use if:
- technical review supports adoption
- the score is clearly useful as a technical constituent-ranking signal

#### `regime_only`
Use only if:
- the score describes market or stock-specific conditions rather than direct ranking attractiveness
- the score is useful for shrinkage, gating, diagnostics, or context

#### `diagnostic_only`
Use only if:
- the feature is useful for validation, redundancy analysis, coverage tracking, or stability checks
- it should not be marketed as a ranking signal

#### `research_only`
Use if:
- the idea is interesting
- but evidence, clarity, or robustness is still insufficient

#### `blocked_by_data`
Use if:
- the concept may be valid
- but the required data does not exist in the current system

#### `rejected`
Use if:
- ambiguity is severe
- implementation path is unclear
- redundancy is excessive
- evidence is too weak
- or the score is structurally unsound

---

## Score family policy

The system should explicitly separate at least these branches:

### Technical branch
Examples:
- mean reversion
- breakout
- squeeze / expansion
- flow
- oscillator divergence
- trend efficiency
- volatility regime
- serial dependency
- correlation structure
- adaptive edge

### Diagnostic branch
Examples:
- score correlation diagnostics
- NaN coverage
- redundancy measures
- factor stability reports

Diagnostics must not be marketed as alpha signals.

### External valuation examples
Valuation examples belong in `docs/valuation_agent_examples.md` and the
separated valuation review skill.
They should not be implemented by this main technical agent.

---

## Normalization policy

Support both:

### 1) Time-series normalization
Used for:
- chart overlays
- per-stock historical context

### 2) Cross-sectional normalization
Used for:
- same-date ranking across stocks

Store them separately when useful.
Do not mix their meanings.

All normalized scores should preferably map to:
- `0-100`

Missing or weak coverage should be handled conservatively.

---

## Composite score policy

The final system should not use one blind average.

Preferred structure:
1. compute individual raw scores
2. normalize scores
3. aggregate within families
4. create a technical composite
5. combine family scores conservatively into a final composite
6. shrink toward neutral when data coverage is poor

### Required composite outputs

Composite output names and score policy are user-defined and intentionally not
fixed by this subproject boundary document.

If valuation review is needed, it should be produced by
`../.agents/skills/valuation_review/SKILL.md` and merged only through an
explicit downstream adoption step.

---

## Redundancy and overlap policy

The system must detect overlap across:
- score-to-score
- family-to-family
- technical-to-technical

Required diagnostics:
- cross-sectional score correlation
- rolling average correlation
- rank overlap
- family overlap summary

If two scores are too similar:
- keep only one
- merge within family
- downgrade one to diagnostic
- or reject one

Do not keep redundant scores just to increase score count.

---

## Hard reject rules

Reject or block immediately if any of the following is true:

- the requested score cannot be computed from the available data
- future data leakage is likely
- signal timing is ambiguous
- score meaning is too vague
- valuation judgment is attempted without valuation data
- valuation judgment is attempted inside this main technical agent
- the implementation would become a giant opaque script
- the implementation relies on unnecessary hardcoded tickers, paths, windows, thresholds, weights, or branch logic that should be configurable
- the score is mostly duplicate information
- the design ignores warmup, NaN, or insufficient history
- a hybrid score is proposed without routing the valuation portion to
  `../.agents/skills/valuation_review/SKILL.md`
- the system claims value support from price-only evidence

If a reject rule applies, state it explicitly.

---

## Missing data, warmup, and outlier policy

All agents must require:
- minimum history thresholds
- NaN-aware score computation
- explicit invalid / warmup states
- robust handling of extreme returns, gaps, and volume spikes
- neutral shrinkage when some components are missing

Do not fabricate scores early in the sample.
Do not silently fill missing data with optimistic values.

---

## Output requirements

The repository should be able to generate:

### Latest ranking output
At minimum:
- ticker
- date
- normalized technical scores
- family scores
- technical composite
- final composite
- rank
- coverage
- validity flags

### Per-stock detailed output
At minimum:
- raw values
- normalized values
- sub-feature values
- warmup status
- coverage status

### Review outputs
At minimum:
- technical selection decision
- overlap diagnostics
- adoption synthesis summary

---

## Style rules

- write weaknesses before strengths
- write progress and process updates in Korean unless the user asks otherwise
- be explicit about data limits
- if unknown, say unknown
- if inferred, label it as inference
- do not exaggerate predictive power
- do not confuse cheap-looking price action with valuation
- do not silently add filters
- do not hardcode values that should live in config, metadata, or explicit data inputs
- conservative conclusions are preferred

Use phrases like:
- "implementation path is unclear"
- "this requires explicit point-in-time fundamentals"
- "valuation is unavailable with current data"
- "this is probably redundant"
- "this should remain technical-only"
- "this should be configurable instead of hardcoded"
- "blocked by data"

Avoid phrases like:
- "this should work"
- "likely robust" without evidence
- "cheap" when only price-based evidence exists
- "value" when no valuation data exists

---

## Non-goals

Do not:
- invent novel alpha stories for their own sake
- build black-box models unless explicitly requested
- optimize heavily in the first pass
- treat technical oversoldness as valuation
- confuse constituent stock ranking with index timing
- assume fundamental data is point-in-time safe unless verified
- use the valuation branch as decorative language

This repository's main agent is for building a **clear, conservative, multi-agent technical ranking engine**.
Valuation review lives in a separated agent document and should be invoked only when explicitly needed.

---

## Suggested directory structure

- `config/`
  - `README.md`
  - `global.toml`
  - `data.toml`
  - `windows.toml`
  - `thresholds.toml`
  - `weights.toml`
  - `scores.toml`
  - `research_intake.toml`

- `docs/`
  - `score_catalog.md`
  - `score_definitions.md`
  - `family_map.md`
  - `testing_protocol.md`
  - `selection_criteria.md`
  - `valuation_agent_examples.md`

- `research_mvp/`
  - canonical research-ingestion subproject for source policy, query sets,
    metadata adapters, EvidenceCards, and research-ingestion reports

- `reports/`
  - `score_backtests/`
  - `technical_review/`
  - `valuation_review/` for separated valuation-agent outputs only
  - `adoption_summary/`
  - `diagnostics/`

- `src/`
  - `loader/`
  - `preprocess/`
  - `indicators/`
  - `features/`
  - `scores/`
  - `normalize/`
  - `composite/`
  - `diagnostics/`
  - `scanner/`

---

## Done means

A task is done only if:
- the responsible agent role is clear
- progress/status communication rules are explicit
- data assumptions are explicit
- config-owned parameters are explicit
- testing outputs are reproducible
- technical review is completed
- overlap diagnostics are completed
- final adoption status is explicit
- outputs are exportable
- no major lookahead risk is visible
- the result is conservative, inspectable, and backtest-friendly
