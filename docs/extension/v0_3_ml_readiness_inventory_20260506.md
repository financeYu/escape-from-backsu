# v0.3 ML Readiness Inventory - 2026-05-06

Status: active readiness inventory.
Route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Gate: `docs/extension/v0_3_adoption_candidate_selector_gate.md`.
Owner lane: ML/evaluator selector with Quant evidence and root boundary review.

This inventory records whether current v0.3 candidate and evidence artifacts are
ready for ML/evaluator use. It is evidence-only. It does not authorize model
training, runtime ranking, reports, trading, adoption, or production activation.

## Scope Lock

Allowed inputs inspected:

- `Quant_mvp/data/v0_3/strategy_candidates/v0_3_strategy_candidate_manifest.json`
- `Quant_mvp/data/v0_3/selector_inputs/v0_3_selector_input_manifest.json`
- `Quant_mvp/data/v0_3/ml_ready_candidate_inputs/v0_3_ml_ready_candidate_input_manifest.json`
- `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/momentum_cohort_1/manifest.json`
- one representative `EvaluationEvidence` packet from `momentum_cohort_1`
- relevant v0.3 route contracts under `docs/extension/`

Blocked or excluded inputs:

- raw backtest tables
- live market data feeds
- runtime reports
- future labels or lookahead fields
- generated raw data, caches, charts, archives, and release evidence

## Current Artifact Counts

| Layer | Current evidence | ML readiness meaning |
| --- | ---: | --- |
| StrategyCandidate registry records | 698 | Candidate universe exists, but most records are not evaluable. |
| Evaluable StrategyCandidate records | 62 | These can proceed toward approved EvaluationEvidence work. |
| Draft StrategyCandidate records | 530 | Need StrategyHypothesis refinement before evaluation. |
| Blocked StrategyCandidate records | 106 | Need blocker resolution before evaluation. |
| Selector input records | 698 | Research/evidence metadata exists for triage. |
| Selector inputs eligible for candidate selector review | 67 | These are review-priority inputs, not supervised labels. |
| Momentum EvaluationEvidence records | 27 | Evidence packets exist for one cohort. |
| ML-ready candidate input rows | 698 | Rows exist as metadata, but training labels are not available. |
| Metric available count | 27 | EvaluationEvidence metric values are available. |
| Candidate-level metric count | 0 | No metric row currently matches a candidate-level supervised label subject. |
| Generic proxy metric count | 27 | Generic momentum proxy metrics are reference feature candidates, not labels. |
| Actual label count | 0 | No candidate-level supervised label is currently available. |
| Supervised-label eligible count | 0 | Generic proxy labels still cannot train a supervised selector. |
| Adoption-review eligible count | 0 | No current row can support AdoptionCandidate review selection. |

The generated ML-ready rows now separate metric source from label source:
`metric_source: approved_evaluation_evidence` marks the 27 available metric
rows, while `label_source: unlabeled` and `actual_label_source: null` keep all
698 rows out of binary supervised training. Generic proxy rows are marked with
`metric_role: generic_momentum_proxy`,
`metric_use_status: benchmark_reference_feature_candidate`,
`metric_subject_type: generic_proxy`, and
`candidate_metric_match: false`.

## Main Blockers For ML Application

1. No approved supervised labels are available.

   The ML-ready manifest now reports `metric_available_count: 27`, but
   `candidate_level_metric_count: 0` and `supervised_label_eligible_count: 0`.
   The current binary supervised ML status is
   `blocked_no_candidate_level_supervised_labels`. This means metrics exist for
   review/reference use, but a supervised selector still cannot be trained yet.

2. Momentum evidence exists, but it is not candidate-specific label evidence.

   The momentum cohort has 27 `evidence_recorded` packets, and those metrics now
   populate the `actual_*` metric value columns. However, the generated rows
   now keep `label_source` as `unlabeled`, set
   `reference_feature_candidate: true`, and mark
   `candidate_metric_match_reason: generic_momentum_proxy_not_candidate_level`.
   The ML-ready builder explicitly blocks generic proxy summaries from becoming
   supervised labels.

3. Walk-forward or out-of-sample stability is not ready for adoption review.

   The required evaluation checks include
   `oos_walk_forward_stability`, but the representative evidence packet uses a
   single-pass momentum proxy context. Without OOS or walk-forward evidence,
   a row may have metrics but still cannot become adoption-review eligible.

4. Benchmark-relative evidence is incomplete.

   The representative evidence packet records `benchmark_comparison` as
   unavailable without an approved benchmark series. Review-preferred selection
   requires performance relative to benchmark, not only standalone metrics.

5. Data quality limitations remain material.

   The cohort manifest records limitations for all 27 momentum packets,
   including survivorship warning, non-point-in-time constituent warning,
   corporate action adjustment unknown, insufficient price history, missing
   exit price, zero OHLCV exclusions, duplicate ticker/date row handling, and
   upstream blocked rows. These do not automatically invalidate the packets, but
   they prevent high-confidence ML/adoption claims.

6. Candidate coverage is still narrow.

   Only 27 momentum-cohort evidence packets are recorded against 698 candidate
   records and 62 evaluable candidates. The current evidence set is too narrow
   for a broad selector claim across strategy families.

## What Is Ready

- Candidate metadata exists and is separated from runtime behavior.
- Selector input metadata exists and keeps the no-feedback boundary.
- ML-ready rows exist as a review triage table with 27 generated metric rows.
- The generated rows make generic-proxy metric role and reference-feature use
  status explicit without requiring inference from blocker fields.
- Evidence-only momentum packets exist for a first cohort.
- The builder has guardrails that keep actual labels null unless approved
  EvaluationEvidence is present.
- The builder rejects pseudo labels and random splits without group isolation.

## What Is Not Ready

- Binary supervised model training.
- AdoptionCandidate selection.
- Production activation.
- Runtime score, ranking, report, backtest, trading, or order integration.
- A review-preferred candidate conclusion.

Current decision:

`selection unavailable / evidence insufficient`

Missing evidence:

- candidate-level EvaluationEvidence metrics that match each StrategyCandidate
  subject and can be promoted to supervised labels
- walk-forward or out-of-sample stability checks
- approved benchmark-relative comparison
- resolved material data quality limitations or explicit downgrade policy
- broader coverage across evaluable candidates or an explicitly scoped
  momentum-only selector task

## Highest-Priority Next Task

Convert the 27 momentum `EvaluationEvidence` labels from generic momentum proxy
labels into candidate-specific supervised labels only if the backtest/evaluation
owner confirms the metric summaries are candidate-specific and OOS/walk-forward
checks can be added.

If that cannot be confirmed, the next task is to run an approved
candidate-specific evaluation for the 62 evaluable StrategyCandidate records,
starting with the 27 momentum records as a bounded pilot cohort.

## Validation Notes

Blocked cheap checks:

- `rg --files | rg ...`: blocked by Windows access denied. Per project policy,
  this was treated as an environment/search-tool blocker, not validation
  evidence.
- Broad recursive `Get-ChildItem` also hit inaccessible temp/cache paths and
  was narrowed to targeted active v0.3 directories.

Substitute evidence:

- Targeted `Get-ChildItem` over active v0.3 data and evidence directories.
- Targeted manifest reads for candidate, selector, ML-ready input, and
  EvaluationEvidence cohort state.
- Representative EvaluationEvidence packet read for label and limitation
  semantics.

No production activation, runtime model connection, trading, valuation
activation, universe expansion, or new data ingestion was performed.
