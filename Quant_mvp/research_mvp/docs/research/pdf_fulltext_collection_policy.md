# PDF/fulltext Collection Policy

This document defines the local `research_mvp` policy for PDF or fulltext
collection. Collection is allowed only for noncommercial research purposes after
explicit license, source, access, and local custody checks. It prepares local
EvidenceCard review material only; it does not authorize score adoption,
ranking, backtests, valuation verdicts, or trading claims.

## Default State

- PDF/fulltext collection is allowed only for explicit open or noncommercial
  research-compatible license candidates.
- Runtime collection remains opt-in through `--allow-pdf` plus the configured
  policy confirmation phrase.
- `research_policy.toml` must keep the license allowlist, blocked TDM licenses,
  blocked access markers, and max-download limits explicit.
- Collection outputs are local-custody artifacts. External upload,
  redistribution, and Git tracking of raw/fulltext/cache data remain disallowed
  unless a separate task explicitly promotes a safe review fixture.

## Required Trace

PDF/fulltext candidates must carry these trace fields before download:

- `license_name`
- `license_url`
- `license_checked_at`
- `license_evidence_quote`
- `collection_basis`
- `fulltext_source_type`
- `fulltext_review_scope`
- `redistribution_allowed`
- `external_upload_allowed`

`redistribution_allowed` and `external_upload_allowed` are explicit source
license facts. They no longer block local download readiness by themselves.
Local collection still does not perform external upload or redistribution.

## Automatic Exclusions

The pipeline must not automatically collect:

- paywall, login, subscription, institutional access, Shibboleth, SSO, or TDM
  access paths
- `scholar.google.com` URLs
- non-PDF responses
- Wiley, Elsevier, Springer, or similar publisher TDM-only licenses
- missing or license-ambiguous fulltext candidates

Google Scholar remains discovery-only. The pipeline must not automatically
download PDFs from Scholar links.

## Allowed Use

Allowed local uses:

- `full_text_reviewed` or `license_verified_pdf_collected` EvidenceCard support
- downstream contract design support
- source/license provenance review

Disallowed uses:

- score definition or score adoption
- ranking generation or report behavior changes
- backtests, performance proof, or alpha claims
- valuation verdicts or trading recommendations
- external upload, redistribution, or Git tracking of PDF/fulltext artifacts

## Git Tracking Check

Raw, PDF/fulltext, and request-cache outputs must remain untracked:

```powershell
git ls-files -- data/research/raw data/research/fulltext data/research/request_cache
git check-ignore -v data/research/fulltext/example.pdf data/research/raw/example.json data/research/request_cache/example.json
```

The first command should return no tracked raw/fulltext/cache artifacts. The
second command should show the `.gitignore` rule blocking those paths. If tracked
raw/PDF/fulltext artifacts are found, close the collection gate as `NEEDS FIX`.

## Closure Report

Separate these items in the final report:

- PDF/fulltext policy result
- EvidenceCard policy changes
- Git tracking check result
- validation command result
- remaining risks

Required boundary statements:

- This work did not adopt a score.
- This work did not run a backtest.
- Paper claims are not proven alpha.
- Valuation candidates still require the separate valuation review skill.
