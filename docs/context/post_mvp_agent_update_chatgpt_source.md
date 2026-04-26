# Post-MVP Agent Update ChatGPT Source

Status: planning source only / not authoritative until accepted.

Purpose: 이 문서는 KOSPI200 technical MVP v0.1 확정 직전 또는 직후,
기존 Step 1-20 로드맵을 닫고 다음 확장 방향에 맞춰 에이전트와 로드맵을
재설계하기 위해 ChatGPT에 제공할 입력 원문이다.

이 문서는 KOSDAQ150, 선물, 옵션, 나스닥 확장을 구현하지 않는다.
데이터 소스, 티커 리스트, 스키마, 점수 공식, 차트 로직, 백테스트 로직을
추가하지 않는다.

## Current Repository Baseline

- Repository: `master_mvp`
- Current product: KOSPI200 daily OHLCV technical/statistical multi-score scanner
- Current version target: MVP v0.1 freeze
- Current roadmap state: Step 1-20 complete
- Active roadmap Step: none
- Current baseline source:
  - `docs/context/MVP_V0_1_BASELINE.md`
  - `docs/releases/mvp_kospi200_baseline_manifest.md`
  - `docs/releases/step20_mvp_final_report.md`
  - `docs/contracts/step20_composite_contract.md`
  - `docs/contracts/step20_ranking_contract.md`
  - `docs/roadmap_status.md`

## What To Preserve From MVP v0.1

- KOSPI200 v0.1 must remain a frozen baseline, not a moving target.
- `technical_composite_score` remains technical-only.
- `final_composite_score` equals `technical_composite_score` in MVP v0.1.
- No financial/fundamental data enters technical or final composite scoring.
- Valuation/fundamental data remains candidate-only unless a later explicit roadmap
  step activates it with point-in-time availability rules.
- Backtest results remain evaluation-only and must not feed upstream scoring,
  ranking, score weights, or score definitions.
- Reports remain explanatory technical context, not buy/sell/hold recommendations.
- Generated charts, caches, scan outputs, and local reports remain non-source by
  default.

## User Direction For The Next Product Arc

The old Step 1-20 roadmap should be treated as complete and retired after MVP v0.1.
The next roadmap should be designed around this expansion order:

1. KOSDAQ150 추가
2. 선물 관련 차트 정보 추가
3. 옵션 관련 차트와 정보 추가
4. 나스닥으로 확장

This order matters. Later tracks must not be implemented early under another name.

## Desired ChatGPT Task

아래 목표에 맞춰 `master_mvp`의 다음 에이전트 개편안과 post-MVP 로드맵 초안을
작성하라.

Do not write implementation code. Do not invent data-source availability. Do not
claim alpha, robustness, or investment usefulness without evidence.

Deliver:

1. old Step 1-20을 닫고 보존하는 방식
2. post-MVP agent map
3. post-MVP routing table
4. post-MVP roadmap phases
5. per-phase hard stops and allowed scope
6. required context packets for future workers
7. required AGENTS.md update outline
8. documents that should be created or archived
9. validation/review gates before each expansion track can start

## Proposed Post-MVP Agent Model

Use this as a starting point, but improve it if needed:

- `master_agent`: repository-level direction, Git hygiene, routing, roadmap state,
  integration validation, freeze/release decisions.
- `baseline_guard_agent`: protects KOSPI200 MVP v0.1 contracts from accidental
  drift while new universes and derivative contexts are added.
- `universe_expansion_agent`: owns KOSDAQ150 and future equity-universe expansion
  planning, universe registry policy, ticker identity, market calendar, and
  per-universe data validation boundaries.
- `data_source_governance_agent`: evaluates whether a data source is allowed,
  reproducible, legal/safe to use, point-in-time safe when relevant, and
  configurable without secrets in source control.
- `chart_runtime_agent`: owns executable scanner/chart/GUI behavior, runtime
  cache boundaries, generated output paths, and visual report ergonomics.
- `quant_score_agent`: owns technical score definitions, normalization,
  composite design, and score adoption rules. Must not implement new score logic
  before design is approved.
- `derivatives_context_agent`: owns futures/options chart-information design,
  contract metadata, roll/expiry context, open-interest/volume/basis/IV/skew
  display semantics, and derivatives-specific guardrails. Must not create
  trading signals or derivative pricing/trading systems.
- `valuation_agent`: remains responsible only for point-in-time fundamental and
  valuation availability review. It must stay separate from technical scoring
  unless a later accepted roadmap explicitly changes that boundary.
- `research_ingestion_agent`: owns evidence intake and source metadata. Evidence
  does not equal score definition or adoption decision.
- `review_agent`: specialist correctness/security/reliability review and minimal
  repair guidance for high-risk code or integration changes.
- `audit_scope_agent`: checks scope creep, roadmap bypass, terminology laundering,
  generated-output leakage, and root-boundary violations.

## Proposed Post-MVP Roadmap Shape

### Phase 0: MVP v0.1 Freeze And Roadmap Retirement

Goal: 기존 Step 1-20을 complete/frozen baseline으로 보존하고, 다음 로드맵과
에이전트 체계가 낡은 Step 번호에 끌려다니지 않게 정리한다.

Allowed:

- archive old roadmap detail
- keep compact MVP baseline context
- define post-MVP authority order
- define new phase naming
- update agent routing docs
- add explicit no-drift baseline guardrails

Forbidden:

- changing KOSPI200 v0.1 scoring/ranking semantics
- adding KOSDAQ150/futures/options/Nasdaq data or logic
- adding new score formulas
- enabling valuation/fundamental scoring
- converting backtest results into score optimization

### Phase 1: KOSDAQ150 Equity Universe Expansion

Goal: KOSDAQ150을 별도 universe로 추가할 수 있는 구조를 설계하고, KOSPI200
baseline을 깨지 않는 방식으로 universe registry, ticker identity, data quality,
normalization, ranking/report boundaries를 확정한다.

Key design questions:

- KOSPI200과 KOSDAQ150을 같은 ranking table에 섞을지, universe별 ranking을
  기본으로 둘지
- cross-sectional normalization을 universe 내부에서만 할지, multi-universe
  comparison을 별도 experimental context로 둘지
- ticker identity, exchange, market calendar, suspended/delisted handling을
  어떻게 기록할지
- KOSDAQ150 데이터 품질과 liquidity/coverage 차이를 report context로만 둘지
  scoring input으로 둘지

Allowed before implementation:

- universe registry contract draft
- data validation checklist
- chart/report UI requirements
- generated-output boundary update
- migration plan for config-first universe selection

Forbidden:

- silently changing KOSPI200 v0.1 ranking behavior
- mixing KOSDAQ150 rows into KOSPI200 baseline outputs
- claiming cross-universe comparability before validation
- adding valuation/fundamental data to technical scores

### Phase 2: Futures Chart Information

Goal: 선물 관련 정보를 차트와 설명 컨텍스트로 추가하기 위한 데이터/표현/계약을
설계한다. 이 단계는 signal generation이 아니라 market context visualization이다.

Candidate information:

- front contract and continuous contract display policy
- roll schedule and expiry date context
- volume and open interest
- basis versus spot/index where reliable
- term structure where data supports it
- gap/roll adjustment notice
- contract multiplier and tick size as metadata

Allowed:

- futures chart context contract
- rollover/continuous-series policy proposal
- generated chart/report output boundary
- data source and licensing review checklist
- user-facing explanatory labels

Forbidden:

- futures trading signals
- buy/sell/hold language
- derivative pricing models as production logic
- score/ranking feedback into equity technical composite
- unverified continuous contract construction

### Phase 3: Options Chart And Information

Goal: 옵션 체인과 옵션 기반 시장 컨텍스트를 차트/정보로 제공하기 위한 범위를
설계한다. 이 단계도 trading system이 아니라 explanatory chart context이다.

Candidate information:

- option chain by expiry and strike
- call/put volume and open interest
- put/call ratio
- implied volatility display where source supports it
- volatility skew/smile visualization
- expiry calendar
- moneyness bands
- Greeks only if source and methodology are explicit

Allowed:

- options chart context contract
- options data schema proposal
- source availability and licensing review
- display-only risk notices
- generated-output boundary update

Forbidden:

- option trade recommendation
- strategy payoff recommendation as advice
- undocumented IV/Greeks calculation
- options-derived score added to equity ranking without a later approved score
  design and review step

### Phase 4: Nasdaq Expansion

Goal: US/Nasdaq 확장을 별도 market expansion으로 설계한다. 이 단계는 단순히
티커를 늘리는 문제가 아니라 calendar, currency, corporate action, vendor,
timezone, symbol identity, survivorship, market microstructure 차이를 다룬다.

Key design questions:

- Nasdaq-only인지, US-listed broader universe인지
- adjusted OHLCV policy and corporate actions
- timezone and trading calendar handling
- currency and FX display policy
- vendor/source restrictions
- ticker collisions and symbol lifecycle
- whether score definitions transfer unchanged or require re-review

Forbidden:

- treating Nasdaq as a drop-in KOSPI/KOSDAQ clone without validation
- claiming score usefulness transfers across markets without evidence
- mixing US and Korea rankings without explicit normalization and comparability
  review

## Global Hard Stops For The New Roadmap

- Do not reopen old Step 1-20 as active implementation work unless explicitly
  doing baseline repair.
- Do not change MVP v0.1 contracts while designing expansion tracks.
- Do not add a new universe, futures, options, or Nasdaq logic before its phase
  has design, source review, guardrails, and validation plan.
- Do not add financial/fundamental data to `technical_composite_score`.
- Do not add financial/fundamental data to `final_composite_score` unless the
  project explicitly creates a new non-v0.1 score contract and passes valuation
  point-in-time review.
- Do not turn diagnostics, chart overlays, futures/options context, or backtest
  results into alpha claims.
- Do not use buy/sell/hold or trading recommendation language.
- Do not require paid APIs, secrets, or local private credentials in source code
  or tests.
- Do not source-control generated charts, caches, scans, or local reports unless
  explicitly promoted as small fixtures.
- Prefer config-first changes for universe, market, data source, chart, and
  output-path behavior.

## Expected Output Format From ChatGPT

Use Korean for reasoning summaries and user-facing policy text. Keep code
identifiers, config keys, file paths, and exported column names in English.

Return:

```text
[요약]
- ...

[기존 로드맵 처리]
- ...

[새 에이전트 맵]
- ...

[새 라우팅 테이블]
| 요청 유형 | 담당 에이전트/프로젝트 | 필수 참조 | 금지 범위 |
| --- | --- | --- | --- |

[Post-MVP 로드맵]
- Phase 0: ...
- Phase 1: ...
- Phase 2: ...
- Phase 3: ...
- Phase 4: ...

[AGENTS.md 업데이트 초안]
- ...

[새로 만들 문서]
- ...

[폐기/보존할 문서]
- ...

[각 Phase 시작 게이트]
- ...

[리스크와 미확정 질문]
- ...
```

## Final Instruction To ChatGPT

이 입력을 바탕으로 즉시 구현 계획을 만들지 말고, 먼저 에이전트 운영 문서와
post-MVP 로드맵 재설계 초안을 작성하라. 기존 KOSPI200 MVP v0.1은 보호해야 할
baseline으로 취급하고, 확장 방향은 KOSDAQ150 -> 선물 차트 정보 -> 옵션 차트와
정보 -> 나스닥 순서를 유지하라.
