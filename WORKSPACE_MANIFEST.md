# WORKSPACE_MANIFEST

workspace_id: mvp_v0_1_freeze
branch: main
role: root-master-integration
task_type: release_freeze_status_control
active_step: post-MVP v0.2 predictive probability score route / candidate-only implementation approved
owner_or_worker: root master agent
created_from_commit: f7c3734

## Purpose

Record the MVP v0.1 freeze decision and manage the post-MVP `v0.2 predictive
probability score route` Step from the root/master integration workspace. This
is release/status-control, approval-record, and review/audit coordination work
only. It preserves the Step 20 KOSPI200 technical-only baseline as frozen and
routes `prob_up_1d_candidate` implementation to a separate role branch/worktree.

This task must not be treated as broad Step 21 entry. It does not activate new
markets, production ranking, valuation scoring, new data ingestion, trading
recommendations, `final_composite_score` replacement, or backtest feedback.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- AGENTS.md
- .agents/skills/
- .github/workflows/
- Quant_mvp/__init__.py
- Quant_mvp/AGENTS.md
- Quant_mvp/config/
- Quant_mvp/docs/
- Quant_mvp/reports/
- Quant_mvp/agents/audit/AGENTS.md
- Quant_mvp/agents/valuation/AGENTS.md
- Quant_mvp/backtest_mvp/
- chart_mvp/AGENTS.md
- chart_mvp/README.md
- chart_mvp/TEMPORARY_TOP5_OVERRIDE.md
- chart_mvp/app/run_gui.py
- chart_mvp/scripts/run_top5_gui.bat
- chart_mvp/src/stock_core/
- chart_mvp/tests/
- config/
- docs/config_policy.md
- docs/contracts/quant_umbrella_handoff_contract.md
- docs/context/
- docs/development_environment.md
- docs/extension/
- docs/release/
- docs/releases/
- docs/roadmap_status.md
- docs/root_hard_stops.md
- docs/project_checklist.md
- docs/review_mvp_policy.md
- gui_mvp/
- quant_project_reference_for_chatgpt_project_current.md
- reports/validation/
- reserch_mvp/AGENTS.md
- reserch_mvp/config/
- reserch_mvp/reports/research_ingestion/
- reserch_mvp/research_ingestion/
- reserch_mvp/src/research_ingestion/
- reserch_mvp/tests/research_ingestion/
- review_mvp/
- scripts/
- src/backtest/
- src/preprocess/
- src/reports/
- src/scanner/
- src/scores/
- src/validation/
- src/valuation/
- tests/backtest/
- tests/context/
- tests/data_validation/
- tests/gui_mvp/
- tests/reports/
- tests/scanner/
- tests/validation/
- tests/valuation/
- tests/test_step9_scores_part_a.py
- tests/test_step9_scores_part_b.py
- tests/test_step10_normalization_cross_sectional.py
- tests/test_step10_normalization_timeseries.py
- tests/test_step11_composite_schema.py

## Read-Only Paths

- completed Step artifacts except targeted handoff, context, config, and
  validation references needed by the collected support branches
- generated market caches
- generated runtime report roots except explicit validation/handoff reports
- secrets and local environment files

## Forbidden Actions

- KOSDAQ150, futures, options, NASDAQ/overseas, or multi-universe activation
- new external market-data source ingestion
- runtime score formula, score weight, score adoption, normalization, ranking,
  report, backtest, or valuation semantic implementation outside the approved
  `prob_up_1d_candidate` candidate-only implementation scope
- `technical_composite_score` or `final_composite_score` semantic changes
- valuation/fundamental scoring activation or financial/fundamental data in
  technical/final composite scoring
- backtest-driven score optimization or return feedback into upstream ranking
- trading recommendations, buy/sell/hold wording, or proven-alpha claims
- committing raw local market caches, chart images, secrets, `.env` files, or
  nested worktree artifacts
- unrelated cleanup, reset, history rewrite, or broad refactor

## Expected Handoff Output

- source-controlled MVP v0.1 freeze record
- compact context and status docs updated from freeze-ready to frozen
- future work routed to separately approved post-MVP versions/Steps
- focused validation summary
- latest local Quant project context snapshot refresh only when explicitly requested by the user
- remaining risk summary for root/master final merge

## Required Validation

- python -m pytest -q -p no:cacheprovider tests/gui_mvp chart_mvp/tests/test_gui_financials.py tests/backtest
- python -m pytest -q -p no:cacheprovider tests/backtest/test_conservative_backtest_core.py tests/data_validation/test_schema_validation_contract.py tests/reports/test_step16_security_detail_report.py tests/reports/test_step16_security_detail_report_contracts.py tests/scanner/test_latest_ranking_symbol_policy.py tests/test_step10_normalization_cross_sectional.py tests/test_step10_normalization_timeseries.py tests/test_step9_scores_part_a.py tests/test_step9_scores_part_b.py tests/validation/test_step15_latest_ranking_guardrails.py chart_mvp/tests/test_market_extensibility.py
- python -c "import pathlib,tomllib; [tomllib.loads(pathlib.Path(p).read_text(encoding='utf-8')) for p in ('Quant_mvp/config/scores.toml','Quant_mvp/config/weights.toml')]"
- python scripts/run_local_validation.py chart
- python scripts/run_local_validation.py context
- python scripts/run_local_validation.py reports-backtest
- python -m pytest -q -p no:cacheprovider reserch_mvp/tests/research_ingestion
- python -m pytest -q -p no:cacheprovider tests/context tests/test_step11_composite_schema.py
- python -m unittest discover -s review_mvp/tests -v
- python scripts/context/check_context_staleness.py
- python scripts/context/check_context_conflicts.py
- python scripts/build_review_packet.py --step "Step20-MVP-v0.1-freeze" --stage "master-up-pending"
- python scripts/refresh_quant_project_context.py --user-requested (only when explicitly requested by the user)
- git diff --check

## Handoff Notes

This workspace records the root/master MVP v0.1 freeze decision. Root/master
may inspect focused freeze evidence first and avoid repeating completed Step
1-20 history unless validation or conflict checks point to a specific risk.
