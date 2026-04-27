# v0.2 Config Ownership Contract

Status: frozen config ownership contract for the post-MVP `v0.2 predictive
probability score route`.

## Config-Owned Items

The following must be config-owned before implementation:

- feature-set version
- old-score feature inclusion toggles
- model family toggle
- training window policy
- validation split policy
- calibration policy
- probability output thresholds used only for diagnostics
- generated-output roots
- rollback/deactivation toggle

## Hardcoding Rule

Runtime code must not silently hardcode model features, windows, thresholds,
output paths, or validation split behavior. Any default must be documented in
config and covered by validation.

## Forbidden Config Defaults

- defaults that activate production ranking
- defaults that write generated outputs into source-controlled paths
- defaults that include future labels or backtest metrics as model inputs
- defaults that include valuation/fundamental data
