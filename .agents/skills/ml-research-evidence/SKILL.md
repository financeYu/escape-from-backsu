---
name: ml-research-evidence
description: "Use for candidate-only ML research evidence work in master_mvp/Quant_mvp: ML research reference plans, EvidenceCard schema/evidence-level policy, license-aware PDF/full-text research policy, implementation-readiness triage, future model-family references, and research query config that must not implement models, data ingestion, scoring, ranking, reports, backtests, valuation, or trading claims."
---

# ML Research Evidence

## Purpose

Keep ML research references and EvidenceCards useful without letting papers,
documentation, or backtest methodology become implemented models, production
ranking behavior, score formula changes, or trading claims.

Use this skill with `.agents/skills/quant-candidate-ml-gate/SKILL.md` whenever
the work concerns the `prob_up_1d_candidate` candidate ML route.

## Loading Process

Read in order:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this `SKILL.md`
4. `.agents/skills/quant-candidate-ml-gate/SKILL.md` when the work names
   `prob_up_1d_candidate`
5. affected subproject `AGENTS.md`
6. targeted research docs/config/EvidenceCard files only

Do not read archives, generated outputs, raw data, caches, PDFs, logs, or chart
artifacts unless the user names a conflict, provenance, or release-evidence
check.

## Allowed Work

- ML research reference plans and review manifests.
- EvidenceCard schema, evidence-level, and implementation-readiness policy.
- License-aware PDF/full-text research policy.
- Research query config for candidate-only ML reference discovery.
- No-lookahead, label availability, `decision_time`, split, calibration,
  overfitting, and multiple-testing contract notes.
- Future model-family references as `reference_only` or
  `model_candidate_reference`.

## Forbidden Work

Do not implement or authorize:

- model training, inference clients, API clients, downloaders, crawlers, or data
  ingestion expansion
- production ranking activation or report behavior changes
- score formula changes, `technical_composite_score` changes, or
  `final_composite_score` changes
- backtest metrics as features, score weights, ranking inputs, or automatic
  model-selection triggers
- valuation/fundamental scoring or valuation verdicts
- trading, buy/sell/hold, expected-return, proven-alpha, profitability, or
  performance-proof wording

## EvidenceCard Rules

EvidenceCards are upstream evidence objects only. They are not score
definitions, adoption decisions, alpha evidence, backtest results, valuation
verdicts, or implementation approval.

Use conservative evidence levels:

- `metadata_only`: discovery and triage only.
- `abstract_reviewed`: taxonomy support only, not gate-closing evidence.
- `license_verified_pdf_collected`: collection permission only.
- `full_text_reviewed`: contract design support only.
- `project_validated`: method assumptions checked against project contracts.

Implementation gate decisions require `full_text_reviewed` or
`project_validated` evidence. Promotion is manual and monotonic; do not upgrade
because a paper has high citations or strong reported performance.

## PDF And Full-Text Policy

PDF/full-text use must be license-aware and local-only unless a separate task
approves artifact storage.

Require explicit trace fields when full text is used:

- `license_name`
- `license_url`
- `source_url`
- `license_checked_at`
- `license_evidence_quote`
- `collection_basis`
- `local_pdf_path`
- `fulltext_source_type`
- `fulltext_review_scope`
- `redistribution_allowed`
- `external_upload_allowed`

Do not collect paywalled, login-only, subscription, unauthorized mirror, or
license-ambiguous PDFs. Do not bulk download PDFs. Do not upload PDFs/full text
to paid APIs or external hosted services.

## Validation Checklist

For docs/config edits, run:

```bash
git diff --check
```

If TOML changed, run a TOML parse check.

If candidate ML gate files or `prob_up_1d_candidate` contracts are involved,
run:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-candidate-ml-gate\scripts\validate_gate_contract.sh
```

Before accepting completion, run or apply the review rules from:

```bash
.agents/skills/quant-review-gate/SKILL.md
```

## Output

Report in Korean with:

- changed files
- preserved progress
- research coverage added
- PDF/full-text policy result
- EvidenceCard policy changes
- ML/backtest contract summary
- validation results
- remaining risks
- next gate proposal
- status: `COMPLETE`, `PARTIALLY COMPLETE`, or `NEEDS FIX`
