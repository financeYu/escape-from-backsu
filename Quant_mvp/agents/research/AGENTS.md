# Quant Research Intake Pointer

## Purpose

`Quant_mvp/agents/research` is no longer the canonical research-ingestion owner.
It is a Quant-side intake and handoff boundary for product-line coordination,
not a source-collection or runtime implementation agent.

The canonical upstream research-ingestion agent lives in:

```text
../../../reserch_mvp/AGENTS.md
```

Use `reserch_mvp` for source policy, paper metadata collection, query-set expansion, metadata adapters, EvidenceCard generation, reject logs, source-health reports, and research-ingestion reports.

## Quant Role

Quant is a downstream consumer of research evidence. It may read source-controlled intake policy and accepted handoff files, then decide whether an EvidenceCard can become Score Architect material.
At the product-line level, Quant may coordinate research ingestion and scanner
runtime handoffs as the score-governance umbrella, but that coordination does
not make Quant the owner of source collection, metadata adapters, EvidenceCard
generation, chart rendering, scanner runtime implementation, or generated chart
outputs.

Quant-owned research intake policy lives in:

```text
../../config/research_intake.toml
```

Allowed Quant responsibilities:

- verify EvidenceCard schema and handoff completeness
- reject or defer research cards that need valuation, fundamentals, intraday data, unresolved hybrid splitting, or manual review
- pass eligible technical or diagnostic cards to Score Architect review only through the documented roadmap flow
- write or update Quant-side score specifications and handoff contracts before downstream chart runtime work is requested
- keep Step 14 adoption synthesis based on Step 13 technical review material unless root explicitly promotes newer research intake

Quant must not:

- collect research sources
- expand research query sets
- own metadata-source adapters
- generate EvidenceCards
- turn an EvidenceCard into a score definition
- turn an EvidenceCard into an adoption decision
- request or begin chart runtime implementation from an EvidenceCard without a documented Quant specification, handoff contract, or explicit root/user assignment
- run paper-derived backtests before Step 17
- perform valuation or fundamental review before Step 18
- put financial/fundamental data into `technical_composite_score` or `final_composite_score`

EvidenceCard intake is not score definition, score adoption, ranking,
reporting, backtest, valuation, or runtime activation. This post-MVP document
clarification keeps the MVP v0.1 baseline intact and changes only governance
and handoff wording.

## Handoff Boundary

Research handoff outputs remain upstream material only:

```text
../../../reserch_mvp/data/research/evidence/evidence_cards.jsonl
../../../reserch_mvp/data/research/evidence/technical_candidates.jsonl
../../../reserch_mvp/data/research/evidence/diagnostic_items.jsonl
../../../reserch_mvp/data/research/evidence/hybrid_review_required.jsonl
../../../reserch_mvp/reports/research_ingestion/ingestion_report.md
```

If a Quant worker needs to change source policy, research query config, source adapters, EvidenceCard schema, or ingestion reports, stop and route the work to `reserch_mvp`.
If a Quant worker needs chart rendering, scanner runtime, cache behavior, or
generated chart output changes, stop and route the work to `chart_mvp` after a
Quant-owned specification, handoff contract, or explicit root/user assignment
exists.
