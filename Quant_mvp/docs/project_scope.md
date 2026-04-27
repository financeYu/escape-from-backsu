# Project Scope

## Purpose

This project is a technical-first, conservative quant engineering repository for a KOSPI200 constituent-level stock scanner.

The scanner is intended to rank individual KOSPI200 constituents using explainable daily OHLCV-derived technical, statistical, regime, and diagnostic scores.

The source of truth for agent behavior is `AGENTS.md`.

## Current phase

Step 1 is agent setup only.

This phase allows:
- creating custom technical agent configuration files
- documenting project scope
- documenting the agent workflow

This phase does not allow:
- score implementation
- backtests
- data loader work
- valuation reviewer activation
- valuation score implementation

## Technical-first scope

Primary scope:
- technical score architecture
- technical score testing plan
- technical diagnostics
- technical selection review
- adoption synthesis after technical review

Allowed data assumption:
- daily OHLCV
- indicators derived from daily OHLCV
- rolling statistics
- rolling correlations and autocorrelations
- cross-feature relationships derived from daily bars

## Valuation policy

Valuation and fundamental analysis are deferred until after:
- technical scanner design is complete
- technical diagnostics are complete
- technical selection review is complete
- adoption synthesis is complete

No active `.codex/agents/valuation-reviewer.toml` is required now.

Valuation review is routed through
`../.agents/skills/valuation_review/SKILL.md` when explicitly needed.

No valuation score should be implemented now.
No valuation output should be merged into `technical_composite_score` or `final_composite_score` during the technical-first phase.

## Non-goals

Do not build:
- a single opaque strategy
- an AI black-box alpha pipeline
- an index-timing-only system
- intraday, tick, order book, options, or execution systems
- valuation claims from price-only evidence

## Done criteria for Step 1

Step 1 is complete when these files exist:
- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/score-architect.toml`
- `.codex/agents/research-tester.toml`
- `.codex/agents/technical-selection-reviewer.toml`
- `docs/project_scope.md`
- `docs/agent_workflow.md`

Step 1 remains incomplete if any score implementation, backtest, data loader work, or active valuation reviewer agent is added.
