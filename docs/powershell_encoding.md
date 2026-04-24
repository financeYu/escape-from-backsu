# PowerShell 인코딩 설정

이 저장소의 문서와 소스 파일은 UTF-8을 기준으로 관리한다.
Windows PowerShell 5.1은 기본 코드 페이지나 파일 입출력 기본값 때문에 한글 출력이 깨질 수 있으므로, 프로젝트 PowerShell 세션에서는 UTF-8을 명시적으로 켠다.

## 현재 세션에 적용

프로젝트 루트에서 아래 명령을 실행한다.

```powershell
. .\scripts\Initialize-PowerShellUtf8.ps1
```

이 스크립트는 현재 PowerShell 세션에 다음 값을 설정한다.

- `[Console]::InputEncoding`
- `[Console]::OutputEncoding`
- `$OutputEncoding`
- 주요 파일 입출력 명령의 `Encoding` 기본값
- `PYTHONUTF8`와 `PYTHONIOENCODING`
- Windows 콘솔 코드 페이지 `65001`

## 프로젝트 자동 적용 설치

새 PowerShell을 프로젝트 폴더에서 열 때 자동 적용하려면 한 번만 실행한다.

```powershell
.\scripts\Install-PowerShellUtf8Profile.ps1
```

설치 스크립트는 현재 사용자 PowerShell profile에 `master_mvp` 경로 안에서만 동작하는 로더 블록을 추가한다.
기존 블록이 있으면 갱신하고, 다른 profile 내용은 유지한다.

설치 후 이미 열려 있는 PowerShell에는 자동으로 적용되지 않으므로 새 터미널을 열거나 현재 세션 적용 명령을 실행한다.

## 확인

아래 출력에서 한글이 깨지지 않으면 정상이다.

```powershell
. .\scripts\Initialize-PowerShellUtf8.ps1 -Quiet
Get-Content .\docs\project_checklist.md -First 3
```
