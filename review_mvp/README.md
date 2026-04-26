# Python Code Review Demo

Swift 기준 리뷰 프롬프트를 Python 기준으로 옮기고, 그 기준 일부를 자동 점검하는 리뷰 프로그램입니다.

`master_mvp` 안에서는 고위험 변경, cross-project 변경, roadmap gate 근처 변경, 또는 unresolved risk가 남은 변경을 점검하는 specialist review 보조 프로젝트로 사용합니다.

기본 리뷰는 가장 좁은 책임 범위를 가진 하위 프로젝트에서 시작합니다. `review_mvp`는 모든 작은 local change의 필수 병목이 아닙니다.

수정 경계도 좁게 유지합니다. `review_mvp` 내부 작업은 기본적으로
`review_mvp` 소유 파일만 수정합니다. 다른 하위 프로젝트나 루트 파일은
해당 하위 프로젝트 또는 master/root가 코드리뷰 수정을 명시적으로 맡긴
경우에만, 구체적인 리뷰 finding을 해결하는 최소 범위로 수정합니다.
그 외에는 findings, handoff, TODO로 넘깁니다.

자세한 호출 기준은 `../docs/review_mvp_policy.md`와 `../docs/review_flow.md`를 따릅니다.

## Python 코드 리뷰 기준

### 보안
- 비밀번호, 토큰, API 키를 평문으로 저장하거나 로그에 출력하지 않습니다.
- 하드코딩된 credentials는 허용하지 않습니다.
- 민감한 값은 환경변수 또는 비밀 관리 도구에서 주입받습니다.
- `subprocess(..., shell=True)`와 TLS 검증 비활성화 같은 위험 설정을 피합니다.

### 안전성
- 리스트/시퀀스 인덱스 접근 전 길이 또는 존재 여부를 확인합니다.
- `eval`, `exec` 같은 위험한 동적 실행은 피합니다.
- `input()`, CLI 인자, 파일/네트워크 입력 등 외부 입력값은 항상 검증합니다.
- mutable default argument와 bare `except:`를 피합니다.

### Python 코드 스타일
- 단순 수집 반복문보다 list comprehension, generator expression, `any()`, `all()`, `next()` 등을 우선 검토합니다.
- 불필요한 재할당을 줄이고 기본은 불변에 가깝게 작성합니다.
- 내부 전용 함수/메서드는 `_name` 형태로 의도를 드러냅니다.

### 일반 품질
- 함수는 단일 책임 원칙(SRP)을 따르도록 너무 길어지지 않게 분리합니다.
- 불필요한 `print` 디버그 로그는 제거합니다.
- 전역 상태보다 주입 가능한 구조를 우선해 테스트 가능성을 높입니다.

## 포함된 리뷰 프로그램

`review.py`는 아래 항목을 정적 분석으로 점검합니다.

- 하드코딩된 비밀번호/API 키/토큰
- 민감 정보의 `print` 또는 로깅
- `eval` / `exec` 사용
- `subprocess(..., shell=True)`
- `requests.*(..., verify=False)`
- 주변 bounds check 없이 보이는 `items[0]`, `items[1]` 같은 직접 인덱스 접근
- `input()` 사용 지점
- mutable default argument
- bare `except:`
- 단순 `append()` 반복문
- 긴 함수
- 내부 API로 보이는 공개 이름

정적 분석이므로 모든 상황을 완벽히 판별하지는 못하며, 최종 리뷰는 사람이 함께 판단해야 합니다.

## 실행 방법

`review_mvp` 내부 변경을 점검할 때는 `review_mvp` 디렉터리 안에서
실행하고 현재 하위 프로젝트만 대상으로 둡니다. 이 local 명령은
`Quant_mvp`, `chart_mvp`, `reserch_mvp`를 스캔하지 않습니다.

기본 텍스트 리포트:

```bash
py -3 review.py .
```

Markdown 리포트:

```bash
py -3 review.py . --format markdown
```

JSON 리포트:

```bash
py -3 review.py . --format json
```

특정 심각도 이상이 있으면 실패 처리:

```bash
py -3 review.py . --fail-on medium
```

특정 디렉터리 제외:

```bash
py -3 review.py . --exclude-dir generated --exclude-dir vendor
```

테스트 실행:

```bash
py -3 -m unittest discover -s tests
```

`master_mvp` 루트에서 실행하는 specialist review:

```bash
py -3 review_mvp/review.py . --exclude-dir data --exclude-dir outputs --exclude-dir __pycache__ --exclude-dir samples --format markdown
py -3 -m unittest discover -s review_mvp/tests -v
```

루트 명령은 `Quant_mvp`, `chart_mvp`, `reserch_mvp` 등 다른 하위
프로젝트까지 검사할 수 있으므로, master/root가 명시적으로 요청한
cross-project 또는 final-validation review에만 사용합니다. 좁은 local
change는 responsible subproject의 local first review와 local
tests/checks만으로 충분할 수 있습니다.

## `/review` 프롬프트 예시

```text
/review

다음 Python 코드에 대해 리뷰해 주세요.

검토 기준:
1. 보안: 평문 비밀번호, 하드코딩된 비밀값, 민감정보 로그 출력, 위험한 subprocess/TLS 설정 여부
2. 안전성: 인덱스 범위 체크, 위험한 동적 실행, 외부 입력 검증, mutable default argument 여부
3. Python 스타일: comprehension/고차 함수 사용 가능성, 불필요한 가변 상태, 내부 API 네이밍
4. 일반 품질: SRP, 디버그 로그, 테스트 가능한 구조

리뷰 결과는 심각도 순으로 정리하고, 파일 경로와 라인 번호를 포함해 주세요.
```
