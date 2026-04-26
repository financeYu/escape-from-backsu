# chart_mvp Agent

## Purpose

`chart_mvp` is the executable scanner-runtime project.

It owns the local KOSPI200 data-fetching pipeline, CSV cache behavior, technical indicator calculation, ranking output, chart rendering, command-line runner, GUI runner, and tests.

Read the workspace root `AGENTS.md` before making cross-project changes.

---

## Why this project exists

This project turns reviewed quant ideas into runnable behavior.

It is intentionally separate from research and score-governance documents because scanner code produces runtime artifacts such as CSV caches, JSON outputs, and chart images. Those artifacts are useful locally, but they should not be confused with source-controlled project state.

---

## Responsibilities

- maintain `src/stock_core` runtime modules
- maintain `src/chart_mvp` compatibility modules
- maintain `app` and `src/app` runners
- maintain CLI and GUI execution paths
- maintain data providers and cache rules
- maintain chart rendering
- maintain tests under `tests`
- document generated outputs and runtime limitations

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

---

## Boundaries

### Chart Scope Approval Gate

`chart_mvp` workers must not expand implementation or repair scope beyond the
`chart_mvp` ownership boundary without explicit root/master approval. If a task
requires edits or implementation decisions in another subproject or root-owned
policy area, stop at the boundary, report the required crossing, and wait for
root/master permission before proceeding.

This agent must not:

- adopt new scores without a `Quant_mvp` score definition or explicit user request
- perform valuation review
- infer valuation from price-only data
- scrape or ingest papers
- commit runtime cache files or chart outputs as source code
- hardcode personal machine paths

If a change requires score taxonomy, formula adoption, or valuation interpretation, route it to `Quant_mvp` first.

---

## Git policy

Commit:

- source code
- tests
- docs
- small static reference files required for deterministic behavior

Do not commit by default:

- `data/*_daily_prices.csv`
- `data/*_financial_statements.csv`
- `outputs/*.csv`
- `outputs/*.json`
- `outputs/charts/*.png`
- `reports/data_quality/*`
- `__pycache__`
- `*.pyc`

If a generated sample is needed in Git, place the smallest possible fixture under an explicit fixture path and document why.

---

## Post-MVP v0.1 task packet intake

When root/master delegates post-Step20 work, accept the compact task packet in
`../docs/context/POST_MVP_AGENT_TASK_PACKET.md`.

For chart runtime work, this packet does not authorize changes to scanner
runtime behavior, scoring, ranking, report behavior, backtest behavior,
valuation/fundamental activation, data ingestion, cache semantics, or generated
output policy unless the concrete post-MVP task explicitly assigns that scope.
If the task is blank or would cross those boundaries, stop and report the needed
clarification or root/master approval.

Final reports must use the Korean sections defined in the packet.

---

## Implementation policy

- Keep runtime paths relative to `chart_mvp` or configurable through environment variables.
- Keep tests deterministic and avoid live network dependencies unless clearly marked as integration checks.
- Preserve UTF-8 output handling for Korean labels and reports.
- Prefer config or explicit function parameters over scattered constants when behavior needs to vary by environment.
- Keep chart rendering local and inspectable unless the user requests a different rendering stack.

---

## Verification

Preferred baseline verification:

```powershell
python -m unittest discover -s tests -v
```

Use narrower tests when the change is localized.
