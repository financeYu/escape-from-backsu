# Config Layout

This directory is the single source of truth for runtime parameters that would otherwise become hardcoded.

## Goals

- keep paths, windows, thresholds, weights, and score toggles out of code
- keep the main technical scanner separate from valuation review examples
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
- `up_probability.toml`: post-MVP evaluation-only candidate settings for
  `next_horizon_up_probability_score`; default `horizon_trading_days = 1`.
  This does not activate production ranking or replace the GUI score. Its
  `primary_score_migration` section records the exception-managed migration
  plan: the new score is the primary candidate, while MVP v0.1 composite scores
  remain archived legacy references until a later cutover branch is approved.
- `research_intake.toml`: score-governance intake contract for EvidenceCards
  produced by `research_mvp`; its paths resolve from the `Quant_mvp` project
  root and prefer canonical `research_mvp/data/research/evidence` files before
  using temporary legacy `data/research/evidence` fallback files
- `v0_4_selector_model.toml`: v0.4 evidence-only ML/rule selector application
  config. It consumes the v0.3 feature matrix and label manifest, runs
  trainability checks first, and allows a logistic-regression baseline only for
  `AdoptionCandidate` review prioritization. It does not authorize trading,
  order generation, production activation, or new market-data ingestion.

Research-ingestion source, query, policy, classification, Scholar discovery,
and v0.2 ML reference query configs live under `research_mvp/config`.

Valuation score examples are separated into
`../.agents/skills/valuation_review/references/valuation_scores.example.toml`.
They are not part of the main technical scanner config.

## Rules

- keep keys stable and descriptive
- prefer editing config before editing code
- document any unavoidable hardcoding in code comments and review notes
- do not treat disabled valuation config as proof that valuation data is point-in-time safe
- do not treat candidate-registry `enabled = true` as runtime implementation permission
- do not treat registry-level `runtime_enabled = false` as a claim that the
  Step 15/20 MVP ranking source contracts are absent
