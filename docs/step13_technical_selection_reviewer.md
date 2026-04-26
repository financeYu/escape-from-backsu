# Step 13 Technical Selection Reviewer

> Historical Step document. Not current authority; use
> `docs/roadmap_status.md` and `docs/context/ARCHIVE_INDEX.md` for current
> routing.

## 1. Purpose

Step 13 is **technical review material only**.

The Technical Selection Reviewer compares the Step 9 raw score candidates, Step
10 normalized score outputs, Step 11 composite input metadata, and Step 12
redundancy/correlation diagnostics. The result is a conservative technical
review recommendation table for Step 14 Adoption Synthesis.

Step 13 does not create final adoption state. Step 14 remains responsible for
turning review recommendations into an explicit adoption synthesis.

## 2. Explicit Non-Outputs

Step 13 is not:

- ranking output
- latest ranking output
- composite score calculation
- family weighted composite calculation
- backtest
- forward or future return analysis
- trading signal generation
- valuation or fundamental judgment
- alpha evidence

Step 13 must not emit:

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

Price-only technical evidence must not be translated into valuation language.
Technical oversoldness is not cheapness. Redundancy diagnostics are review
evidence only, not alpha evidence.

## 3. Upstream Inputs

Step 13 may use only review material from the completed technical steps:

| source | allowed use |
| --- | --- |
| Step 9 raw score | Formula traceability, warmup and implementation notes. |
| Step 10 normalized score | Input column availability and coverage review. |
| Step 11 composite metadata | `family`, `branch`, `role`, `eligibility`, candidate input column names. |
| Step 12 diagnostics | Coverage, redundancy, threshold flags, insufficient data reasons. |

Financial/fundamental data remains outside Step 13. `PER`, `PBR`, `ROE`,
financial statements, valuation scores, and target-price language must not be
used in technical review decisions.

## 4. Review Table Contract

Canonical contract source:

```text
src/selection/technical_selection_contracts.py
```

Required Step 13 review table columns:

| column | meaning |
| --- | --- |
| `score_name` | Locked Step 9 MVP score name. |
| `family` | Step 11 family metadata, unchanged. |
| `branch` | Step 11 branch metadata, unchanged. |
| `role` | Step 11 role metadata, unchanged. |
| `eligibility` | Step 11 design-stage eligibility, unchanged. |
| `normalized_score_column` | Step 10 normalized column used as review input, if available. |
| `score_input_column` | Raw/component input column used for traceability, if normalized input is unavailable or secondary. |
| `coverage_status` | Step 13 coverage review label. |
| `redundancy_status` | Step 12 redundancy diagnostic label carried into review. |
| `complexity_status` | Complexity and interpretability cost label. |
| `regime_fit_status` | Market-structure or regime-fit label. |
| `review_status` | Step 13 technical review recommendation, not final adoption. |
| `review_reason` | Conservative explanation of the recommendation. |
| `evidence_sources` | Step 9/10/11/12 source references used for the row. |
| `manual_review_required` | Boolean flag for unresolved manual review need. |

At least one of `normalized_score_column` or `score_input_column` must be
present for every row. `normalized_score_column` must not point to a raw score
column.

## 5. Status Vocabulary

### 5.1 `coverage_status`

Allowed values:

```text
ok
warn
insufficient_input
insufficient_data
blocked_by_data
unknown
```

### 5.2 `redundancy_status`

Allowed values:

```text
ok
warn
block_candidate
severe_redundancy
insufficient_input
insufficient_data
config_missing
undefined_correlation
unknown
```

These are review inputs from diagnostics. They are not removal or adoption
decisions.

### 5.3 `complexity_status`

Allowed values:

```text
simple
moderate
complex
excessive_complexity
unknown
```

### 5.4 `regime_fit_status`

Allowed values:

```text
broad
regime_specific
diagnostic_context
unclear
blocked_by_data
unknown
```

### 5.5 `review_status`

Allowed values:

```text
adopt_candidate
conditional_candidate
research_only
diagnostic_only
reject_candidate
blocked_by_data
needs_manual_review
```

`review_status` is a Step 13 technical review recommendation. It is not final
adoption state.

Step 14 final adoption status may later use labels such as `core_adopted`,
`conditional_adopted`, `technical_only`, `regime_only`, `diagnostic_only`,
`research_only`, `rejected`, or `blocked_by_data`. Step 13 must not directly
confirm those final states. When an overlapping label such as `diagnostic_only`,
`research_only`, or `blocked_by_data` appears in Step 13, it means only a review
recommendation inside `review_status`.

## 6. Validation Functions

Worker B should validate generated Step 13 output with:

```text
validate_step13_review_table(df)
validate_step13_review_bundle(bundle)
validate_step13_status_values(df)
reject_step13_forbidden_columns(df)
validate_step13_review_language(text)
```

Validation checks:

- required columns are present
- review status values are from the Step 13 vocabulary
- Step 11 family/branch/role/eligibility metadata is preserved
- all final ranking, composite, backtest, trading, and valuation columns are blocked
- `manual_review_required` is boolean
- `needs_manual_review` rows set `manual_review_required = true`
- review text fields do not use forbidden ranking, trading, alpha, backtest, or valuation language

`validate_step13_review_bundle(bundle)` requires all eight Step 9 MVP scores by
default and screens optional source tables for forbidden output columns.

## 7. Step 14 Boundary

Step 13 hands review material to Step 14. It may recommend that a score is an
`adopt_candidate`, `conditional_candidate`, `research_only`,
`diagnostic_only`, `reject_candidate`, `blocked_by_data`, or
`needs_manual_review`.

Step 13 must not:

- choose final family weights
- choose final adoption state
- merge score families into a composite
- output a constituent ranking
- infer valuation from price-only evidence

Step 14 Adoption Synthesis must explicitly document any final adoption mapping
from Step 13 review recommendations.

## 8. Generated Report Boundary

Generated Step 13 reports are runtime review artifacts. They must be written
under:

```text
reports/selection/
```

Generated reports must not be written under `docs/`.

Every generated report must include the exact phrase:

```text
technical selection review material only
```

The source-controlled boundary note is:

```text
reports/selection/README.md
```

Generated reports are not Step 14 final adoption synthesis, ranking output,
composite output, backtest output, or valuation output.

## 9. Worker B Handoff

Worker B can implement the review engine against this fixed schema.

Required integration checks:

- generated review table validates with `validate_step13_review_table`
- final review bundle validates with `validate_step13_review_bundle`
- Step 12 redundancy statuses are treated as evidence, not automatic decisions
- no forbidden output columns appear in review or source tables
- generated narrative uses the phrase `technical review material only`
- generated narrative uses the phrase `technical selection review material only`
- generated report paths stay under `reports/selection/`
- generated narrative avoids forbidden ranking, trading, alpha, backtest, and
  valuation language

## 10. Test Commands

Focused Step 13 tests:

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/selection
```

Step 11/12/13 integration tests:

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/test_step11_composite_schema.py tests/diagnostics tests/selection
```

## 11. Step 13 Completion Criteria

Step 13 is complete when:

- Step 13 documentation exists
- Step 13 review table schema is fixed
- Step 13 status vocabulary is fixed
- Step 13 forbidden column and language guardrails exist
- Step 13 review engine maps Step 11 metadata and Step 12 diagnostics into
  conservative technical review recommendations
- generated report boundary is fixed to `reports/selection/`
- focused contract tests pass
- Step 11/12/13 integration tests pass
- no ranking, composite score, backtest, trading, valuation, or financial-data
  scoring is implemented
