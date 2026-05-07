param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$GitArgs
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\run_git.ps1") @GitArgs
exit $LASTEXITCODE
