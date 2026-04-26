# GPT Context Quant

Status: GPT submission brief / routing aid, not an authority document.

## Confirmed Context

- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.
- The baseline is KOSPI200-only and technical-only.
- Completed Step 1-20 history, full validation logs, and full score catalog material are archive-only.

## Current Request

Use this brief only when the user explicitly asks for GPT-facing context.
Replace this section with the active GPT request before submission.

## Do Not Repeat

Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.

## What The Improved Codex Prompt Should Optimize

- Start from the current task, not the old roadmap.
- State at most 3 confirmed context facts before reasoning.
- Use file paths as routes instead of pasting long document bodies.
- Keep completed Step 1-20 outputs trusted unless conflict, regression,
  provenance, or release/freeze verification requires narrow lookup.
- Separate context facts from new judgment or recommendations.
- Keep implementation prompts narrow, testable, and aligned to allowed files.
- Make Codex report changed files, validation run, and remaining risk in Korean.

## Hard Boundaries

- Do not change quant logic, score formulas, ranking behavior, report behavior,
  backtest behavior, valuation/fundamental activation, or data ingestion.
- Do not implement KOSDAQ150, futures/options, Nasdaq, or new market data sources
  from a prompt-writing task.
- Do not introduce trading recommendation, proven-alpha, or expected-return
  language.
- Do not ask Codex to read archives or long history by default.
- Do not ask Codex to paste old validation logs or full score catalogs into GPT
  context.

## Prompt Pattern To Improve

```text
You are working in `master_mvp`.
Use the current baseline as trusted context.
Confirmed facts, max 3:
1. Step 20 is complete and MVP v0.1 is frozen.
2. The baseline is KOSPI200-only and technical-only.
3. Completed Step 1-20 history is archive-only.

Current task:
<write the task here>

Boundaries:
<write only task-relevant forbidden scope here>

Required output:
<write exact deliverables and validation expectations here>
```

## Ask GPT To Produce

- A shorter, stronger Codex prompt template for future tasks.
- A checklist for avoiding context bloat.
- Rules for when Codex may look up archive/history files.
- A Korean final-report shape for Codex.
- Any risky wording in the prompt that could cause scope creep.

## Route-Only References

- `docs/context/MVP_V0_1_BASELINE.md`
- task-specific files only
