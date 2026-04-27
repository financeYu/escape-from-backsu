# v0.2 Candidate ML Score Contract

## Scope

`prob_up_1d_candidate` is a post-MVP v0.2 candidate-only modeled probability
field. It is allowed only as a sidecar research artifact and must not replace,
redefine, weight, or feed `technical_composite_score`, `final_composite_score`,
production rank, production report order, GUI order, or trading language.

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

## Timing And No-Lookahead Rules

- Feature rows must be built from data available at or before `decision_time`.
- The next-day label uses `adjusted_close[t+1] > adjusted_close[t]` and is
  valid only after `t+1` close is available.
- Rows whose next-day label is unavailable must be excluded from
  training/evaluation labels, not filled optimistically.
- `up_1d_label`, `label_time`, realized returns, evaluation outcomes, and
  backtest metrics must never be used as inference-time features.
- The inference artifact may contain `prob_up_1d_candidate` and timing metadata,
  but not future labels.

## Allowed Inputs

Allowed feature families are candidate-only and must remain explainable:

- existing technical score columns as optional feature inputs
- daily OHLCV-derived indicators available at or before `decision_time`
- conservative missing-data, coverage, and warmup indicators
- static non-fundamental identifiers needed for joins, when they do not encode
  future outcomes

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

## Reporting Language

Allowed wording:

- candidate probability
- modeled probability
- sidecar candidate ranking
- research/evaluation-only candidate artifact

Forbidden wording:

- buy, sell, hold, trading recommendation
- expected-return, proven-alpha, robust-alpha
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
- candidate sidecar sorting is deterministic
- production composite and ranking fields remain unchanged
