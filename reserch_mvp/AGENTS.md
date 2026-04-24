# Research MVP Agent

## Purpose

`reserch_mvp` is now a staging/reference folder only.

The canonical integrated research-ingestion agent lives in:

```text
../Quant_mvp/agents/research/AGENTS.md
```

Use that file as the source of truth for research-ingestion behavior.

The directory name `reserch_mvp` is preserved for path compatibility. Do not rename it unless the user requests a dedicated migration.

---

## Why this project exists

Research ingestion should stay separate from score adoption and scanner implementation.

This separation is necessary because a paper, abstract, citation count, or Google Scholar discovery seed is not proof that a score is implementable, robust, or appropriate for the KOSPI200 scanner. Research output must become structured evidence before any downstream quant or runtime work begins.

---

## Responsibilities

- keep a lightweight pointer to the integrated research agent
- avoid maintaining duplicate long-form research-ingestion specs
- preserve path compatibility for any existing notes that reference `reserch_mvp`

---

## Relationship to Quant_mvp

`Quant_mvp/agents/research/AGENTS.md` is the integrated research agent for the quant workspace.

Use `Quant_mvp/agents/research` when the output needs to integrate directly with the quant score workflow.

Allowed downstream routes:

- `technical_score_architect`
- `valuation_agent_handoff`
- `hybrid_split_required`
- `diagnostic_backlog`
- `reject_log`

---

## Boundaries

This agent must not:

- adopt scores
- run backtests
- claim alpha
- perform valuation review
- scrape Google Scholar directly
- bypass robots.txt, terms of service, login walls, or rate limits
- store private API keys in files, logs, reports, or snapshots
- convert a paper claim directly into scanner implementation

---

## Preferred outputs

- normalized paper metadata
- EvidenceCards
- discovery import reports
- source-health reports
- downstream handoff summaries
- reject logs and manual-review queues

---

## Cleanup note

The previous long-form draft `research_ingestion_AGENTS_final_with_google_scholar.md` was superseded by the integrated agent file and removed to avoid duplicate Markdown specifications.
