# 퀀트 프로젝트

KOSPI200 구성 종목을 대상으로 하는 일봉 OHLCV 기반 기술적/통계적 멀티 스코어 랭킹 엔진 MVP입니다.

이 저장소는 하나의 매매 전략을 빠르게 만드는 프로젝트가 아닙니다. 리서치, 점수 설계, 데이터 검증, 실행 코드, 코드 리뷰를 분리해서 보수적으로 쌓아가는 퀀트 엔지니어링 워크스페이스입니다.

## 현재 상태

| 항목 | 상태 |
| --- | --- |
| 현재 단계 | Step 5: `Score Architect: MVP 기술 점수 후보 정의` |
| Step 1 | COMPLETE or mostly complete |
| Step 2 | PARTIALLY COMPLETE |
| Step 3 | COMPLETE |
| Step 4 | COMPLETE |
| 밸류에이션 상태 | `valuation_status = deferred` |
| 금융 데이터 사용 | `inventory_only_or_gui_display_only` |
| 백테스트 | Step 17 전까지 금지 |
| 랭킹 생성 | 허용된 단계 전까지 금지 |

자세한 진행 상태는 [docs/roadmap_status.md](docs/roadmap_status.md)를 봅니다.

## 핵심 원칙

- 미래 데이터와 lookahead를 금지합니다.
- 점수 정의 없이 score implementation을 하지 않습니다.
- 결과를 본 뒤 score definition을 조용히 바꾸지 않습니다.
- diagnostics를 alpha signal처럼 표현하지 않습니다.
- 가격 기반 신호를 valuation evidence로 부르지 않습니다.
- 기술적 oversold 상태를 cheap/value로 표현하지 않습니다.
- financial data는 `technical_composite_score`와 `final_composite_score`에 들어가지 않습니다.
- valuation/fundamental analysis는 기술 스캐너가 완성된 뒤로 미룹니다.
- paths, config keys, column names, function names는 English를 유지합니다.

## 프로젝트 구조

| 경로 | 역할 |
| --- | --- |
| `AGENTS.md` | 마스터 에이전트 운영 규칙 |
| `docs/project_checklist.md` | 전체 로드맵과 hard stop rules |
| `docs/roadmap_status.md` | 현재 단계와 남은 follow-up |
| `docs/technical_valuation_boundary.md` | 기술 분석과 밸류에이션 경계 |
| `docs/score_branch_policy.md` | Step 4 score branch 분류 정책 |
| `docs/selection_criteria.md` | Step 4 technical / valuation / diagnostic routing 기준 |
| `config/` | root-level config 초안 |
| `src/` | Step 3에서 만든 target module boundary |
| `chart_mvp/` | 현재 실행 가능한 스캐너/차트/캐시 하위 프로젝트 |
| `Quant_mvp/` | 점수 설계, 기술 검토, 밸류에이션 경계 문서 |
| `reserch_mvp/` | 리서치 수집/증거 준비 reference project |
| `review_mvp/` | 코드 리뷰와 최종 검증 보조 도구 |

## 로드맵

전체 Step 1-20 로드맵은 [docs/project_checklist.md](docs/project_checklist.md)에 있습니다.

현재 기준:

```text
Step 1: 에이전트 / 운영 규칙 수립 = COMPLETE or mostly complete
Step 2: 네이버 파이낸셜 데이터 수집기 검증 = PARTIALLY COMPLETE
Step 3: 디렉터리 / config / 표준 스키마 정리 = COMPLETE
Step 4: 기술 분석과 밸류에이션 경계 고정 = COMPLETE
Step 5: Score Architect: MVP 기술 점수 후보 정의 = NEXT
```

Step 4 정리 기준:

- `technical`, `valuation`, `diagnostic`, `hybrid`, `out_of_scope` branch를 분리합니다.
- root `config/scores.toml`은 runtime score/composite를 모두 비활성화합니다.
- `Quant_mvp/config/scores.toml`의 candidate registry는 Step 5 검토용이며 production scoring permission이 아닙니다.
- `PER`, `PBR`, `ROE` 등 financial display 값은 technical scoring이나 final composite에 들어가지 않습니다.

## Git 관리 정책

Git에 포함합니다:

- source code
- tests
- docs
- config
- 작은 reference fixture
- agent instructions

Git에 포함하지 않습니다:

- `chart_mvp/data/`
- `chart_mvp/outputs/`
- `chart_mvp/reports/`
- `__pycache__/`
- `*.pyc`
- virtual environment
- secrets

## PowerShell 인코딩

Windows PowerShell에서 한글 출력이 깨지면 프로젝트 루트에서 아래 스크립트를 현재 세션에 적용합니다.

```powershell
. .\scripts\Initialize-PowerShellUtf8.ps1
```

새 PowerShell을 프로젝트 폴더에서 열 때마다 자동 적용하려면 한 번만 설치합니다.

```powershell
.\scripts\Install-PowerShellUtf8Profile.ps1
```

## 실행 전 주의

현재 저장소에는 legacy/background artifact가 일부 남아 있습니다. 예를 들어 `outputs/latest_top*`와 `data/scan_results/*`는 과거 산출물이며, 현재 Step에서 새로 만든 랭킹이 아닙니다.

Step 5부터는 Score Architect 단계입니다. 즉, 먼저 점수 후보의 목적, 입력, 공식 설계 경로, normalization 후보, 실패 모드, 중복 위험을 문서화해야 합니다. 구현은 그 다음입니다.
