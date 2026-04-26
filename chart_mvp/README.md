# chart_mvp

로컬에서 실행하는 주식 데이터 수집, 기술지표 계산, 차트 렌더링, KOSPI200 Top-5 배치 분석 프로젝트입니다.

현재 프로젝트는 다음 원칙을 유지합니다.

- 로컬 실행 전용
- 웹 UI 없음
- 무거운 프레임워크 없음
- `matplotlib` 기반 로컬 차트 렌더링 유지
- `chart_mvp` 자체 Top-N 스코어링 알고리즘은 legacy placeholder 상태 유지
  - canonical Step 20 latest ranking은 루트 `src.scanner.latest_ranking` 경로가 소유한다.
  - `chart_mvp/outputs/latest_top*.csv|json`은 로컬 차트 런타임 산출물이며 Step 20 ranking evidence가 아니다.

## 구조

```text
chart_mvp/
├─ app/
│  └─ run_daily.py
├─ data/
├─ outputs/
│  └─ charts/
├─ scripts/
│  ├─ run_top5.bat
│  └─ run_top5.sh
├─ src/
│  ├─ app/
│  ├─ chart_mvp/
│  └─ stock_core/
├─ tests/
├─ universe/
│  └─ kospi200_snapshot.csv
├─ main.py
└─ requirements.txt
```

## 설치

```powershell
python -m pip install -r requirements.txt
```

## 수동 실행

### 1. 권장 원클릭 실행

프로젝트 루트에서:

```powershell
python -m app.run_daily
```

빠르게 돌리려면:

```powershell
python -m app.run_daily --pages 1 --workers 8 --no-render-charts
```

### 1-1. 그래픽 인터페이스 실행

Top-5 목록을 보고, 항목을 더블클릭하거나 버튼을 눌러 개별 차트를 확인하려면:

```powershell
python -m app.run_gui
```

이 경로는 기존 실행 호환을 위한 wrapper입니다. 저장소 checkout 루트에서는 새 공유 GUI 모듈로 직접 실행할 수 있습니다.

```powershell
python -m gui_mvp chart
```

GUI 기능:

- Top-5 갱신 실행
- GUI 시작 시 영업일 21시 기준 갱신이 누락되어 있으면 자동 갱신 실행
- 상위 5개 목록 표시
- 선택 종목 차트 창 열기
- 임시 Top-5 override 안내 표시
- 저장된 `latest_top5.csv`가 있으면 GUI 시작 시 즉시 먼저 표시
- `빠른 갱신 모드` 사용 시 최근 데이터 중심으로 더 빠르게 실행
- 진행률 바 표시
- 마지막 갱신 시각 표시
- 자동 새로고침 설정 가능

백테스트 평가는 `chart_mvp`가 아니라 새 `gui_mvp`의 별도 evaluation-only viewer에서 실행합니다.

```powershell
python -m gui_mvp backtest
```

이 백테스트 viewer는 `src.backtest` 결과를 표시만 하며, score/ranking/report 설정이나 산출물을 갱신하지 않습니다.

안전한 경량 실행 예시:

```powershell
python -m app.run_daily --pages 1 --no-render-charts
```

직접 캐시를 무시하려면:

```powershell
python -m app.run_daily --pages 1 --no-cache
```

영업일 오후 9시 기준으로 갱신이 필요할 때만 실행하려면:

```powershell
python -m app.run_daily --due-only
```

이 명령은 `outputs/last_run_meta.json`의 마지막 성공일을 확인합니다. 영업일 21시 이후 성공 기록이 없으면 갱신하고, 이미 갱신되어 있거나 주말이면 조용히 건너뜁니다. 자정 직후에는 직전 날짜가 영업일인 경우 누락 갱신을 보정할 수 있습니다.

유니버스 live refresh를 시도한 뒤 snapshot으로 fallback 하려면:

```powershell
python -m app.run_daily --refresh-universe
```

### 2. 스크립트 실행

Windows:

```powershell
scripts\run_top5.bat --pages 1 --no-render-charts
```

Linux/macOS:

```bash
sh scripts/run_top5.sh --pages 1 --no-render-charts
```

### 3. 기존 단일 종목 차트

```powershell
python main.py single --code 005930 --pages 20
```

## 출력 파일 위치

배치 실행 후 자동으로 아래 파일들이 생성되거나 갱신됩니다.

- `outputs/latest_top5.csv`
- `outputs/latest_top5.json`
- `outputs/last_run_meta.json`
- `outputs/charts/<code>.png`

기존 캐시 파일은 계속 `data/<code>_daily_prices.csv`에 저장됩니다.
재무제표 검증용 캐시는 `data/<code>_financial_statements.csv`에 저장됩니다.

## 캐시 / 유니버스 준비

### 캐시

- 캐시는 자동 생성됩니다.
- 현재 가격 캐시 정책은 그대로 유지됩니다.
  - 평일: 최신 데이터를 다시 가져옴
  - 주말: 기존 캐시가 있으면 재사용

가격 캐시 갱신은 기본적으로 재무제표 캐시를 함께 새로고침하지 않습니다.
재무제표 캐시는 가격 Top-N 배치와 분리해 필요할 때 아래 명령으로 갱신합니다.

Step 2 재무제표 캐시 검증을 재현하려면:

```powershell
python scripts/refresh_financial_cache.py
```

이 명령은 로컬 runtime cache만 갱신합니다. valuation score, technical score, composite, ranking, backtest는 생성하지 않습니다.

### 유니버스 snapshot

우선 경로:

- `universe/kospi200_snapshot.csv`

fallback 경로:

- `src/stock_core/providers/kospi200.csv`

snapshot CSV 형식은 반드시 아래 두 컬럼만 사용해야 합니다.

```text
code,name
005930,삼성전자
000660,SK하이닉스
...
```

규칙:

- `code`는 6자리 종목코드로 정규화됩니다.
- 중복 코드는 제거됩니다.
- 최종적으로 200개 종목이 있어야 합니다.

## 테스트

가벼운 로컬 테스트는 표준 라이브러리 `unittest`로 실행합니다.

```powershell
python -m unittest discover -s tests -v
```

현재 포함된 테스트:

- selector 동작
- trading calendar 동작
- simple helper 동작

## Windows Task Scheduler 등록 예시

1. 작업 스케줄러 열기
2. `기본 작업 만들기` 선택
3. 매일 원하는 시간 지정
4. 프로그램/스크립트:

```text
cmd.exe
```

5. 인수 추가:

```text
/c "%USERPROFILE%\Project\master_mvp\chart_mvp\scripts\run_top5.bat" --due-only --pages 20 --no-render-charts
```

6. 시작 위치:

```text
%USERPROFILE%\Project\master_mvp\chart_mvp
```

## cron 등록 예시

매시간 실행하되, 실제 갱신은 가장 최근 도래한 영업일 오후 9시 기준으로 필요할 때만 수행:

```cron
0 * * * * cd /path/to/chart_mvp && python -m app.run_daily --due-only --pages 20 --no-render-charts
```

## 현재 placeholder 경계

- `score_stock(df)`는 항상 `0.0`을 반환합니다.
- 이 placeholder는 legacy chart runtime 전용입니다. 루트 Step 20 canonical ranking으로 사용하지 않습니다.
- `fetch_kospi200_universe_live()`는 아직 stub입니다.
- `trading_calendar`는 한국 휴장일을 반영하지 않고 평일/주말만 구분합니다.

## 참고

- 차트 렌더링은 기존 `matplotlib` 로컬 방식 그대로 유지됩니다.
- 일부 snapshot 데이터 품질 문제는 배치에서 개별 종목 실패로 기록되고 전체 실행은 계속 진행됩니다.
