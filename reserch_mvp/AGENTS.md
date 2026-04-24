# Research MVP Agent

## Purpose

`reserch_mvp` holds the research-ingestion specification for upstream evidence collection.

The current detailed specification lives in:

```text
research_ingestion_AGENTS_final_with_google_scholar.md
```

Read the workspace root `AGENTS.md` first. Then use this file as the project-level entry point and the detailed specification above as the long-form operating manual.

The directory name `reserch_mvp` is preserved for path compatibility. Do not rename it unless the user requests a dedicated migration.

---

## Why this project exists

Research ingestion should stay separate from score adoption and scanner implementation.

This separation is necessary because a paper, abstract, citation count, or Google Scholar discovery seed is not proof that a score is implementable, robust, or appropriate for the KOSPI200 scanner. Research output must become structured evidence before any downstream quant or runtime work begins.

---

## Responsibilities

- define approved research-ingestion behavior
- define Google Scholar discovery-only constraints
- define EvidenceCard expectations
- define source, metadata, and raw snapshot policies
- route research-derived ideas to downstream agents
- document limitations and rejected evidence conservatively

---

## Relationship to Quant_mvp

`Quant_mvp/agents/research/AGENTS.md` is the integrated research agent for the quant workspace.

Use `reserch_mvp` as the source/reference project for the research-ingestion design, and use `Quant_mvp/agents/research` when the output needs to integrate directly with the quant score workflow.

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

