# Agent Workflow

## Source of truth

The workflow follows `AGENTS.md`.

The `.codex` files define the Step 1 custom agent setup for the technical-first phase.

## Active technical agents

Step 1 configures three active technical agents:

1. `score-architect`
2. `research-tester`
3. `technical-selection-reviewer`

No active valuation reviewer agent is created in Step 1.

## Stage 1: Score Architect

The Score Architect defines and classifies technical score candidates.

Required output before handoff:
- score name
- score family
- score branch
- purpose
- raw input features
- raw formula design
- normalization candidates
- minimum history needed
- overlap risk
- failure modes
- data requirements
- interpretability notes

The Score Architect must not implement, backtest, optimize, or create valuation claims.

## Stage 2: Research Tester

The Research Tester activates only after score definitions are explicit and approved.

Its later responsibilities include:
- faithful implementation of predefined technical scores
- raw and normalized score generation
- time-series normalization
- cross-sectional normalization
- NaN, warmup, coverage, outlier, stability, turnover, and correlation diagnostics

During Step 1, the Research Tester is configured only.
It must not implement scores, run backtests, or touch data loaders.

## Stage 3: Technical Selection Reviewer

The Technical Selection Reviewer activates only after reproducible technical score outputs and diagnostics exist.

It reviews:
- interpretability
- signal clarity
- technical distinctiveness
- regime fit
- stability
- coverage
- turnover
- cost sensitivity
- redundancy
- contribution to the technical composite

It must not claim valuation support or merge valuation outputs.

## Stage 4: Adoption Synthesis

Adoption synthesis happens only after technical review is complete.

Allowed final states:
- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

## Valuation deferral

Valuation and fundamental analysis are deferred until the technical scanner, technical diagnostics, technical selection review, and adoption synthesis are complete.

Current rules:
- do not create `.codex/agents/valuation-reviewer.toml`
- treat `agents/valuation/AGENTS.md` as an optional placeholder only
- do not implement valuation scores
- do not merge valuation output into `technical_composite_score`
- do not merge valuation output into `final_composite_score`

## Global guardrails

All active technical agents must enforce:
- conservative quant engineering
- config-first implementation
- no lookahead
- no future data
- no silent score redefinition
- no valuation claims from price-only evidence
- technical analysis first
- valuation deferred
