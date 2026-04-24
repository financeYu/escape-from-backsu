# Config Layout

This directory is the single source of truth for runtime parameters that would otherwise become hardcoded.

## Goals

- keep paths, windows, thresholds, weights, and score toggles out of code
- keep the main technical scanner separate from valuation-agent examples
- support conservative defaults and easy review diffs

## File map

- `global.toml`: project-level defaults, communication defaults, branch switches, and policy flags
- `data.toml`: data paths, availability flags, schema expectations, and validation rules
- `windows.toml`: indicator, return, normalization, and warmup windows
- `thresholds.toml`: coverage, outlier, redundancy, and stability thresholds
- `weights.toml`: family, branch, and shrinkage weights
- `scores.toml`: technical score registry and enable/disable switches

Valuation score examples are separated into `agents/valuation/valuation_scores.example.toml`.
They are not part of the main technical scanner config.

## Rules

- keep keys stable and descriptive
- prefer editing config before editing code
- document any unavoidable hardcoding in code comments and review notes
- do not treat disabled valuation config as proof that valuation data is point-in-time safe
