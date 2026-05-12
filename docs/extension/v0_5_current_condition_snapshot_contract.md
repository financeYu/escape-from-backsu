# v0.5 Current Condition Snapshot Contract

Status: active contract for fail-closed personal decision support snapshots.
Parent route: `docs/extension/v0_5_personal_decision_support_route.md`.

## Purpose

`CurrentConditionSnapshot` records whether a v0.5
`PersonalDecisionSupportPacket` has an approved, current, KOSPI/KOSPI200-only
condition snapshot. It is a decision-support input only. It does not create
orders, position sizing, live trading behavior, or production activation.

## Boundary

The first implementation is fail-closed. If an approved current-condition input
is not supplied, every candidate remains `blocked_missing_current_condition`.

This contract does not authorize:

- new market-data ingestion
- new vendor/live data assumptions
- KOSDAQ150, futures, options, Nasdaq, overseas, or multi-universe expansion
- buy/sell/hold/rebalance/move-to-cash instructions
- target price, expected return, profit, or position-size claims
- brokerage integration, order generation, or production activation

## Required Fields

Each snapshot row must include:

- `snapshot_id`
- `candidate_id`
- `candidate_version`
- `as_of_date`
- `universe_boundary`
- `data_source_ref`
- `price_recency_status`
- `liquidity_check`
- `cost_profile_ref`
- `condition_check_status`
- `current_condition_status`
- `no_new_ingestion_check`
- `no_universe_expansion_check`
- `no_order_generation_check`
- `manual_review_required`

## Allowed Statuses

`current_condition_status` values:

- `blocked_missing_current_condition`
- `snapshot_available`

`condition_check_status` values:

- `blocked_missing_approved_current_condition_snapshot`
- `current_condition_passed`
- `current_condition_failed`
- `current_condition_not_checked`

## Snapshot Availability Rule

`snapshot_available` is allowed only when all are true:

- `universe_boundary = KOSPI_or_KOSPI200_only`
- `no_new_ingestion_check = pass_no_new_market_data_ingestion`
- `no_universe_expansion_check = pass_no_universe_expansion`
- `no_order_generation_check = pass_no_order_generation`
- `data_source_ref` points to an approved local KOSPI/KOSPI200 lane artifact
- `price_recency_status` and `liquidity_check` are not blank

If any item is missing, the row must fail closed as
`blocked_missing_current_condition`.

## Packet Integration

`PersonalDecisionSupportPacket` may consume this snapshot as a read-only input.
The packet must keep transaction action language forbidden even when a snapshot
is available. Snapshot availability may change review status, but it must not
generate an action, rank, order, or position size.
