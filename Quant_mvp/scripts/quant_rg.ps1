param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RgArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$rgPath = Join-Path $repoRoot "tools\rg\rg.exe"

if (-not (Test-Path -LiteralPath $rgPath -PathType Leaf)) {
    Write-Error "Project-local ripgrep was not found at $rgPath"
    exit 127
}

& $rgPath @RgArgs
exit $LASTEXITCODE
