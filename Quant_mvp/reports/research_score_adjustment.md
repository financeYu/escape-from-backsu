# Research-Informed Score Adjustment

## Scope

Branch: `quant/post-mvp-research-score-adjust`

Status: MVP v0.1 pre-freeze candidate-governance support only. This is not
Step 21 entry, runtime score activation, ranking generation, or post-freeze
roadmap work.

This is a Quant-side candidate governance adjustment. It does not activate
runtime scoring, ranking generation, valuation/fundamental scoring, or backtest
feedback.

## Research Material Consulted

- `Quant_mvp/research_mvp/reports/research_ingestion/step5_candidate_evidence.md`
- `Quant_mvp/research_mvp/reports/research_ingestion/handoff_summary.md`
- `Quant_mvp/reports/technical_review/pretest_screening.md`

## Adjustment Summary

| Candidate or family | Adjustment | Reason |
| --- | --- | --- |
| `mean_reversion` | provisional family weight `1.00 -> 1.10` | Korea-specific intake is more supportive of short-term reversal than plain momentum |
| `short_term_overreaction` | high research priority | simplest reversal baseline and lowest role confusion |
| `atr_adjusted_oversold_distance` | secondary redundancy check | useful scaling idea, but overlaps strongly with the simple reversal baseline |
| `breakout` | provisional family weight `1.00 -> 0.90` | still useful, but capped because trend, breakout, 52-week-high, and momentum variants are redundant |
| `bollinger_width_squeeze` | provisional family weight `0.75 -> 0.50` | compression is setup/regime context, not direction by itself |
| `flow` | provisional family weight `0.75 -> 0.50` | volume participation is safer as a filter/context until linked role is explicit |
| `oscillator_divergence` | provisional family weight `0.75 -> 0.25` | pattern-like logic carries parameter-mining and redundancy risk |
| `efficiency_ratio_trend` | unchanged at `0.75` | kept as the limited trend-quality representative instead of adding more momentum variants |

## Guardrail Result

- No financial or fundamental data was added.
- `technical_composite_score` and `final_composite_score` semantics were not
  changed.
- Runtime score activation remains disabled in Quant candidate config.
- Paper-reported backtests were not used as optimization targets.
- No buy/sell/hold, proven-alpha, or valuation language was introduced.

## Remaining Risks

- These weights remain provisional candidate governance values while runtime
  activation is disabled.
- Any future runtime promotion needs an explicit post-freeze Step, focused
  diagnostics, redundancy checks, and master-up review.
- KOSPI200 large-cap behavior may differ from broader Korean stock evidence.
