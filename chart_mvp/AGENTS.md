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

## Boundaries

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

