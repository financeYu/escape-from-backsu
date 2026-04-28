# PDF/fulltext 1차 수집 프로세스 종료 보고서

## 실행 개요

- 범위: `Quant_mvp/research_mvp` 리서치 수집 서브프로젝트
- 목적: license-aware PDF/fulltext 수집 프로세스의 1차 검증 및 종료 정리
- 결론: 1차 프로세스는 안전하게 종료 가능하나, 실제 PDF/fulltext 수집은 수행되지 않았다.
- 이번 실행은 score 채택을 수행하지 않았다.
- 이번 실행은 backtest를 수행하지 않았다.
- 논문 claim은 검증된 alpha가 아니다.
- valuation 후보는 valuation review skill로 handoff해야 한다.

## Policy 상태

- `[pdf_policy].allow_pdf = true`
- `[pdf_policy].max_downloads_per_run = 3`
- `[pdf_policy].allowed_manifest_categories = ["auto_cc", "noncommercial_cc"]`
- `[license_policy].fulltext_download_remains_disabled = false`
- `external_upload_default_allowed = false`
- `generated_raw_fulltext_git_tracked_allowed = false`

## Manifest 결과

| 항목 | Count |
| --- | ---: |
| 전체 papers.jsonl scan | 691 |
| auto_cc 후보 | 32 |
| noncommercial_cc 후보 | 9 |
| excluded | 517 |
| manual_review | 133 |
| missing_trace | 691 |
| dry-run 입력 후보 | 41 |
| would_download | 0 |
| skipped_missing_trace | 41 |
| 실제 다운로드 성공 | 0 |
| fulltext 추출 성공 | 0 |
| Evidence/review 상태 갱신 | 0 |

## Dry-run과 실제 수집 정합성

- dry-run `would_download = 0`이었다.
- 실제 수집 단계는 `download_attempted = false`, `download_success_count = 0`이었다.
- dry-run에서 허용된 실제 다운로드 후보가 없었으므로 실제 수집 0건은 일치한다.
- `max_downloads_per_run = 3`이고 `max_downloads_exceeded = false`였다.
- bulk download는 발생하지 않았다.

## PDF/fulltext 로컬 파일 상태

- `data/research/fulltext` 아래 실제 `.pdf` 파일 수: 0
- `data/research/fulltext` 아래 실제 `.txt` fulltext 파일 수: 0
- 생성된 것은 manifest `.json` 6개와 `.jsonl` 5개뿐이다.
- raw PDF/fulltext는 Git 추적 대상이 아니다.

## EvidenceCard 및 review packet 정합성

- trace와 hash가 완비된 항목이 없어 EvidenceCard는 `license_verified_pdf_collected` 또는 `fulltext_local_extracted`로 승격하지 않았다.
- review packet은 `data/research/fulltext/manifests/pdf_fulltext_evidence_review_packet_20260428.json`에 기록했다.
- 실패 또는 보류 항목은 기존 `manual_review`, `excluded`, `skipped_missing_trace` 상태로 유지했다.
- 외부 업로드 허용 플래그는 기본 `false`로 유지했다.

## 검증 명령 결과

- `python -m pytest tests/research_ingestion`: 141 passed, 4 skipped
- `python -c "import tomllib; ..."`: TOML parse OK
- `git diff --check`: whitespace error 없음
- `git ls-files -- data/research/fulltext data/research/raw data/research/request_cache data/research/evidence data/research/normalized`: 빈 출력
- `git check-ignore -v data/research/fulltext/...`: `.gitignore` 규칙 확인
- `bash .agents/skills/quant-review-gate/scripts/validate_review_gate.sh`: PASS

## 남은 blocker

- PDF-ready 후보 41건 모두 필수 license trace가 부족하다.
- `local_pdf_path`, `local_pdf_hash`, `fulltext_path`, `text_hash`가 연결된 항목이 없다.
- 다음 배치로 실제 수집하려면 후보별 license evidence quote와 license URL, checked timestamp, collection basis, review scope를 먼저 보강해야 한다.

## 다음 배치 진행 조건

1. `auto_cc` 또는 `noncommercial_cc` 후보 중 필수 trace 필드를 모두 채운다.
2. `noncommercial_cc` 후보는 `collection_basis = noncommercial_research_only`를 유지한다.
3. `external_upload_allowed = false`와 `redistribution_allowed = false`를 유지한다.
4. `download-pdfs --dry-run`에서 `would_download` 후보가 생기고 trace 누락이 0인지 확인한다.
5. 첫 실제 배치는 `max_downloads_per_run = 3` 이하로 제한한다.

## 종료 판정

1차 PDF/fulltext 수집 프로세스는 bulk download 없이 안전하게 dry-run, no-op collection, no-op extraction, Evidence/review 정리까지 완료했다. 실제 수집은 trace blocker 때문에 0건이며, 다음 배치는 trace 보강 후에만 진행 가능하다.
