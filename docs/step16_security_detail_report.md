# Step 16 Security Detail Report

## Purpose

Step 16 adds a deterministic per-ticker detail report layer for the current
technical snapshot.

The report explains one or more securities using already-built Step 15 latest
ranking output and optional upstream metadata from Step 10, Step 14, and Step
15. It is a structured explanation layer only:

- technical-only detail report
- not a trading recommendation
- not a backtest
- not valuation/fundamental analysis
- no forward/future return used

Step 16 does not create a new ranking, recalculate rank, run historical
simulation, calculate forward labels, or merge financial statement data.

## Allowed Inputs

The core builder accepts already-loaded in-memory tables.

Required Step 15 latest ranking input columns:

| column | use |
| --- | --- |
| `ticker` | Six-digit ticker string. |
| `date` | Latest snapshot date from the Step 15 output. |

Optional Step 15 read-only display fields:

| column | use |
| --- | --- |
| `rank` | Existing Step 15 rank, displayed read-only. |
| `technical_composite_score` | Existing Step 15 technical composite score, displayed read-only. |
| `final_composite_score` | Existing Step 15 final composite score, displayed with technical-only wording. |
| `coverage_metric` | Coverage context for the row. |
| `coverage_status` | Row-level coverage status. |
| `ranking_validity_flag` | Step 15 validity flag, displayed read-only. |
| `valid_score_count` | Count of valid score components from Step 15. |
| `expected_score_count` | Expected score component count from Step 15. |
| `review_routed_score_count` | Count of Step 14 rows routed away from direct Step 15 score use. |
| `final_score_policy` | Existing Step 15 score policy text. |

Optional metadata tables may include Step 14 adoption synthesis fields such as:

| column | use |
| --- | --- |
| `score_name` | Stable score identifier. |
| `family` | Score family. |
| `branch` | Technical or diagnostic branch metadata. |
| `role` | Candidate, confirmation, setup, or diagnostic role. |
| `eligibility` | Step 11 eligibility metadata. |
| `adoption_state` | Step 14 adoption synthesis state. |
| `source_review_status` | Step 13 source review status. |
| `manual_review_required` | Unresolved review flag. |
| `limitations` | Conservative limitation text. |

Optional metadata is copied only after Step 16 forbidden-column and
forbidden-language screening.

## Output Schema

The canonical structured output is `SecurityDetailReport`.

| field | meaning |
| --- | --- |
| `ticker` | Report ticker. |
| `snapshot_date` | Date from the Step 15 input row. |
| `report_date` | Caller-supplied report date, or `snapshot_date` when omitted. |
| `source_latest_ranking_date` | Source Step 15 snapshot date. |
| `rank_fields_are_readonly` | Always true for the core builder. |
| `readonly_rank_fields` | Existing Step 15 rank/context fields if present. |
| `technical_composite_score` | Existing Step 15 technical score if present. |
| `final_composite_score` | Existing Step 15 final score if present. |
| `final_composite_score_note` | Explicit technical-only interpretation text. |
| `score_breakdown` | Read-only score component rows present in Step 15 input. |
| `component_breakdown` | Family/component score rows present in Step 15 input. |
| `diagnostic_context` | Diagnostic or context metadata rows shown outside direct score components. |
| `source_adoption_metadata` | Compact Step 14 source metadata when supplied. |
| `quality_flags` | Warmup, coverage, status, count, and quality fields when present. |
| `explanations` | Blocked, low-quality, rejected, or manual-review explanations when available. |
| `boundary_notice` | Required Step 16 technical-only boundary notice. |

`SecurityScoreBreakdown` rows can show source score column, value, family,
role, branch, eligibility, adoption state, source review status, status,
quality flag, valid count, and explanation text.

Diagnostic/context rows are marked as context-only and not Step 15 direct
score components.

## Technical-Only Interpretation

`technical_composite_score` and `final_composite_score` are displayed only when
they already exist in the Step 15 input. Step 16 does not compute either field.

The `final_composite_score` note is intentionally conservative:

```text
final_composite_score is displayed as existing Step 15 technical-only context; it is not a separate non-technical result.
```

The report can explain coverage, warmup, data quality, adoption state, source
review status, and diagnostic limitations. It must not describe the ticker as a
trade, a price objective, a performance label, or a valuation conclusion.

## Step 15 Read-Only Dependency

Step 15 is the sole source for current rank and latest technical composite
fields consumed by Step 16.

Step 16 may display Step 15 fields such as `rank`, `coverage_metric`, and
`ranking_validity_flag`, but it must not:

- recalculate rank
- resort rows by score to create a new order
- change the Step 15 score policy
- promote diagnostic/context metadata into direct score components
- write generated reports by default

When multiple reports are requested, output follows the caller's ticker order.
When no ticker list is supplied, output follows the input table order. This is
display consistency only, not new ranking generation.

## Step 17 Backtest Boundary

Step 17 is not started.

Step 16 output may later become explanatory input material for a conservative
backtest workflow, but this builder does not implement any Step 17 behavior.

The Step 16 report must not contain:

- `forward_return`
- `future_return`
- `backtest_return`
- realized performance labels
- simulated portfolio metrics
- execution or rebalance assumptions

Backtest-specific metrics and generated outputs belong only to Step 17 or
later, after that step is explicitly opened.

## Step 18 Valuation Boundary

Step 18 valuation/fundamental expansion is deferred.

Step 16 must not read, merge, infer, or display valuation/fundamental scoring.
Financial statement data and fundamental ratios remain outside
`technical_composite_score`, `final_composite_score`, and this detail report
core.

Forbidden Step 16 input/output examples include:

- `valuation_score`
- `fundamental_score`
- `PER`
- `PBR`
- `ROE`
- `target_price`
- `expected_return`

If such fields appear in the input, the core builder rejects the input before
creating report content.

## Toy Data Example

This example uses toy rows only. It does not require real market data.

```python
import pandas as pd

from src.reports.security_detail_report import build_security_detail_report

latest_ranking = pd.DataFrame(
    [
        {
            "ticker": "005930",
            "date": "2026-04-24",
            "rank": 1,
            "technical_composite_score": 1.25,
            "final_composite_score": 1.25,
            "coverage_metric": 1.0,
            "data_quality_flag": "valid",
            "coverage_status": "adequate",
            "ranking_validity_flag": "valid",
            "short_term_overreaction_cross_sectional_robust_z": 0.75,
            "short_term_overreaction_cross_sectional_status": "adequate",
            "short_term_overreaction_cross_sectional_quality_flag": "valid",
            "short_term_overreaction_cross_sectional_valid_count": 3,
        }
    ]
)

adoption_metadata = pd.DataFrame(
    [
        {
            "score_name": "short_term_overreaction",
            "family": "mean_reversion",
            "branch": "technical",
            "role": "candidate_signal",
            "eligibility": "eligible",
            "adoption_state": "core_adopted",
            "source_review_status": "adopt_candidate",
            "manual_review_required": False,
            "limitations": "Toy-data limitation text.",
        }
    ]
)

report = build_security_detail_report(
    latest_ranking,
    "005930",
    report_date="2026-04-25",
    adoption_synthesis=adoption_metadata,
)

record = report.to_dict()
```

The returned `record` is ready for a future JSON, CLI, or Markdown renderer.
The core builder itself does not write generated report files.
