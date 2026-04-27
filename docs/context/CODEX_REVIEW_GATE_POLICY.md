# Codex Review Gate Policy

This policy turns review into a conditional project-local Codex skill gate. Run
the lightweight Review Gate first, then invoke a specialized skill only when the
gate selects a required review result.

Primary dispatcher: `.agents/skills/review_gate/SKILL.md`

Specialized on-demand skills:

- `.agents/skills/quant-subproject-audit-gate/SKILL.md`
- `.agents/skills/technical_review/SKILL.md`
- `.agents/skills/valuation_review/SKILL.md`
- `.agents/skills/review_mvp_specialist/SKILL.md`

Legacy context notes:

- `docs/context/review_gate.md`
- `docs/context/technical_review_skill.md`
- `docs/context/valuation_review_skill.md`

The gate is not a reviewer. If it starts making score, valuation, adoption,
backtest, or advice judgments, stop and route to the matching skill.

This is local/project-level review routing only. Do not use GitHub review
trigger wording, configure automatic GitHub PR review, or require GitHub PR
review usage.

## Trigger Matrix

| File path pattern or signal | Trigger reason | Required skill | Minimum validation profile |
| --- | --- | --- | --- |
| `Quant_mvp/docs/score_*.md`, `Quant_mvp/docs/family_map.md`, `docs/score_branch_policy.md` | Technical score definition, family, or branch semantics may change. | `.agents/skills/technical_review/SKILL.md` | focused doc grep plus relevant schema/config check if changed |
| `Quant_mvp/AGENTS.md` scope-check process, `docs/scope_audit_process.md`, or explicit Quant scope-watchdog/audit request | Subproject-wide audit routing or audit/validation separation may change. | `.agents/skills/quant-subproject-audit-gate/SKILL.md` | audit gate contract script plus focused forbidden-scope grep |
| `Quant_mvp/config/**`, `config/**` with score, normalization, branch, or weight keys | Technical scoring or adoption defaults may change. | `.agents/skills/technical_review/SKILL.md` or `full_review_required` if runtime behavior changes | affected config/schema tests or targeted parser check |
| `src/**`, `chart_mvp/src/**`, `tests/**` touching score, normalization, diagnostics, ranking, reports, or backtests | Runtime behavior or output semantics may change. | `full_review_required`; include `.agents/skills/review_mvp_specialist/SKILL.md` when code review policy triggers | affected unit tests plus focused integration check |
| `docs/contracts/**`, `docs/release/**`, `docs/releases/**`, `reports/validation/**` with ranking/composite/report/backtest semantics | Contract or generated-output boundary may change. | `.agents/skills/technical_review/SKILL.md` or `full_review_required` | contract/schema grep plus focused report validation |
| `docs/step14_adoption_synthesis.md`, adoption reports, composite membership docs, ranking handoff docs | Adoption, composite membership, or score-to-production handoff may change. | `.agents/skills/technical_review/SKILL.md` via `adoption_review_required` | focused diff review plus affected contract check |
| `.agents/skills/valuation_review/**`, `Quant_mvp/docs/valuation*.md`, `docs/architecture/*valuation*`, `reports/*valuation*` | Valuation/fundamental review boundary may change. | `.agents/skills/valuation_review/SKILL.md` | focused doc grep plus PIT field/policy check |
| Changed fields containing `PER`, `PBR`, `ROE`, `fundamental`, `valuation`, `filing_date`, `availability_date`, `quality`, `profitability`, `revision` | Fundamental data may be entering a forbidden path. | `.agents/skills/valuation_review/SKILL.md` or `full_review_required` | schema/field grep plus affected validation |
| Validation failure mentioning schema mismatch, missing required column, composite/ranking/report contract, PIT timing, generated-output boundary, or guardrail wording | Failure may indicate a boundary or contract breach. | `full_review_required`, with `review_mvp_required: true` when code/schema/integration risk is present | rerun smallest affected check after fix |
| Explicit user request for technical, valuation, adoption, full, specialist, or final review | User requested review. | requested skill, or `full_review_required` when ambiguous | validation requested by user or affected checks |
| Changed docs or generated reports include forbidden wording below | Investment-claim guardrail may be breached. | `full_review_required` | focused wording grep plus affected docs/report check |

## No-Review Matrix

Use `review_not_required` or `light_policy_check_only` when all changed files are
docs/context-only or repo-local skill-routing docs only and none of the trigger
matrix entries apply.

| File path pattern | Allowed result | Minimum validation profile |
| --- | --- | --- |
| `docs/context/*.md` routing, packet, or context-budget notes only | `review_not_required` or `light_policy_check_only` | targeted grep for gate vocabulary and forbidden wording, when relevant |
| `.agents/skills/**/SKILL.md` project-local skill playbook changes only | `light_policy_check_only` unless trigger semantics are weakened | targeted grep for frontmatter, gate vocabulary, on-demand wording, and GitHub review exclusions |
| `docs/context/domain/*.md` lightweight stubs that only point to canonical docs | `light_policy_check_only` | targeted path/link grep |
| README or local docs that mention workflow but do not change score, ranking, report, backtest, valuation, schema, or generated-output semantics | `light_policy_check_only` | focused wording grep |
| comments or typo fixes that do not change policy meaning or output claims | `review_not_required` | file existence or diff check |
| documentation adding reminders that valuation is unavailable or technical-only | `light_policy_check_only` | forbidden wording grep |

If a docs/context-only change adds, removes, or weakens a hard stop, promotes a
candidate score, changes roadmap verdicts, changes generated-output boundaries,
or introduces investment-claim language, it is not a no-review change.

## Forbidden Wording

Changed docs, generated reports, or user-facing outputs must not claim:

- proven alpha
- expected return
- buy/sell recommendation
- undervalued/cheap from price-only data
- target price

Also block close variants such as "guaranteed edge", "return forecast",
"recommend buy", "cheap because RSI is low", or "fair value target" unless a
separately approved valuation workflow has verified point-in-time fundamentals
and still avoids advice language.

## Light Policy Check

`light_policy_check_only` is a compact policy sanity check, not a specialist
review. It may confirm:

- the gate remained a dispatcher
- specialized skills are on-demand, not default
- `review_mvp` remains conditional on `review_mvp_required: true` or explicit
  master/root request
- changed files stay within allowed docs/context scope
- forbidden wording is listed as prohibited, not used as a claim
- local Git/network policy still prefers file checks, diffs, and local
  validation during work; `fetch`, `pull`, and `push` remain final-stage or
  root-explicit actions only

It must not evaluate technical usefulness, valuation support, adoption quality,
or backtest evidence.

## Korean Final-Report Format

Use this compact final report format after a Review Gate or review-skill task:

```text
[변경 파일]
- ...

[추가한 gate 구조]
- ...

[리뷰 스킬 호출 조건 요약]
- gate_result:
- next_skills:
- reason:

[실행한 검증]
- ...

[변경하지 않은 보호 영역]
- quant logic / score formulas / ranking / reports / backtests / valuation activation:

[남은 리스크]
- ...

[커밋/푸시 여부]
- ...

[Step 판정]
COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```

Keep the report focused on the current task. Do not repeat completed Step 1-20
history or paste validation logs.
