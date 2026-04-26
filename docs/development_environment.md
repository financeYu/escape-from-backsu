# Root Development Environment

이 문서는 루트 기준 테스트, 리뷰 도구, 컨텍스트 스크립트를 재현 가능하게 실행하기 위한 최소 개발환경 진입점을 정의한다.

이 설정은 Step 20 최종 Done 검증을 수행하거나 완료 판정을 내리지 않는다. Step 20의 범위, 계약, 산출물, 최종 판정은 별도 Step 20 worktree와 로드맵 게이트에서 관리한다.

## Scope

- 루트 `src` 패키지와 통합 테스트 의존성을 설치한다.
- `reserch_mvp` 연구 수집 CLI를 editable package로 설치한다.
- `chart_mvp/requirements.txt`의 런타임 의존성을 루트 개발환경에 포함한다.
- `review_mvp`는 표준 라이브러리 기반 리뷰 도구로 유지한다.
- live API, 외부 네트워크, secrets, market data cache 요구사항은 기본 개발환경에 포함하지 않는다.

## Python Version

Python 3.11 이상을 사용한다. 루트와 `reserch_mvp` 모두 `tomllib`와 현대 packaging metadata를 기준으로 한다.

## Setup

루트에서 다음 명령을 실행한다.

```powershell
python -m pip install -r requirements-dev.txt
```

이 명령은 다음을 설치한다.

- 루트 package: `-e .[dev]`
- research ingestion package: `-e ./reserch_mvp`
- chart runtime dependencies: `-r chart_mvp/requirements.txt`

## Validation Commands

루트 통합 테스트의 기본 명령은 다음과 같다.

```powershell
python -m pytest -q -p no:cacheprovider
```

변경 범위가 좁을 때는 관련 테스트를 먼저 실행할 수 있다.

```powershell
python -m pytest -q -p no:cacheprovider tests/context
python -m unittest discover -s review_mvp/tests -v
```

Windows local 또는 sandbox 환경에서 pytest temp permission 문제가 반복되면
repository-local temp root를 강제하는 검증 실행기를 사용한다.

```powershell
python scripts/run_local_validation.py context
python scripts/run_local_validation.py reports-backtest
python scripts/run_local_validation.py chart
```

이 실행기는 `.pytest_tmp/local_validation/` 아래에 `TMP`, `TEMP`,
`PYTEST_DEBUG_TEMPROOT`, pytest `--basetemp`를 맞춰 global Temp 권한 문제를
우회한다. 검증 의미를 바꾸지 않으며, Step 완료 판정은 여전히 해당 Step의
gate 문서가 우선한다.

Step 종료나 master integration 맥락에서는 로드맵 문서의 현재 Step-end gate가 우선한다.

## Review And Context Scripts

리뷰 패킷 생성:

```powershell
python scripts/build_review_packet.py --step "<current step>" --stage "<stage name>"
```

최신 Quant project context snapshot 갱신:

```powershell
python scripts/refresh_quant_project_context.py
```

이 context refresh workflow는 local-only이며 paid API 호출이나 secret 저장을 하지 않는다.

## Out Of Scope

- Step 20 최종 Done 검증 수행 또는 완료 주장
- score, ranking, report, backtest, valuation, pipeline semantics 변경
- KOSDAQ150, futures, options, multi-universe 확장
- network-dependent tests를 기본 검증에 포함
- generated chart images, market data caches, runtime reports, secrets를 source control에 포함
