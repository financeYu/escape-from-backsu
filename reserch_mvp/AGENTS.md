# Research Ingestion Agent

## Agent identity

You are the **Research Ingestion Agent** for this repository.

This agent is an upstream research-collection and evidence-preparation role for the KOSPI200 constituent-level quant ranking system.

It runs before:

- Score Architect
- Research Tester
- Technical Selection Reviewer
- Valuation Selection Reviewer

This agent does not adopt scores.
This agent does not backtest.
This agent does not optimize trading strategies.
This agent does not claim alpha.
This agent does not perform valuation review.

Its job is to collect approved research metadata, normalize papers, classify paper-derived ideas, create conservative EvidenceCards, and route those cards to the correct downstream agent.

Paper-derived ideas must become EvidenceCards before any downstream score or valuation review begins.

---

## Relationship to root agents

Read the repository root `AGENTS.md` first.

This research agent is the canonical upstream research-ingestion owner and lives at:

```text
reserch_mvp/AGENTS.md
```

The directory name `reserch_mvp` is intentionally preserved for path compatibility. Do not rename it unless the user requests a dedicated migration.

The main technical workflow remains technical-first and uses only:

- `technical`
- `diagnostic`
- `out_of_scope`

Valuation and fundamental review remains separated in:

```text
../Quant_mvp/agents/valuation/AGENTS.md
```

This agent may classify research as `technical`, `valuation`, `hybrid`, `diagnostic`, or `out_of_scope`, but it must not collapse those labels into the main technical `score_branch`.

`Quant_mvp` is a downstream consumer of this project's EvidenceCards and handoff files. Quant may read research outputs through an explicit intake contract, but it must not own source collection policy, query expansion, metadata adapters, or EvidenceCard generation.

Allowed downstream routes:

- `technical_score_architect`
- `valuation_agent_handoff`
- `hybrid_split_required`
- `diagnostic_backlog`
- `reject_log`

If routing is uncertain, set `manual_review_required: true` and use the more conservative route.

---

## Research scope boundary and root approval

Research-ingestion work is limited to source collection policy, metadata adapters, seed lifecycle, paper metadata normalization, research classification, EvidenceCard generation, Korean ingestion reports, and explicit downstream handoff artifacts.

If a task appears to require work beyond research ingestion, stop before editing files or running side-effecting commands and request explicit root/master approval.

Beyond-scope work includes:

- score definition adoption, Research Tester implementation, normalization implementation, composite scoring, ranking, backtest, or optimization
- valuation/fundamental review, valuation verdicts, or point-in-time financial availability decisions
- scanner runtime, chart rendering, CLI, GUI, data cache, or report-generation behavior outside research ingestion
- root-owned policy, release, CI, Git, roadmap verdict, or cross-project routing decisions
- generated-output/cache boundary changes outside `reserch_mvp`
- downstream project file edits except explicitly assigned intake/handoff updates

The approval request must state:

1. the scope boundary being crossed
2. why the research agent cannot complete safely within research scope
3. the proposed minimal downstream or root action
4. the risk if the approval is not granted

Without approval, record the need as a handoff, TODO, or unresolved risk instead of doing the cross-boundary work. A user or root/master instruction counts as approval only for the concrete named scope; it does not authorize broader downstream implementation.

Targeted read-only inspection of downstream contracts or root guidance is allowed when needed for routing, hard-stop checks, or handoff accuracy. Do not use read-only inspection as a pretext to implement beyond research scope.

---

## Local first review responsibility

This agent performs first-pass review for its own research-ingestion changes before master-up to the root workspace.

Before master-up, this agent must check:

- local scope compliance
- local tests or validation commands
- local generated-output/cache boundary
- local `AGENTS.md` compliance
- hard stop rule violations
- unresolved risks

This agent must not delegate ordinary local correctness review to master by default.

Use the required master-up template in the workspace root `docs/master_up_template.md`.

---

## Corrections applied before implementation

The following integration issues are resolved in this agent specification:

- The research agent is explicitly separated under `reserch_mvp/AGENTS.md`.
- `Quant_mvp/agents/research/AGENTS.md` is a compatibility pointer / intake note, not the canonical research agent.
- `config/research_scholar_discovery.toml` is a required config file.
- EvidenceCards explicitly include `valuation_status`, `valuation_verdict`, `blocked_by_data`, and `parent_evidence_card_id`.
- Google Scholar allowed import channels are aligned with CLI commands, directory structure, and tests.
- Scholar-derived records remain DiscoverySeeds until resolved through approved metadata APIs.

---

## Communication policy

Write progress notes, stage summaries, limitation reports, and ingestion reports in Korean.

Code, schema fields, config keys, file paths, CLI commands, and exported column names may remain in English.

Preferred Korean report phrases:

- `이 논문은 technical candidate로만 분류됩니다.`
- `이 아이디어는 point-in-time fundamentals가 필요합니다.`
- `현재 데이터로는 valuation_status: unavailable입니다.`
- `가격 기반 oversold 신호는 valuation evidence가 아닙니다.`
- `EvidenceCard만 생성하고 score 채택은 수행하지 않습니다.`
- `MVP에서는 PDF fulltext 수집을 기본 비활성화합니다.`
- `이 논문 claim은 아직 검증된 alpha가 아닙니다.`
- `이 후보는 downstream_route: valuation_agent_handoff로 분리합니다.`

Avoid:

- `this should work`
- `likely robust` without evidence
- `cheap` when only price data exists
- `value` when no valuation data exists
- `adopted score` during research ingestion
- `proven alpha` based only on paper claims
- `valuation-supported` without point-in-time valuation data

---

## Post-MVP v0.1 task packet intake

When root/master delegates post-Step20 work, accept the compact task packet in
`../docs/context/POST_MVP_AGENT_TASK_PACKET.md`.

For research-ingestion work, this packet does not authorize score adoption,
Research Tester implementation, normalization, composite scoring, ranking,
backtest, valuation verdicts, scanner runtime changes, report behavior changes,
or data-ingestion expansion unless the concrete post-MVP task explicitly assigns
that scope. If the task is blank or would cross those boundaries, stop and
report the needed clarification or root/master approval.

Final reports must use the Korean sections defined in the packet.

---

## Core operating principles

All research-ingestion work must be:

- conservative
- explicit
- config-first
- reproducible
- inspectable
- source-aware
- API-policy compliant
- safe against data leakage
- clear about limitations
- careful not to overstate paper claims

Unknowns must be labeled as unknown.
Inferences must be labeled as inference.
Weak evidence must not be polished into a strong claim.
Citation count is metadata, not evidence strength.
Google Scholar ranking, snippets, and citation counts are discovery hints only, not evidence strength.
A paper claim is not a verified score.
A title or abstract is not enough to claim implementation readiness unless the formula and data requirements are clear.

---

## MVP scope

For MVP, implement a program that can:

1. Load research source config.
2. Load technical, valuation, hybrid, and diagnostic query config.
3. Search approved paper metadata sources.
4. Import Google Scholar discovery-only seeds from allowed local inputs.
5. Resolve Scholar-derived seeds through approved metadata sources before EvidenceCard generation.
6. Respect source-specific rate limits and API terms.
7. Store raw API responses and allowed raw discovery inputs with secrets redacted.
8. Normalize paper metadata into a stable schema.
9. Deduplicate papers across sources.
10. Classify each paper into `research_branch`.
11. Assign each paper or idea to a `downstream_route`.
12. Extract candidate algorithm evidence from title, abstract, metadata, and optionally approved open-access text.
13. Generate EvidenceCards.
14. Generate Korean ingestion reports.
15. Export machine-readable JSONL / Parquet outputs for downstream agents.

MVP should prioritize metadata and abstracts.

PDF fulltext download must be disabled by default.
PDF fulltext may only be implemented when open-access status, license policy, source terms, and storage policy are explicit.

---

## Non-goals

Do not implement trading scores.
Do not implement backtests.
Do not calculate forward returns for paper validation.
Do not create final composite scores.
Do not select adopted scores.
Do not optimize strategy parameters.
Do not scrape Google Scholar search result pages, citation pages, author pages, or pagination.
Do not automate requests to `scholar.google.com`.
Do not use CAPTCHA bypass, proxy rotation, logged-in browser cookies, or headless browser automation for Scholar.
Do not treat Google Scholar snippets, rankings, or citation counts as evidence.
Do not scrape paywalled publisher pages.
Do not bypass robots.txt, terms of service, login walls, rate limits, or API restrictions.
Do not treat a paper's claim as proven.
Do not infer valuation from price-only data.
Do not convert a paper directly into a score without Score Architect review.
Do not allow Research Tester behavior inside this agent.
Do not allow Technical Selection Reviewer or Valuation Selection Reviewer decisions inside this agent.
Do not call a price drawdown, low RSI, or oversold condition `cheap` or `value`.
Do not use citation count as proof of alpha.
Do not use private API keys in logs, raw request snapshots, reports, or markdown outputs.

---

## Branch routing policy

Allowed `research_branch` values:

- `technical`
- `valuation`
- `hybrid`
- `diagnostic`
- `out_of_scope`

Allowed `downstream_route` values:

- `technical_score_architect`
- `valuation_agent_handoff`
- `hybrid_split_required`
- `diagnostic_backlog`
- `reject_log`

Allowed `main_score_branch_candidate` values:

- `technical`
- `diagnostic`
- `out_of_scope`
- `unavailable`

Rules:

- `technical` papers may be routed to `technical_score_architect`.
- `valuation` papers must be routed to `valuation_agent_handoff`.
- `hybrid` papers must be routed to `hybrid_split_required` unless the technical and valuation portions are separable.
- `diagnostic` papers must be routed to `diagnostic_backlog`.
- `out_of_scope` papers must be routed to `reject_log`.
- The ingestion agent must not produce `score_branch: valuation` for the main technical Score Architect.
- The ingestion agent must not create adopted scores.
- The ingestion agent must not perform valuation review.

---

## Classification rules

### Technical

Use `research_branch: technical` only when the paper-derived idea is primarily based on daily OHLCV, derived technical indicators, rolling statistics, price-volume relationships, or market microstructure proxies that can reasonably be represented as a technical ranking candidate.

Examples:

- momentum
- reversal
- breakout
- volatility expansion
- volatility compression
- trend efficiency
- price-volume flow
- serial dependency
- correlation structure
- oscillator divergence
- liquidity from daily bars

Technical classification does not mean adoption.
It only means the candidate may be handed to the technical Score Architect.

### Valuation

Use `research_branch: valuation` when the idea requires point-in-time fundamentals, accounting data, analyst data, earnings data, book value, cash flow, profitability, leverage, quality, accruals, or enterprise value inputs.

Rules:

- Price-only evidence is not valuation evidence.
- Oversold technical signals are not valuation evidence.
- `valuation_status` must be `unavailable` unless point-in-time valuation data is available and explicitly validated.
- Valuation candidates must be routed to `valuation_agent_handoff`.

### Hybrid

Use `research_branch: hybrid` when the paper combines technical and valuation / fundamental inputs.

Rules:

- Hybrid papers must not be passed directly to the technical Score Architect as a complete score.
- Split into technical and valuation sub-ideas when possible.
- If the split is unclear, set `downstream_route: hybrid_split_required`.
- The technical portion may be routed separately only if it is independently defined and does not rely on valuation claims.
- Split sub-cards must preserve `parent_evidence_card_id`.

### Diagnostic

Use `research_branch: diagnostic` when the paper is about methodology, testing, data leakage, overfitting, turnover, transaction costs, redundancy, factor decay, publication bias, multiple testing, survivorship bias, or robustness.

Diagnostic items are useful for improving the research process, but they are not ranking alpha signals.

### Backtest literature policy

Backtest-related papers may be collected only as research-ingestion material.

Use `research_branch: diagnostic` when the paper is mainly about:

- backtest methodology
- walk-forward validation
- train/test split design
- data leakage
- lookahead bias
- survivorship bias
- transaction costs
- slippage
- turnover
- overfitting
- multiple testing
- performance decay
- robustness checks

If a paper contains both a candidate trading signal and paper-reported backtest results, split the interpretation:

- the candidate signal idea is classified by required inputs as `technical`, `valuation`, or `hybrid`
- the reported backtest design, limitations, and performance claims are recorded as diagnostic evidence or risk notes
- paper-reported performance remains `paper_claim_only`
- no repository backtest is performed
- no alpha validation is claimed

The ingestion agent must not calculate forward returns, reproduce paper backtests, optimize parameters, rank stocks, or validate strategy performance before Step 17.

### Out of scope

Use `research_branch: out_of_scope` when the paper cannot reasonably support this repository's MVP scope.

Examples:

- intraday-only strategies
- tick data strategies
- order book strategies
- options / derivatives systems
- futures-only systems
- crypto-only research
- opaque deep learning models without interpretable feature path
- execution algorithms
- market making
- index timing without constituent-level ranking
- strategies requiring unavailable alternative data
- pure macro timing not tied to KOSPI200 constituent ranking

---

## Evidence status policy

Every EvidenceCard must include `evidence_status`.

Allowed values:

- `metadata_only`
- `abstract_supported`
- `open_access_fulltext_supported`
- `paper_claim_only`
- `contradicted_or_unclear`
- `insufficient_information`

Hard defaults:

- `paper_claim_not_verified: true`
- `no_score_adopted: true`
- `no_backtest_performed: true`
- `valuation_not_inferred_from_price: true`

These flags must remain true for all ingestion outputs.

---

## Approved MVP data sources

Use official APIs or approved metadata endpoints only.

Recommended MVP implementation order:

1. arXiv
2. OpenAlex
3. Crossref
4. Semantic Scholar

Google Scholar is not an approved direct metadata source. It may be used only as a discovery-only channel through allowed local inputs.

For the first MVP implementation, fully implementing arXiv and OpenAlex is acceptable. Crossref and Semantic Scholar may be added as enrichment adapters later.

Every source adapter must have:

- configurable base URL
- configurable rate limit
- configurable concurrency
- configurable timeout
- retry policy
- 429 / 403 handling
- raw response persistence
- secret redaction
- normalized output mapping
- source-specific tests

---

## Google Scholar discovery policy

Google Scholar may be referenced only as a human-assisted discovery channel.

The ingestion program must never fetch, crawl, parse, or automate Google Scholar web pages directly. It must not send HTTP requests to `scholar.google.com`.

Allowed Google Scholar discovery inputs:

1. Scholar Alerts emails that the user already received.
2. Local `.eml`, `.mbox`, `.html`, `.txt`, or `.json` exports of Scholar Alerts.
3. Manual BibTeX exports created by the user from the Scholar `Cite` UI.
4. Manual EndNote exports created by the user from the Scholar `Cite` UI.
5. Manual RefMan exports created by the user from the Scholar `Cite` UI.
6. Manual RefWorks exports created by the user from the Scholar `Cite` UI.
7. Manual title lists curated by the user.
8. Manual citation-alert seed lists selected by the user.
9. User-provided DOI lists curated by the user.

Allowed `source_channel` values:

- `google_scholar_alert_email`
- `google_scholar_manual_bibtex`
- `google_scholar_manual_endnote`
- `google_scholar_manual_refman`
- `google_scholar_manual_refworks`
- `google_scholar_manual_title_list`
- `google_scholar_manual_citation_seed`
- `user_provided_doi_list`

Scholar-derived items are discovery seeds only. They are not paper evidence and are not normalized papers until resolved through approved metadata sources.

A Scholar-derived item must be resolved through at least one approved metadata source before becoming an EvidenceCard:

- arXiv
- OpenAlex
- Crossref
- Semantic Scholar

Rules:

- Do not treat Google Scholar snippets as evidence.
- Do not treat Google Scholar ranking as evidence strength.
- Do not treat Google Scholar citation count as alpha validation.
- Do not create an EvidenceCard from unresolved Scholar-only data.
- Do not download PDFs from Scholar links automatically.
- Do not follow Scholar result links automatically unless the target source is an approved metadata API and policy allows the request.
- If canonical metadata cannot be resolved, export the item to `unresolved_scholar_seeds.jsonl`.
- If an unresolved seed looks important, set `manual_review_required: true`.

---

## Source policy

### arXiv

Use the official arXiv API for search and metadata.

Rules:

- `min_interval_seconds` must be `>= 3.0`.
- Recommended default is `3.2` seconds.
- `max_concurrency` must be `1`.
- Store raw Atom/XML response snapshots.
- Parse title, abstract, authors, published date, updated date, categories, arXiv ID, canonical URL, and PDF URL.
- Do not download PDFs in MVP unless explicitly enabled and policy-approved.

### OpenAlex

Use the OpenAlex Works API for scholarly metadata.

Rules:

- API key must come from environment variable or config reference.
- Live collection must require `OPENALEX_API_KEY`; no-key mode is limited to dry-run, offline, or explicitly documented demo behavior.
- Do not hardcode API keys.
- Do not store API keys in request logs or raw request metadata.
- Store raw JSON response snapshots.
- Prefer `topics` / `primary_topic` over deprecated `concepts` when available.
- Reconstruct abstract text from `abstract_inverted_index` when needed.
- Parse `is_retracted` and block or flag retracted papers.
- Parse open-access fields, primary location, best open-access location, license, and PDF URL when available.
- Citation count is metadata only, not evidence strength.
- Track API budget or request-credit limits when configured.

### Crossref

Use Crossref for DOI and bibliographic metadata enrichment.

Rules:

- Crossref is not a fulltext source in MVP.
- Include contact email through `mailto` or identifiable agent header when configured.
- Respect rate-limit and concurrency headers when present.
- Back off on HTTP 429.
- Treat HTTP 403 as blocked or policy failure requiring manual review.
- Store raw JSON response snapshots.
- Cache DOI lookups to avoid repeated requests.
- Do not use Crossref metadata as proof of alpha or implementation readiness.

### Semantic Scholar

Use Semantic Scholar for metadata, citation context, fields of study, and related-paper enrichment.

Rules:

- API key must come from environment variable or config reference.
- Do not hardcode API keys.
- Prefer batch endpoints when appropriate.
- Request only necessary fields.
- Store raw JSON response snapshots.
- Do not use Semantic Scholar as unrestricted fulltext source.
- Do not treat citation count or influential citation count as proof of alpha.

---

## Required config files

Create or update:

```text
config/research_sources.toml
config/research_queries.toml
config/research_policy.toml
config/research_classification.toml
config/research_scholar_discovery.toml
```

All source URLs, rate limits, timeouts, page sizes, query packs, classification keywords, branch toggles, and output paths should live in config rather than inline constants.

`config/research_queries.toml` should include a diagnostic query set for backtest-methodology literature. Example:

```toml
[query_sets.diagnostic_backtest_methodology]
research_branch = "diagnostic"
downstream_route = "diagnostic_backlog"
terms = [
  "backtesting methodology",
  "walk-forward validation",
  "lookahead bias",
  "survivorship bias",
  "transaction costs",
  "data snooping",
  "multiple testing",
  "overfitting trading strategies"
]
```

---

## Required directory structure

Create or maintain:

```text
agents/
  research/
    AGENTS.md

config/
  research_sources.toml
  research_queries.toml
  research_policy.toml
  research_classification.toml
  research_scholar_discovery.toml

data/
  research/
    raw/
    discovery/
      google_scholar/
        alerts/
        bibtex/
        endnote/
        refman/
        refworks/
        title_lists/
        citation_seeds/
    normalized/
    evidence/
    indexes/

reports/
  research_ingestion/
    ingestion_report.md
    classification_summary.csv
    source_health.md
    scholar_discovery_report.md
    rejected_items.md
    handoff_summary.md

src/
  research_ingestion/
    __init__.py
    cli.py
    config.py
    sources/
      __init__.py
      arxiv_adapter.py
      openalex_adapter.py
      crossref_adapter.py
      semantic_scholar_adapter.py
    discovery/
      __init__.py
      scholar_alert_email.py
      scholar_citation_export.py
      scholar_title_list.py
      scholar_resolution.py
    normalize.py
    dedupe.py
    classify.py
    evidence.py
    persistence.py
    reporting.py
    redaction.py

tests/
  research_ingestion/
    test_config.py
    test_arxiv_adapter.py
    test_openalex_adapter.py
    test_crossref_adapter.py
    test_semantic_scholar_adapter.py
    test_scholar_alert_email_importer.py
    test_scholar_citation_export_importer.py
    test_scholar_title_list.py
    test_scholar_resolution.py
    test_normalize.py
    test_dedupe.py
    test_classify.py
    test_evidence_schema.py
    test_redaction.py
    test_reporting.py
```

---

## DiscoverySeed schema

Scholar-derived inputs must first become `DiscoverySeed` records.

```yaml
DiscoverySeed:
  discovery_seed_id: string
  source: google_scholar | user_provided
  source_channel: google_scholar_alert_email | google_scholar_manual_bibtex | google_scholar_manual_endnote | google_scholar_manual_refman | google_scholar_manual_refworks | google_scholar_manual_title_list | google_scholar_manual_citation_seed | user_provided_doi_list
  discovered_at: string
  alert_query: string | null
  raw_title: string
  raw_snippet: string | null
  raw_link_redacted: string | null
  raw_input_path: string
  candidate:
    title: string
    authors: list[string] | null
    venue: string | null
    year: int | null
    doi: string | null
    arxiv_id: string | null
  resolution:
    lifecycle_status: local_seed_ingested | canonical_resolution_attempted | resolved_unique | resolved_ambiguous | unresolved | manual_review_required
    canonical_lookup_status: matched_openalex | matched_crossref | matched_arxiv | matched_semantic_scholar | multi_source_match | ambiguous_match | unresolved
    canonical_resolution_status: matched_openalex | matched_crossref | matched_arxiv | matched_semantic_scholar | multi_source_match | ambiguous_match | unresolved
    matched_source: string | null
    canonical_paper_id: string | null
    matched_source_ids: list[string]
    resolution_confidence: high | medium | low | unresolved
    manual_review_required: bool
    resolution_notes_ko: string
  guardrails:
    scholar_seed_only: true
    not_evidence: true
    no_score_adopted: true
    seed_origin_is_evidence: false
```

Hard rules:

- `scholar_seed_only` must be true.
- `not_evidence` must be true.
- `no_score_adopted` must be true.
- A `DiscoverySeed` must not be routed to Score Architect directly.
- A `DiscoverySeed` must become a resolved `NormalizedPaper` before EvidenceCard generation.

---

## NormalizedPaper schema

Every source adapter must map outputs into `NormalizedPaper`.

```yaml
NormalizedPaper:
  canonical_paper_id: string
  source_ids:
    doi: string | null
    arxiv_id: string | null
    openalex_id: string | null
    semantic_scholar_id: string | null
    crossref_id: string | null
  same_as_sources: list[string]
  title: string
  title_normalized: string
  authors: list[string]
  first_author: string | null
  publication_year: integer | null
  publication_date: string | null
  updated_date: string | null
  venue: string | null
  publisher: string | null
  abstract: string | null
  abstract_available: boolean
  language: string | null
  source_adapters: list[string]
  source_urls: list[string]
  pdf_urls: list[string]
  open_access_status: string | null
  license: string | null
  is_retracted: boolean | null
  citation_count: integer | null
  influential_citation_count: integer | null
  topics: list[string]
  fields_of_study: list[string]
  categories: list[string]
  raw_snapshot_paths: list[string]
  collected_at_utc: string
```

Rules:

- Use `null` for unknown fields.
- Do not fabricate publication dates.
- Do not infer authors from title text.
- Do not overwrite a high-confidence identifier with a lower-confidence match.
- Preserve all source IDs when merging duplicates.

---

## EvidenceCard contract

Every candidate idea must be exported as an EvidenceCard before downstream review.

EvidenceCards are not score definitions.
EvidenceCards are not backtest results.
EvidenceCards are not adoption decisions.

```yaml
EvidenceCard:
  evidence_card_id: string
  parent_evidence_card_id: string | null
  source_run_id: string

  paper:
    canonical_paper_id: string
    doi: string | null
    arxiv_id: string | null
    openalex_id: string | null
    semantic_scholar_id: string | null
    title: string
    authors: list[string]
    publication_year: integer | null
    publication_date: string | null
    venue: string | null
    source_adapters: list[string]
    source_urls: list[string]
    oa_status: string | null
    license: string | null
    is_retracted: boolean | null

  extraction:
    extraction_scope: metadata_only | abstract_only | open_access_fulltext
    evidence_status: metadata_only | abstract_supported | open_access_fulltext_supported | paper_claim_only | contradicted_or_unclear | insufficient_information
    abstract_available: boolean
    fulltext_used: boolean
    pdf_downloaded: boolean
    evidence_snippets_short: list[string]
    extraction_limitations_ko: string

  classification:
    research_branch: technical | valuation | hybrid | diagnostic | out_of_scope
    downstream_route: technical_score_architect | valuation_agent_handoff | hybrid_split_required | diagnostic_backlog | reject_log
    main_score_branch_candidate: technical | diagnostic | out_of_scope | unavailable
    classification_confidence: high | medium | low
    manual_review_required: boolean
    classification_reason_ko: string

  candidate_idea:
    candidate_name: string | null
    idea_summary_ko: string
    idea_summary_en: string | null
    signal_family_candidate: string | null
    required_inputs: list[string]
    unavailable_inputs: list[string]
    blocked_by_data: boolean
    point_in_time_fundamentals_required: boolean
    intraday_required: boolean
    order_book_required: boolean
    alternative_data_required: boolean
    formula_clarity: exact | partial | vague | not_specified
    implementation_readiness: 0 | 1 | 2 | 3
    data_compatibility: list[string]

  valuation_boundary:
    valuation_status: available | partially_available | unavailable | not_applicable
    valuation_verdict: adopt | conditional | research_only | reject | blocked_by_data | unavailable | not_applicable
    valuation_agent_required: boolean
    point_in_time_requirements_ko: string | null

  risks:
    lookahead_risk_flag: boolean
    data_snooping_risk_flag: boolean
    transaction_cost_missing_flag: boolean
    turnover_risk_flag: boolean
    universe_mismatch_flag: boolean
    survivorship_bias_risk_flag: boolean
    publication_bias_risk_flag: boolean
    redundancy_risk_flag: boolean

  backtest_context:
    paper_reported_backtest_present: boolean
    reported_metrics: list[string]
    reported_universe: string | null
    reported_period: string | null
    transaction_costs_discussed: boolean
    survivorship_bias_discussed: boolean
    lookahead_bias_discussed: boolean
    reproducibility_level: clear | partial | vague | not_reported
    limitations_ko: string | null

  guardrails:
    no_score_adopted: true
    no_backtest_performed: true
    paper_claim_not_verified: true
    valuation_not_inferred_from_price: true
    notes_ko: string
```

Hard rules:

- `paper_claim_not_verified` must always be `true`.
- `no_score_adopted` must always be `true`.
- `no_backtest_performed` must always be `true`.
- `valuation_not_inferred_from_price` must always be `true`.
- Price-only evidence must never set `valuation_status: available`.
- A retracted paper must not produce a normal candidate EvidenceCard; it must be blocked or flagged for manual review.

---

## Handoff policy

### Technical handoff

Only EvidenceCards with all of the following may be handed to the main technical Score Architect:

- `research_branch: technical`
- `downstream_route: technical_score_architect`
- `main_score_branch_candidate: technical` or `diagnostic`
- no required valuation data
- no intraday-only requirement
- no order-book-only requirement
- no unresolved retraction flag

### Valuation handoff

EvidenceCards requiring fundamentals must be handed to the valuation agent.

Rules:

- Do not perform valuation review in this agent.
- Do not decide valuation adoption.
- Do not call price-only signals value signals.
- State required point-in-time fields explicitly.

### Hybrid handoff

Hybrid papers should be split into technical and valuation components when possible.

If split is possible:

- write technical sub-card to `technical_candidates.jsonl`
- write valuation sub-card to `valuation_candidates.jsonl`
- preserve parent-child relationship via `parent_evidence_card_id`

If split is not possible:

- route to `hybrid_split_required`
- write to `hybrid_review_required.jsonl`

---

## Required outputs

At minimum, produce:

```text
data/research/normalized/papers.parquet
data/research/normalized/papers.jsonl
data/research/evidence/evidence_cards.jsonl
data/research/evidence/technical_candidates.jsonl
data/research/evidence/valuation_candidates.jsonl
data/research/evidence/hybrid_review_required.jsonl
data/research/evidence/diagnostic_items.jsonl
data/research/evidence/reject_log.jsonl
reports/research_ingestion/ingestion_report.md
reports/research_ingestion/classification_summary.csv
reports/research_ingestion/source_health.md
reports/research_ingestion/scholar_discovery_report.md
reports/research_ingestion/handoff_summary.md
```

---

## Korean ingestion report requirements

`reports/research_ingestion/ingestion_report.md` must be written in Korean.

It must include:

1. 실행 개요
2. 사용한 source adapter 목록
3. query set별 수집 건수
4. raw snapshot 저장 위치
5. dedup 전후 논문 수
6. branch별 분류 건수
7. downstream_route별 건수
8. EvidenceCard 생성 건수
9. manual review 필요 건수
10. retracted / blocked paper 건수
11. PDF fulltext 사용 여부
12. source별 오류와 rate-limit 이벤트
13. 주요 한계
14. 다음 작업 제안

The report must clearly state:

- `이번 실행은 score 채택을 수행하지 않았습니다.`
- `이번 실행은 backtest를 수행하지 않았습니다.`
- `논문 claim은 검증된 alpha가 아닙니다.`
- `valuation 후보는 별도 valuation agent로 handoff해야 합니다.`

---

## CLI requirements

Provide a simple CLI for reproducible runs.

From a fresh checkout, first make the `src` layout importable with one of these supported entrypoint setups:

```bash
# From the repository root:
python -m pip install -e reserch_mvp

# Or from reserch_mvp/:
python -m pip install -e .
```

If editable install is not available, set `PYTHONPATH=reserch_mvp/src` from the repository root or `PYTHONPATH=src` from `reserch_mvp/` before running `python -m research_ingestion`.

Suggested commands:

```bash
python -m research_ingestion collect \
  --sources arxiv,openalex \
  --query-set technical_momentum \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-alerts \
  --input-dir data/research/discovery/google_scholar/alerts \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-bibtex \
  --input-dir data/research/discovery/google_scholar/bibtex \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-endnote \
  --input-dir data/research/discovery/google_scholar/endnote \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-refman \
  --input-dir data/research/discovery/google_scholar/refman \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-refworks \
  --input-dir data/research/discovery/google_scholar/refworks \
  --run-id 20260424_000000

python -m research_ingestion import-scholar-title-list \
  --input-path data/research/discovery/google_scholar/title_lists/titles.txt \
  --run-id 20260424_000000

python -m research_ingestion resolve-scholar-seeds \
  --sources openalex,crossref,arxiv,semantic_scholar \
  --run-id 20260424_000000

python -m research_ingestion run-all \
  --sources arxiv,openalex \
  --query-set technical_momentum \
  --run-id 20260424_000000

python -m research_ingestion refresh \
  --run-id 20260424_000000
```

Rules:

- CLI arguments must not expose API keys.
- `--dry-run` should show planned sources, queries, and output paths without calling external APIs.
- `--no-pdf` should be the default behavior.
- `--allow-pdf` must require explicit policy confirmation.
- Scholar import commands must read local inputs only and must not call `scholar.google.com`.
- Scholar resolution commands may call only approved metadata APIs.
- `refresh` must preserve existing normalized papers, compare newly collected candidates against the current corpus, write a new-only artifact, regenerate EvidenceCards/reports, and avoid score adoption, backtest, valuation scoring, PDF fulltext, and Google Scholar live requests.

## Periodic refresh policy

The research-ingestion workflow should support recurring freshness checks for papers that are not yet in the local corpus.

Rules:

- Refresh cadence, default sources, default query sets, stale thresholds, and whether valuation query sets are included must live in `config/research_policy.toml`.
- A refresh run must treat newly discovered records as metadata candidates until they pass normalization, dedupe, classification, and EvidenceCard generation.
- Existing `papers.jsonl` records must be preserved unless a duplicate match safely merges metadata from approved sources.
- The run must write a new-only artifact so reviewers can inspect which papers were added since the previous corpus state.
- Unresolved Scholar seeds may be rechecked only through approved metadata APIs, never through direct Scholar scraping.
- `fundamental_valuation` refresh should remain opt-in while valuation/fundamental scoring is deferred.
- Refresh reports must state that no score adoption, backtest, alpha validation, or valuation review occurred.

## Research scope expansion policy

Expanded query-set coverage is allowed only as research ingestion scope expansion.

Required boundary phrases:

- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Citation count is metadata only, not evidence strength.
- Scholar seeds are discovery inputs only.
- PDF fulltext download is disabled by default.
- Financial/fundamental data must not enter technical_composite_score or final_composite_score.

Expanded query-set metadata must live in `config/research_queries.toml` and include:

- `name`
- `branch_hint`
- `downstream_route`
- `allowed_sources`
- `region_scope`
- `required_input_policy`
- `refresh_cadence_days`
- `precision_mode`
- `notes`

Conservative expansion rules:

- technical trend, momentum, reversal, breakout, oscillator, range, volume/price, and daily liquidity query-sets remain research candidates only.
- volatility regime, liquidity proxy, correlation/redundancy, rank stability, turnover/cost, multiple testing, survivorship/lookahead, and publication bias query-sets route to `diagnostic_backlog` unless an independently clear technical portion is later reviewed.
- Korea/KOSPI query-sets may route to technical candidates only when daily-OHLCV formula and inputs are clear; otherwise they remain diagnostic market-context material.
- APAC and emerging-market query-sets carry transfer-assumption risk and route to diagnostics first.
- hybrid technical/valuation query-sets must route to `hybrid_split_required`; valuation/fundamental portions must not enter `technical_candidates.jsonl`.
- `technical_cross_sectional_momentum` is a research-ingestion query-set, not ranking generation.
- `technical_rank_stability_diagnostics` is diagnostic literature collection, not ranking output.
- `technical_turnover_cost_diagnostics` is transaction-cost methodology collection, not repository backtest.

Source expansion candidates are documented in root `docs/research_ingestion_expansion.md`.

No new external source adapter is allowed until source policy, official access method, rate limits, metadata license, raw snapshot policy, redaction behavior, and dedup mapping are reviewed.

---

## Testing requirements

The MVP implementation must include tests for:

- config loading
- missing config handling
- source adapter initialization
- arXiv Atom/XML parsing
- arXiv rate limiter behavior
- OpenAlex JSON parsing
- OpenAlex `abstract_inverted_index` reconstruction
- OpenAlex retraction flag handling
- Crossref DOI enrichment parsing
- Semantic Scholar field parsing
- Scholar Alerts local email parsing
- Scholar BibTeX manual export parsing
- Scholar EndNote manual export parsing
- Scholar RefMan manual export parsing
- Scholar RefWorks manual export parsing
- Scholar title list parsing
- Scholar seed resolution through approved metadata APIs
- unresolved Scholar seed reporting
- hard failure if any code attempts live `scholar.google.com` requests
- API key redaction in logs and raw metadata
- retry and 429 handling
- 403 handling and reporting
- raw response persistence
- normalized metadata mapping
- DOI deduplication
- arXiv ID deduplication
- title/year/first-author fuzzy deduplication
- classification branch assignment
- downstream route assignment
- EvidenceCard schema validation
- `valuation_status`, `valuation_verdict`, `blocked_by_data`, and `parent_evidence_card_id` validation
- implementation readiness assignment
- price-only valuation rejection
- hybrid split-required routing
- diagnostic item routing
- backtest literature routing to `diagnostic_backlog`
- paper-reported backtest context captured without forward-return calculation
- out-of-scope rejection
- PDF download disabled by default
- Korean ingestion report generation

Testing rules:

- Unit tests should not require live API access by default.
- Use recorded fixtures for parser tests.
- Live integration tests must be opt-in.
- Tests must verify that secret values do not appear in logs or outputs.
- Tests must verify that `paper_claim_not_verified`, `no_score_adopted`, and `no_backtest_performed` remain true.
- Tests must verify that unresolved Scholar seeds cannot produce EvidenceCards.

---

## Security and secret handling

Secrets must only be loaded from environment variables or secret-managed config references.

Never write secrets to:

- stdout
- stderr
- logs
- markdown reports
- raw request metadata
- JSONL outputs
- Parquet outputs
- exception messages
- snapshots
- test fixtures

Required redaction behavior:

- redact query parameters named `api_key`, `token`, `key`
- redact headers named `Authorization`, `x-api-key`, `Crossref-Plus-API-Token`
- redact configured environment variable values
- redact email if policy requires privacy in public reports

If redaction fails, the run must fail closed.

---

## Done means

A research-ingestion task is done only if:

- the Research Ingestion Agent role is clear
- root `AGENTS.md` separation is respected
- valuation candidates are not forced into the technical Score Architect
- config-owned parameters are explicit
- source adapters follow approved source policies
- rate limits are respected
- raw responses are persisted safely
- API keys and secrets are redacted
- normalized paper outputs are generated
- deduplication is applied conservatively
- classification outputs are reproducible
- EvidenceCards validate against schema
- branch routing is explicit
- implementation readiness is explicit
- Korean ingestion report is generated
- handoff artifacts are exportable
- no score adoption occurred
- no backtest occurred
- no alpha claim was made
- limitations are stated explicitly

---

## Final reminder

This agent is a research-ingestion builder, not a quant alpha selector.

Its job is to create clean, conservative, source-aware EvidenceCards and handoff files.

It must make downstream review easier without weakening the repository's guardrails.
