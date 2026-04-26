# WORKSPACE_MANIFEST

workspace_id: master_up_post20_pending
branch: codex/master-up-post20-pending
role: root-master-integration
task_type: master_up_integration_preparation
active_step: Step 20 COMPLETE / MVP v0.1 pre-freeze hardening and readiness merge
owner_or_worker: root master agent
created_from_commit: f6f51e9eaa15562899611124646859031cc0533e

## Purpose

Prepare Step 20 closure and MVP v0.1 freeze-support branches for root/master
review by integrating their commits into one conflict-resolved master-up branch.

This branch preserves the Step 20 final baseline and records work that belongs
to MVP v0.1 freeze preparation. It must not be treated as Step 21 entry. It
does not activate new markets, valuation scoring, new data ingestion, trading
recommendations, or backtest feedback. It collects:

1. runtime and validation optimizations needed before MVP v0.1 freeze
2. pre-freeze config, release, and local market-data readiness notes
3. review_mvp worktree-exclusion and modification-boundary repair
4. research ingestion operations optimization handoff
5. local Review Gate and on-demand review skill routing docs
6. pre-freeze GUI extraction into `gui_mvp`
7. approved MVP v0.1 pre-freeze readiness policy and symbol-contract refactors
8. research-informed Quant candidate-governance notes and inactive config
   metadata

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
- docs/context/
- docs/development_environment.md
- docs/extension/
- docs/release/
- docs/releases/
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

- docs/project_checklist.md
- docs/roadmap_status.md
- completed Step artifacts except targeted handoff, context, config, and
  validation references needed by the collected support branches
- generated market caches
- generated runtime report roots except explicit validation/handoff reports
- secrets and local environment files

## Forbidden Actions

- KOSDAQ150, futures, options, NASDAQ/overseas, or multi-universe activation
- new external market-data source ingestion
- score formula, score weight, score adoption, normalization, ranking, report,
  backtest, or valuation semantic changes beyond the reviewed support-branch
  patches
- `technical_composite_score` or `final_composite_score` semantic changes
- valuation/fundamental scoring activation or financial/fundamental data in
  technical/final composite scoring
- backtest-driven score optimization or return feedback into upstream ranking
- trading recommendations, buy/sell/hold wording, or proven-alpha claims
- committing raw local market caches, chart images, secrets, `.env` files, or
  nested worktree artifacts
- unrelated cleanup, reset, history rewrite, or broad refactor

## Expected Handoff Output

- one conflict-resolved master-up integration branch for Step 20 closure and
  MVP v0.1 freeze preparation
- retained branch-local handoff documents for pre-freeze review_mvp, research
  ingestion, GUI extraction, and readiness support work
- focused validation summary
- latest local Quant project context snapshot refresh
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
- python scripts/refresh_quant_project_context.py
- git diff --check

## Handoff Notes

This branch is intended as a master-up integration branch for Step 20 closure
and MVP v0.1 freeze preparation. Root/master may inspect focused handoff
documents first and avoid repeating completed Step 1-20 history unless
validation or conflict checks point to a specific risk.
