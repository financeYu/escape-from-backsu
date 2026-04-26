# Step 14 Adoption Synthesis

> Historical Step document. Not current authority; use
> `docs/roadmap_status.md` and `docs/context/ARCHIVE_INDEX.md` for current
> routing.

## 1. Purpose

Step 14 turns Step 13 Technical Selection Reviewer material into a documented
score-level adoption synthesis table.

The output is **adoption synthesis material only**. It is a contract and review
handoff layer between Step 13 review recommendations and Step 15 ranking
implementation. It does not order tickers, compute portfolio decisions, or
activate production scoring.

Step 14 answers:

- which score-level technical candidates are core, conditional, context-only,
  research-only, rejected, blocked, or still manual-review items
- why the synthesis is conservative
- which Step 13 evidence supports the synthesis
- what limitations must remain visible before Step 15 can consume the material

## 2. Step 13 `review_status` Versus Step 14 `adoption_state`

Step 13 `review_status` is a technical review recommendation. It is not a final
adoption decision.

Step 14 `adoption_state` is the synthesis result for the score-level adoption
plan. It is still not a ranking bucket, trading decision, alpha label, composite
score output, or valuation verdict.

The Step 14 output preserves the Step 13 value as `source_review_status` and
stores the Step 14 result separately as `adoption_state`. A plain
`review_status` column is not part of the Step 14 output schema because that
would blur the boundary between source review material and synthesis result.

Allowed Step 14 `adoption_state` values:

```text
core_adopted
conditional_adopted
technical_only
regime_only
diagnostic_only
research_only
rejected
blocked_by_data
needs_manual_review
```

These states describe score-level adoption synthesis only. They do not imply
constituent ranking, latest ranking, buy/sell action, expected return, target
price, position sizing, or final composite contribution.

## 3. Inputs From Step 13 Review Material

Step 14 may consume the Step 13 review table and its source-review fields:

| input | Step 14 use |
| --- | --- |
| `score_name` | Stable Step 9 MVP score identifier. |
| `family` | Step 11 family metadata preserved unchanged. |
| `branch` | Step 11 branch metadata preserved unchanged. |
| `role` | Step 11 role metadata preserved unchanged. |
| `eligibility` | Step 11 eligibility metadata preserved unchanged. |
| `normalized_score_column` | Traceability to the Step 10 normalized score column. |
| `score_input_column` | Traceability to the Step 9 raw/component score column. |
| `coverage_status` | Review input for data availability limitations. |
| `redundancy_status` | Review input from Step 12 redundancy diagnostics. |
| `complexity_status` | Review input for implementation and interpretation cost. |
| `regime_fit_status` | Review input for broad, regime-specific, or diagnostic context. |
| `review_status` | Copied only into Step 14 `source_review_status`. |
| `review_reason` | Evidence input, not final synthesis wording by itself. |
| `evidence_sources` | Source traceability for synthesis. |
| `manual_review_required` | Carry-forward manual review flag. |

Step 14 should not re-run Step 12 diagnostics or reclassify Step 13 review
material as if it were a new technical reviewer.

## 4. Conservative Adoption Synthesis Rules

Step 14 synthesis is allowed to be more conservative than Step 13. It must not
optimistically promote uncertain review material.

Rules:

- `adopt_candidate` may become `core_adopted` only when limitations are explicit
  and no Step 13 blocker remains.
- `conditional_candidate` should usually become `conditional_adopted`,
  `technical_only`, `regime_only`, `research_only`, or `needs_manual_review`.
- `diagnostic_only` should remain `diagnostic_only`, `regime_only`, blocked,
  rejected, or manual-review material. It must not become core direct adoption.
- `research_only` should remain research-only, rejected, blocked, or manual
  review material.
- `reject_candidate` should remain rejected or manual-review material.
- `blocked_by_data` should remain blocked, rejected, or manual-review material
  until the data issue is fixed in the proper upstream step.
- `needs_manual_review` must keep `manual_review_required = true` unless a later
  source-controlled review resolves the issue.

Context and diagnostic roles must stay visibly separate from direct technical
candidates. Redundancy warnings and blocked data states are not automatic
removal decisions, but they also must not be hidden in the synthesis.

## 5. Output Schema

Canonical contract source:

```text
src/selection/adoption_synthesis_contracts.py
```

Required Step 14 adoption synthesis columns:

| column | meaning |
| --- | --- |
| `score_name` | Locked Step 9 MVP score name. |
| `family` | Step 11 family metadata, unchanged. |
| `branch` | Step 11 branch metadata, unchanged. |
| `role` | Step 11 role metadata, unchanged. |
| `eligibility` | Step 11 design-stage eligibility, unchanged. |
| `source_review_status` | Step 13 `review_status` copied as source material. |
| `adoption_state` | Step 14 adoption synthesis state. |
| `adoption_reason` | Conservative reason for the synthesis state. |
| `evidence_sources` | Step 13 and upstream source references used for the row. |
| `limitations` | Known limitations or unresolved review constraints. |
| `manual_review_required` | Boolean flag for unresolved manual review need. |

Optional traceability columns:

| column | meaning |
| --- | --- |
| `normalized_score_column` | Step 10 normalized score column used as traceability. |
| `score_input_column` | Step 9 raw/component score column used as traceability. |
| `coverage_status` | Step 13 coverage label copied as source material. |
| `redundancy_status` | Step 13 redundancy label copied as source material. |
| `complexity_status` | Step 13 complexity label copied as source material. |
| `regime_fit_status` | Step 13 regime-fit label copied as source material. |
| `downstream_usage_note` | Note for Step 15 about allowed downstream use. |

Required fields must be non-empty unless a later source-controlled contract
explicitly allows an empty value. `manual_review_required` must contain boolean
values.

## 6. Forbidden Columns

Step 14 output must reject columns that imply ranking, composite scoring,
future-looking performance, trading decisions, valuation, or position sizing.

Forbidden columns include at minimum:

```text
rank
ranking
latest_rank
technical_composite_score
final_composite_score
forward_return
future_return
backtest_return
alpha
signal
buy
sell
valuation_score
undervalued
cheap
bargain
target_price
expected_return
position_size
```

Additional forbidden examples include `review_status`, `adoption_decision`,
`final_adoption_status`, `final_adoption_decision`, `selected_for_composite`,
`fundamental_score`, `PER`, `PBR`, `ROE`, and any financial/fundamental or
valuation-prefixed field.

Use:

```text
validate_adoption_synthesis_columns(...)
assert_no_forbidden_adoption_columns(...)
validate_adoption_synthesis_table(...)
```

## 7. Forbidden Language

Generated Step 14 narrative must avoid language that turns synthesis into
trading, alpha, backtest, ranking, valuation, or final confirmation language.

Forbidden report language includes at minimum:

```text
alpha evidence
buy signal
sell signal
trading signal
expected return
future return
backtest proves
undervalued
cheap
bargain
value stock
target price
실전 매수 후보
수익률 보장
최종 랭킹
최종 채택 확정
```

Use:

```text
validate_adoption_report_text(...)
assert_no_forbidden_adoption_language(...)
```

## 8. Generated Report Boundary

This document is source-controlled canonical Step 14 documentation.

Generated Step 14 reports, if added by another worker, are runtime artifacts and
should be written under:

```text
reports/selection/
```

Generated reports must not be written under `docs/`. A generated report should
include the phrase:

```text
adoption synthesis material only
```

Generated report files are not canonical roadmap state unless a small fixture is
explicitly promoted for tests with a source-controlled explanation.

## 9. Explicit Non-Outputs

Step 14 does not:

- generate ranking or latest ranking output
- compute `technical_composite_score`
- compute `final_composite_score`
- compute family weighted composite output
- run or add backtests
- compute forward or future returns
- create alpha labels, trading signals, buy/sell signals, expected returns,
  target prices, or position sizes
- use valuation/fundamental/financial data
- make valuation judgments from price-only technical evidence
- present score-level synthesis as a final trading decision

Financial and fundamental data remain deferred to Step 18. Step 14 must not use
`PER`, `PBR`, `ROE`, financial statements, valuation scores, target prices, or
point-in-time fundamental inference.

## 10. Step 15 Preparation Boundary

Step 14 prepares Step 15 by producing clean score-level adoption synthesis
material:

- score-level adoption states
- evidence and limitation notes
- manual-review flags
- traceability back to Step 13 review material
- clear separation of direct technical candidates from context, diagnostic, and
  research-only material

Step 14 does not perform Step 15 ranking. Step 15 may later consume the
synthesis material only after its own contract defines how ordering, display,
and generated output boundaries are handled.

## 11. Focused Validation Command

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/selection/test_step14_adoption_synthesis_contracts.py
```
