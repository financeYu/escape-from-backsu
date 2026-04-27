# v0.2 ML Research Reference Plan

## Purpose

이 문서는 post-MVP v0.2 candidate-only `prob_up_1d_candidate` route의
향후 ML 개선을 위한 리서치 참조 패키지다. 목적은 label design,
no-lookahead control, walk-forward / purged validation, probability
calibration, overfitting prevention, model-family 후보, Qlib-style reference
architecture, implementation-readiness gate를 EvidenceCard로 보존하는 것이다.

이 문서는 score 채택, 모델 구현, production ranking activation, trading
language, valuation/fundamental scoring을 승인하지 않는다. EvidenceCard만
생성하고 score 채택은 수행하지 않는다.

Selected reusable gates:

- `.agents/skills/quant-candidate-ml-gate/SKILL.md`
- `.agents/skills/ml-research-evidence/SKILL.md`

Confirmed context는 다음 3개로 제한한다.

- Step 20 is complete, and the KOSPI200 technical MVP v0.1 baseline is frozen.
- The active post-MVP route is v0.2 candidate-only `prob_up_1d_candidate`.
- Backtest output is evaluation-only and must not feed back into scoring,
  ranking, model features, or production behavior.

## Scope

허용 범위:

- `prob_up_1d_candidate` 연구 참조 수집, 분류, EvidenceCard schema 정리.
- label / timing / validation / calibration / overfitting audit 계약 정리.
- 비상업적 또는 open-access 조건이 확인된 full-text 참조 가능 정책 정리.
- future model-family expansion 후보를 reference-only로 정리.

금지 범위:

- Quant logic, score formula, `technical_composite_score`,
  `final_composite_score` 변경.
- production ranking activation 또는 production report behavior 변경.
- backtest result를 model feature, score weight, ranking input으로 사용하는 것.
- KOSDAQ150, futures/options, Nasdaq/overseas, multi-universe activation.
- buy/sell/hold, proven-alpha, expected-return, profitability claim.

## Source Policy

우선 소스는 academic papers, official documentation, journal pages, arXiv,
SSRN, NBER, Oxford / academic publisher pages, OpenAlex metadata, Crossref
metadata, Semantic Scholar metadata를 사용한다. scikit-learn, XGBoost,
LightGBM, Microsoft Qlib 같은 official project documentation은
implementation reference 후보로 사용할 수 있다.

Reusable query strings and taxonomy mappings for this candidate-only route live
in `Quant_mvp/research_mvp/config/v0_2_ml_research_queries.toml`.

Google Scholar는 discovery-only seed channel이다. Scholar ranking,
snippet, citation count는 evidence strength가 아니며 unresolved Scholar-only
seed에서 EvidenceCard를 만들지 않는다.

낮은 품질의 trading blog는 authority로 쓰지 않는다. 불가피하게 참고하면
`review_status: background_only`로 표시한다.

Full-text가 존재하더라도 license 또는 source terms가 불명확하면
`metadata_only` 또는 `abstract_reviewed`로만 남긴다. 외부 paid API, hosted LLM,
또는 third-party extraction service에 PDF/full-text를 업로드하지 않으며,
본문 기반 요약은 local review note와 짧은 non-verbatim evidence summary로
제한한다.

## PDF / Full-Text Collection Policy

PDF 원천 수집 금지는 폐기한다. 다만 PDF / full-text 수집은 라이선스 또는
공식 약관이 명확할 때만 허용한다.

현재 `Quant_mvp/research_mvp/config/research_policy.toml`의 기본 실행 정책은
`pdf_download_default = false`와 `fulltext_download_remains_disabled = true`다.
따라서 이 plan은 future reference policy를 정의하지만, 별도 승인 없는 현재
작업에서 PDF downloader, full-text crawler, cache writer를 구현하거나 실행하지
않는다.

허용되는 수집 기준:

- CC BY, CC BY-SA, CC BY-NC, CC BY-NC-SA.
- CC BY-ND, CC BY-NC-ND. 단, no-derivatives restriction을
  `allowed_use`와 `forbidden_use`에 반영하고 수정본을 재배포하지 않는다.
- public domain 또는 CC0.
- official open-access publisher PDF가 research download / local research
  use를 명확히 허용하는 경우.
- arXiv, SSRN, institutional repository PDF가 공식 페이지에서 접근 가능하고
  local research use가 명확한 경우.
- user-provided PDF.

금지되는 수집 기준:

- paywalled PDF, login-only PDF, subscription PDF, institutional access PDF.
- Sci-Hub, unauthorized mirror, unauthorized repost.
- license 또는 download/reuse permission이 모호한 publisher PDF.
- source terms가 local storage, text/data mining, reuse를 금지하는 PDF.
- bulk automated PDF download.

저장 및 배포 정책:

- PDF collection은 local-only가 기본이다.
- PDF는 root/master가 별도 artifact-storage task를 승인하지 않는 한 Git에
  commit하지 않는다.
- PDF cache를 만들 경우 `Quant_mvp/research_mvp/data/research/fulltext/pdf_cache/`
  같은 local path를 쓰고 `.gitignore` 또는 동등한 exclusion을 먼저 확인한다.
- PDF를 paid API 또는 외부 서비스에 업로드하지 않는다.
- 수집한 PDF를 재배포하지 않는다.
- 논문 본문을 길게 인용하지 않는다.

필수 license trace:

- `license_name`
- `license_url`
- `source_url`
- `license_checked_at`
- `license_evidence_quote`
- `collection_basis`
- `local_pdf_path`
- `license_allows_noncommercial_use`
- `license_allows_derivatives`
- `license_allows_redistribution`
- `license_requires_attribution`

Full-text review trace:

- `fulltext_source_type`: `official_html`, `official_pdf`, `repository_pdf`,
  `user_provided_pdf`, `documentation_page`, `none`
- `fulltext_access_method`: manual/local review method only
- `fulltext_reviewed_at`
- `fulltext_reviewer`
- `fulltext_review_scope`
- `redistribution_allowed`: false unless explicitly proven
- `external_upload_allowed`: false by default

Creative Commons BY-NC는 noncommercial use와 attribution requirement를
명시하며, BY-NC-ND는 noncommercial과 no-derivatives restriction을 함께
가진다. 이 제한은 EvidenceCard의 `allowed_use`와 `forbidden_use`에 그대로
남긴다.

이번 reference package 작성에서는 PDF를 수집하지 않았다. 중요한 문헌은 먼저
`abstract_reviewed` 또는 `metadata_only`로 카드화하고, 라이선스 검증 후에만
`license_verified_pdf_collected`로 올린다.

Reference별 license/full-text 상태와 local risk burn-down은
`docs/extension/v0_2_ml_reference_review_manifest.md`를 따른다. 수동 검토
대기열과 `full_text_reviewed` / `project_validated` 승격 후보 분리는
`docs/extension/v0_2_ml_fulltext_license_review_packet.md`를 따른다.

## Research Taxonomy

각 Reference/EvidenceCard는 하나 이상의 `taxonomy_tags`를 가진다.

- `labeling_no_lookahead`: fixed-horizon label, triple-barrier method,
  meta-labeling, label availability time, decision/execution/label timing.
- `time_series_validation`: walk-forward, expanding window, rolling window,
  purged K-fold, embargo/gap handling.
- `backtest_overfitting_prevention`: PBO, CSCV, multiple testing,
  data snooping, model-selection bias, strategy-selection bias.
- `probability_calibration`: Brier score, log loss, calibration curve,
  sigmoid calibration, isotonic calibration, calibrated classifier workflow.
- `model_candidates`: logistic regression baseline, random forest,
  extra trees, XGBoost, LightGBM, neural models as later-only candidates.
- `cross_sectional_equity_ml`: technical signal interaction, volatility,
  liquidity, momentum features, cross-sectional prediction artifact.
- `reference_architecture`: Qlib-style data handler, feature processor,
  dataset splitter, trainer, recorder, evaluator, report artifact.
- `decision_time_controls`: feature observation time, decision time,
  execution time, label time, label availability time, unlabeled latest row.
- `purged_embargo_validation`: label horizon overlap, purge window, embargo
  window, split gap, split manifest.
- `future_model_family_reference`: logistic baseline, calibrated linear model,
  tree ensemble, GBDT, neural later-only, stacking/ensembling later-only.

## Evidence Levels

각 EvidenceCard는 정확히 하나의 `evidence_level`을 가진다.

- `metadata_only`: title, authors, DOI/arXiv/SSRN ID, source metadata only.
  Discovery와 triage 전용이며 implementation gate decision 근거가 아니다.
- `abstract_reviewed`: abstract, official summary, official documentation
  page가 검토됨. taxonomy classification을 지원할 수 있으나 implementation
  contract의 유일 근거가 될 수 없다.
- `license_verified_pdf_collected`: license/terms가 확인되고 허용 정책 안에서
  PDF가 local-only로 수집됨. 아직 full-text review 전이다.
- `full_text_reviewed`: 허용된 PDF, official HTML, publisher full text,
  arXiv text, SSRN text, institutional repository, user-provided PDF를 검토함.
- `project_validated`: method 또는 assumption이 이 프로젝트의 data structure,
  contract, validation harness와 대조됨.

Implementation gate decision은 `full_text_reviewed` 또는 `project_validated`
근거를 요구한다. `metadata_only` EvidenceCard는 discovery-only로만 남긴다.

Promotion은 수동이며 단조 증가만 허용한다. `project_validated`는 논문 성과를
인정한다는 뜻이 아니라, 해당 method assumption이 이 repository의 feature,
label, split, calibration, sidecar, evaluation-only boundary와 충돌하지 않음을
검토했다는 뜻이다.

## Implementation Readiness

허용 값:

- `discovery_only`
- `contract_reference_candidate`
- `implementation_reference_candidate`
- `requires_license_review`
- `requires_full_text_review`
- `requires_project_validation`

Readiness는 implementation 승인 상태가 아니다. `implementation_reference_candidate`
도 직접 feature, score formula, production rank, report behavior 변경을 허용하지
않는다. Candidate ML implementation gate에서 사용할 수 있는 근거는 다음을 모두
만족해야 한다.

- `evidence_level`이 `full_text_reviewed` 또는 `project_validated`.
- `implementation_readiness`가 `contract_reference_candidate`,
  `implementation_reference_candidate`, 또는 `requires_project_validation` 중 하나로
  명시되어 있고, 남은 조건이 risk note에 기록됨.
- no-lookahead, label availability, split, calibration, overfitting control에
  대해 unchecked assumption이 비어 있거나 gate-blocking backlog로 남아 있음.
- `allowed_use`가 reference/validation/label/calibration/model/architecture 후보
  중 하나이며, `forbidden_use`에 candidate-only 금지 항목이 남아 있음.

## EvidenceCard Schema

```yaml
EvidenceCard:
  paper_id: string
  title: string
  authors: list[string]
  year: integer | null
  source: string
  doi_or_arxiv_or_ssrn_id: string | null
  url: string
  pdf_url: string | null
  local_pdf_path: string | null
  license_name: string | null
  license_url: string | null
  license_allows_noncommercial_use: boolean | null
  license_allows_derivatives: boolean | null
  license_allows_redistribution: boolean | null
  license_requires_attribution: boolean | null
  license_checked_at: string | null
  license_evidence_quote: string | null
  collection_basis: string
  taxonomy_tags: list[string]
  evidence_level: metadata_only | abstract_reviewed | license_verified_pdf_collected | full_text_reviewed | project_validated
  review_basis: string
  implementation_readiness: discovery_only | contract_reference_candidate | implementation_reference_candidate | requires_license_review | requires_full_text_review | requires_project_validation
  method_summary_ko: string
  checked_assumptions:
    target_horizon: string | null
    asset_universe: string | null
    data_frequency: string | null
    feature_observation_time_rule: string | null
    decision_time_rule: string | null
    execution_time_rule: string | null
    label_time_rule: string | null
    label_availability_rule: string | null
    train_test_split_method: string | null
    leakage_controls: string | null
    purging_embargo_controls: string | null
    transaction_cost_handling: string | null
    calibration_method: string | null
    calibration_fit_scope: string | null
    overfitting_controls: string | null
    multiple_testing_controls: string | null
    evaluation_metrics: list[string]
    method_type: classification | probability_estimation | ranking | portfolio_simulation | architecture | validation | unknown
  candidate_ml_boundary:
    candidate_output_name: prob_up_1d_candidate
    candidate_only: true
    sidecar_required: true
    production_rank_activation: false
    technical_composite_score_change: false
    final_composite_score_change: false
    report_behavior_change: false
    backtest_feedback_to_training: false
  unchecked_assumptions: list[string]
  implementation_relevance: string
  allowed_use:
    - reference_only | validation_method_candidate | label_design_reference | calibration_reference | model_candidate_reference | architecture_reference
  forbidden_use:
    - direct_feature_input
    - production_ranking_activation
    - final_composite_score_change
    - backtest_metric_as_feature
    - backtest_feedback_to_training
    - trading_claim
    - expected_return_claim
    - buy_sell_hold_recommendation
  risk_notes: list[string]
  review_status: pending | reviewed | needs_license_review | needs_full_text_review | needs_project_validation | rejected | background_only
```

## Candidate ML Timing Controls

`prob_up_1d_candidate` reference cards must record timing assumptions even when
the reference itself does not provide repository-ready details.

Required timing interpretation:

- `decision_time`: the time at which the candidate probability would be known.
- `feature_observation_time`: the latest timestamp used by every feature before
  or at `decision_time`.
- `execution_time`: optional later timestamp for evaluation convention only; it
  is not a trading instruction.
- `label_time`: the timestamp represented by `adjusted_close[t+1]`.
- `label_availability_time`: the timestamp when `up_1d_label` can be known.
- latest unlabeled row remains `candidate_unlabeled` and cannot enter
  training/evaluation labels.

If a reference does not state these controls, set
`implementation_readiness: requires_project_validation` and add a risk note
instead of filling the gap optimistically.

## Validation And Calibration Controls

Walk-forward, purged split, embargo, and calibration references are contract
tools only. They may define audit fields and validation harness expectations,
but they do not adopt a model or prove project performance.

Required validation interpretation:

- chronological split only; no random shuffle for time-dependent evaluation.
- rolling or expanding window must be explicit in config.
- purge and embargo must be tied to label horizon and label availability, not
  only to a generic split gap.
- scaler, imputer, clipper, feature selector, model, and calibration parameters
  must be fit inside the training/calibration scope only.
- Brier score, log loss, and calibration curve are probability diagnostics, not
  ranking activation criteria.
- multiple model families, feature sets, label variants, or trial counts trigger
  data-snooping and selection-bias warnings.

## Future Model-Family Reference Boundary

Future model-family references are allowed as `model_candidate_reference` only.
The current package records them to prepare review, not to implement models.

Allowed future-only families:

- calibrated logistic regression / linear probability baseline.
- random forest and extra trees with probability calibration checks.
- XGBoost / LightGBM tabular GBDT candidates.
- neural tabular or sequence models only as later-only references with explicit
  calibration and overfit risk notes.
- stacking or ensembling only after base-family validation and multiple-testing
  controls are project-validated.

Every future model-family EvidenceCard must preserve `candidate_only: true`,
`production_rank_activation: false`, and `final_composite_score_change: false`.

## Reference Inventory

| ID | Reference | Taxonomy | Evidence level | Readiness | Relevance |
| --- | --- | --- | --- | --- | --- |
| REF-LABEL-001 | Lopez de Prado, [Advances in Financial Machine Learning](https://www.oreilly.com/library/view/advances-in-financial/9781119482086/ftoc.xhtml), 2018 | `labeling_no_lookahead`, `time_series_validation`, `model_candidates` | `metadata_only` | `requires_full_text_review` | fixed-horizon, triple-barrier, meta-labeling, purged CV를 후보 개념으로 분류한다. 책 본문 접근권/라이선스가 검증되기 전에는 contract hint까지만 사용한다. |
| REF-LABEL-002 | scikit-learn [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | `time_series_validation`, `labeling_no_lookahead` | `full_text_reviewed` | `implementation_reference_candidate` | time-ordered split과 `gap` parameter를 walk-forward/gap contract 참고로 사용한다. 금융 overlap label의 purging 전체 대체물은 아니다. |
| REF-TIMEVAL-001 | Lopez de Prado, AFML Chapter 7 listing via O'Reilly | `time_series_validation` | `metadata_only` | `requires_full_text_review` | purged K-fold와 embargo 개념을 financial CV 후보로 남긴다. 구현 전 full-text 검토 필요. |
| REF-TIMEVAL-002 | Qlib docs, [Data Layer](https://qlib.readthedocs.io/en/v0.9.2/component/data.html) and [Workflow](https://qlib.readthedocs.io/en/stable/component/workflow.html) | `reference_architecture`, `time_series_validation`, `labeling_no_lookahead` | `full_text_reviewed` | `architecture_reference` | DataHandler, Dataset, learn/infer separation, recorder/evaluator style를 sidecar architecture 참조로 사용한다. |
| REF-OVERFIT-001 | Bailey et al., [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253), SSRN | `backtest_overfitting_prevention`, `time_series_validation` | `abstract_reviewed` | `requires_full_text_review` | PBO/CSCV를 backtest audit field 후보로 분류한다. PDF collection은 license review 전까지 보류한다. |
| REF-OVERFIT-002 | Bailey and Lopez de Prado, [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551), SSRN | `backtest_overfitting_prevention` | `abstract_reviewed` | `requires_full_text_review` | multiple testing / selection bias correction을 diagnostic-only field 후보로 분류한다. |
| REF-OVERFIT-003 | White, [A Reality Check for Data Snooping](https://www.econometricsociety.org/publications/econometrica/2000/09/01/reality-check-data-snooping), Econometrica | `backtest_overfitting_prevention` | `abstract_reviewed` | `requires_full_text_review` | repeated data reuse와 model-selection bias warning의 academic reference다. |
| REF-CAL-001 | scikit-learn, [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html) | `probability_calibration` | `full_text_reviewed` | `implementation_reference_candidate` | sigmoid/isotonic calibration, calibration curve, calibration workflow를 참고한다. Candidate probability calibration은 fold 내부에서만 학습해야 한다. |
| REF-CAL-002 | Guo et al., [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html), PMLR 2017 | `probability_calibration`, `model_candidates` | `abstract_reviewed` | `contract_reference_candidate` | neural model은 later-only 후보이며, temperature scaling은 calibration idea로만 보존한다. |
| REF-MODEL-001 | Chen and Guestrin, [XGBoost: A Scalable Tree Boosting System](https://arxiv.org/abs/1603.02754), arXiv/KDD 2016 | `model_candidates` | `abstract_reviewed` | `requires_license_review` | sparse tabular features와 tree boosting 후보. PDF 수집은 arXiv license 확인 후 local-only로만 가능하다. |
| REF-MODEL-002 | Ke et al., [LightGBM](https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree), NeurIPS 2017 | `model_candidates` | `abstract_reviewed` | `requires_license_review` | GBDT family expansion 후보. PDF 수집은 NeurIPS page/license 확인 후 local-only로만 가능하다. |
| REF-ARCH-001 | Yang et al., [Qlib: An AI-oriented Quantitative Investment Platform](https://arxiv.org/abs/2009.11189), arXiv/Microsoft Research | `reference_architecture`, `cross_sectional_equity_ml` | `abstract_reviewed` | `architecture_reference` | data handler, dataset split, model training, recorder, evaluator artifact boundary의 reference architecture다. |
| REF-XSEC-001 | Gu, Kelly, and Xiu, [Empirical Asset Pricing via Machine Learning](https://www.nber.org/papers/w25398), NBER/RFS | `cross_sectional_equity_ml`, `model_candidates` | `abstract_reviewed` | `requires_full_text_review` | cross-sectional equity ML에서 momentum, liquidity, volatility interaction을 연구 reference로만 사용한다. 이 논문 claim은 아직 검증된 alpha가 아니다. |

## Minimum Quality Bar

- 각 reference는 공식 URL, source, taxonomy, evidence_level,
  implementation_readiness를 가져야 한다.
- `metadata_only`는 discovery-only로만 사용한다.
- implementation gate decision은 `full_text_reviewed` 또는
  `project_validated` evidence를 요구한다.
- license가 모호한 PDF는 수집하지 않는다.
- citation count는 metadata이며 evidence strength가 아니다.
- paper-reported backtest 또는 benchmark는 project validation이 아니다.

## How Research May Influence Implementation

- label design reference: fixed-horizon label, label availability time,
  decision/execution/label timing separation을 계약화하는 데 사용한다.
- validation method candidate: walk-forward, purged split, embargo/gap,
  rolling/expanding window contract를 설계하는 데 사용한다.
- calibration reference: Brier score, log loss, calibration curve,
  sigmoid/isotonic calibration audit fields를 정리하는 데 사용한다.
- architecture reference: feature table, label table, model training,
  sidecar prediction artifact, evaluation-only report의 분리를 문서화한다.
- model candidate reference: logistic regression baseline, random forest,
  extra trees, XGBoost, LightGBM 후보군을 future-only로 분류한다.

## How Research May Not Influence Implementation

- 논문 또는 문서 내용을 direct feature input으로 쓰지 않는다.
- 논문 backtest metric을 model feature, score weight, ranking input으로 쓰지
  않는다.
- research claim을 trading claim, expected_return_claim,
  buy_sell_hold_recommendation으로 바꾸지 않는다.
- candidate sidecar artifact를 production rank, production report order,
  `technical_composite_score`, `final_composite_score`에 병합하지 않는다.
- full-text review 또는 project validation 없이 implementation gate decision을
  닫지 않는다.

## Candidate-Only Boundary

Research package의 올바른 영향 경로는 다음뿐이다.

```text
research reference
-> EvidenceCard
-> contract field candidate
-> future implementation review
```

활성 모델 경로는 다음 boundary를 유지해야 한다.

```text
feature_table
-> label_table separated
-> walk-forward / purged split
-> model training
-> calibration
-> out-of-sample prob_up_1d_candidate
-> candidate-only sidecar artifact
-> evaluation-only backtest report
```

Backtest evaluator는 out-of-sample prediction artifact를 읽을 수 있다. Backtest
evaluator는 upstream model features, score weights, ranking changes,
final composite changes, production report changes를 만들 수 없다.
