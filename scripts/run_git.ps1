param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$GitArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

if ($GitArgs -and $GitArgs[0] -eq "--") {
    if ($GitArgs.Count -gt 1) {
        $GitArgs = $GitArgs[1..($GitArgs.Count - 1)]
    } else {
        $GitArgs = @()
    }
}

if (-not $GitArgs -or $GitArgs.Count -eq 0) {
    Write-Output "PROJECT_GIT_ERROR: missing git arguments"
    exit 2
}

$gitCandidates = @()
if ($env:PROJECT_GIT -and (Test-Path -LiteralPath $env:PROJECT_GIT -PathType Leaf)) {
    $gitCandidates += $env:PROJECT_GIT
}
$gitCandidates += "C:\Program Files\Git\cmd\git.exe"
$gitCandidates += "C:\Program Files\Git\bin\git.exe"

$gitPath = $gitCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $gitPath) {
    Write-Output "BLOCKED_GIT_ENV: no project-approved git.exe found"
    exit 125
}

$env:GIT_OPTIONAL_LOCKS = "0"
$env:GIT_TERMINAL_PROMPT = "0"
$gitTemp = Join-Path $repoRoot ".pytest_tmp\git_shell"
New-Item -ItemType Directory -Force -Path $gitTemp | Out-Null
$env:TMP = $gitTemp
$env:TEMP = $gitTemp

$command = $GitArgs[0]
$indexWriteCommands = @(
    "add",
    "am",
    "apply",
    "checkout",
    "cherry-pick",
    "commit",
    "merge",
    "mv",
    "rebase",
    "reset",
    "restore",
    "rm",
    "stash",
    "switch"
)

if ($indexWriteCommands -contains $command) {
    if ($env:PROJECT_ALLOW_GIT_INDEX_WRITE -notin @("1", "true", "TRUE", "yes", "YES")) {
        Write-Output "BLOCKED_GIT_INDEX_WRITE: project-local git wrapper blocks index-writing command '$command' by default."
        Write-Output "Run the project finalize path or set PROJECT_ALLOW_GIT_INDEX_WRITE=1 only for an explicitly approved staging/commit operation."
        exit 125
    }

    $lockPath = Join-Path $repoRoot ".git\index.lock"
    if (Test-Path -LiteralPath $lockPath) {
        Write-Output "BLOCKED_GIT_INDEX_LOCK: .git\index.lock already exists; not deleting it automatically."
        exit 125
    }

    $probePath = Join-Path $repoRoot ".git\codex_index_write_probe.tmp"
    try {
        Set-Content -LiteralPath $probePath -Value "probe" -Encoding ASCII -NoNewline
        Remove-Item -LiteralPath $probePath -Force
    } catch {
        Write-Output "BLOCKED_GIT_INDEX_LOCK: cannot write to .git for index-lock operations: $($_.Exception.Message)"
        exit 125
    }
}

& $gitPath @GitArgs
exit $LASTEXITCODE
