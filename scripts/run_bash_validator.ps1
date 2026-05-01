param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ValidatorArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

$candidatePath = if ([System.IO.Path]::IsPathRooted($ScriptPath)) {
    $ScriptPath
} else {
    Join-Path $repoRoot $ScriptPath
}

if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
    Write-Output "BASH_VALIDATOR_ERROR: validator script was not found: $ScriptPath"
    exit 127
}

$validatorPath = (Resolve-Path -LiteralPath $candidatePath).Path
if (-not $validatorPath.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Output "BASH_VALIDATOR_ERROR: validator script must stay inside the repository: $ScriptPath"
    exit 126
}

$relative = $validatorPath.Substring($repoRoot.Length + 1).Replace("\", "/")
if ($relative -notmatch "^\.agents/skills/[^/]+/scripts/[^/]+\.sh$") {
    Write-Output "BASH_VALIDATOR_ERROR: only project-local gate validators under .agents/skills/*/scripts/*.sh are allowed: $relative"
    exit 126
}

$bashCandidates = @()
if ($env:PROJECT_BASH -and (Test-Path -LiteralPath $env:PROJECT_BASH -PathType Leaf)) {
    $bashCandidates += $env:PROJECT_BASH
}
$bashCandidates += "C:\Program Files\Git\bin\bash.exe"
$bashCandidates += "C:\Program Files\Git\usr\bin\bash.exe"
$bashCandidates += "C:\Windows\System32\bash.exe"

$availableBashCandidates = $bashCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
if (-not $availableBashCandidates) {
    Write-Output "BLOCKED_BASH_VALIDATOR: no bash executable found for $relative"
    Write-Output "Record this via .agents/skills/cost-aware-review-refactor/SKILL.md, then route the exact validator through .agents/skills/quant-validator-approval/SKILL.md when required."
    exit 125
}

$argumentList = @($validatorPath)
if ($ValidatorArgs) {
    $argumentList += $ValidatorArgs
}

function ConvertTo-ProcessArgument {
    param([string]$Argument)
    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }
    return '"' + ($Argument -replace '"', '\"') + '"'
}

function Get-BlockedSummary {
    param(
        [string]$RawText,
        [string]$NormalizedText
    )
    if ($NormalizedText -like "*win32 error 5*") {
        return "Git Bash failed with Win32 error 5"
    }
    if ($NormalizedText -like "*couldn't create signal pipe*") {
        return "Git Bash could not create signal pipe"
    }
    if ($NormalizedText -like "*createfilemapping*") {
        return "Git Bash CreateFileMapping failure"
    }
    if ($NormalizedText -like "*wsl.exe --update*" -or $NormalizedText -like "*aka.ms/wslinstall*" -or $NormalizedText -like "*windows subsystem for linux*") {
        return "WSL bash is unavailable or requires install/update"
    }
    return ($RawText.Trim() -replace "\s+", " ")
}

$blockedPatterns = @(
    "Win32 error 5",
    "couldn't create signal pipe",
    "CreateFileMapping",
    "wsl.exe --update",
    "Windows Subsystem for Linux",
    "aka.ms/wslinstall"
)

$blockedAttempts = @()

foreach ($bashPath in $availableBashCandidates) {
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $bashPath
    $processInfo.Arguments = (($argumentList | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " ")
    $processInfo.WorkingDirectory = $repoRoot
    $processInfo.UseShellExecute = $false
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    try {
        [void]$process.Start()
        $stdoutText = $process.StandardOutput.ReadToEnd()
        $stderrText = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
    } catch {
        $blockedAttempts += "bash_path: $bashPath; blocked_error: failed to start bash candidate: $($_.Exception.Message)"
        continue
    }
    $exitCode = $process.ExitCode

    $text = ($stdoutText + $stderrText)
    $normalizedText = ($text -replace "`0", "").ToLowerInvariant()
    $isBlocked = $false
    foreach ($pattern in $blockedPatterns) {
        if ($normalizedText -like "*$($pattern.ToLowerInvariant())*") {
            $isBlocked = $true
            break
        }
    }

    if ($isBlocked) {
        $blockedAttempts += "bash_path: $bashPath; blocked_error: $(Get-BlockedSummary $text $normalizedText)"
        continue
    }

    if ($text.Trim().Length -gt 0) {
        Write-Output $text.TrimEnd()
    }

    exit $exitCode
}

Write-Output "BLOCKED_BASH_VALIDATOR: all bash candidates failed for $relative"
foreach ($attempt in $blockedAttempts) {
    Write-Output $attempt
}
Write-Output "Record this via .agents/skills/cost-aware-review-refactor/SKILL.md, then route the exact validator through .agents/skills/quant-validator-approval/SKILL.md when required."
exit 125
