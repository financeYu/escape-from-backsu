[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("codex", "quant", "research", "chart", "review", "audit", "docs", "minor", "hotfix")]
    [string]$Role,

    [Parameter(Mandatory = $true)]
    [string]$Step,

    [Parameter(Mandatory = $true)]
    [string]$Scope,

    [string]$BranchName,
    [string]$WorktreeName,
    [string]$TaskType,
    [string]$ActiveStep,
    [string]$OwnerOrWorker = "",
    [string]$Purpose = "",

    [Parameter(Mandatory = $true)]
    [string[]]$AllowedWritePaths,

    [string[]]$ReadOnlyPaths = @(
        "AGENTS.md",
        "docs/project_checklist.md",
        "docs/roadmap_status.md",
        "docs/workspace_parallel_work_policy.md"
    ),

    [string[]]$ForbiddenActions = @(),
    [string[]]$ExpectedOutput = @("branch-local commit", "role-specific handoff summary"),
    [string[]]$RequiredValidation = @("focused validation for changed files", "git status review"),
    [string]$WorktreesRoot,
    [string]$BaseRef = "HEAD",
    [switch]$AllowTrackedManifest,
    [switch]$Lightweight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-GitOutput {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    $output = & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("git {0} failed with exit code {1}" -f ($Arguments -join " "), $LASTEXITCODE)
    }

    return ($output -join [Environment]::NewLine).Trim()
}

function Invoke-GitChecked {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("git {0} failed with exit code {1}" -f ($Arguments -join " "), $LASTEXITCODE)
    }
}

function ConvertTo-Slug {
    param([Parameter(Mandatory = $true)][string]$Value)

    $slug = $Value.Trim().ToLowerInvariant() -replace "[^a-z0-9._-]+", "-"
    $slug = $slug.Trim("-")
    if ([string]::IsNullOrWhiteSpace($slug)) {
        throw "Scope must contain at least one letter or number after slug conversion."
    }

    return $slug
}

function Get-StepToken {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -match "\d+") {
        return ([int]$Matches[0]).ToString("00")
    }

    return (ConvertTo-Slug -Value $Value)
}

function Get-StepLabel {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -match "\d+") {
        return ("Step {0}" -f [int]$Matches[0])
    }

    return $Value.Trim()
}

function ConvertTo-WorktreeName {
    param([Parameter(Mandatory = $true)][string]$Value)

    $name = $Value -replace "[\\/:\s]+", "_"
    $name = $name -replace "[^A-Za-z0-9._-]", "_"
    return $name.Trim("_")
}

function Format-MarkdownList {
    param([string[]]$Items)

    if (-not $Items -or $Items.Count -eq 0) {
        return "- TBD"
    }

    return (($Items | ForEach-Object { "- {0}" -f $_ }) -join [Environment]::NewLine)
}

$commonGitDir = Get-GitOutput rev-parse --path-format=absolute --git-common-dir
$mainRepoRoot = Split-Path -Parent $commonGitDir
$baseCommit = Get-GitOutput rev-parse $BaseRef
$trackedManifestAtBase = Get-GitOutput ls-tree --name-only $baseCommit -- WORKSPACE_MANIFEST.md
$stepToken = Get-StepToken -Value $Step
$scopeSlug = ConvertTo-Slug -Value $Scope

if (-not $BranchName) {
    $BranchName = ("{0}/step{1}-{2}" -f $Role, $stepToken, $scopeSlug)
}

if (-not $WorktreeName) {
    $WorktreeName = ConvertTo-WorktreeName -Value $BranchName
}

if (-not $TaskType) {
    $TaskType = if ($Lightweight) { ("{0}_lightweight_support" -f $Role) } else { ("{0}_support" -f $Role) }
}

if (-not $ActiveStep) {
    $ActiveStep = Get-StepLabel -Value $Step
}

if (-not $Purpose) {
    $Purpose = "Create a bounded role worktree for the declared task without mixing implementation, review, audit, research, or master integration work."
}

if (-not $WorktreesRoot) {
    $WorktreesRoot = Join-Path (Split-Path -Parent $mainRepoRoot) "worktrees"
}

$existingBranch = Get-GitOutput branch --list $BranchName
if ($existingBranch) {
    throw ("Branch already exists: {0}" -f $BranchName)
}

if ($trackedManifestAtBase -and -not $AllowTrackedManifest) {
    throw "BaseRef already tracks WORKSPACE_MANIFEST.md. Use a base without a tracked root manifest, remove/promote that manifest through master integration, or rerun with -AllowTrackedManifest after confirming the merge-conflict risk."
}

$worktreePath = Join-Path $WorktreesRoot $WorktreeName
if (Test-Path -LiteralPath $worktreePath) {
    throw ("Worktree path already exists: {0}" -f $worktreePath)
}

$commonForbidden = @(
    "roadmap status or final Step verdict changes unless explicitly assigned",
    "ranking output, composite scoring, backtest, valuation/fundamental scoring, or trading signals unless explicitly assigned by the active Step",
    "financial/fundamental data in technical_composite_score or final_composite_score",
    "generated market-data output commits unless explicitly promoted as review fixtures",
    "unrelated worktree cleanup, staging, committing, merging, or reset operations"
)

if ($Lightweight) {
    $commonForbidden += "expanding beyond Level 1 lightweight support without updating scope through master/root approval"
}

$allForbidden = $commonForbidden + $ForbiddenActions

if ($PSCmdlet.ShouldProcess($worktreePath, "Create role worktree $BranchName")) {
    if (-not (Test-Path -LiteralPath $WorktreesRoot)) {
        New-Item -ItemType Directory -Force -Path $WorktreesRoot | Out-Null
    }

    Invoke-GitChecked worktree add -b $BranchName $worktreePath $baseCommit

    $manifestLines = @(
        "# WORKSPACE_MANIFEST",
        "",
        ("workspace_id: {0}" -f $WorktreeName),
        ("branch: {0}" -f $BranchName),
        ("task_type: {0}" -f $TaskType),
        ("active_step: {0}" -f $ActiveStep),
        ("owner_or_worker: {0}" -f $OwnerOrWorker),
        ("created_from_commit: {0}" -f $baseCommit),
        "",
        "## Purpose",
        "",
        $Purpose,
        "",
        "## Allowed write paths",
        "",
        (Format-MarkdownList -Items $AllowedWritePaths),
        "",
        "## Read-only paths",
        "",
        (Format-MarkdownList -Items $ReadOnlyPaths),
        "",
        "## Forbidden actions",
        "",
        (Format-MarkdownList -Items $allForbidden),
        "",
        "## Expected output",
        "",
        (Format-MarkdownList -Items $ExpectedOutput),
        "",
        "## Required validation",
        "",
        (Format-MarkdownList -Items $RequiredValidation),
        "",
        "## Handoff notes",
        "",
        "Update this manifest before editing outside the allowed write paths.",
        "After focused validation passes, commit source-controlled branch changes by default and report the commit SHA.",
        "Do not stage the local WORKSPACE_MANIFEST.md unless the master explicitly promotes it."
    )

    $manifest = $manifestLines -join [Environment]::NewLine
    $manifestPath = Join-Path $worktreePath "WORKSPACE_MANIFEST.md"
    if ((Test-Path -LiteralPath $manifestPath) -and -not $AllowTrackedManifest) {
        throw ("Manifest already exists at {0}. Rerun with -AllowTrackedManifest only after confirming the merge-conflict risk." -f $manifestPath)
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($manifestPath, $manifest + [Environment]::NewLine, $utf8NoBom)

    Write-Host ("Created worktree: {0}" -f $worktreePath)
    Write-Host ("Created branch:   {0}" -f $BranchName)
    Write-Host ("Created manifest: {0}" -f $manifestPath)
}
