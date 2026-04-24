# Valuation Pre-Screening

## Scope and current hard blockers

This document records a conservative pre-screening pass for valuation candidates in the KOSPI200 stock-level research system.

Weaknesses and blockers first:

- valuation work is separated from the main technical agent into `agents/valuation/AGENTS.md`.
- valuation score examples are stored in `agents/valuation/valuation_scores.example.toml`, not in the main `config/scores.toml`.
- `config/data.toml` currently sets `point_in_time_fundamentals = false`.
- `config/data.toml` currently sets `quality_fields = false`.
- `config/data.toml` currently sets `analyst_revisions = false`.
- `config/data.toml` currently sets `sector_metadata = false`.

Because of those flags, no valuation candidate is test-ready in the current repository state.
This pre-screening pass therefore does not promote any valuation score to implementation now.
It only defines a conservative staging slate for later implementation once point-in-time-safe data is explicitly available.

Source note:

- `earnings_yield`, `book_to_price`, `operating_cash_flow_yield`, `gross_profitability`, and `accrual_quality_penalty` are present only as separated valuation-agent examples.
- `revision_supported_value` and `kospi200_relative_drawdown_discount` are included as screened ideas that should not move forward in the current design.
- Any Korea-specific fit judgment below is an inference, not an established empirical conclusion in this repository.

## Candidate evaluations

### 1. earnings_yield

- score_name: `earnings_yield`
- score_family: `raw valuation`
- score_branch: `valuation`
- role_type: `core`
- purpose: Measure how cheap or expensive a stock is relative to point-in-time-safe trailing earnings.
- why_it_might_work: If earnings are durable enough, lower price paid per unit of earnings may help identify stocks that are mispriced on a stock-level basis.
- why_it_might_fail: Cyclical earnings, negative earnings, financial-sector accounting differences, stale filings, and value traps can all weaken the raw signal.
- raw_input_features: `price`, `market_cap`, `shares_outstanding` if needed, `point_in_time trailing net income or operating earnings`, `filing date or effective date`
- minimum_viable_formula: `earnings_yield_raw = ttm_net_income_pti / market_cap_t`; winsorize cross-sectionally, invalidate stale observations, neutral-shrink non-positive or missing cases before percentile mapping
- likely_overlap_with: `book_to_price`, `operating_cash_flow_yield`, `enterprise_value style ratios`
- valuation_purity: `high`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `medium`
- revision_dependency: `none`
- implementation_risk: `medium`
- korea_kospi200_fit: `medium`
- testing_priority: `high`
- recommendation: `defer`
- pretest_comment: Worth keeping on the shortlist, but implementation should wait until explicit point-in-time earnings availability and filing-lag policy exist.

### 2. book_to_price

- score_name: `book_to_price`
- score_family: `raw valuation`
- score_branch: `valuation`
- role_type: `core`
- purpose: Measure how cheaply the market values common equity relative to point-in-time book equity.
- why_it_might_work: This is a simple and interpretable asset-anchor valuation ratio that may add distinct information where earnings are temporarily weak or noisy.
- why_it_might_fail: Sector dependence is high, intangible-heavy firms can look structurally expensive, financials need special care, and cheap book equity alone does not prevent value traps.
- raw_input_features: `price`, `market_cap`, `shares_outstanding` if needed, `point_in_time common equity or book equity`, `filing date or effective date`, `sector or industry classification if later adjusted`
- minimum_viable_formula: `book_to_price_raw = common_equity_pti / market_cap_t`; percentile-rank valid observations cross-sectionally and keep any later sector adjustment separate
- likely_overlap_with: `earnings_yield`, `sector_relative_value_spread`, `gross_profitability as a value-trap filter`
- valuation_purity: `high`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `high`
- revision_dependency: `none`
- implementation_risk: `medium`
- korea_kospi200_fit: `high`
- testing_priority: `high`
- recommendation: `defer`
- pretest_comment: This appears worth testing only after point-in-time book equity is available; sector distortion should be handled as a later secondary adjustment, not in the first raw score.

### 3. free_cash_flow_yield

- score_name: `free_cash_flow_yield`
- score_family: `raw valuation`
- score_branch: `valuation`
- role_type: `core`
- purpose: Measure price relative to free cash generation rather than accounting earnings.
- why_it_might_work: If cash generation is more reliable than reported earnings, the ratio may help avoid some accrual-heavy cheap-looking names.
- why_it_might_fail: Capex definitions are often noisy, negative or unstable cash flow is common, sector comparability is uneven, and this can become implementation-heavy too early.
- raw_input_features: `price`, `market_cap`, `point_in_time operating cash flow`, `point_in_time capex`, `filing date or effective date`
- minimum_viable_formula: This should first be simplified into `operating_cash_flow_yield = ttm_operating_cash_flow_pti / market_cap_t`; only reintroduce full free cash flow after capex mapping is stable and documented
- likely_overlap_with: `earnings_yield`, `gross_profitability`, `accrual_quality_penalty`
- valuation_purity: `high`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `medium`
- revision_dependency: `none`
- implementation_risk: `high`
- korea_kospi200_fit: `medium`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: The idea is not rejected, but the first pass should avoid a full free-cash-flow construction and start with a simpler operating-cash-flow-yield proxy.

### 4. gross_profitability

- score_name: `gross_profitability`
- score_family: `profitability`
- score_branch: `valuation`
- role_type: `adjustment`
- purpose: Refine raw value signals by favoring cheap firms with better gross-profit generation relative to assets.
- why_it_might_work: It may help separate cheap-and-productive firms from cheap-but-weak firms and can act as a conservative value-trap adjustment.
- why_it_might_fail: Valuation purity is lower than a raw price-to-fundamental ratio, sector margin structures differ, and it should not be sold as raw cheapness.
- raw_input_features: `point_in_time revenue`, `point_in_time cost_of_goods_sold or gross profit`, `point_in_time total assets`, `filing date or effective date`
- minimum_viable_formula: `gross_profitability_raw = ttm_gross_profit_pti / average_total_assets_pti`; use as a separate overlay or adjustment, not as the main raw valuation score
- likely_overlap_with: `operating_margin quality`, `return_on_assets`, `earnings_yield as a coarse trap filter`
- valuation_purity: `medium`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `medium`
- revision_dependency: `none`
- implementation_risk: `medium`
- korea_kospi200_fit: `medium`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: This is better treated as an adjustment layered on top of a raw value ratio, not as a standalone replacement for raw valuation.

### 5. accrual_quality_penalty

- score_name: `accrual_quality_penalty`
- score_family: `accounting quality`
- score_branch: `valuation`
- role_type: `adjustment`
- purpose: Penalize cheap stocks whose reported earnings quality looks weak relative to cash flow support.
- why_it_might_work: It may reduce value-trap exposure when cheapness is driven by accrual-heavy earnings rather than cash-backed profitability.
- why_it_might_fail: Required fields are not currently available, financial-sector comparability is weak, and implementation can become fragile if definitions are not tightly controlled.
- raw_input_features: `point_in_time net income`, `point_in_time operating cash flow`, `point_in_time total assets`, `filing date or effective date`
- minimum_viable_formula: `accrual_ratio_raw = (ttm_net_income_pti - ttm_operating_cash_flow_pti) / average_total_assets_pti`; invert or penalize high-accrual names only after a raw value score already exists
- likely_overlap_with: `operating_cash_flow_yield`, `gross_profitability`, `earnings quality overlays`
- valuation_purity: `medium`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `medium`
- revision_dependency: `none`
- implementation_risk: `high`
- korea_kospi200_fit: `medium`
- testing_priority: `low`
- recommendation: `defer`
- pretest_comment: This should wait until basic raw value scores and quality fields are available; otherwise the implementation path is unclear.

### 6. sector_relative_earnings_yield

- score_name: `sector_relative_earnings_yield`
- score_family: `sector-relative valuation`
- score_branch: `valuation`
- role_type: `adjustment`
- purpose: Re-express raw earnings yield relative to sector peers so that structural sector pricing differences do not dominate the signal.
- why_it_might_work: It may improve comparability across capital-intensive and structurally high-multiple sectors if the raw signal is already valid.
- why_it_might_fail: The usefulness may come mainly from sector preference rather than the raw valuation signal, sector metadata is currently unavailable, and narrow sectors may create unstable ranks.
- raw_input_features: `earnings_yield_raw`, `sector or industry classification`, `same-date peer group membership`
- minimum_viable_formula: Compute `earnings_yield_raw` first, store it separately, then map a secondary within-sector percentile or robust z-score as an overlay
- likely_overlap_with: `book_to_price`, `raw earnings_yield`, `sector preference effects`
- valuation_purity: `medium`
- expected_return_linkage: `medium`
- point_in_time_safety: `conditional`
- sector_dependence: `high`
- revision_dependency: `none`
- implementation_risk: `medium`
- korea_kospi200_fit: `medium`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: This is better treated as an adjustment only after a raw valuation score exists and sector metadata is explicitly available.

### 7. revision_supported_value

- score_name: `revision_supported_value`
- score_family: `revision enhancement`
- score_branch: `valuation`
- role_type: `out_of_scope`
- purpose: Combine cheapness with supportive analyst estimate revisions.
- why_it_might_work: Possibly useful only if revisions are point-in-time-safe and meaningfully reduce false-positive cheap names.
- why_it_might_fail: Revision data is excluded by default, point-in-time safety is difficult, overlap with re-rating narratives is high, and evidence is not established yet in this repository.
- raw_input_features: `earnings_yield_raw or book_to_price_raw`, `point_in_time analyst revision series`, `trailing revision window definition`
- minimum_viable_formula: No first-pass implementation is recommended under the current project scope; keep revision work separate from the default valuation model
- likely_overlap_with: `earnings_yield`, `post-earnings re-rating themes`, `market expectation overlays`
- valuation_purity: `medium`
- expected_return_linkage: `unknown`
- point_in_time_safety: `unsafe`
- sector_dependence: `medium`
- revision_dependency: `high`
- implementation_risk: `high`
- korea_kospi200_fit: `unknown`
- testing_priority: `low`
- recommendation: `reject`
- pretest_comment: This should not move forward in the current round because revision dependency is high and default scope explicitly excludes it.

### 8. kospi200_relative_drawdown_discount

- score_name: `kospi200_relative_drawdown_discount`
- score_family: `market-context adjustment`
- score_branch: `out_of_scope`
- role_type: `out_of_scope`
- purpose: Treat stock underperformance versus the KOSPI200 as evidence of cheapness.
- why_it_might_work: The only plausible support is a narrative claim that markets may overreact, not a direct price-to-fundamental relationship.
- why_it_might_fail: This is not valuation, it overlaps heavily with technical mean-reversion or relative-strength logic, and it violates the stock-level valuation purity rule.
- raw_input_features: `stock return`, `KOSPI200 return`, `relative drawdown`, `relative performance window`
- minimum_viable_formula: `relative_underperformance_percentile` versus the KOSPI200 over a trailing window
- likely_overlap_with: `low momentum`, `drawdown depth`, `mean reversion`, `relative weakness`
- valuation_purity: `low`
- expected_return_linkage: `low`
- point_in_time_safety: `safe`
- sector_dependence: `low`
- revision_dependency: `none`
- implementation_risk: `low`
- korea_kospi200_fit: `low`
- testing_priority: `low`
- recommendation: `reject`
- pretest_comment: Reject for valuation testing. This should remain outside the valuation branch and should not be re-labeled as value.

## Recommended pretest slate

Current round decision:

- No valuation candidate should move into implementation now because point-in-time-safe fundamentals are unavailable in config.

If point-in-time fundamentals later become available, the conservative first-pass slate should be:

1. `earnings_yield`
2. `book_to_price`
3. `operating_cash_flow_yield` as the simplified cash-flow value candidate
4. `gross_profitability` only as an adjustment, not as the main raw valuation score

Lower-priority later additions:

1. `accrual_quality_penalty`
2. `sector_relative_earnings_yield`

Items screened out for the current design:

1. `revision_supported_value`
2. `kospi200_relative_drawdown_discount`

## Implementation notes for the Score Architect

- Keep raw valuation scores separate from sector-relative overlays.
- Keep raw value separate from profitability and accounting-quality adjustments.
- Do not enable the valuation branch until `point_in_time_fundamentals` is explicitly true and reporting lag rules are documented.
- If `operating_cash_flow_yield` is added, prefer it over a more elaborate free-cash-flow construction in the first pass.
- If sector metadata later becomes available, store raw and sector-adjusted scores separately.
