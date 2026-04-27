# Quant Umbrella Handoff Contract

## Purpose

This contract records the post-MVP logical routing model for the KOSPI200
technical quant system.

`Quant_mvp` acts as the product umbrella and owns the research-ingestion lane in
`Quant_mvp/research_mvp`. `chart_mvp` remains a separate scanner/runtime
subproject with its own local boundaries, tests, generated-output rules, and
master-up duties.

## Confirmed Baseline

- Step 20 is complete and MVP v0.1 is frozen.
- MVP v0.1 remains KOSPI200-only and technical-only.
- This contract changes governance and handoff language only. It does not
  change score formulas, ranking behavior, report behavior, backtest behavior,
  valuation status, data-ingestion behavior, or cache semantics.

## Lanes

### Research Evidence Lane

Owner: `Quant_mvp/research_mvp`

Responsibilities:

- source policy
- paper metadata normalization
- local discovery seed handling
- metadata adapters
- conservative EvidenceCard generation
- research-ingestion reports and handoff artifacts

Hard boundary:

- EvidenceCards are not score definitions.
- EvidenceCards are not adoption decisions.
- Paper-reported backtests are diagnostic metadata only.
- Research ingestion does not run repository backtests or issue valuation
  verdicts.

### Quant Governance Lane

Owner: `Quant_mvp`

Responsibilities:

- research intake contract
- score taxonomy
- score definition and adoption review
- technical review
- valuation boundary routing
- implementation-ready handoff specs for scanner/runtime work

Hard boundary:

- Quant score governance may consume EvidenceCards, but it must not treat them
  as score definitions or adoption decisions.
- Financial/fundamental data must not enter `technical_composite_score` or
  `final_composite_score`.
- Backtest output must not feed upstream scoring or ranking.

### Scanner Runtime Lane

Owner: `chart_mvp`

Responsibilities:

- KOSPI200 data fetching
- local cache behavior
- technical indicator calculation
- scanner output
- chart rendering
- CLI/GUI execution paths
- runtime tests

Hard boundary:

- Scanner runtime must not adopt new scores without an explicit Quant-owned
  score definition or root/user assignment.
- Runtime caches, generated reports, local data, and chart images are not
  Quant source-controlled state.
- Chart implementation does not decide valuation status.

## Handoff Rules

1. Research hands only validated intake artifacts to Quant through the configured
   intake contract.
2. Quant turns accepted technical candidates into explicit score specs before
   implementation.
3. Chart implements only explicit specs or concrete root/user assignments.
4. Valuation or hybrid candidates stay separated until
   `.agents/skills/valuation_review/SKILL.md` gives an explicit
   availability/verdict handoff.
5. Any scanner/runtime folder migration must be handled as a separate post-MVP
   migration step.

## Non-Authorizations

This contract does not authorize:

- scanner/runtime physical directory moves
- score formula changes
- score adoption
- ranking or report semantic changes
- backtest behavior changes
- valuation/fundamental activation
- new live data ingestion or vendor assumptions
- generated-output promotion into source control
