# v0.5 Pre-Entry Gap Assessment

Status: v0.5 entry readiness assessment after v0.4.2 evidence coverage work.
Assessment date: 2026-05-08.
Scope: personal decision support readiness, not live trading or production
activation.

## Current v0.4.2 Baseline

The v0.4.2 evidence coverage work improves the input surface for selector
diagnostics, but the current artifacts still remain review-only:

- total candidate rows: 698
- candidate-level metric rows: 62
- training-eligible rows: 62
- positive rows: 25
- negative rows: 37
- null-label rows: 636
- missing EvaluationEvidence rows: 616
- needs-more-evidence rows: 20

The v0.4.2 fix pass also corrected three readiness blockers before v0.5 entry:

- coverage cohort reruns now reproduce the same selected packet set
- options-sourced candidates are excluded from the KOSPI/KOSPI200 equity
  coverage cohort
- `needs_more_evidence` rows no longer report actual metric summary
  availability

## Remaining Gaps Before Decision Support

These gaps block any direct trading advice interpretation:

- Most candidates still have no candidate-level EvaluationEvidence.
- `needs_more_evidence` packets are gap records, not recorded performance
  evidence.
- The selector score artifacts are diagnostic and review-prioritization-only.
- There is no approved current-condition snapshot that maps a strategy
  candidate to today's eligible KOSPI200 symbols.
- There is no portfolio context, cash constraint, position sizing rule,
  stop-loss rule, or exposure budget.
- There is no execution model for liquidity, spread, partial fills, or order
  timing.
- Walk-forward and out-of-sample coverage is still limited.
- v0.4.2 full validation was interrupted after focused checks and artifact
  sanity checks; completion still requires the normal pytest, diff, and gate
  validator pass.

## v0.5 Entry Decision

v0.5 may start only as a personal decision support contract route. It may
organize existing evidence, current-condition checks from approved local
KOSPI200 lanes, risk flags, and review checklists for private human judgment.

v0.5 must not convert selector scores or EvaluationEvidence into:

- buy, sell, hold, rebalance, or move-to-cash instructions
- order generation
- position sizing commands
- expected-return or profit claims
- live brokerage or production activation
- new market-data ingestion
- universe expansion beyond the approved KOSPI/KOSPI200 boundary

## Highest-Priority Next Task

Create a v0.5 `PersonalDecisionSupportPacket` contract that consumes v0.3 and
v0.4 artifacts read-only, records evidence and risk flags, and blocks runtime
action language.
