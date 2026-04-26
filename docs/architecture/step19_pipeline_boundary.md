# Step 19 Pipeline Boundary

## Role

Step 19 owns orchestration contracts, run manifests, dry-run behavior, and
pipeline-specific guardrails. It does not own score formulas, normalization
policy, composite semantics, ranking semantics, report semantics, backtest
evaluation semantics, or valuation/fundamental scoring activation.

## Allowed Data Flow

```text
explicit local inputs
-> preprocessing contract
-> technical indicator contract
-> raw technical score contract
-> normalization contract
-> technical-only adoption/composite context
-> Step 15 latest ranking snapshot
-> Step 16 technical-only detail report context
-> Step 17 conservative evaluation-only backtest output
-> Step 18 candidate-only valuation boundary check
-> Step 19 structured summary
```

The Step 17 and Step 18 stages remain downstream or sidecar checks. Their
outputs are not score, ranking, or report inputs.

## Forbidden Data Flow

```text
Step 17 returns or evaluation metrics
-> score formulas
-> normalization
-> adoption states
-> Step 15 ranking
-> Step 16 report score context
```

```text
Step 18 valuation/fundamental candidate records
-> technical_composite_score
-> final_composite_score
-> latest ranking
-> Step 17 backtest selection input
```

```text
Step 16 generated reports
-> raw scores
-> normalization
-> adoption context
-> latest ranking
```

## Output Boundary

Source-controlled Step 19 files are limited to docs, config, source code, tests,
and this boundary documentation. Runtime summaries belong under
`reports/pipeline/generated/` and are not committed by default.

Generated security, backtest, and valuation candidate artifacts remain in their
own generated report roots. Market data caches, chart outputs, scan outputs,
and local report bodies are not Step 19 source-controlled outputs.

## Failure Behavior

The pipeline fails closed:

- missing required input paths become `blocked`
- disabled optional stages become `skipped`
- boundary violations raise validation errors
- partial execution does not mark blocked stages successful
- dry-run writes no production output

## Existing Module References

Step 19 records the existing module references for traceability:

- `src.preprocess.daily_ohlcv`
- `src.indicators.technical`
- `src.scores.technical_scores`
- `src.scores.normalization_timeseries`
- `src.scores.normalization_cross_sectional`
- `src.selection.adoption_synthesis`
- `src.scanner.latest_ranking`
- `src.reports.security_detail_report`
- `src.backtest.engine`
- `src.valuation.validation`

Those modules remain owners of their domain behavior. Step 19 validates the
contract sequence and writes a compact manifest/summary only when explicitly
requested.
