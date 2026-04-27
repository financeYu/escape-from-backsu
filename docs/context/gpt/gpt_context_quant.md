# GPT Context Quant

Status: routing aid, not an authority document.
Generated only after an explicit user request with a non-empty request string.

## Confirmed Context

- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.
- MVP v0.1 is KOSPI200-only and technical-only.
- Valuation/fundamental scoring, KOSDAQ150, futures/options, Nasdaq, and trading recommendation work remain outside the baseline unless a later routed task opens them.

## Current Request

- Task: gpt 폴더에 있는 두 GPT-facing context 파일을 모두 갱신하고, 명시 요청이 있을 때만 갱신되도록 생성 guard를 점검/수정
- Decision needed: focus on the current request, not old roadmap narration.

## Do Not Repeat

Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.

## Boundaries

- No quant logic, score formula, ranking behavior, report behavior, backtest behavior, valuation/fundamental activation, data ingestion, or trading language changes unless explicitly requested and allowed.
- Do not implement KOSDAQ150, futures/options, or Nasdaq from this brief.
- Completed Step 1-20 history is archive-only. Full validation logs are archive-only. Full score catalog is not default context.
- Internal generation rules, budget policy, and routing index are not GPT prompt inputs.

## Route-Only References

- `docs/context/MVP_V0_1_BASELINE.md` - FOUND
- add task-specific file paths only when needed

## Missing Referenced Files

- none
