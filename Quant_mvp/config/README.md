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
- `scores.toml`: Step 5/9 technical candidate registry with Step 20 downstream
  contract context. In this file, `enabled = true` means candidate review
  visibility only; `runtime_enabled = false` means this registry does not
  activate runtime scoring by itself.
- `research_sources.toml`: approved research metadata sources, rate limits, retry settings, and secret-redaction settings
- `research_queries.toml`: conservative research query packs for technical, diagnostic, valuation, and Korea/KOSPI context discovery
- `research_policy.toml`: hard-stop policy for research ingestion, including no score adoption, no backtest, and PDF-disabled defaults
- `research_classification.toml`: transparent keyword rules for research_branch and downstream_route assignment
- `research_scholar_discovery.toml`: Google Scholar discovery-only policy for local human-assisted inputs

Valuation score examples are separated into `agents/valuation/valuation_scores.example.toml`.
They are not part of the main technical scanner config.

## Rules

- keep keys stable and descriptive
- prefer editing config before editing code
- document any unavoidable hardcoding in code comments and review notes
- do not treat disabled valuation config as proof that valuation data is point-in-time safe
- do not treat candidate-registry `enabled = true` as runtime implementation permission
- do not treat registry-level `runtime_enabled = false` as a claim that the
  Step 15/20 MVP ranking source contracts are absent
