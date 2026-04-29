# v0.3 KOSPI200 Historical Universe Tracking Contract

Status: contract-only historical universe tracking proposal.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Related registry: `docs/extension/v0_3_strategy_candidate_registry_contract.md`.
Owner lane: root governance with chart_mvp runtime handoff review.

This contract defines how KOSPI200 historical membership, security identity,
and corporate-action events should be represented before any later approved
runtime or data-ingestion task. It supports point-in-time candidate/evidence
work. It does not authorize new market-data ingestion, live vendor assumptions,
production ranking behavior changes, report behavior changes, or automatic
production activation.

## Boundary

Allowed:

- define KOSPI200 historical membership schema and validation rules
- define security identity fields for company, ticker, ISIN, and stable
  project-local IDs
- define corporate-action event fields for name changes, ticker changes,
  delisting, mergers, splits, and successor mapping
- define point-in-time universe reconstruction semantics for historical
  candidate/evidence work
- define handoff requirements for a later root-approved chart_mvp runtime task
- define fixture-only or contract-only examples for deterministic tests

Blocked without later explicit approval:

- automatic collection from KRX, Naver, pykrx, or any new live data source
- changing the default scanner runtime universe from current KOSPI200 to a
  one-year historical constituent superset
- adding KOSDAQ150, futures, options, Nasdaq, overseas, or multi-universe scope
- feeding historical universe expansion into production ranking or reports
- using membership changes, delisting, or price-only evidence as valuation
  language
- automatic production activation from candidate/evidence outputs

## Purpose

The current KOSPI200 list is not enough for one-year historical evaluation.
Historical candidate/evidence work needs the set of securities that were in
KOSPI200 at each decision date, including securities that later left the index,
changed names, changed tickers, merged, or delisted.

The contract separates three concerns:

1. `index_membership_history`: who belonged to KOSPI200 and when.
2. `security_master`: how the same listed security is identified over time.
3. `corporate_action_events`: what identity or listing events changed and when.

This separation prevents survivorship bias and avoids treating lookup failures
as missing data when they may be valid delisting or identity-change outcomes.

## Required Artifacts

Proposed contract-owned paths:

- `docs/extension/v0_3_kospi200_historical_universe_tracking_contract.md`

Future fixture or schema paths, only after a separate implementation task:

- `Quant_mvp/tests/fixtures/v0_3_kospi200_membership_history_minimal.toml`
- `Quant_mvp/tests/test_v0_3_kospi200_historical_universe_contract.py`
- `chart_mvp/tests/fixtures/kospi200_historical_universe_minimal.csv`

Future generated or local data paths, only after a separate approved
data-ingestion or runtime task:

- `chart_mvp/data/kospi200_membership_history.csv`
- `chart_mvp/data/security_master.csv`
- `chart_mvp/data/corporate_action_events.csv`

Generated or local data files remain non-default context and must not be
source-controlled unless explicitly promoted as small review fixtures.

## Membership History Schema

`index_membership_history` records KOSPI200 membership intervals.

Required fields:

- `membership_id`: stable record ID.
- `index_code`: must be `KOSPI200`.
- `security_id`: stable project-local security ID.
- `isin`: ISIN when available, otherwise explicit `unknown`.
- `ticker`: ticker valid for the membership source date.
- `company_name`: company name valid for the membership source date.
- `effective_start`: first date the security is treated as a member.
- `effective_end`: last date the security is treated as a member, or empty for
  currently active membership.
- `change_type`: one of `initial_snapshot`, `added`, `removed`, `rebalanced`,
  `manual_correction`, or `unknown`.
- `source_ref`: source document, file, or provider label.
- `source_observed_at`: date or timestamp when the source was observed.
- `as_of_policy`: point-in-time rule used to decide availability.
- `raw_record_hash`: optional hash of the raw source row or payload.

Rules:

- `effective_start` must be less than or equal to `effective_end` when
  `effective_end` is present.
- Overlapping active intervals for the same `index_code` and `security_id`
  are invalid unless the overlap is explicitly marked `manual_correction`.
- A historical evaluation must use membership available at the decision date,
  not a future revised constituent list.
- Current KOSPI200 membership must not be backfilled across the previous year
  without source evidence for each effective interval.

## Security Master Schema

`security_master` records stable identity across ticker or name changes.

Required fields:

- `security_id`: stable project-local security ID.
- `isin`: ISIN when available.
- `ticker`: ticker value.
- `ticker_start`: first date the ticker is valid.
- `ticker_end`: last date the ticker is valid, or empty if current.
- `company_name`: company name value.
- `name_start`: first date the company name is valid.
- `name_end`: last date the company name is valid, or empty if current.
- `exchange`: exchange or market label, for example `KRX`.
- `listing_status`: one of `listed`, `delisted`, `merged`, `suspended`,
  `unknown`, or `not_applicable_for_fixture`.
- `source_ref`: source document, file, or provider label.

Rules:

- `security_id` is the primary join key between membership, price data, and
  corporate-action events.
- Ticker is not a permanent identity key.
- Company name is not a permanent identity key.
- ISIN is preferred when available, but missing ISIN must be represented
  explicitly rather than silently replaced by ticker.

## Corporate Action Event Schema

`corporate_action_events` records identity and listing events that affect
historical tracking.

Required fields:

- `event_id`: stable event ID.
- `security_id`: affected security ID.
- `event_type`: one of `name_change`, `ticker_change`, `delisting`, `merger`,
  `split`, `spin_off`, `successor_mapping`, `listing_status_change`,
  `manual_correction`, or `unknown`.
- `event_date`: effective date of the event.
- `old_value`: previous ticker, name, status, or related ID where applicable.
- `new_value`: new ticker, name, status, or related ID where applicable.
- `successor_security_id`: successor ID for merger, split, spin-off, or
  mapping events when applicable.
- `source_ref`: source document, file, or provider label.
- `point_in_time_availability`: when the event information was knowable.

Rules:

- Delisting is not a data error by itself.
- A lookup failure after delisting must be distinguishable from a provider or
  cache failure.
- Successor mappings must not imply continuous return history unless a later
  evaluation contract explicitly defines an adjustment rule.
- Corporate-action information available only after the decision date must not
  be used to construct historical eligibility for that earlier date.

## Point-In-Time Universe Function

The contract-level function is:

```text
point_in_time_universe(index_code, decision_date, lookback_window)
```

For this request, the intended parameters are:

- `index_code = KOSPI200`
- `decision_date = evaluation or runtime reference date`
- `lookback_window = one_year`

The function returns securities with any valid KOSPI200 membership overlap
inside the requested lookback window, including securities that are no longer
listed on the decision date. Each returned row must include:

- `security_id`
- `ticker_as_of_decision_date` when listed, or explicit
  `not_listed_on_decision_date`
- `last_known_ticker` when no decision-date ticker is valid
- `company_name_as_of_decision_date` when listed, or `last_known_company_name`
  when no decision-date name is valid
- `membership_intervals`
- `listing_status_on_decision_date`
- `identity_event_flags`
- `source_refs`
- `point_in_time_check`

For delisted, merged, or renamed securities, the implementation must preserve
the last known identity available at or before the decision date, or the
identity valid at the membership interval end when the security is no longer
listed. It must not synthesize a current ticker, drop the security, or treat the
row as a provider/cache failure solely because no decision-date ticker exists.

This produces a one-year KOSPI200 historical constituent set. It is a tracking
universe for candidate/evidence work and must not become the default production
scanner universe without a later root-approved runtime task.

## Validation Rules

Required validation checks for a later implementation:

- membership interval overlap check
- same-date point-in-time availability check
- current-list backfill leakage check
- delisted-security retention check
- ticker and name change continuity check
- successor mapping non-continuity check unless an explicit adjustment rule
  exists
- generated-output boundary check
- no production activation wording check

Minimum deterministic fixture scenarios:

- a continuously listed constituent
- a constituent added during the one-year window
- a constituent removed during the one-year window
- a constituent that changed name
- a constituent that changed ticker
- a constituent that delisted
- a constituent involved in a successor mapping

## Handoff To chart_mvp

A later chart_mvp implementation task may consume this contract only after
root/master explicitly authorizes the implementation scope. That future task
must state whether it is:

- fixture-only schema/test work
- local file ingestion from already approved source files
- runtime-local historical universe reconstruction
- default scanner universe behavior change

The first three may be narrow implementation tasks if separately approved. The
fourth is a production behavior change and requires a separate root-approved
runtime decision.

## Review Checklist

Before any later implementation is accepted:

- KOSPI200 remains the only universe.
- No live vendor or new market-data source is silently assumed.
- Historical membership is point-in-time and avoids future data.
- Delisted, renamed, and ticker-changed securities remain traceable.
- Generated local data remains outside default context and source control.
- No ranking, report, score, valuation, or automatic activation behavior is
  changed by this contract.
