# Paper Registry + No-Recollect Gate

이 문서는 신규 논문 후보를 처리하기 전에 이미 수집한 논문과 충분한 EvidenceCard를 재사용하기 위한 로컬 절차다. 이 절차는 `Quant_mvp/research_mvp` 범위의 research-ingestion 정책이며, score 채택, ranking 생성, backtest, valuation verdict를 허용하지 않는다.

## 목적

- 이미 `review_status = "sufficient"`인 논문은 재수집하거나 전체 재점검하지 않는다.
- DOI, arXiv ID, canonical URL, normalized title hash, title+author+year 기준으로 중복을 먼저 확인한다.
- 기존 EvidenceCard가 현재 research question에 충분하면 같은 카드를 재사용한다.
- PDF/body/fulltext 재수집 없이 가능한 보강은 metadata-only targeted update로 분리한다.

## 후보 처리 전 필수 조회

신규 후보가 들어오면 수집기나 사람이 먼저 아래 identity를 정규화한다.

1. `doi`: `https://doi.org/`, `doi:` prefix 제거 후 lowercase.
2. `arxiv_id`: `arxiv:` prefix 제거 후 lowercase, identity 비교에서는 version suffix 제거.
3. `canonical_url`: scheme/host lowercase, fragment와 tracking query 제거.
4. `title_normalized`: Unicode NFKC, lowercase, punctuation 제거, whitespace collapse.
5. `normalized_title_hash`: `sha256(title_normalized)` full hex.
6. `title_author_year_key`: `title_normalized + first_author_family_name_normalized + publication_year`.

조회 순서는 반드시 다음과 같다.

1. DOI exact match
2. arXiv ID exact match
3. canonical URL exact match
4. normalized title hash exact match
5. title+author+year match

Title-derived match만 있는 경우에는 자동 재사용 대신 `manual_review_required = true`로 기록한다. DOI, arXiv ID, canonical URL 중 하나가 같은 논문임을 보강하면 재사용할 수 있다.

## No-Recollect 판정

다음 조건이 모두 참이면 `NO_RECOLLECT_REUSE`로 판정한다.

- registry match가 존재한다.
- `review_status = "sufficient"`이다.
- `review_question`이 현재 후보의 research question과 같다.
- `evidence_card_id`와 `evidence_card_path`가 존재한다.
- retraction, erratum, license status change가 새로 감지되지 않았다.

이 판정이면 다음을 수행하지 않는다.

- PDF 재다운로드
- publisher fulltext 재수집
- Google Scholar live request
- 기존 EvidenceCard 전체 재검토
- 새 EvidenceCard 중복 생성

대신 기존 `evidence_card_id`와 `evidence_card_path`를 반환하고, 실행 로그나 report에는 "기존 EvidenceCard 재사용"으로 기록한다.

## No-Recheck 판정

`review_status = "sufficient"`인 논문은 현재 research question에 대해 EvidenceCard 본문을 다시 읽거나 판단을 다시 쓰지 않는다. 충분한 카드의 의미는 "현재 질문에 필요한 upstream evidence object가 이미 존재한다"는 뜻이며, score definition이나 alpha 검증을 의미하지 않는다.

재점검이 금지되는 예:

- refresh가 실행되었다는 이유만으로 충분한 카드를 다시 생성
- citation count가 바뀌었다는 이유만으로 paper claim 재평가
- 같은 DOI 후보를 새 query set에서 다시 발견했다는 이유만으로 PDF 또는 fulltext 재수집
- downstream agent가 score adoption 전에 EvidenceCard를 참고한다는 이유만으로 research-ingestion 카드 전체를 재작성

## 허용 예외

재점검은 아래 예외 중 하나가 명시될 때만 허용한다.

- `new_version_or_erratum`: 새 version, erratum, correction, retraction 관련 이벤트가 확인됨.
- `changed_research_question`: 기존 카드와 다른 질문으로 검토해야 함.
- `missing_required_fields`: registry 또는 EvidenceCard 참조에 필수 identity/reference field가 없음.
- `license_status_change`: open access, license, retraction, redistribution status가 바뀜.
- `root_approved_refresh`: root/master가 범위와 검증 명령을 명시해 refresh를 승인함.

예외를 쓰려면 registry entry에 `exception_reason`, `requested_by`, `allowed_update_scope`를 먼저 기록한다. 예외는 대량 PDF 재다운로드나 권리/라이선스 정책 변경을 자동으로 허용하지 않는다.

## Metadata-Only Targeted Update

본문/PDF 없이 보강할 수 있는 경우는 full recheck가 아니라 metadata-only targeted update로 처리한다.

허용되는 업데이트:

- DOI, arXiv ID, OpenAlex ID, Semantic Scholar ID, Crossref ID 추가
- canonical URL 정리
- title/authors/venue/publication date 보정
- source URL 추가
- open access status, license, retraction flag 보정
- citation count 같은 metadata 갱신

금지되는 업데이트:

- candidate idea 해석 변경
- classification verdict 변경
- implementation readiness 승격
- valuation verdict 작성
- paper-reported backtest를 alpha evidence로 승격
- score/ranking/report behavior 변경

metadata-only update 후에도 기존 `review_status = "sufficient"` 판정은 유지하되, research question을 바꾸거나 EvidenceCard 의미를 바꾸는 경우에는 예외 절차로 전환한다.

## EvidenceCard 재사용 규칙

EvidenceCard는 upstream evidence object이며 score definition, adoption decision, alpha evidence, backtest result, valuation verdict가 아니다.

- 한 논문은 하나 이상의 EvidenceCard를 가질 수 있지만, 같은 research question에는 기존 충분 카드 하나를 우선 재사용한다.
- split card는 `parent_evidence_card_id`를 유지한다.
- 새 EvidenceCard는 신규 논문, changed research question, 또는 승인된 예외가 있을 때만 생성한다.
- 기존 카드 참조는 repo-relative path로 기록한다.
- curated card는 `docs/research/evidence_cards/`, generated JSONL card는 `data/research/evidence/`를 우선 참조한다.

## Root 승인 필요 경계

다음은 research_mvp 로컬 정책으로 처리하지 않고 승인 요청만 남긴다.

- 권리/라이선스 정책 자체 변경
- 대량 PDF/fulltext 재수집
- root-owned roadmap, CI, release, cross-project routing 변경
- score formula, normalization, ranking, report behavior 변경
- valuation/fundamental scoring 또는 valuation verdict 활성화

이 절차의 기본 결론은 보수적이다. 불확실하면 신규 수집을 확대하지 말고 `manual_review_required = true` 또는 root 승인 필요사항으로 남긴다.
