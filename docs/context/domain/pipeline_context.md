# Pipeline / Automation Context

Purpose: preserve Step 19 pipeline boundaries for later review without reloading
completed implementation history.

Current status:

- Step 19 is complete in the roadmap status.
- Step 20 is complete; no roadmap Step is currently active.
- Pipeline context is review or regression context, not a request to redesign the pipeline.

Use when:

- a Step 20 validation question touches Step 19 orchestration evidence
- a regression or conflict is reported against pipeline guardrails
- a generated-output or no-network/no-secret pipeline boundary needs review

Forbidden without a separately approved post-MVP Step:

- scheduler, CI, runtime automation, or pipeline behavior changes
- new market data sources
- KOSDAQ150, futures, or options expansion
- scoring, ranking, backtest, valuation scoring, or report semantic changes
- reopening Step 20 or inventing new Step 20 final-validation evidence
