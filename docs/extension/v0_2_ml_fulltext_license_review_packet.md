# v0.2 ML Full-Text / License Review Packet

## Purpose

이 packet은 `prob_up_1d_candidate` candidate-only ML research reference의
full-text/license backlog를 별도 수동 검토 단위로 분리한다. 목표는
`metadata_only` 또는 `abstract_reviewed` reference가 implementation gate
근거로 조용히 승격되지 않도록 막고, `full_text_reviewed` 또는
`project_validated` 승격 후보만 명시적으로 검토하는 것이다.

이 packet은 PDF 수집, full-text crawler, API client, model training, data
ingestion, score formula, production ranking, report behavior, backtest, valuation
review, trading language를 승인하지 않는다.

Selected reusable gates:

- `.agents/skills/ml-research-evidence/SKILL.md`
- `.agents/skills/quant-candidate-ml-gate/SKILL.md`

## Confirmed Context

- Step 20 is complete, and the KOSPI200 technical MVP v0.1 baseline is frozen.
- The active post-MVP route is v0.2 candidate-only `prob_up_1d_candidate`.
- Backtest output is evaluation-only and must not feed back into scoring,
  ranking, model features, or production behavior.

## Scope

Allowed:

- split reference backlog into license-first, full-text-first, and
  project-validation-first review queues.
- define manual evidence promotion checks.
- identify references that are already `full_text_reviewed` and may be reviewed
  for `project_validated` status later.
- keep official-doc references separate from paper/full-text references.

Forbidden:

- collecting PDFs or storing full-text files.
- promoting any reference automatically.
- using paper claims as project validation.
- using citation count, source reputation, or benchmark claims as evidence
  strength.
- changing candidate model features, training behavior, score formulas,
  production ranking, reports, or final composite semantics.

## Current Review State

No PDF or full-text artifact was collected in this packet. Existing EvidenceCard
JSONL files do not contain the v0.2 `REF-*` IDs from the reference plan, so this
packet is a research-reference review queue, not a generated EvidenceCard update.

## Evidence Promotion Rule

Promotion is manual and monotonic:

```text
metadata_only
-> abstract_reviewed
-> license_verified_pdf_collected
-> full_text_reviewed
-> project_validated
```

Rules:

- `metadata_only` and `abstract_reviewed` cannot close an implementation gate.
- `license_verified_pdf_collected` proves collection permission only.
- `full_text_reviewed` can support contract design, but does not change model,
  ranking, score, report, or backtest behavior by itself.
- `project_validated` means the method assumption was checked against the local
  no-lookahead, label availability, split, calibration, sidecar, and
  evaluation-only contracts.

## Manual Promotion Checklist

Before any reference is promoted to `full_text_reviewed`, confirm:

- official source URL and source type are recorded.
- license or terms allow local research review.
- `license_name`, `license_url`, `license_checked_at`,
  `license_evidence_quote`, and `collection_basis` are recorded.
- `redistribution_allowed` is false unless explicitly proven.
- `external_upload_allowed` is false unless separately approved.
- no paywalled, login-only, subscription, or unauthorized mirror source is used.
- full-text notes are short summaries, not long copied passages.

Before any reference is promoted to `project_validated`, confirm:

- relevant method assumptions map to
  `docs/extension/v0_2_ml_backtest_validation_contract.md`.
- `decision_time`, `feature_observation_time`, `label_time`, and
  `label_availability_time` assumptions are explicit or marked not applicable.
- walk-forward, purge, embargo, and split-gap implications are explicit.
- calibration fit scope is limited to training or calibration windows.
- multiple-testing and overfitting risks are warning or blocker fields.
- use remains `reference_only`, `validation_method_candidate`,
  `label_design_reference`, `calibration_reference`,
  `model_candidate_reference`, or `architecture_reference`.
- forbidden use retains `production_ranking_activation: false`,
  `final_composite_score_change: false`, `backtest_feedback_to_training: false`,
  and no trading claim.

## Queue A: Already Full-Text Reviewed, Project-Validation Candidates

These references may be manually reviewed for `project_validated` status without
PDF collection because the reviewed material is official web documentation.

| Ref ID | Current basis | Candidate promotion | Manual check focus | Boundary |
| --- | --- | --- | --- | --- |
| REF-LABEL-002 | scikit-learn TimeSeriesSplit official docs, `full_text_reviewed` | `project_validated` for time-ordered split and `gap` semantics only | confirm it is only a split/gap reference and not a full financial purging substitute | no model training or ranking activation |
| REF-TIMEVAL-002 | Qlib official docs, `full_text_reviewed` | `project_validated` for architecture separation only | confirm DataHandler/Dataset/workflow concepts map to sidecar and recorder boundaries | no Qlib runtime adoption |
| REF-CAL-001 | scikit-learn calibration docs, `full_text_reviewed` | `project_validated` for calibration audit fields only | confirm Brier/log loss/calibration curve and fit-scope fields map to contract | no automatic model promotion |
| REF-ARCH-001 | Qlib official docs portion, `full_text_reviewed`; arXiv paper portion remains `abstract_reviewed` | docs portion only may support architecture validation | keep paper claims separate from official docs | no paper PDF collection or platform adoption |

## Queue B: License-First Before Full-Text Review

These references require license/source-terms review before any local PDF or
full-text collection. They remain blocked for implementation gate closure.

| Ref ID | Current state | Required next check | Promotion target | Gate status |
| --- | --- | --- | --- | --- |
| REF-MODEL-001 | arXiv XGBoost, `abstract_reviewed`, `requires_license_review` | capture individual arXiv license and allowed local use | `license_verified_pdf_collected` only if policy allows | model candidate reference only |
| REF-MODEL-002 | NeurIPS LightGBM, `abstract_reviewed`, `requires_license_review` | capture NeurIPS/paper page license and terms | `license_verified_pdf_collected` only if policy allows | model candidate reference only |
| REF-CAL-002 | PMLR calibration paper page, `abstract_reviewed` | capture PMLR page license/terms before PDF storage | `full_text_reviewed` only after license trace | later-only calibration reference |
| REF-XSEC-001 | NBER/RFS Gu-Kelly-Xiu, `abstract_reviewed` | check NBER/Oxford license and access terms | `full_text_reviewed` only after license trace | research reference only |

## Queue C: Full-Text-First Methodology Backlog

These references need full-text review and project validation before their
method assumptions can support an implementation gate. Access may require manual
non-PDF review or separate license approval.

| Ref ID | Current state | Required next check | Gate blocker |
| --- | --- | --- | --- |
| REF-LABEL-001 | AFML, `metadata_only` | access/reuse terms and full-text method review | fixed-horizon/triple-barrier/meta-labeling cannot close a gate yet |
| REF-TIMEVAL-001 | AFML Chapter 7 listing, `metadata_only` | access/reuse terms and full-text method review | purged K-fold/embargo cannot close a gate yet |
| REF-OVERFIT-001 | SSRN PBO, `abstract_reviewed` | SSRN license plus full-text review | PBO/CSCV remains diagnostic backlog |
| REF-OVERFIT-002 | SSRN Deflated Sharpe Ratio, `abstract_reviewed` | SSRN license plus full-text review | deflated metrics remain diagnostic backlog |
| REF-OVERFIT-003 | Econometrica Reality Check, `abstract_reviewed` | publisher license plus full-text review | data-snooping reference remains diagnostic backlog |

## Review Packet Output Template

Manual reviewer output should use this shape:

```yaml
ref_id: "<REF-ID>"
review_date: "<YYYY-MM-DD>"
reviewer: "<name or role>"
source_url: "<official URL>"
fulltext_source_type: official_html | official_pdf | repository_pdf | user_provided_pdf | documentation_page | none
license_name: "<license or terms label>"
license_url: "<URL or null>"
license_checked_at: "<timestamp>"
license_evidence_quote: "<short quote only>"
collection_basis: "<why local review is allowed>"
evidence_level_before: metadata_only | abstract_reviewed | license_verified_pdf_collected | full_text_reviewed
evidence_level_after: metadata_only | abstract_reviewed | license_verified_pdf_collected | full_text_reviewed | project_validated
promotion_decision: promote | keep_backlog | reject | needs_legal_or_root_review
allowed_use:
  - reference_only
forbidden_use:
  - production_ranking_activation
  - final_composite_score_change
  - backtest_metric_as_feature
  - backtest_feedback_to_training
  - trading_claim
project_validation_checks:
  decision_time_controls: pass | fail | not_applicable
  label_availability_controls: pass | fail | not_applicable
  walk_forward_purge_embargo: pass | fail | not_applicable
  calibration_fit_scope: pass | fail | not_applicable
  multiple_testing_controls: pass | fail | not_applicable
remaining_risks:
  - "<risk>"
gate_status: candidate_only | blocked | needs_root_approval
```

## Completion Status

This packet separates the backlog and identifies manual promotion candidates.
No reference was promoted by this packet. No EvidenceCard JSONL was changed. No
PDF/full-text artifact was collected.
