# v0.2 Candidate ML Score Contract

## Scope

`prob_up_1d_candidate` is a post-MVP v0.2 candidate-only modeled probability
field. It is allowed only as a sidecar research artifact and must not replace,
redefine, weight, or feed `technical_composite_score`, `final_composite_score`,
production rank, production report order, GUI order, or recommendation language.

Confirmed baseline:

- MVP v0.1 remains frozen and KOSPI200 technical-only.
- v0.2 candidate ML output is not production ranking activation.
- Backtest, evaluation, diagnostics, and realized outcomes must not feed
  upstream scoring, ranking, reports, or model features.

## Field Definition

| Field | Required | Meaning |
| --- | --- | --- |
| `ticker` | yes | KOSPI200 constituent ticker identifier used by the candidate pipeline. |
| `date` | yes | Candidate row date, preserved as an identity column. |
| `decision_time` | yes | Time at which all candidate features are considered known. Features must be available at or before this time. |
| `execution_time` | yes | Candidate timing field for the simulated next actionable time after the decision point. In the current daily artifact this is recorded at daily granularity and must not imply execution guidance. |
| `label_time` | training/evaluation metadata | Time represented by `adjusted_close[t+1]`. It may be missing for the latest as-of-date candidate row. |
| `label_availability_time` | training/evaluation metadata | Time when the next-day label can be known. It may be missing for unlabeled current rows. |
| `prob_up_1d_candidate` | yes | Candidate-only probability that `adjusted_close[t+1] > adjusted_close[t]`, estimated using features available at `decision_time`. Higher means a higher modeled probability, not a recommendation. |
| `up_1d_label` | label table only | Integer label where `1` means `adjusted_close[t+1] > adjusted_close[t]`. Must not appear in candidate inference feature rows. |
| `prob_up_1d_candidate_sidecar_rank` | sidecar only | Optional sidecar rank sorted by `prob_up_1d_candidate` descending, then `ticker` ascending for ties. |
| `prob_up_1d_candidate_status` | yes | Candidate output status such as `candidate_probability` or `missing_features`. |
| `prob_up_1d_candidate_sample_role` | yes | Training/evaluation/inference role metadata. The latest unlabeled row remains `candidate_unlabeled`. |

## Gate 1 Availability Preconditions

- The label definition remains `adjusted_close[t+1] > adjusted_close[t]`.
- The existing repo config has optional `adj_close` OHLCV support in
  `Quant_mvp/config/data.toml`.
- `adj_close` is the only approved alias for the candidate ML label source and
  must be normalized to canonical `adjusted_close` before label construction.
- Gate 1 therefore treats canonical adjusted-close availability as
  `CONFIRMED_EXISTING_OPTIONAL_ALIAS_ADJ_CLOSE`.
- If neither `adjusted_close` nor `adj_close` is present in the candidate input,
  label construction remains blocked.
- It must not reinterpret `close` as adjusted close and must not add new
  market-data ingestion to satisfy this gate.

## Timing And No-Lookahead Rules

- Feature rows must be built from data available at or before `decision_time`.
- `decision_time` is the point where all candidate features are frozen.
- `execution_time` is the next simulated actionable timestamp after
  `decision_time`; it is metadata only and must not imply execution guidance.
- `label_time` is the timestamp represented by `adjusted_close[t+1]`.
- `label_availability_time` is when the next-day label can be known, and for
  labeled rows it must be after `decision_time`.
- The next-day label uses `adjusted_close[t+1] > adjusted_close[t]` and is
  valid only after `t+1` close is available.
- Rows whose next-day label is unavailable must be excluded from
  training/evaluation labels, not filled optimistically.
- `up_1d_label`, `label_time`, realized returns, evaluation outcomes, and
  backtest metrics must never be used as inference-time features.
- The inference artifact may contain `prob_up_1d_candidate` and timing metadata,
  but not future labels.

## Allowed Inputs

Allowed feature families are candidate-only and must remain explainable. The
implementation gate uses default-deny: every feature must trace to the
allowlist in `Quant_mvp/config/v0_2_candidate_ml_score.toml` or to this
contract before implementation begins.

- pre-composite technical indicator or component columns that trace back to
  allowed OHLCV-derived sources
- the current feature input path is
  `src.scores.prob_up_1d_candidate.build_prob_up_1d_feature_input_frame`
- the current feature source is `step9_raw_technical_old_scores`, restricted to
  `[feature_allowlist].old_score_feature_columns`
- daily OHLCV-derived indicators available at or before `decision_time`
- conservative missing-data, coverage, and warmup indicators
- static non-fundamental identifiers needed for joins, when they do not encode
  future outcomes

Current old-score feature allowlist:

- `short_term_overreaction_raw`
- `atr_adjusted_oversold_distance_raw`
- `rsi_price_divergence_raw`
- `realized_vol_percentile_raw`
- `donchian_breakout_distance_raw`
- `bollinger_width_squeeze_raw`
- `cmf_confirmation_raw`
- `efficiency_ratio_trend_raw`

Excluded even when present in a table:

- `technical_composite_score`
- `final_composite_score`
- production `rank`
- generated report, generated sidecar, cache, chart, backtest, evaluation, and
  realized-outcome fields

## Forbidden Inputs

The candidate pipeline must not use:

- valuation, fundamental, PER, PBR, ROE, accounting, filing, or point-in-time
  financial data
- realized future returns or future labels as features
- backtest metrics, evaluation diagnostics, paper backtest results, adoption
  decisions, or review verdicts as features
- external vendor assumptions, live ingestion changes, KOSDAQ, derivatives,
  Nasdaq, overseas markets, or multi-universe activation

## Ranking Boundary

`prob_up_1d_candidate` may produce a sidecar candidate ranking only:

```text
sort: prob_up_1d_candidate desc, ticker asc
artifact_type: sidecar_candidate_only
production_rank_activation: false
```

This sidecar rank is not the production rank and must not be merged into
`technical_composite_score`, `final_composite_score`, or production reports.

## Selection Packet Boundary

The candidate sidecar selection packet is a sorted candidate probability
artifact generated by:

```text
src.scores.prob_up_1d_candidate.build_prob_up_1d_candidate_selection_packet
```

It is exported under:

```text
reports/v0_2_predictive_probability/candidate_sidecar/selection_packet/
```

The only allowed packet sort is:

```text
prob_up_1d_candidate desc, ticker asc
```

Required packet fields include ticker, `as_of_date`, `decision_time`,
`prob_up_1d_candidate`, model metadata, feature schema metadata,
`adjusted_close` canonical source metadata, and data-quality or coverage
fields.

The packet must not include production rank fields, must not expose
`final_composite_score`, must not feed reports, and must not change production
output order.

## Walk-Forward Evaluation Boundary

The candidate model quality diagnostic uses a time-ordered expanding-window
evaluation path:

```text
src.scores.prob_up_1d_candidate.evaluate_prob_up_1d_candidate_walk_forward
```

Fold definition:

- train period: all configured label-available dates before the evaluation
  period
- evaluation period: the next configured date period after the train window
- step period: configured date increment for the next fold
- inference rows remain separate from training and evaluation rows

Required metrics:

- `brier_score`
- `log_loss`
- `calibration_error`
- `coverage`
- `nan_missing_rate`
- `feature_stability_mean_abs_shift`

Generated evaluation artifacts live under:

```text
reports/v0_2_predictive_probability/evaluation/
```

These artifacts are candidate-only diagnostics. They do not activate production
ranking, replace composite fields, change reports, or provide model-selection
feedback from return-performance fields.

## Evaluation-Only Backtest Approval Boundary

An approval packet for a possible evaluation-only backtest connection is stored
at:

```text
Quant_mvp/docs/v0_2_candidate_ml_evaluation_backtest_approval_packet.md
```

This packet is now root-approved for diagnostic-only implementation. It does
not authorize production ranking, report exposure, composite replacement, or
feedback into model or feature selection.

Allowed evaluation-only scope:

- read `prob_up_1d_candidate` candidate artifacts as evaluation inputs
- validate candidate artifact schema and timing fields before evaluation
- write generated diagnostic artifacts only

Forbidden scope:

- feeding backtest diagnostics into model training or model selection
- feeding diagnostics into feature selection, score weights, ranking rules, or
  composite definitions
- exposing candidate artifacts through production reports
- replacing `technical_composite_score` or `final_composite_score`

The implemented diagnostic adapter is:

```text
src.scores.prob_up_1d_candidate.run_prob_up_1d_evaluation_only_backtest
```

## Production Activation Root Approval Boundary

A root approval review packet for possible future production activation review
is stored at:

```text
Quant_mvp/docs/v0_2_candidate_ml_production_activation_root_approval_packet.md
```

This packet is decision material only. It does not activate production ranking,
replace `final_composite_score`, change reports, or convert the candidate field
into order-action strategy behavior.

Required review material before any later activation decision:

- current candidate-only artifact summary
- walk-forward model evaluation summary
- leakage and no-lookahead audit result
- adjusted-close canonical source evidence
- sidecar packet schema and sorting validation
- evaluation-only backtest approval and diagnostic boundary evidence
- required additional gates
- disable and rollback plan

Current state remains:

- `approval_review_ready_not_decided`
- `activation_executed = false`
- `root_approval_required = true`
- `candidate_only_state_preserved = true`
- `evaluation_only_backtest_approved = true`

## Reporting Language

Allowed wording:

- candidate probability
- modeled probability
- sidecar candidate ranking
- research/evaluation-only candidate artifact

Forbidden wording:

- direct trading recommendation wording
- forecasted-return, performance-proof, or robustness-overclaim wording
- valuation support or cheap/expensive based on price-only evidence
- production ranking replacement

## Validation Expectations

Validation should check:

- required output schema and candidate-only naming
- no feature column contains labels, future returns, backtest outputs, or
  evaluation outcomes
- required timing fields: `decision_time`, `execution_time`, `label_time`, and
  `label_availability_time`
- label rows keep labels separated from inference feature rows
- train, evaluation, and inference paths use the same allowlisted feature schema
- missing allowlisted feature values remain `missing_features` and do not
  fabricate `prob_up_1d_candidate`
- candidate sidecar sorting is deterministic
- production composite and ranking fields remain unchanged
