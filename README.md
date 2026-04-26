# 퀀트 프로젝트

> Post-MVP notice:
> Some roadmap/status sections in this README are historical pre-freeze
> material, not the active roadmap.
> Use `docs/roadmap_status.md`, `docs/context/MVP_V0_1_BASELINE.md`, and
> `docs/context/ARCHIVE_INDEX.md` for current routing and archive lookup.

KOSPI200 구성 종목을 대상으로 하는 일봉 OHLCV 기반 기술적/통계적 멀티 스코어 랭킹 엔진 MVP입니다.

이 저장소는 하나의 매매 전략을 빠르게 만드는 프로젝트가 아닙니다. 리서치, 점수 설계, 데이터 검증, 실행 코드, 코드 리뷰를 분리해서 보수적으로 쌓아가는 퀀트 엔지니어링 워크스페이스입니다.

## 현재 상태

| 항목 | 상태 |
| --- | --- |
| 현재 단계 | active roadmap Step 없음 |
| 기준선 | KOSPI200 technical MVP v0.1 frozen |
| Step 20 | COMPLETE |
| 밸류에이션 상태 | `candidate_only_not_activated` |
| 금융 데이터 사용 | technical/final composite 입력 금지 |
| 백테스트 | evaluation-only, scoring/ranking feedback 금지 |
| 향후 확장 | 별도 승인된 post-MVP Step 필요 |

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
| `docs/project_checklist.md` | historical roadmap/checklist body와 hard stop rules |
| `docs/roadmap_status.md` | latest-only roadmap status와 current gate |
| `docs/technical_valuation_boundary.md` | 기술 분석과 밸류에이션 경계 |
| `docs/score_branch_policy.md` | Step 4 score branch 분류 정책 |
| `docs/selection_criteria.md` | Step 4 technical / valuation / diagnostic routing 기준 |
| `docs/review_flow.md` | subproject-first review -> master-up 운영 흐름 |
| `docs/master_up_template.md` | 하위 프로젝트 master-up 제출 template |
| `docs/review_mvp_policy.md` | `review_mvp` specialist review 호출 기준 |
| `config/` | root-level config 초안 |
| `src/` | Step 3에서 만든 target module boundary |
| `chart_mvp/` | 현재 실행 가능한 스캐너/차트/캐시 하위 프로젝트 |
| `Quant_mvp/` | 점수 설계, 기술 검토, research intake contract, 밸류에이션 경계 문서 |
| `Quant_mvp/backtest_mvp/` | Quant에 종속된 evaluation-only 백테스트 하위 프로젝트 |
| `reserch_mvp/` | 리서치 수집/증거 준비 canonical project |
| `review_mvp/` | 전문 코드 리뷰와 선택적 최종 검증 보조 도구 |

## 로드맵 / 아카이브

이전 Step 1-20 로드맵과 체크리스트 본문은 historical pre-freeze material입니다.
현재 작업 라우팅은 [docs/roadmap_status.md](docs/roadmap_status.md)와
[docs/context/MVP_V0_1_BASELINE.md](docs/context/MVP_V0_1_BASELINE.md)를
먼저 사용합니다. 과거 Step 계획이나 검증 근거가 필요하면
[docs/context/ARCHIVE_INDEX.md](docs/context/ARCHIVE_INDEX.md)에서 허용된
lookup reason을 확인한 뒤 가장 좁은 파일만 엽니다.

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

현재 활성 roadmap Step은 없습니다. MVP v0.1은 frozen baseline이며, 새 구현,
확장, scoring/ranking/report/backtest/valuation/data-ingestion 변경은 별도
승인된 post-MVP 버전/Step과 routed context packet이 필요합니다.
