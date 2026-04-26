# MVP v0.1 Pre-Freeze Checklist

## 1. Scope / Contract Gate

### P0 Freeze Blockers
- [ ] Universe is not KOSPI200 only.
- [ ] technical_composite_score semantics changed.
- [ ] final_composite_score semantics changed.
- [ ] valuation/fundamental enters score/final/ranking.
- [ ] KOSDAQ150, futures, options, overseas, or multi-universe behavior is active.
- [ ] Future/planned extension material is described as implemented MVP behavior.

### P1 Pre-Freeze Recommended
- [ ] Confirm `final_composite_score = technical_composite_score` for MVP v0.1.
- [ ] Confirm ranking uses one same-date KOSPI200 technical snapshot.
- [ ] Confirm valuation/fundamental fields remain candidate-only or display-only.
- [ ] Confirm all future expansion references are marked blocked/planned only.

### P2 Post-Freeze Acceptable
- [ ] Plan KOSDAQ150 or overseas routing only after an approved future step.
- [ ] Plan futures/options routing only after an approved future step.
- [ ] Plan valuation activation only after point-in-time availability proof.

### Evidence Required
- [ ] `docs/context/MVP_V0_1_BASELINE.md`
- [ ] `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- [ ] `docs/contracts/step20_composite_contract.md`
- [ ] `docs/contracts/step20_ranking_contract.md`
- [ ] `docs/context/EXTENSION_REGISTRY.toml`

### Common Failure Modes
- [ ] Treating extension registry entries as implementation approval.
- [ ] Adding a new universe through config, docs, examples, or output schema.
- [ ] Calling a technical-only final score valuation-aware.
- [ ] Updating contract wording without matching validation evidence.

## 2. Data Reliability

### P0 Freeze Blockers
- [ ] missing/bad data silently passes.
- [ ] Future-dated, duplicate ticker/date, or non-six-digit ticker rows can rank.
- [ ] Missing direct score inputs receive favorable values instead of explicit neutral shrinkage.
- [ ] Manual-review or blocked-by-data rows can enter direct ranking.
- [ ] Data source assumptions require live network access to validate MVP v0.1.

### P1 Pre-Freeze Recommended
- [ ] Confirm coverage, warmup, validity, and neutral shrinkage fields are visible.
- [ ] Confirm bad OHLCV, duplicate rows, and insufficient history are rejected or flagged.
- [ ] Confirm local market-cache readiness is evidence, not a source-controlled baseline.
- [ ] Confirm raw market data and runtime caches are ignored unless promoted as small fixtures.

### P2 Post-Freeze Acceptable
- [ ] Add new vendor readiness checks only in an approved future step.
- [ ] Add expanded local-cache diagnostics without changing scoring semantics.
- [ ] Add broader PIT financial availability checks for valuation planning only.

### Evidence Required
- [ ] `docs/contracts/step20_ranking_contract.md`
- [ ] `reports/validation/mvp_v0_1_local_market_data_readiness.md`
- [ ] Focused data validation test results for any changed validation surface.
- [ ] `git status` showing no raw data, cache, or generated artifact staged.

### Common Failure Modes
- [ ] Treating absent data as bullish or rankable.
- [ ] Preserving ticker as number and losing leading zeros.
- [ ] Reusing stale per-ticker rows from older dates in latest ranking.
- [ ] Promoting local cache state into context, baseline, or release claims.

## 3. Algorithm Reliability

### P0 Freeze Blockers
- [ ] look-ahead bias risk remains.
- [ ] Non-finite, blocked, rejected, diagnostic-only, or context-only scores can enter the composite.
- [ ] Direct family composition differs from the frozen Step 20 contract.
- [ ] Score status, quality, warmup, or coverage gates are bypassed.
- [ ] Tie handling is not deterministic.

### P1 Pre-Freeze Recommended
- [ ] Confirm direct families are `mean_reversion_family_score` and `trend_breakout_family_score`.
- [ ] Confirm missing direct scores shrink to neutral `0.0` and are counted.
- [ ] Confirm higher `final_composite_score` ranks better.
- [ ] Confirm tied scores sort by six-digit ticker ascending.

### P2 Post-Freeze Acceptable
- [ ] Evaluate new technical families only after documented score-definition approval.
- [ ] Add diagnostics that remain non-score, non-ranking context.
- [ ] Refactor implementation internals without changing contract semantics.

### Evidence Required
- [ ] `docs/contracts/step20_composite_contract.md`
- [ ] `docs/contracts/step20_ranking_contract.md`
- [ ] Scanner/ranking focused test results when algorithm surfaces change.
- [ ] Diff review showing no score formula, weight, or normalization semantic change.

### Common Failure Modes
- [ ] Reclassifying diagnostics as direct score inputs.
- [ ] Changing weights while calling the result a documentation update.
- [ ] Sorting blocked rows ahead of rankable rows.
- [ ] Using future return, realized return, or backtest fields as upstream inputs.

## 4. Backtest Reliability

### P0 Freeze Blockers
- [ ] backtest output feeds scoring/ranking.
- [ ] Backtest results alter score definitions, weights, adoption states, or report semantics.
- [ ] Backtest consumes future data relative to the tested decision date.
- [ ] Backtest language is used as a proven alpha or expected return claim.
- [ ] Evaluation-only backtest outputs are stored as MVP baseline inputs.

### P1 Pre-Freeze Recommended
- [ ] Confirm Step 17 backtest output remains evaluation-only.
- [ ] Confirm reports describe backtest results without recommendation language.
- [ ] Confirm no ranking command reads generated backtest reports as input.
- [ ] Confirm any backtest evidence records commit, input, config, and validation profile.

### P2 Post-Freeze Acceptable
- [ ] Add broader backtest diagnostics without upstream scoring feedback.
- [ ] Plan walk-forward or robustness checks as evaluation-only future work.
- [ ] Compare strategies only after the MVP freeze decision is recorded.

### Evidence Required
- [ ] `docs/release/MVP_V0_1_VALIDATION_LADDER.md`
- [ ] Step 17 boundary docs or release evidence when freeze validation includes backtests.
- [ ] Diff review showing no scoring/ranking dependency on generated backtest outputs.
- [ ] Generated backtest artifacts remain outside source-controlled baseline docs.

### Common Failure Modes
- [ ] Tuning technical score weights from backtest performance.
- [ ] Treating a diagnostic metric as an adoption decision.
- [ ] Copying generated backtest reports into context or release baseline.
- [ ] Using performance wording that implies trade advice.

## 5. Deployable MVP

### P0 Freeze Blockers
- [ ] MVP cannot be run/validated from docs alone.
- [ ] Required commands, inputs, outputs, or validation tiers are missing or stale.
- [ ] MVP requires personal machine paths, secrets, or unstated local services.
- [ ] Runtime output paths can overwrite source-controlled baseline files.
- [ ] User-facing MVP docs claim live production readiness.

### P1 Pre-Freeze Recommended
- [ ] Confirm quickstart names the supported MVP behavior and unsupported extensions.
- [ ] Confirm validation ladder maps docs-only, focused, integration, and full-suite checks.
- [ ] Confirm generated reports, charts, pipeline summaries, and caches have non-source-controlled paths.
- [ ] Confirm paths are repository-relative or configurable.

### P2 Post-Freeze Acceptable
- [ ] Add packaging, installer, or scheduled-run polish after freeze.
- [ ] Add richer operational monitoring without changing scoring/ranking behavior.
- [ ] Add new deployment environments only after explicit scope approval.

### Evidence Required
- [ ] `docs/release/MVP_V0_1_QUICKSTART.md`
- [ ] `docs/release/MVP_V0_1_VALIDATION_LADDER.md`
- [ ] `docs/releases/step20_mvp_final_report.md`
- [ ] Fresh command results for the chosen validation profile.

### Common Failure Modes
- [ ] Assuming local cache presence is the same as deployability.
- [ ] Documenting commands that require untracked secrets.
- [ ] Mixing generated runtime outputs with release evidence.
- [ ] Claiming production readiness from fixture-only validation.

## 6. Reproducibility / Validation

### P0 Freeze Blockers
- [ ] same commit + same input + same config is not reproducible.
- [ ] Validation profile is missing, ambiguous, or not tied to the checked commit.
- [ ] Local-only data or generated outputs are required but not recorded as limitations.
- [ ] `git diff --check` or equivalent whitespace validation fails.
- [ ] Required freeze evidence cannot be traced to source-controlled docs or commands.

### P1 Pre-Freeze Recommended
- [ ] Record commit checked, validation profile, and evidence reviewed in the Freeze Decision Record.
- [ ] Run Tier 1 context/guardrail checks for docs/context changes.
- [ ] Run focused scanner/report/validation checks when contract or output interpretation changes.
- [ ] Run full suite only for final freeze or broad integration changes.

### P2 Post-Freeze Acceptable
- [ ] Add reproducibility tooling for generated reports after freeze.
- [ ] Add historical validation summaries as archive-only references.
- [ ] Expand validation fixtures without changing MVP semantics.

### Evidence Required
- [ ] `git status`
- [ ] `git diff`
- [ ] `git diff --check`
- [ ] Selected validation commands and results.
- [ ] Commit hash after the freeze checklist commit.

### Common Failure Modes
- [ ] Running validation on a different commit than the one being checked.
- [ ] Reusing stale local outputs without naming the limitation.
- [ ] Recording PASS without command output or scope.
- [ ] Treating archive history as current validation.

## 7. Extensibility

### P0 Freeze Blockers
- [ ] Future expansion is activated without a separately approved post-MVP step.
- [ ] Extension docs change current MVP scoring, ranking, ingestion, or output semantics.
- [ ] Extension registry state is changed from blocked/planned to implemented.
- [ ] Future universe fields appear in current ranking or report outputs.
- [ ] Valuation/fundamental extension planning changes MVP final score behavior.

### P1 Pre-Freeze Recommended
- [ ] Confirm future expansion context is routing-only or planning-only.
- [ ] Confirm policy injection points do not activate new market ingestion.
- [ ] Confirm future work names required approval, branch/worktree, and conflict checkpoint.
- [ ] Confirm KOSPI200/Naver/six-digit assumptions are explicit where current MVP requires them.

### P2 Post-Freeze Acceptable
- [ ] Open a future KOSDAQ150, overseas, futures/options, or valuation step after freeze.
- [ ] Add new schemas only after ownership and generated-output boundaries are approved.
- [ ] Add cross-universe comparison only after a separate roadmap gate.

### Evidence Required
- [ ] `docs/context/EXTENSION_REGISTRY.toml`
- [ ] `docs/context/CHANGE_IMPACT_MATRIX.yml`
- [ ] Future domain context docs when an extension is discussed.
- [ ] Diff review showing no activation paths in code, config, tests, or docs.

### Common Failure Modes
- [ ] Marking planned expansion as available to users.
- [ ] Adding example output columns for blocked markets.
- [ ] Hiding activation in config defaults.
- [ ] Treating readiness refactors as Step 21 entry.

## 8. Maintainability

### P0 Freeze Blockers
- [ ] Existing roadmap, history, context, code, tests, scoring, ranking, backtest, data ingestion, or config files are rewritten for this docs-only sidecar task.
- [ ] Checklist text copies long prose from existing docs instead of compact references.
- [ ] Active baseline conflicts with authority order or hard-stop policy.
- [ ] The file embeds generated logs, raw market data, chart images, secrets, or archive bodies.
- [ ] Review scope cannot identify current requirements versus future/planned extensions.

### P1 Pre-Freeze Recommended
- [ ] Keep checklist bullets compact and verifiable.
- [ ] Reference evidence paths instead of duplicating source documents.
- [ ] Keep current MVP requirements separate from future/planned extensions.
- [ ] Keep docs-only diff additive under `docs/context/`.

### P2 Post-Freeze Acceptable
- [ ] Consolidate duplicate docs after freeze through an explicit docs cleanup task.
- [ ] Add cross-links from routing docs after root/master approval.
- [ ] Archive superseded pre-freeze material only through the archive process.

### Evidence Required
- [ ] `git diff -- docs/context/MVP_V0_1_PRE_FREEZE_CHECKLIST.md`
- [ ] `git diff --name-only`
- [ ] Review of source-controlled versus generated-output boundaries.
- [ ] No unrelated files staged for this commit.

### Common Failure Modes
- [ ] Editing authority files to make the new checklist fit.
- [ ] Importing old Step history into active context.
- [ ] Adding narrative background that weakens checklist usability.
- [ ] Mixing implementation TODOs with freeze blockers.

## 9. Safety / Claims Hygiene

### P0 Freeze Blockers
- [ ] buy/sell/hold, investment recommendation, proven-alpha, expected-return wording exists.
- [ ] Price-only technical evidence is described as cheap, value, undervalued, bargain, or target-price support.
- [ ] MVP outputs imply market-beating performance or investment suitability.
- [ ] Backtest diagnostics are presented as alpha proof.
- [ ] Valuation/fundamental candidate data is described as active scoring support.

### P1 Pre-Freeze Recommended
- [ ] Confirm user-facing wording says technical-only scanner, not trading system.
- [ ] Confirm report language preserves uncertainty and avoids valuation claims.
- [ ] Confirm validation results are stated as evidence of software behavior, not expected returns.
- [ ] Confirm candidate-only valuation status is explicit where valuation is mentioned.

### P2 Post-Freeze Acceptable
- [ ] Add investor-facing risk disclosures only after release copy is explicitly in scope.
- [ ] Add educational explanations without recommendation or expected-return wording.
- [ ] Add future performance-analysis docs as evaluation-only material.

### Evidence Required
- [ ] Forbidden-language search over changed source-controlled files.
- [ ] `docs/contracts/step20_composite_contract.md`
- [ ] `docs/contracts/step20_ranking_contract.md`
- [ ] Changed-doc review for claim hygiene.

### Common Failure Modes
- [ ] Translating technical oversold into value or cheapness.
- [ ] Describing rankings as picks.
- [ ] Calling backtest improvement validated alpha.
- [ ] Using expected-return wording in examples or headings.

## 10. Git / Release Operations

### P0 Freeze Blockers
- [ ] secrets/raw market data/cache/generated artifacts enter repo/context/baseline docs.
- [ ] Unrelated dirty files are staged or committed with the checklist.
- [ ] Existing docs are heavily rewritten instead of adding the sidecar checklist.
- [ ] Commit is made before status, diff, and validation checks are reviewed.
- [ ] Push is performed without explicit root instruction.

### P1 Pre-Freeze Recommended
- [ ] End sequence uses local git only: `git status`, `git diff`, validation checks, commit.
- [ ] Commit only `docs/context/MVP_V0_1_PRE_FREEZE_CHECKLIST.md`.
- [ ] Leave unrelated dirty files unstaged and report that separation.
- [ ] Record commit hash and push state in the final report.

### P2 Post-Freeze Acceptable
- [ ] Push only after root explicitly instructs.
- [ ] Tag or release only after freeze decision is GO.
- [ ] Delete disposable branches only after integration target is accepted.

### Evidence Required
- [ ] Final `git status`
- [ ] Final `git diff`
- [ ] Validation command results.
- [ ] Commit hash for this checklist.
- [ ] Confirmation that no push occurred.

### Common Failure Modes
- [ ] Accidentally staging pre-existing unrelated changes.
- [ ] Committing generated validation outputs.
- [ ] Running fetch, pull, or push during local-only work.
- [ ] Treating a docs-only checklist commit as the freeze decision itself.

## Freeze Decision Record

- Freeze decision: GO / NO-GO
- Commit checked:
- Validation profile:
- P0 blockers remaining:
- P1 deferred:
- Evidence reviewed:
- Known limitations:
- Next allowed step:
- Explicitly blocked expansions:
