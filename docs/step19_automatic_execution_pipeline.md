# Step 19 Automatic Execution Pipeline

## Purpose

Step 19 adds a deterministic local orchestration layer for already approved
project stages. It sequences existing preprocessing, indicator, raw score,
normalization, adoption/composite context, latest ranking, detail report,
conservative backtest, and candidate-only valuation/fundamental boundary stages
without redefining their formulas or semantics.

This Step is pipeline wiring. It is not a new score, not a new ranking model,
not a report redesign, not a backtest redesign, and not Step 20 final
validation.

## Pipeline Stages

The canonical stage order is:

1. `preflight`
2. `context_check`
3. `data_preprocess`
4. `technical_indicators`
5. `raw_scores`
6. `normalized_scores`
7. `composite_or_adoption_context`
8. `latest_ranking`
9. `security_detail_reports`
10. `conservative_backtest_optional`
11. `candidate_valuation_boundary_check_optional`
12. `output_validation`
13. `final_summary`

The optional backtest and valuation candidate stages are disabled by default in
`config/step19_pipeline.toml`. They can be selected only as contract-validation
stages unless explicit local inputs and a later approved workflow provide safe
execution wiring.

## Run Modes

- `dry_run`: default. Builds a plan and validation summary. It writes no
  production output.
- `validate_only`: validates selected stage contracts and boundaries without
  invoking domain execution.
- `run_allowed_stages`: marks selected stage contracts as completed only after
  local contract checks pass. The Step 19 layer still does not redefine or
  mutate domain semantics.

CLI:

```powershell
python scripts/run_step19_pipeline.py
python scripts/run_step19_pipeline.py --stage ranking
python scripts/run_step19_pipeline.py --mode validate_only --stage validation_only
python scripts/run_step19_pipeline.py --write-summary --summary-output reports/pipeline/generated/step19_pipeline_summary.json
```

## Structured Summary

The run summary contains:

- selected and skipped stages
- stage status, input refs, output refs, warnings, errors, and boundary notes
- validation status
- forbidden-scope check result
- timestamp
- git commit when available
- no-semantics-changed notice

The summary must not include secrets, large data dumps, runtime market cache
content, or generated chart/report bodies.

## Boundary Preservation

Step 19 preserves the following boundaries:

- Step 15 remains the latest ranking source. Step 19 does not re-rank
  securities.
- Step 16 detail reports read Step 15 ranking context as read-only display
  context. Step 19 does not change report semantics.
- Step 17 remains evaluation-only. Step 17 realized or evaluation returns do
  not feed upstream scores, adoption states, ranking, or reports.
- Step 18 valuation/fundamental records remain candidate-only sidecar data.
  They do not enter `technical_composite_score`, `final_composite_score`,
  latest ranking, or Step 17 backtest inputs.

## Guardrails

`src/validation/step19_pipeline_guardrails.py` rejects:

- active valuation/fundamental scoring activation
- valuation/fundamental fields in protected score or ranking outputs
- future, forward, expected, realized, or evaluation return feedback into
  upstream scoring/ranking/report inputs
- Step 16 report output feedback into upstream scoring or ranking
- generated output paths under data/cache/runtime output areas
- network or secret requirements
- Step 20 completion claims
- trading recommendation or overstated performance language

## Validation

Focused validation:

```powershell
python -m pytest -q tests/pipeline tests/validation/test_step19_pipeline_guardrails.py
```

Broader relevant validation:

```powershell
python -m pytest -q tests/scanner tests/reports tests/backtest tests/validation
```

Full validation:

```powershell
python -m pytest -q
```

If the environment uses the established no-cache-provider convention:

```powershell
python -m pytest -q -p no:cacheprovider
```

## Step 20 Boundary

Step 19 prepares deterministic automation and validation summaries. Step 20 is
still a separate final done-validation stage and is not implemented or completed
by this work.
