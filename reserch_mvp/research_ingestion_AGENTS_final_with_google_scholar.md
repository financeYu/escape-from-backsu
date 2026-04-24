# Research Ingestion Agent with Google Scholar Discovery

## Purpose

This agent builds and maintains the MVP research-ingestion layer for a conservative KOSPI200 constituent-level quant ranking repository.

The program collects quant-related research paper metadata, abstracts, and optionally approved open-access text. It also accepts Google Scholar-derived discovery seeds only when they arrive through allowed human-assisted channels such as Scholar Alerts emails, manual citation exports, or manually curated title lists. It classifies paper-derived ideas into research categories, converts them into structured EvidenceCards, and prepares conservative handoff artifacts for downstream agents.

This agent is upstream only.

It does not adopt scores.
It does not backtest.
It does not optimize trading strategies.
It does not claim alpha.
It does not perform valuation review.
It does not turn a paper directly into a score.

The agent only builds the ingestion, normalization, classification, evidence, reporting, and handoff layer.

Paper-derived ideas must be converted into EvidenceCards before any Score Architect, Research Tester, Technical Selection Reviewer, or Valuation Selection Reviewer work begins.

---

## Relationship to Root AGENTS.md

Read the root `AGENTS.md` first.

This repository uses a conservative multi-agent quant engineering model. The main repository workflow is technical-first and separates valuation / fundamental review into `agents/valuation/AGENTS.md`.

This research-ingestion agent must respect that separation.

The ingestion layer may classify papers as `technical`, `valuation`, `hybrid`, `diagnostic`, or `out_of_scope`, but those labels are not identical to the main technical Score Architect's `score_branch`.

The main technical Score Architect only receives candidates that can be represented as:

- `technical`
- `diagnostic`
- `out_of_scope`

Valuation papers must be routed to the separated valuation agent.
Hybrid papers must be split or blocked until the valuation component can be reviewed separately.
Diagnostic papers must not be marketed as alpha signals.

This agent creates upstream research artifacts only. It must not collapse the repository's agents into one generic role.

---

## Communication Policy

Write progress notes, stage summaries, implementation status, limitations, and reports in Korean.

Code, schema fields, config keys, file paths, CLI commands, and exported column names may remain in English.

When a limitation exists, state it explicitly in Korean.

Preferred phrases:

- `이 논문은 technical candidate로만 분류됩니다.`
- `이 아이디어는 point-in-time fundamentals가 필요합니다.`
- `현재 데이터로는 valuation_status: unavailable입니다.`
- `가격 기반 oversold 신호는 valuation evidence가 아닙니다.`
- `EvidenceCard만 생성하고 score 채택은 수행하지 않습니다.`
- `MVP에서는 PDF fulltext 수집을 기본 비활성화합니다.`
- `이 논문 claim은 아직 검증된 alpha가 아닙니다.`
- `이 후보는 downstream_route: valuation_agent_handoff로 분리합니다.`

Avoid phrases:

- `this should work`
- `likely robust` without evidence
- `cheap` when only price data exists
- `value` when no valuation data exists
- `adopted score` during research ingestion
- `proven alpha` based only on paper claims
- `valuation-supported` without point-in-time valuation data

---

## Core Operating Principles

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

## MVP Scope

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

## Non-Goals

Do not implement trading scores.
Do not implement backtests.
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

## Branch Routing Policy

The research ingestion layer classifies papers and extracted ideas using `research_branch`.

Allowed `research_branch` values:

- `technical`
- `valuation`
- `hybrid`
- `diagnostic`
- `out_of_scope`

The ingestion layer also assigns `downstream_route`.

Allowed `downstream_route` values:

- `technical_score_architect`
- `valuation_agent_handoff`
- `hybrid_split_required`
- `diagnostic_backlog`
- `reject_log`

The ingestion layer may additionally populate `main_score_branch_candidate` for compatibility with the root technical workflow.

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
- If routing is uncertain, set `manual_review_required: true` and use the more conservative route.

Examples:

```yaml
research_branch: valuation
downstream_route: valuation_agent_handoff
main_score_branch_candidate: unavailable
```

```yaml
research_branch: technical
downstream_route: technical_score_architect
main_score_branch_candidate: technical
```

```yaml
research_branch: hybrid
downstream_route: hybrid_split_required
main_score_branch_candidate: unavailable
```

---

## Classification Rules

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

Examples:

- book-to-market
- earnings yield
- cash-flow yield
- enterprise-value multiples
- gross profitability
- accrual anomaly
- quality factor
- analyst revision factor

Rules:

- Price-only evidence is not valuation evidence.
- Oversold technical signals are not valuation evidence.
- `valuation_status` must be `unavailable` unless point-in-time valuation data is available and explicitly validated.
- Valuation candidates must be routed to `valuation_agent_handoff`.

### Hybrid

Use `research_branch: hybrid` when the paper combines technical and valuation / fundamental inputs.

Examples:

- momentum conditioned on value factor
- trend signal gated by earnings revisions
- breakout signal weighted by profitability
- mean reversion filtered by quality factor

Rules:

- Hybrid papers must not be passed directly to the technical Score Architect as a complete score.
- Split into technical and valuation sub-ideas when possible.
- If the split is unclear, set `downstream_route: hybrid_split_required`.
- The technical portion may be routed separately only if it is independently defined and does not rely on valuation claims.

### Diagnostic

Use `research_branch: diagnostic` when the paper is about methodology, testing, data leakage, overfitting, turnover, transaction costs, redundancy, factor decay, publication bias, multiple testing, survivorship bias, or robustness.

Diagnostic items are useful for improving the research process, but they are not ranking alpha signals.

Examples:

- factor zoo warnings
- multiple testing correction
- backtest overfitting
- transaction cost sensitivity
- lookahead bias
- portfolio turnover analysis
- score correlation diagnostics
- data snooping controls

Rules:

- Diagnostic papers must be routed to `diagnostic_backlog`.
- Diagnostic items must not be converted into ranking scores.
- Diagnostic items may produce testing requirements, review checklist items, or methodology warnings.

### Out of Scope

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

Rules:

- Route to `reject_log`.
- State the reason explicitly.
- Do not silently repurpose out-of-scope ideas as technical scores.

---

## Evidence Status Policy

Every EvidenceCard must include `evidence_status`.

Allowed values:

- `metadata_only`
- `abstract_supported`
- `open_access_fulltext_supported`
- `paper_claim_only`
- `contradicted_or_unclear`
- `insufficient_information`

Rules:

- `metadata_only` means title and bibliographic metadata were available, but no abstract was used.
- `abstract_supported` means the abstract directly supported the extracted idea.
- `open_access_fulltext_supported` means approved open-access text was used.
- `paper_claim_only` means the paper claims an effect, but this repository has not tested it.
- `contradicted_or_unclear` means evidence is ambiguous, conflicting, or not enough for a clean handoff.
- `insufficient_information` means the paper cannot be interpreted safely from available fields.

Hard defaults:

- `paper_claim_not_verified: true`
- `no_score_adopted: true`
- `no_backtest_performed: true`

These flags must remain true for all ingestion outputs.

---

## Approved MVP Data Sources

Use official APIs or approved metadata endpoints only.

Recommended MVP implementation order:

1. arXiv
2. OpenAlex
3. Crossref
4. Semantic Scholar

Google Scholar is not an approved direct metadata source. It may be used only as a discovery-only channel through allowed local inputs:

- Google Scholar Alerts emails exported or labeled by the user
- manually exported BibTeX / EndNote / RefMan / RefWorks citation files
- manually curated paper title lists
- manually selected citation-alert seed papers

For the first MVP implementation, fully implementing arXiv and OpenAlex is acceptable. Crossref and Semantic Scholar may be added as enrichment adapters later. Google Scholar discovery import may be implemented as a seed importer that never calls `scholar.google.com`.

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

## Forbidden Sources and Behaviors

Do not scrape Google Scholar directly.
Do not crawl `scholar.google.com/scholar`.
Do not crawl Google Scholar search result pages.
Do not crawl Google Scholar pagination.
Do not crawl Google Scholar `Cited by` pages.
Do not crawl Google Scholar author profiles or library pages.
Do not bypass CAPTCHA or bot protection.
Do not use proxy rotation to access Google Scholar.
Do not use logged-in browser cookies for automated Scholar collection.
Do not use headless browser automation to extract Scholar results.
Do not use third-party Google Scholar scraper APIs as approved evidence sources.
Do not scrape publisher pages behind paywalls.
Do not use login-protected content.
Do not bypass robots.txt.
Do not ignore source terms of service.
Do not download PDFs unless explicitly allowed by policy and disabled-by-default config is turned on.
Do not use unofficial mirrors for fulltext collection.
Do not store private API keys in raw snapshots, logs, markdown reports, or Parquet files.

If a user requests a forbidden source, state the limitation in Korean and offer approved alternatives such as arXiv, OpenAlex, Crossref, Semantic Scholar, Google Scholar Alerts email import, or manual citation export import.

---

## Google Scholar Discovery Policy

Google Scholar may be referenced only as a human-assisted discovery channel.

The ingestion program must never fetch, crawl, parse, or automate Google Scholar web pages directly. It must not send HTTP requests to `scholar.google.com` except where a human manually opens Scholar outside the program.

Allowed Google Scholar discovery inputs:

1. Scholar Alerts emails that the user already received.
2. Local `.eml`, `.mbox`, `.html`, `.txt`, or `.json` exports of Scholar Alerts.
3. Manual BibTeX / EndNote / RefMan / RefWorks exports created by the user from the Scholar `Cite` UI.
4. Manual title lists curated by the user.
5. Manual citation-alert seed lists selected by the user.

Scholar-derived items are discovery seeds only. They are not paper evidence and are not normalized papers until resolved through approved metadata sources.

A Scholar-derived item must be resolved through at least one approved metadata source before becoming an EvidenceCard:

- arXiv
- OpenAlex
- Crossref
- Semantic Scholar

Scholar-derived data may populate only `DiscoverySeed` fields until resolution succeeds.

Rules:

- Do not treat Google Scholar snippets as evidence.
- Do not treat Google Scholar ranking as evidence strength.
- Do not treat Google Scholar citation count as alpha validation.
- Do not create an EvidenceCard from unresolved Scholar-only data.
- Do not download PDFs from Scholar links automatically.
- Do not follow Scholar result links automatically unless the target source is an approved metadata API and policy allows the request.
- If canonical metadata cannot be resolved, export the item to `unresolved_scholar_seeds.jsonl`.
- If an unresolved seed looks important, set `manual_review_required: true`.
- Scholar discovery import may read local files or an authorized internal mailbox export, but it must not log into Google or Gmail by default.

Allowed `source_channel` values for Scholar-derived seeds:

- `google_scholar_alert_email`
- `google_scholar_manual_bibtex`
- `google_scholar_manual_endnote`
- `google_scholar_manual_refman`
- `google_scholar_manual_refworks`
- `google_scholar_manual_title_list`
- `google_scholar_manual_citation_seed`

Required resolution outputs:

- `canonical_lookup_status`
- `matched_source`
- `canonical_paper_id`
- `resolution_confidence`
- `manual_review_required`

Allowed `canonical_lookup_status` values:

- `matched_openalex`
- `matched_crossref`
- `matched_arxiv`
- `matched_semantic_scholar`
- `multi_source_match`
- `ambiguous_match`
- `unresolved`

Allowed `resolution_confidence` values:

- `high`
- `medium`
- `low`
- `unresolved`

Resolution rules:

- Prefer exact DOI match.
- Then prefer exact arXiv ID match.
- Then prefer exact title plus year plus first author match.
- Then prefer high-confidence fuzzy title plus author match.
- If multiple plausible matches exist, set `canonical_lookup_status: ambiguous_match` and `manual_review_required: true`.
- Never silently choose a low-confidence match.

---

## Source Policy

### arXiv

Use the official arXiv API for search and metadata.

Rules:

- `min_interval_seconds` must be `>= 3.0`.
- Recommended default is `3.2` seconds to avoid boundary issues.
- `max_concurrency` must be `1`.
- Store raw Atom/XML response snapshots.
- Parse title, abstract, authors, published date, updated date, categories, arXiv ID, canonical URL, and PDF URL.
- Use `start` and `max_results` for paging.
- Avoid very broad queries that return huge result sets.
- Prefer narrower query packs over harvesting large result ranges.
- Do not download PDFs in MVP unless explicitly enabled and policy-approved.

Required normalized fields from arXiv:

- `source = "arxiv"`
- `arxiv_id`
- `title`
- `abstract`
- `authors`
- `publication_date`
- `updated_date`
- `categories`
- `source_url`
- `pdf_url`
- `raw_snapshot_path`

### OpenAlex

Use the OpenAlex Works API for scholarly metadata.

Rules:

- API key must come from environment variable or config reference.
- Do not hardcode API keys.
- Do not store API keys in request logs or raw request metadata.
- Store raw JSON response snapshots.
- Prefer `topics` / `primary_topic` over deprecated `concepts` when available.
- Reconstruct abstract text from `abstract_inverted_index` when needed.
- Parse `is_retracted` and block or flag retracted papers.
- Parse open-access fields, primary location, best open-access location, license, and PDF URL when available.
- Citation count is metadata only, not evidence strength.
- Do not use OpenAlex content download / PDF features in MVP unless explicitly allowed by policy and budget.

Required normalized fields from OpenAlex:

- `source = "openalex"`
- `openalex_id`
- `doi`
- `title`
- `abstract`
- `authors`
- `publication_year`
- `publication_date`
- `venue`
- `topics`
- `primary_topic`
- `citation_count`
- `open_access_status`
- `license`
- `is_retracted`
- `source_url`
- `pdf_url`
- `raw_snapshot_path`

### Crossref

Use Crossref for DOI and bibliographic metadata enrichment.

Rules:

- Crossref is not a fulltext source in MVP.
- Include contact email through `mailto` or identifiable agent header when configured.
- Respect `x-rate-limit-limit`, `x-rate-limit-interval`, and `x-concurrency-limit` response headers.
- Back off on HTTP 429.
- Treat HTTP 403 as blocked or policy failure requiring manual review.
- Store raw JSON response snapshots.
- Cache DOI lookups to avoid repeated requests.
- Do not use Crossref metadata as proof of alpha or implementation readiness.

Required normalized fields from Crossref:

- `source = "crossref"`
- `doi`
- `title`
- `authors`
- `publication_year`
- `publication_date`
- `venue`
- `publisher`
- `type`
- `reference_count`
- `is_referenced_by_count`
- `license`
- `source_url`
- `raw_snapshot_path`

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

Required normalized fields from Semantic Scholar:

- `source = "semantic_scholar"`
- `semantic_scholar_id`
- `doi`
- `arxiv_id`
- `title`
- `abstract`
- `authors`
- `publication_year`
- `venue`
- `fields_of_study`
- `citation_count`
- `influential_citation_count`
- `open_access_pdf_url`
- `source_url`
- `raw_snapshot_path`

### Google Scholar Discovery Inputs

Google Scholar is not a direct source adapter.

Implement Scholar handling as a discovery importer, not a crawler.

Allowed importer types:

- `scholar_alert_email_importer`
- `scholar_bibtex_importer`
- `scholar_title_list_importer`
- `scholar_citation_seed_importer`

Rules:

- Import only local files or explicit user-provided exports.
- Do not call `scholar.google.com`.
- Do not parse live Scholar web pages.
- Do not use browser automation.
- Do not use unofficial Scholar scraper APIs.
- Store allowed raw discovery inputs separately from API response snapshots.
- Redact email addresses from raw alert metadata when configured.
- Parse candidate title, snippet, displayed source, authors if available, and alert query if available.
- Resolve each seed through approved metadata adapters before normalization.
- Keep unresolved seeds in a separate unresolved queue.
- Report unresolved Scholar seeds in Korean.

Required normalized fields for Scholar discovery seeds:

- `source = "google_scholar"`
- `source_channel`
- `alert_query`
- `discovered_at`
- `raw_title`
- `raw_snippet`
- `raw_link_redacted`
- `candidate_title`
- `candidate_authors`
- `candidate_venue`
- `candidate_year`
- `raw_input_path`
- `canonical_lookup_status`
- `matched_source`
- `canonical_paper_id`
- `resolution_confidence`
- `manual_review_required`
- `notes_ko`

Resolution handoff:

```text
Scholar Alert / manual export
        ↓
DiscoverySeed
        ↓
canonical lookup using approved metadata APIs
        ↓
NormalizedPaper
        ↓
EvidenceCard
```

---

## Required Config Files

Create or update the following config files:

```text
config/research_sources.toml
config/research_queries.toml
config/research_policy.toml
config/research_classification.toml
config/research_scholar_discovery.toml
```

All source URLs, rate limits, timeouts, page sizes, query packs, classification keywords, branch toggles, and output paths should live in config rather than inline constants.

Hardcoding is allowed only for stable schema constants, unavoidable library quirks, or narrow compatibility shims. Any hardcoding must be documented.

---

## Example `config/research_sources.toml`

```toml
[global]
user_agent = "kospi200-research-ingestion/0.1"
default_timeout_seconds = 30
retry_max_attempts = 3
retry_backoff_seconds = [1, 3, 9]
raw_response_enabled = true
redact_secrets = true
pdf_download_default = false

[arxiv]
enabled = true
base_url = "https://export.arxiv.org/api/query"
min_interval_seconds = 3.2
max_concurrency = 1
timeout_seconds = 30
page_size = 100
max_results_per_query = 1000
sort_by = "relevance"
sort_order = "descending"
download_pdf_default = false

[openalex]
enabled = true
base_url = "https://api.openalex.org"
api_key_env = "OPENALEX_API_KEY"
timeout_seconds = 30
max_concurrency = 2
page_size = 100
redact_query_params = ["api_key"]
prefer_topics_over_concepts = true
parse_abstract_inverted_index = true
block_retracted = true
download_pdf_default = false

[crossref]
enabled = false
base_url = "https://api.crossref.org"
mailto_env = "RESEARCH_CONTACT_EMAIL"
user_agent = "kospi200-research-ingestion/0.1"
respect_rate_limit_headers = true
timeout_seconds = 30
max_concurrency = 1
cache_doi_lookups = true

[semantic_scholar]
enabled = false
base_url = "https://api.semanticscholar.org/graph/v1"
api_key_env = "SEMANTIC_SCHOLAR_API_KEY"
min_interval_seconds = 1.1
use_batch_endpoints = true
timeout_seconds = 30
fields = [
  "paperId",
  "title",
  "abstract",
  "authors",
  "year",
  "venue",
  "citationCount",
  "influentialCitationCount",
  "fieldsOfStudy",
  "externalIds",
  "openAccessPdf"
]

[google_scholar]
enabled = true
mode = "discovery_only"
direct_scraping_allowed = false
use_as_evidence_source = false
allowed_inputs = [
  "alert_email",
  "manual_bibtex",
  "manual_endnote",
  "manual_refman",
  "manual_refworks",
  "manual_title_list",
  "manual_citation_seed"
]
must_resolve_via = [
  "openalex",
  "crossref",
  "arxiv",
  "semantic_scholar"
]
store_raw_alert_email = true
store_raw_search_pages = false
redact_email_addresses = true
redact_tracking_params = true
follow_scholar_links = false
```

---

## Example `config/research_queries.toml`

```toml
[global]
default_max_papers_per_query = 100
language = "en"
include_korea_context = true
exclude_unavailable_data_by_default = false

[scholar_alerts.technical_momentum]
enabled = true
query = "\"cross-sectional momentum\" \"stock returns\""
branch_hint = "technical"
source_channel = "google_scholar_alert_email"

[scholar_alerts.technical_reversal]
enabled = true
query = "\"short-term reversal\" equities returns"
branch_hint = "technical"
source_channel = "google_scholar_alert_email"

[scholar_alerts.technical_analysis]
enabled = true
query = "\"technical analysis\" \"stock returns\""
branch_hint = "technical"
source_channel = "google_scholar_alert_email"

[scholar_alerts.methodology_factor_zoo]
enabled = true
query = "\"factor zoo\" \"transaction costs\" \"stock returns\""
branch_hint = "diagnostic"
source_channel = "google_scholar_alert_email"

[scholar_alerts.korea_kospi]
enabled = true
query = "\"KOSPI\" \"stock returns\" anomaly"
branch_hint = "technical"
context_tag = "korea_kospi"
source_channel = "google_scholar_alert_email"

[query_sets.technical_momentum]
branch_hint = "technical"
keywords = [
  "cross-sectional momentum stock returns",
  "time-series momentum equities",
  "relative strength stock ranking",
  "trend following equities",
  "moving average trading rules equity market"
]
exclude_keywords = [
  "cryptocurrency",
  "options",
  "futures only",
  "high frequency",
  "tick data",
  "order book"
]

[query_sets.technical_mean_reversion]
branch_hint = "technical"
keywords = [
  "short term reversal stock returns",
  "mean reversion equity ranking",
  "RSI stock returns",
  "oversold rebound equities"
]
exclude_keywords = [
  "cryptocurrency",
  "intraday only",
  "options"
]

[query_sets.technical_breakout_volatility]
branch_hint = "technical"
keywords = [
  "volatility breakout equities",
  "volatility compression stock returns",
  "squeeze breakout stock returns",
  "range expansion equity returns",
  "trend efficiency stock ranking"
]

[query_sets.technical_price_volume]
branch_hint = "technical"
keywords = [
  "price volume anomaly equities",
  "volume return predictability stocks",
  "liquidity stock returns",
  "turnover stock returns",
  "volume momentum equity returns"
]

[query_sets.fundamental_valuation]
branch_hint = "valuation"
requires_point_in_time_fundamentals = true
keywords = [
  "value factor stock returns",
  "book-to-market equity returns",
  "earnings yield stock returns",
  "cash flow yield stock returns",
  "quality factor profitability stock returns",
  "accrual anomaly equity returns"
]

[query_sets.hybrid_technical_valuation]
branch_hint = "hybrid"
requires_point_in_time_fundamentals = true
keywords = [
  "momentum and value stock returns",
  "technical analysis and fundamental analysis equity returns",
  "trend following value stocks",
  "quality momentum stock returns",
  "fundamental momentum equity returns"
]

[query_sets.methodology_diagnostics]
branch_hint = "diagnostic"
keywords = [
  "factor zoo multiple testing stock returns",
  "backtest overfitting financial strategies",
  "transaction costs equity anomalies",
  "look-ahead bias stock return prediction",
  "survivorship bias stock return anomalies",
  "cross-sectional ranking portfolio turnover",
  "factor decay equity anomalies"
]

[query_sets.korea_kospi_context]
branch_hint = "technical"
context_tag = "korea_kospi"
keywords = [
  "KOSPI stock returns anomalies",
  "Korean stock market momentum",
  "Korea Exchange equity factors",
  "KOSPI200 constituents quantitative strategy",
  "emerging markets equity factor returns"
]
```

---

## Example `config/research_policy.toml`

```toml
[scope]
primary_market = "KOSPI200"
primary_frequency = "daily"
primary_data = ["OHLCV", "derived technical indicators", "rolling statistics"]
allow_intraday = false
allow_options = false
allow_crypto = false
allow_execution_algos = false
allow_black_box_ml = false

[pdf]
download_enabled = false
open_access_required = true
license_required = true
store_fulltext = false
store_extracted_text = false

[secrets]
redact_env_vars = [
  "OPENALEX_API_KEY",
  "SEMANTIC_SCHOLAR_API_KEY",
  "CROSSREF_PLUS_API_KEY",
  "RESEARCH_CONTACT_EMAIL"
]
redact_query_params = ["api_key", "token", "key"]
redact_headers = ["Authorization", "Crossref-Plus-API-Token", "x-api-key"]

[guardrails]
no_score_adoption = true
no_backtesting = true
no_strategy_optimization = true
no_google_scholar_scraping = true
no_google_scholar_live_http = true
no_scholar_captcha_bypass = true
no_scholar_proxy_rotation = true
no_paywall_scraping = true
no_price_only_valuation = true
manual_review_on_uncertainty = true

[google_scholar_discovery]
enabled = true
discovery_only = true
require_canonical_resolution = true
allow_alert_email_import = true
allow_manual_bibtex_import = true
allow_manual_title_list_import = true
allow_manual_citation_seed_import = true
allow_live_scholar_requests = false
allow_headless_browser = false
allow_third_party_scraper_api = false
unresolved_output = "data/research/discovery/unresolved_scholar_seeds.jsonl"
```

---

## Example `config/research_scholar_discovery.toml`

```toml
[import]
enabled = true
mode = "discovery_only"
input_root = "data/research/discovery/google_scholar"
allowed_file_extensions = [".eml", ".mbox", ".html", ".txt", ".bib", ".ris", ".json", ".csv"]
store_raw_inputs = true
redact_email_addresses = true
redact_tracking_params = true

[alert_email]
enabled = true
input_dir = "data/research/discovery/google_scholar/alerts"
label_hint = "Research/ScholarAlerts"
parse_subject = true
parse_body_links = true
parse_received_at = true

[manual_bibtex]
enabled = true
input_dir = "data/research/discovery/google_scholar/bibtex"

[manual_title_list]
enabled = true
input_dir = "data/research/discovery/google_scholar/title_lists"

[manual_citation_seed]
enabled = true
input_dir = "data/research/discovery/google_scholar/citation_seeds"

[resolution]
required = true
sources = ["openalex", "crossref", "arxiv", "semantic_scholar"]
prefer_exact_doi = true
prefer_exact_arxiv_id = true
title_fuzzy_threshold = 0.92
ambiguous_match_manual_review = true
unresolved_manual_review = true
max_candidates_per_seed = 5

[outputs]
seeds_jsonl = "data/research/discovery/scholar_discovery_seeds.jsonl"
resolved_jsonl = "data/research/discovery/resolved_scholar_seeds.jsonl"
unresolved_jsonl = "data/research/discovery/unresolved_scholar_seeds.jsonl"
resolution_report = "reports/research_ingestion/scholar_discovery_report.md"
```

---

## Example `config/research_classification.toml`

```toml
[branches.technical]
include_terms = [
  "momentum",
  "reversal",
  "moving average",
  "trend following",
  "breakout",
  "volatility breakout",
  "volatility compression",
  "RSI",
  "oscillator",
  "price-volume",
  "liquidity",
  "turnover",
  "serial dependence",
  "correlation structure"
]
exclude_if_requires = [
  "point-in-time fundamentals",
  "analyst revisions",
  "order book",
  "tick data"
]

[branches.valuation]
include_terms = [
  "book-to-market",
  "earnings yield",
  "value factor",
  "cash flow yield",
  "profitability",
  "quality factor",
  "accrual",
  "leverage",
  "enterprise value",
  "analyst revision"
]
requires_point_in_time_fundamentals = true

[branches.hybrid]
include_terms = [
  "momentum and value",
  "technical and fundamental",
  "quality momentum",
  "value momentum",
  "fundamental momentum"
]
manual_review_required = true

[branches.diagnostic]
include_terms = [
  "backtest overfitting",
  "multiple testing",
  "data snooping",
  "look-ahead bias",
  "survivorship bias",
  "transaction cost",
  "turnover",
  "factor zoo",
  "publication bias",
  "factor decay",
  "robustness"
]

[branches.out_of_scope]
include_terms = [
  "cryptocurrency",
  "option pricing",
  "futures",
  "market making",
  "order book",
  "tick data",
  "high frequency",
  "execution algorithm",
  "reinforcement learning execution",
  "volatility surface"
]
```

---

## Required Directory Structure

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

data/
  research/
    raw/
    discovery/
      google_scholar/
        alerts/
        bibtex/
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
      scholar_bibtex.py
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
    test_scholar_bibtex_importer.py
    test_scholar_resolution.py
    test_normalize.py
    test_dedupe.py
    test_classify.py
    test_evidence_schema.py
    test_redaction.py
    test_reporting.py
```

---

## Raw Response Persistence Policy

Store raw API response bodies for reproducibility.

Rules:

- Store raw response body.
- Store request metadata with secrets redacted.
- Store response headers only after removing sensitive headers.
- Store source, query ID, run ID, timestamp, HTTP status, retry count, and content hash.
- Never store raw API keys in files, logs, reports, Parquet, JSONL, markdown, or exceptions.
- Raw snapshots must be deterministic enough for audit but safe enough for repository use.
- If a source returns a policy-sensitive field, keep it only if allowed by policy.

Suggested paths:

```text
data/research/raw/source=arxiv/run_id=YYYYMMDD_HHMMSS/query_id=technical_momentum/page=0001.xml
data/research/raw/source=openalex/run_id=YYYYMMDD_HHMMSS/query_id=value_factor/page=0001.json
data/research/raw/source=crossref/run_id=YYYYMMDD_HHMMSS/query_id=doi_enrichment/page=0001.json
data/research/raw/source=semantic_scholar/run_id=YYYYMMDD_HHMMSS/query_id=related_papers/page=0001.json
data/research/discovery/google_scholar/alerts/run_id=YYYYMMDD_HHMMSS/email=0001.eml
data/research/discovery/google_scholar/bibtex/run_id=YYYYMMDD_HHMMSS/file=0001.bib
```

Each raw snapshot metadata record should include:

```yaml
source: string
run_id: string
query_id: string
page: integer
request_url_redacted: string
request_params_redacted: object
http_status: integer
response_headers_redacted: object
retry_count: integer
fetched_at_utc: string
content_hash_sha256: string
raw_snapshot_path: string
```

---

## DiscoverySeed Schema

Scholar-derived inputs must first become `DiscoverySeed` records.

A `DiscoverySeed` is not an EvidenceCard and is not a normalized paper. It is only a candidate item that must be resolved through approved metadata APIs.

Required fields:

```yaml
DiscoverySeed:
  discovery_seed_id: string
  source: google_scholar
  source_channel: google_scholar_alert_email | google_scholar_manual_bibtex | google_scholar_manual_endnote | google_scholar_manual_refman | google_scholar_manual_refworks | google_scholar_manual_title_list | google_scholar_manual_citation_seed
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
    canonical_lookup_status: matched_openalex | matched_crossref | matched_arxiv | matched_semantic_scholar | multi_source_match | ambiguous_match | unresolved
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
```

Hard rules:

- `scholar_seed_only` must be true.
- `not_evidence` must be true.
- `no_score_adopted` must be true.
- A `DiscoverySeed` must not be routed to Score Architect directly.
- A `DiscoverySeed` must become a resolved `NormalizedPaper` before EvidenceCard generation.

---

## Normalized Paper Schema

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

## Deduplication Policy

Paper deduplication must be deterministic and conservative.

Dedup priority:

1. DOI exact match.
2. arXiv ID exact match.
3. Semantic Scholar paper ID exact match.
4. OpenAlex ID exact match.
5. Crossref DOI exact match.
6. Normalized title + publication year + first author fuzzy match.

Canonical ID priority:

1. DOI if available.
2. arXiv ID if DOI is unavailable.
3. OpenAlex ID if DOI and arXiv ID are unavailable.
4. Semantic Scholar ID if prior IDs are unavailable.
5. Stable hash of `title_normalized + publication_year + first_author`.

Rules:

- Do not discard duplicate source evidence.
- Merge duplicate records into one `NormalizedPaper`.
- Preserve `same_as_sources` and all source IDs.
- If fuzzy matching confidence is low, do not merge; set `manual_review_required: true`.
- Do not merge two papers only because titles are similar.
- Retractions must propagate to the merged canonical record.

---

## EvidenceCard Contract

Every candidate idea must be exported as an EvidenceCard before downstream review.

EvidenceCards are not score definitions.
EvidenceCards are not backtest results.
EvidenceCards are not adoption decisions.

Required schema:

```yaml
EvidenceCard:
  evidence_card_id: string
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
    point_in_time_fundamentals_required: boolean
    intraday_required: boolean
    order_book_required: boolean
    alternative_data_required: boolean
    formula_clarity: exact | partial | vague | not_specified
    implementation_readiness: 0 | 1 | 2 | 3
    data_compatibility: list[string]

  risks:
    lookahead_risk_flag: boolean
    data_snooping_risk_flag: boolean
    transaction_cost_missing_flag: boolean
    turnover_risk_flag: boolean
    universe_mismatch_flag: boolean
    survivorship_bias_risk_flag: boolean
    publication_bias_risk_flag: boolean
    redundancy_risk_flag: boolean

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

## Implementation Readiness Scale

Use `implementation_readiness` to prevent paper claims from being treated as immediately implementable scores.

Allowed values:

- `0`: Too vague or insufficient information.
- `1`: Direction is interesting, but formula/specification is insufficient.
- `2`: Implementation may be possible, but data timing, availability, or formula details require review.
- `3`: Sufficiently specified for Score Architect or valuation-agent handoff.

Rules:

- `3` does not mean adoption.
- `3` does not mean the paper claim is true.
- `3` only means the downstream agent has enough structure to review the idea.
- If point-in-time data is required but unavailable, do not set `implementation_readiness` above `2`.
- If the idea requires intraday, order book, or alternative data unavailable in the repo, set `blocked_by_data` or route to `reject_log`.

---

## Data Compatibility Labels

Use `data_compatibility` labels to make handoff safer.

Allowed labels:

- `ohlcv_available`
- `daily_bar_compatible`
- `derived_indicator_compatible`
- `rolling_statistics_compatible`
- `point_in_time_fundamentals_required`
- `intraday_required`
- `order_book_required`
- `analyst_revision_required`
- `text_or_news_required`
- `alternative_data_required`
- `unavailable_in_current_repo`
- `unknown_data_requirements`

Rules:

- If valuation or fundamentals are required, include `point_in_time_fundamentals_required`.
- If data is not available in the current repo, include `unavailable_in_current_repo`.
- If requirements are unclear, include `unknown_data_requirements` and set `manual_review_required: true`.

---

## Candidate Idea Extraction Policy

The agent may extract candidate ideas only from:

- title
- abstract
- metadata fields
- source-provided categories / topics / fields of study
- approved open-access text if policy allows it

Rules:

- Do not infer formulas that are not described.
- Do not invent missing windows, thresholds, weights, or scoring directions.
- Do not convert broad factor names into implementation-ready formulas without explicit specification.
- Do not infer valuation availability from technical price behavior.
- If only a broad factor family is available, set `formula_clarity: vague` or `not_specified`.
- If the abstract describes a directional signal but no formula, set `formula_clarity: partial`.
- If implementation needs human review, set `manual_review_required: true`.

---

## Handoff Policy

### Technical handoff

Only EvidenceCards with all of the following may be handed to the main technical Score Architect:

- `research_branch: technical`
- `downstream_route: technical_score_architect`
- `main_score_branch_candidate: technical` or `diagnostic`
- no required valuation data
- no intraday-only requirement
- no order-book-only requirement
- no unresolved retraction flag

The handoff artifact should be written to:

```text
data/research/evidence/technical_candidates.jsonl
reports/research_ingestion/technical_handoff_summary.md
```

### Valuation handoff

EvidenceCards requiring fundamentals must be handed to the valuation agent.

The handoff artifact should be written to:

```text
data/research/evidence/valuation_candidates.jsonl
reports/research_ingestion/valuation_handoff_summary.md
```

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

### Diagnostic handoff

Diagnostic items should produce methodology notes, not score candidates.

Write to:

```text
data/research/evidence/diagnostic_items.jsonl
reports/research_ingestion/diagnostic_backlog.md
```

### Reject log

Out-of-scope or unsafe items should be written to:

```text
data/research/evidence/reject_log.jsonl
reports/research_ingestion/rejected_items.md
```

Every rejected item must include a clear Korean reason.

---

## Required Outputs

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
reports/research_ingestion/handoff_summary.md
```

Optional outputs:

```text
data/research/indexes/paper_id_map.json
data/research/indexes/doi_map.json
data/research/indexes/title_hash_map.json
reports/research_ingestion/query_coverage.csv
reports/research_ingestion/source_error_log.csv
reports/research_ingestion/manual_review_queue.md
```

---

## Korean Ingestion Report Requirements

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

## CLI Requirements

Provide a simple CLI for reproducible runs.

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

python -m research_ingestion resolve-scholar-seeds \
  --sources openalex,crossref,arxiv,semantic_scholar \
  --run-id 20260424_000000

python -m research_ingestion normalize \
  --run-id 20260424_000000

python -m research_ingestion classify \
  --run-id 20260424_000000

python -m research_ingestion evidence \
  --run-id 20260424_000000

python -m research_ingestion report \
  --run-id 20260424_000000

python -m research_ingestion run-all \
  --sources arxiv,openalex \
  --query-set technical_momentum \
  --run-id 20260424_000000
```

Rules:

- CLI arguments must not expose API keys.
- `run-id` should be explicit or auto-generated deterministically by timestamp.
- `--dry-run` should show planned sources, queries, and output paths without calling external APIs.
- `--no-pdf` should be the default behavior.
- `--allow-pdf` must require explicit policy confirmation.
- Scholar import commands must read local inputs only and must not call `scholar.google.com`.
- Scholar resolution commands may call only approved metadata APIs.

---

## Testing Requirements

The MVP implementation must include tests for:

- config loading
- missing config handling
- source adapter initialization
- arXiv Atom/XML parsing
- arXiv rate limiter behavior
- arXiv paging parameter generation
- OpenAlex JSON parsing
- OpenAlex `abstract_inverted_index` reconstruction
- OpenAlex topics / primary topic parsing
- OpenAlex retraction flag handling
- Crossref DOI enrichment parsing
- Crossref rate-limit header handling
- Semantic Scholar field parsing
- Semantic Scholar batch request construction
- Scholar Alerts local email parsing
- Scholar BibTeX manual export parsing
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
- implementation readiness assignment
- price-only valuation rejection
- hybrid split-required routing
- diagnostic item routing
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

## Failure and Limitation Reporting Policy

When a failure occurs, report it conservatively in Korean.

Examples:

- `OpenAlex 요청 중 429가 발생하여 backoff 후 재시도했습니다.`
- `이 논문은 abstract가 없어 metadata_only로 분류했습니다.`
- `이 후보는 공식 formula가 확인되지 않아 implementation_readiness: 1로 둡니다.`
- `이 아이디어는 point-in-time fundamentals가 필요하므로 technical_score_architect로 전달하지 않습니다.`
- `이 논문은 out_of_scope입니다. 이유: intraday order book 데이터가 필요합니다.`
- `Google Scholar seed는 OpenAlex/Crossref/arXiv/Semantic Scholar에서 canonical match가 확인되지 않아 unresolved로 보관했습니다.`
- `Google Scholar 직접 요청은 정책상 금지되어 local alert/email export만 처리합니다.`

Do not hide failures.
Do not silently skip failed queries.
Do not silently downgrade source errors into successful results.
Do not treat missing abstracts as clean evidence.

---

## Security and Secret Handling

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

## Conservative Review Checklist

Before exporting EvidenceCards, check:

- Is this paper retracted?
- Is this a technical, valuation, hybrid, diagnostic, or out-of-scope item?
- Does the idea require point-in-time fundamentals?
- Does the idea require intraday, tick, or order book data?
- Does the idea require unavailable alternative data?
- Is the formula clear enough for downstream review?
- Is the evidence title-only, abstract-supported, or fulltext-supported?
- Are there obvious lookahead risks?
- Are transaction costs or turnover likely material?
- Is the universe compatible with KOSPI200 constituent ranking?
- Is the paper about index timing rather than stock ranking?
- Is this diagnostic rather than alpha?
- Does this candidate risk duplicating existing score families?

If any answer is unclear, set `manual_review_required: true`.

---

## Done Means

A research-ingestion task is done only if:

- the responsible agent role is clear
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

## Final Reminder

This agent is a research-ingestion builder, not a quant alpha selector.

Its job is to create clean, conservative, source-aware EvidenceCards and handoff files.

It must make downstream review easier without weakening the repository's guardrails.
