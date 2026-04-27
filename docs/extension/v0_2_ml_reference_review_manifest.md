# v0.2 ML Reference Review Manifest

## Purpose

이 manifest는 `v0_2_ml_research_reference_plan.md` 작성 후 남은 리스크를
local gate 상태로 정리한다. 목표는 중요한 reference가 metadata/abstract 단계에
머물러도 implementation gate로 조용히 승격되지 않도록 막고, PDF/full-text
검토가 가능한 항목과 보류 항목을 명확히 분리하는 것이다.

작성일: 2026-04-27

## Risk Burn-Down

| Risk | Status | Resolution |
| --- | --- | --- |
| PDF cache path가 Git에 들어갈 수 있음 | `RESOLVED_LOCAL` | `.gitignore`에 `Quant_mvp/research_mvp/data/research/fulltext/`와 legacy `Quant_mvp/data/research/fulltext/`를 추가했다. |
| Optional research query config가 없음 | `RESOLVED_LOCAL` | `Quant_mvp/research_mvp/config/v0_2_ml_research_queries.toml`을 추가했다. 이 config는 query/taxonomy/reference metadata만 담고 runtime network dependency가 없다. |
| PDF 전면 금지 폐기 후 수집 기준이 흐려질 수 있음 | `RESOLVED_LOCAL` | EvidenceCard license fields, evidence levels, local-only storage, no-redistribution rule을 reference plan과 이 manifest에 고정했다. |
| metadata/abstract reference가 implementation 근거로 오용될 수 있음 | `RESOLVED_BY_GATE` | `metadata_only`와 `abstract_reviewed`는 implementation gate decision 근거가 아니며, `full_text_reviewed` 또는 `project_validated`만 gate 근거가 된다. |
| 중요한 논문 full-text 검토가 아직 부족함 | `CONTROLLED_BACKLOG` | 아래 table에서 `requires_license_review`, `requires_full_text_review`, `requires_project_validation`로 남긴다. 이는 숨은 리스크가 아니라 gate-blocking backlog다. |

## Local PDF Storage Rule

PDF 또는 full-text snapshot을 later task에서 수집할 경우 기본 저장 위치는 다음
범위로 제한한다.

```text
Quant_mvp/research_mvp/data/research/fulltext/
Quant_mvp/data/research/fulltext/
```

두 경로는 Git ignore 대상이다. Root/master가 별도 artifact-storage task를 승인하지
않는 한 PDF를 commit하지 않는다.

## License Evidence Notes

- Creative Commons BY-NC 계열은 noncommercial restriction과 attribution
  requirement를 EvidenceCard에 남긴다.
- Creative Commons ND 계열은 no-derivatives restriction을 EvidenceCard
  `forbidden_use`에 남긴다.
- arXiv policy reference는 논문 접근에 대해 "viewed and downloaded freely"라고
  안내하지만, 각 paper의 reuse license는 개별 arXiv license link를 확인해야 한다.
- SSRN, NBER, Oxford / academic publisher page는 PDF 수집 전에 각 paper page의
  license/terms를 별도 확인한다.

## Reference Review Matrix

| Ref ID | Source | Current evidence level | License/PDF decision | Gate decision |
| --- | --- | --- | --- | --- |
| REF-LABEL-001 | O'Reilly/Wiley AFML | `metadata_only` | No PDF collected. Access and reuse terms require manual review. | `BLOCKED_FOR_IMPLEMENTATION`: requires full-text review and project validation. |
| REF-LABEL-002 | scikit-learn TimeSeriesSplit docs | `full_text_reviewed` | Official web docs reviewed. No PDF involved. | `ALLOWED_AS_CONTRACT_REFERENCE`: gap/split semantics only. |
| REF-TIMEVAL-001 | O'Reilly/Wiley AFML Chapter 7 listing | `metadata_only` | No PDF collected. Access and reuse terms require manual review. | `BLOCKED_FOR_IMPLEMENTATION`: purged/embargo contract requires full-text review. |
| REF-TIMEVAL-002 | Qlib official docs | `full_text_reviewed` | Official web docs reviewed. No PDF involved. | `ALLOWED_AS_ARCHITECTURE_REFERENCE`: data handler / workflow separation only. |
| REF-OVERFIT-001 | SSRN PBO | `abstract_reviewed` | No PDF collected. SSRN page/license must be checked before local PDF storage. | `BLOCKED_FOR_IMPLEMENTATION`: PBO/CSCV audit use requires full-text review and project validation. |
| REF-OVERFIT-002 | SSRN Deflated Sharpe Ratio | `abstract_reviewed` | No PDF collected. SSRN page/license must be checked before local PDF storage. | `BLOCKED_FOR_IMPLEMENTATION`: diagnostic field only until full-text review. |
| REF-OVERFIT-003 | Econometrica Reality Check | `abstract_reviewed` | No PDF collected. Publisher license must be checked before local PDF storage. | `BLOCKED_FOR_IMPLEMENTATION`: data-snooping reference only until full-text review. |
| REF-CAL-001 | scikit-learn calibration docs | `full_text_reviewed` | Official web docs reviewed. No PDF involved. | `ALLOWED_AS_CONTRACT_REFERENCE`: Brier/log loss/calibration curve fields only. |
| REF-CAL-002 | PMLR calibration paper page | `abstract_reviewed` | No PDF collected. PMLR page/license must be checked before local PDF storage. | `CONTRACT_REFERENCE_CANDIDATE`: neural calibration remains later-only. |
| REF-MODEL-001 | arXiv XGBoost | `abstract_reviewed` | arXiv official access supports local read-only review; no PDF collected in this task. Individual license must be captured before storage. | `MODEL_CANDIDATE_REFERENCE_ONLY`: no direct feature or production activation. |
| REF-MODEL-002 | NeurIPS LightGBM | `abstract_reviewed` | No PDF collected. NeurIPS page/license must be checked before local PDF storage. | `MODEL_CANDIDATE_REFERENCE_ONLY`: no implementation gate use until full-text/project validation. |
| REF-ARCH-001 | arXiv Qlib + Microsoft/Qlib docs | `abstract_reviewed` for paper, `full_text_reviewed` for docs | arXiv paper PDF not collected. Official docs reviewed as HTML. | `ALLOWED_AS_ARCHITECTURE_REFERENCE`: artifact boundary only. |
| REF-XSEC-001 | NBER/RFS Gu-Kelly-Xiu | `abstract_reviewed` | No PDF collected. NBER/Oxford license must be checked before local PDF storage. | `RESEARCH_REFERENCE_ONLY`: cross-sectional ML context, no project validation. |

## Evidence Promotion Rule

Evidence promotion is manual and monotonic:

```text
metadata_only
-> abstract_reviewed
-> license_verified_pdf_collected
-> full_text_reviewed
-> project_validated
```

Rules:

- `metadata_only` and `abstract_reviewed` cannot close an implementation gate.
- `license_verified_pdf_collected` proves collection permission only; it does not
  prove method suitability.
- `full_text_reviewed` can support contract design, but still cannot change
  score formulas, ranking, production reports, or model features by itself.
- `project_validated` is required before a method assumption can support an
  implementation gate decision.

## Completion Status

Local risks are resolved. External paper review remains as an explicit,
gate-blocking backlog rather than an unresolved hidden risk.
