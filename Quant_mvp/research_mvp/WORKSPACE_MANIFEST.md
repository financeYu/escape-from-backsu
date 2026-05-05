# WORKSPACE_MANIFEST

workspace_id: research_manifest_v0_3_architecture_alignment
branch: current-worktree
role: research-ingestion
task_type: architecture_alignment_reference
active_step: post-MVP v0.3 research-to-strategy adoption route
owner_or_worker: research subproject agent under root architecture chain

## Purpose

Keep the research-ingestion workspace aligned with the active root architecture
while preserving the existing research evidence contracts. This workspace
collects approved research metadata, normalizes papers, creates conservative
EvidenceCards, and prepares v0.3 intake artifacts such as
`ResearchHypothesis` handoffs.

The research lane does not download PDFs by default, adopt scores, run
backtests, optimize strategies, perform valuation review, activate production
behavior, or make trading claims.

## Architecture Route

Research-ingestion work is assigned through:

```text
agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor
  -> agent-worker-pool -> agent-reporter
```

Existing downstream route labels such as `technical_score_architect`,
`valuation_agent_handoff`, `hybrid_split_required`, `diagnostic_backlog`, and
`reject_log` remain data-contract labels. They are compatibility targets under
the architecture chain, not direct worker entry points.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- config/
- src/research_ingestion/
- tests/research_ingestion/
- input/
- output/
- data/research/
- reports/research_ingestion/

Generated outputs under `input/`, `output/`, `data/research/`, and
`reports/research_ingestion/` are allowed only when the current root packet
explicitly assigns research-ingestion generation or refresh work.

## Forbidden Actions

- PDF or fulltext download unless an explicit license/source/custody task
  authorizes it
- broad web crawling or non-official source scraping
- score, ranking, report, backtest, scanner runtime, or valuation behavior
  changes
- trading, buy/sell/hold, proven-alpha, profitability, or expected-return
  claims
- edits outside `Quant_mvp/research_mvp` without explicit root/master approval
- bypassing the architecture chain or treating compatibility route labels as
  direct execution authority

## Required Validation

Use the validation commands named by the current root/supervisor packet. Common
research-ingestion checks include:

- `.venv\Scripts\python.exe -m pytest Quant_mvp\research_mvp\tests\research_ingestion`
- `.venv\Scripts\python.exe -m pytest Quant_mvp\tests\test_v0_3_research_hypothesis_builder.py Quant_mvp\tests\test_v0_3_selector_input_builder.py`
- `git diff --check`

When generated manifest or license-trace work is explicitly assigned, also
validate JSONL parsing, duplicate keys, selection-rank continuity, required
source identifiers, license evidence fields, and generated PDF/fulltext file
count according to that task packet.
