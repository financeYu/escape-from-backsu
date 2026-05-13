# v1.0-rc Guardrail Audit

## HorizonPolicy
- supported_horizons: 1d, 1m, 1w
- explicit_default_1d: True
- hidden_1d_hardcoding_found: False
- status: COMPLETE

## Evidence / Selector / Review Boundaries
- core_boundary_lock_status: COMPLETE
- core_boundary_evidence_only: True
- core_boundary_candidate_only: True
- core_boundary_manual_review_support: True
- core_boundary_live_trading_enabled: False
- core_boundary_brokerage_integration_enabled: False
- core_boundary_order_generation_enabled: False
- core_boundary_buy_sell_hold_framing_present: False
- core_boundary_valuation_fundamental_active_scoring_enabled: False
- core_boundary_futures_index_macro_regime_active_scoring_enabled: False
- core_boundary_production_ranking_replacement_enabled: False
- core_boundary_blockers: none
- evidence_only_boundary_preserved: True
- candidate_only_boundary_preserved: True
- manual_review_only_boundary_preserved: True
- selector_output_review_prioritization_only: True
- manual_review_packet_requires_manual_review: True
- production_ranking_changed: False
- backtest_feedback_score_optimization_introduced: False
- prohibited_flags_false: True
- valuation_fundamental_active_layers: []
- futures_index_macro_regime_active_layers: []
- valuation_fundamental_active_scoring_enabled: False
- futures_index_macro_regime_active_scoring_enabled: False
- universe_expansion_introduced: False
- new_market_data_ingestion_introduced: False
- status: COMPLETE
- prohibited_language_leaks: none

## Route State Alignment
- expected_route_state: active_v1_0_rc_phase_9_readiness_route
- status: COMPLETE
- missing_required_markers: none
- stale_markers: none
