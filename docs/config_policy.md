# Config Policy

## Principle

The project is config-first.

Paths, windows, thresholds, weights, score toggles, normalization modes, and branch enablement should live in config unless a narrow hardcoded exception is necessary and documented.

## Step 3 Status

The root `config/` files are draft scaffolds:

- `config/global.toml`
- `config/data.toml`
- `config/windows.toml`
- `config/thresholds.toml`
- `config/weights.toml`
- `config/scores.toml`

They prepare config-first management. They do not activate scores, composites, rankings, backtests, valuation scores, or fundamental scores.

## Score Config Policy

Score config remains placeholder-only until score definitions are documented and approved.

Rules:

- no silent score redefinition after seeing results
- no implementation before score purpose, formula path, input fields, normalization, and failure modes are documented
- no diagnostic may be presented as an alpha signal
- no valuation or fundamental score may be enabled while valuation status is deferred
- root `config/scores.toml` is the active runtime guardrail and keeps all runtime score/composite toggles off
- `Quant_mvp/config/scores.toml` may list Step 5 candidate registry entries, but `runtime_enabled = false` means those entries are not implemented production scores

## Branch Policy

The Step 4 branch policy is fixed in:

```text
docs/score_branch_policy.md
docs/selection_criteria.md
```

Allowed branch labels are:

- `technical`
- `valuation`
- `diagnostic`
- `hybrid`
- `out_of_scope`

Only `technical` and `diagnostic` candidates may proceed to Step 5 definition work in the main technical flow. `valuation` and unresolved `hybrid` candidates remain separated or blocked until point-in-time fundamentals are explicitly verified.

## Config Change Documentation

Any meaningful config change should state:

- file and key changed
- reason for change
- expected behavioral effect
- whether it affects validation, score design, runtime scanning, or reporting
- whether it changes any historical interpretation

## Hardcoding Policy

Hardcoding is allowed only for:

- stable schema constants
- narrow compatibility aliases
- unavoidable library quirks
- explicitly documented temporary shims

Hardcoding is not allowed for:

- score windows
- score weights
- ranking thresholds
- universe assumptions that should be configurable
- personal machine paths
- valuation timing assumptions

## Financial and Valuation Boundary

Financial data status is:

```text
valuation_deferred
inventory_only
GUI display only if already present
```

Financial data must not enter:

- `technical_composite_score`
- `final_composite_score`
- technical ranking logic
- valuation scoring

Point-in-time financial availability must be explicit before any valuation work can proceed.
