# WORKSPACE_MANIFEST

workspace_id: research_manifest_candidate_selection_20260428
branch: codex/v0-2-ml-research-reference
role: research-ingestion
task_type: pdf_fulltext_candidate_manifest_and_license_trace_generation
active_step: post-MVP v0.2 research evidence support
owner_or_worker: research subproject agent

## Purpose

Generate a deterministic PDF/fulltext candidate manifest from the existing
research normalized papers corpus and create metadata-only or verified license
trace outputs for those candidates. This workspace step does not download PDFs,
collect full text, adopt scores, run backtests, or make trading or valuation
claims.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- input/manifest/papers.jsonl
- input/manifest/skipped_papers.jsonl
- input/manifest/candidate_selection_summary.json
- output/license_trace/pdf_license_trace.jsonl
- output/license_trace/license_trace_summary.json
- data/research/fulltext/manifest/pdf_collection_manifest.jsonl
- data/research/fulltext/manifest/pdf_collection_pending.jsonl
- data/research/fulltext/manifest/pdf_collection_failed.jsonl

## Forbidden Actions

- PDF or fulltext download
- broad web crawling or non-official source scraping
- score, ranking, report, backtest, or valuation behavior changes
- trading, buy/sell/hold, proven-alpha, profitability, or expected-return claims
- edits outside `Quant_mvp/research_mvp`

## Required Validation

- JSONL parse validation for generated manifests
- candidate line count <= 41
- duplicate_key duplicate count equals 0
- candidate selection_rank starts at 1 and is contiguous
- each candidate has title and at least one source_url/doi/arxiv_id/pdf_url
- git diff --check
- JSONL parse validation for license trace
- trace result count equals input candidate count
- trace_complete rows must include explicit license evidence fields
- generated PDF/fulltext file count remains 0
