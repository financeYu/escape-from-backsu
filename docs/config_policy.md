# Config Policy

## Principle

The project is config-first.

Paths, windows, thresholds, weights, score toggles, normalization modes, and branch enablement should live in config unless a narrow hardcoded exception is necessary and documented.

## Config Status

The root `config/` files are conservative control surfaces:

- `config/global.toml`
- `config/data.toml`
- `config/windows.toml`
- `config/thresholds.toml`
- `config/weights.toml`
- `config/scores.toml`

After Step 20, the approved MVP v0.1 source contracts implement technical score
processing, latest ranking, reports, and evaluation-only backtest boundaries.
The config files still keep config-driven production activation disabled unless
a later approved Step changes that explicitly.

## Score Config Policy

Score config remains placeholder-only until score definitions are documented and approved.

Rules:

- no silent score redefinition after seeing results
- no implementation before score purpose, formula path, input fields, normalization, and failure modes are documented
- no diagnostic may be presented as an alpha signal
- no valuation or fundamental score may be enabled while valuation status is deferred
- root `config/scores.toml` is the activation guardrail and keeps config-driven
  score/composite toggles off
- `Quant_mvp/config/scores.toml` lists candidate registry metadata; in that
  file, `runtime_enabled = false` means the registry does not activate runtime
  scoring by itself
- current MVP source status comes from `docs/context/MVP_V0_1_BASELINE.md`,
  `docs/contracts/step20_composite_contract.md`, and
  `docs/contracts/step20_ranking_contract.md`, not from pre-Step registry flags

## Pre-Freeze Consistency Note

Do not spend root-agent review tokens reconciling `runtime_enabled = false` with
Step 20 completion. The intended meaning is:

- source contracts: MVP v0.1 technical ranking path exists and is validated
- config switches: production-style config activation remains disabled
- valuation/fundamental activation: still disabled and candidate-only
- backtest feedback: still forbidden from upstream scoring or ranking

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
