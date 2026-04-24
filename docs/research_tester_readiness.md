# Research Tester Readiness

## Purpose

This document records the Step 9 Research Tester readiness checks and the
formula-contract lock used by the raw score implementation. It does not
authorize normalized scores, rankings, composite scores, production score files,
adoption decisions, or backtests.

## Gate Determinations

| question | determination | evidence | consequence |
|---|---|---|---|
| Is Step 5 Score Architect complete with explicit predefined score definitions? | Yes. Step 9 formula-contract follow-up has locked the previously ambiguous MVP raw variants. | `docs/roadmap_status.md`, `Quant_mvp/docs/score_definitions.md`, `Quant_mvp/docs/score_catalog.md`, `Quant_mvp/docs/family_map.md`, `Quant_mvp/config/scores.toml` | Step 9 raw Research Tester implementation may use the locked variants only; later normalization, ranking, composite, and backtest work remain gated. |
| Is Step 7 technical indicator layer complete or available? | Yes. The root Step 7 layer computes raw OHLCV-derived indicator dependencies only. | `src/indicators/technical.py`, `docs/step7_indicator_layer.md`, `tests/indicators/test_step7_indicators.py`, `docs/roadmap_status.md` | Step 9 raw score code may consume these dependencies. Normalized score output, ranking, composite, and backtest work remain gated. |
| Is Step 8 testing/normalization protocol complete or available? | Yes for protocol definition only. Root normalization remains a placeholder and no production normalization code is implemented. | `docs/step8_testing_normalization_protocol.md`, `src/normalize/__init__.py`, `Quant_mvp/AGENTS.md`, `Quant_mvp/config/thresholds.toml` | Step 9 raw score implementation may proceed under the protocol. No normalized score output, ranking, or Research Tester production export is generated in Step 9. |
| Is Step 6 processed data interface stable enough to consume? | Yes for canonical OHLCV handoff into Step 7. | `docs/data_schema.md`, `src/preprocess/daily_ohlcv.py`, `src/preprocess/schema_validator.py`, `tests/preprocess/test_step6_preprocess.py`, `tests/data_validation/test_schema_validation_contract.py`, `docs/roadmap_status.md` | Step 7 consumes the processed OHLCV interface. Step 9 consumes Step 7 indicator output only and keeps valuation/fundamental inputs blocked. |

## Prerequisite Review

| prerequisite | status | evidence_path | blocker_if_missing | notes |
|---|---|---|---|---|
| Step 5 score definitions | complete_with_step9_formula_locks | `docs/roadmap_status.md`; `Quant_mvp/docs/score_definitions.md`; `Quant_mvp/docs/score_catalog.md`; `Quant_mvp/docs/family_map.md` | Yes | Step 5 is marked complete and Step 9 follow-up has locked the MVP raw variants used by Research Tester code. |
| Step 6 processed data interface | complete_for_preprocessing_interface | `docs/data_schema.md`; `src/preprocess/daily_ohlcv.py`; `src/preprocess/schema_validator.py`; `tests/preprocess/test_step6_preprocess.py`; `tests/data_validation/test_schema_validation_contract.py`; `docs/roadmap_status.md` | Yes | Canonical `ticker`, `date`, OHLCV schema, validation checks, deterministic processed output, and preprocessing reports exist. Step 9 consumes the Step 7 indicator contract rather than raw financial/fundamental data. |
| Step 7 technical indicator layer | complete_for_raw_indicator_dependencies | `src/indicators/technical.py`; `docs/step7_indicator_layer.md`; `tests/indicators/test_step7_indicators.py`; `config/windows.toml`; `docs/roadmap_status.md` | Yes | Root indicator layer emits OHLCV columns, warmup metadata, and raw indicator dependencies only. It does not emit score, rank, ranking, composite, alpha, or trading-signal columns. |
| Step 8 testing/normalization protocol | complete_for_protocol_only | `docs/step8_testing_normalization_protocol.md`; `src/normalize/__init__.py`; `Quant_mvp/AGENTS.md`; `Quant_mvp/config/thresholds.toml` | Yes | Protocol now defines toy tests, missing-data rules, clipping, percentile behavior, diagnostics, and deviation logging. It does not implement score formulas, normalized production output, ranking, composite, or backtest. |
| config/scores.toml | guardrail_only | `config/scores.toml`; `Quant_mvp/config/scores.toml` | Yes | Root config keeps runtime scoring, composite scoring, ranking, backtesting, valuation scoring, and fundamental scoring disabled. Quant config lists Step 5 candidates for registry visibility only with `runtime_enabled = false`. |
| config/windows.toml | active_for_step7_raw_indicators_only | `config/windows.toml`; `docs/step7_indicator_layer.md` | Yes | Root windows drive raw Step 7 indicator dependencies only. They do not activate score windows, ranking thresholds, composites, or backtests. |
| config/thresholds.toml | validation_and_diagnostic_thresholds_only | `config/thresholds.toml`; `Quant_mvp/config/thresholds.toml` | Yes | Thresholds support validation and future diagnostics. They do not activate alpha thresholds, ranking thresholds, or adoption decisions. |
| config/weights.toml | inactive_for_step_9_readiness | `config/weights.toml`; `Quant_mvp/config/weights.toml` | Yes | Root weights are inactive. Quant family weights are provisional and must not be used to create composite scores during readiness work. |

## Expected Research Tester Input Schema

Future Step 9 inputs should come only from the completed Step 6/7 pipeline.

| field | required | source step | notes |
|---|---|---|---|
| `ticker` | yes | Step 6 | Six-character string, leading zeros preserved. |
| `date` | yes | Step 6 | Parseable scoring date with no future-data leakage. |
| `open` | yes | Step 6 | Validated numeric OHLCV field. |
| `high` | yes | Step 6 | Validated numeric OHLCV field. |
| `low` | yes | Step 6 | Validated numeric OHLCV field. |
| `close` | yes | Step 6 | Validated numeric OHLCV field. |
| `volume` | yes | Step 6 | Validated numeric OHLCV field. |
| `data_quality_flag` | yes | Step 6 or Step 8 | Must identify missing, invalid, stale, duplicate, or insufficient-history rows. |
| `warmup_state` | yes | Step 7 | Must distinguish `ready`, `warmup`, and `insufficient_history` coverage. |
| indicator columns | per score | Step 7 | Required columns must be named before score code is written. |

## Candidate Score Implementation Readiness

Step 8 remained protocol-only. Step 9 has since opened and implemented the
locked MVP raw variants below. These rows do not authorize normalized output,
ranking, composite scoring, adoption decisions, or backtests.

| score_name | score_family | status | required_inputs | required_indicators | ambiguity | action |
|---|---|---|---|---|---|---|
| `short_term_overreaction` | `mean_reversion` | implemented_for_research | `ticker`, `date`, `close` | `return_Nd` or close-derived trailing return | Locked variant is `-return_N`, with `N = [returns].short`. | Keep as raw technical-only output until Step 10 normalization. |
| `atr_adjusted_oversold_distance` | `mean_reversion` | implemented_for_research | `ticker`, `date`, `close` | ATR and Bollinger middle band | Locked anchor is `bollinger_mid_N`; raw form is `(bollinger_mid_N - close) / ATR_M`. | Keep as raw technical-only output until Step 10 normalization. |
| `donchian_breakout_distance` | `breakout` | implemented_for_research | `ticker`, `date`, `high`, `close` | prior rolling high | Implemented ratio form with Step 7 prior-bar convention. | Keep as raw technical-only output until Step 10 normalization. |
| `bollinger_width_squeeze` | `squeeze_expansion` | implemented_for_research | `ticker`, `date`, `close` | Bollinger band width | Implemented as negative configured Bollinger width; setup/regime context only. | Keep as raw context output until Step 10 normalization/review. |
| `cmf_confirmation` | `flow` | implemented_for_research | `ticker`, `date`, `high`, `low`, `close`, `volume` | Chaikin Money Flow | Implemented as standalone configured CMF value. | Keep as raw confirmation output until Step 10 normalization/review. |
| `rsi_price_divergence` | `oscillator_divergence` | implemented_for_research | `ticker`, `date`, `close` | RSI; trailing price change; trailing RSI change | Locked deterministic proxy: `max(0, -return_N) * max(0, RSI_t - RSI_{t-N})`. | Keep complex swing labeling out of scope. |
| `realized_vol_percentile` | `volatility_regime` | implemented_for_research | `ticker`, `date`, `close` | daily returns; rolling realized volatility | Implemented as ticker-local trailing percentile of realized volatility. | Diagnostic context only, not alpha. |
| `efficiency_ratio_trend` | `trend_efficiency` | implemented_for_research | `ticker`, `date`, `close` | endpoint change; efficiency ratio | Implemented as signed trend efficiency. | Keep as raw technical-only output until Step 10 normalization. |
| valuation or fundamental score candidates | valuation | valuation_deferred | point-in-time fundamentals, if a later branch opens | none for current technical Step 9 | Current workflow keeps financial and fundamental data outside Step 9. | Do not implement or include in technical or final composites. Keep separated until an explicit valuation branch is opened. |

## Required Indicator Dependencies

| dependency | needed_by | current availability | Step 9 readiness note |
|---|---|---|---|
| trailing returns | `short_term_overreaction`, `rsi_price_divergence`, `efficiency_ratio_trend` | Present as `return_1d`, `return_5d`, `return_20d`, `return_60d`, `return_120d`. | Step 9 must apply Step 8 missingness and normalization behavior. |
| ATR | `atr_adjusted_oversold_distance`, optional `donchian_breakout_distance` | Present as `atr_14`. | Step 9 must apply Step 8 zero/invalid handling and normalization behavior. |
| moving average or reference price | `atr_adjusted_oversold_distance`, `bollinger_width_squeeze` | Bollinger mid is present as `bollinger_mid_20`. | Step 9 locks the oversold-distance anchor to the configured Bollinger middle band. |
| prior Donchian rolling high | `donchian_breakout_distance` | Present as `donchian_high_prior_20`. | Prior-bar convention is available; Step 9 must apply Step 8 downstream missingness behavior. |
| Bollinger band width | `bollinger_width_squeeze` | Present as `bollinger_width_20`. | Step 9 must apply Step 8 percentile or other normalization context. |
| CMF | `cmf_confirmation` | Present as `cmf_20`. | Step 9 must apply Step 8 missingness and normalization behavior. |
| RSI | `rsi_price_divergence` | Present as `rsi_14`. | Divergence pairing is locked to the configured short return window for Step 9 raw testing. |
| rolling realized volatility | `realized_vol_percentile` | Present as `realized_vol_20`. | Step 9 must apply Step 8 percentile context, clipping, and diagnostic handling. |
| efficiency ratio | `efficiency_ratio_trend` | Present as `efficiency_ratio_20`. | Step 9 locks the signed trend-efficiency role for raw testing. |

## Normalization Dependencies

Step 8 defines the protocol. Step 10 must implement the config/code behavior
before any normalized Research Tester output is generated:

| dependency | required decision |
|---|---|
| time-series normalization | Rolling window, minimum observations, tie handling, clipping, and 0-100 mapping. |
| cross-sectional normalization | Same-date universe membership, minimum cross-section count, tie handling, clipping, and missing-data behavior. |
| robust z-score | Median/MAD or equivalent definition, fallback for zero dispersion, and clipping limits. |
| winsorization | Whether clipping occurs before or after raw score construction, with configured lower and upper percentiles. |
| warmup handling | Explicit `warmup_state` states and whether insufficient history yields missing, neutral, or blocked output. |
| coverage handling | Explicit `coverage_status` states and neutral shrinkage rules if later allowed. |
| implementation deviation log | Required note when implementation differs from `Quant_mvp/docs/score_definitions.md`. |

## Config Requirements For Step 9

- `config/scores.toml` must remain the runtime guardrail; root runtime scoring,
  ranking, composite scoring, backtesting, and valuation scoring stay disabled.
- `Quant_mvp/config/scores.toml` may expose Step 9 raw Research Tester metadata,
  but `runtime_enabled = false` still means no production score computation is
  allowed.
- Step 9 score code may only consume candidates present in
  `Quant_mvp/docs/score_definitions.md` or a versioned Score Architect update.
- Formula windows must be read from config after the formula variant is locked.
- Diagnostic thresholds may be read from config, but diagnostics do not adopt,
  rank, or backtest scores.
- `config/weights.toml` must not be used to create `technical_composite_score`
  or `final_composite_score` during readiness work.
- Financial and fundamental sources must remain excluded from Step 9 technical
  readiness.

## Diagnostics Checklist

Future Step 9 diagnostics must include:

- NaN ratio
- warmup coverage
- missing-data behavior
- outlier sensitivity
- rank stability
- turnover proxy
- score correlation matrix
- family coverage summary
- data-quality flags
- implementation deviation log

Diagnostics are quality-control outputs. They are not alpha signals, adoption
decisions, rankings, valuation review, or backtest results.

## Hard Stop Notes

- Research Tester may only implement predefined scores.
- Ambiguous formulas were locked through explicit Step 9 formula-contract
  follow-up rather than guessed from test results.
- Diagnostics are not alpha signals.
- Backtest is not allowed before Step 17.
- Latest ranking output is not allowed before Step 15.
- Financial/fundamental data remains valuation_deferred.
