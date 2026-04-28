# EvidenceCard Reference Rules

이 디렉터리는 curated EvidenceCard 참조 규칙을 둔다. 생성형 JSONL EvidenceCard가 `data/research/evidence/`에 있더라도, registry에서 재사용할 안정 참조는 repo-relative path로 기록한다.

## 참조 원칙

- `review_status = "sufficient"`인 논문은 같은 research question에서 기존 `evidence_card_id`를 재사용한다.
- 충분한 기존 card가 있으면 PDF, body, fulltext, 기존 카드 본문을 재수집/재점검하지 않는다.
- split EvidenceCard는 `parent_evidence_card_id`를 보존한다.
- 같은 논문이라도 research question이 달라지면 새 card를 만들 수 있지만, `changed_research_question` 예외를 registry에 먼저 기록한다.
- generated card를 curated card로 승격할 때도 해석을 바꾸지 않는 metadata/reference 이동만 허용한다.

## Registry 필수 연결

`docs/research/paper_registry.toml`에서 `review_status = "sufficient"`를 쓰려면 최소한 다음 필드를 채운다.

- `registry_id`
- `review_question`
- `evidence_card_id`
- `evidence_card_path`
- `match_keys`
- `normalized_title_hash`

`evidence_card_path`는 다음 중 하나를 사용한다.

- `docs/research/evidence_cards/<evidence_card_id>.toml`
- `docs/research/evidence_cards/<evidence_card_id>.md`
- `data/research/evidence/evidence_cards.jsonl`
- `data/research/evidence/<run_id>_evidence_cards.jsonl`

## 재사용 판정 결과

후보 처리 게이트는 다음 중 하나를 기록한다.

- `NO_RECOLLECT_REUSE`: 충분한 기존 card를 재사용한다.
- `METADATA_ONLY_UPDATE`: identity/reference metadata만 보강한다.
- `NEW_CARD_ALLOWED`: 신규 논문 또는 승인된 예외로 새 card를 만든다.
- `MANUAL_REVIEW_REQUIRED`: title-derived match 또는 불완전 metadata 때문에 사람이 확인한다.
- `ROOT_APPROVAL_REQUIRED`: 로컬 research scope를 넘는다.

## 금지 사항

- 충분 카드 전체 재검토
- PDF 대량 재다운로드
- license policy 변경
- score 채택 또는 ranking 생성
- backtest 재현 또는 alpha 검증 claim
- valuation verdict 작성

EvidenceCard는 downstream review를 돕기 위한 보수적 evidence record다. 충분하다는 말은 "이미 재사용 가능한 upstream card가 있다"는 뜻이며, paper claim이 검증되었다는 뜻이 아니다.
