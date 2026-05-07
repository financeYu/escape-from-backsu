param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$RgArgs
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    $pythonExe = "python"
}

& $pythonExe (Join-Path $repoRoot "scripts\run_rg.py") @RgArgs
exit $LASTEXITCODE
