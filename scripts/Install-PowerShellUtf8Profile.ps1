[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ProjectRoot,
    [switch]$CurrentUserAllHosts
)

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}

$profilePath = if ($CurrentUserAllHosts) {
    $PROFILE.CurrentUserAllHosts
} else {
    $PROFILE.CurrentUserCurrentHost
}

$profileDir = Split-Path -Parent $profilePath
if (-not (Test-Path -LiteralPath $profileDir)) {
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
}

$startMarker = "# >>> master_mvp utf8 >>>"
$endMarker = "# <<< master_mvp utf8 <<<"
$escapedProjectRoot = $ProjectRoot.Replace("'", "''")

$block = @(
    $startMarker,
    "`$masterMvpRoot = '$escapedProjectRoot'",
    "if (`$PWD.Provider.Name -eq 'FileSystem') {",
    "    `$masterMvpCurrentPath = `$PWD.ProviderPath",
    "    `$masterMvpComparison = [System.StringComparison]::OrdinalIgnoreCase",
    "    `$masterMvpIsRoot = `$masterMvpCurrentPath.Equals(`$masterMvpRoot, `$masterMvpComparison)",
    "    `$masterMvpIsChild = `$masterMvpCurrentPath.StartsWith(`$masterMvpRoot + [System.IO.Path]::DirectorySeparatorChar, `$masterMvpComparison)",
    "    if (`$masterMvpIsRoot -or `$masterMvpIsChild) {",
    "        `$masterMvpEncodingScript = Join-Path `$masterMvpRoot 'scripts\Initialize-PowerShellUtf8.ps1'",
    "        if (Test-Path -LiteralPath `$masterMvpEncodingScript) {",
    "            . `$masterMvpEncodingScript -Quiet",
    "        }",
    "    }",
    "}",
    $endMarker
) -join [Environment]::NewLine

$existing = if (Test-Path -LiteralPath $profilePath) {
    Get-Content -LiteralPath $profilePath -Raw
} else {
    ""
}

$pattern = [regex]::Escape($startMarker) + ".*?" + [regex]::Escape($endMarker)
if ($existing -match $pattern) {
    $updated = [regex]::Replace(
        $existing,
        $pattern,
        [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $block },
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
} else {
    $separator = if ($existing.Length -gt 0 -and -not $existing.EndsWith([Environment]::NewLine)) {
        [Environment]::NewLine + [Environment]::NewLine
    } elseif ($existing.Length -gt 0) {
        [Environment]::NewLine
    } else {
        ""
    }
    $updated = $existing + $separator + $block + [Environment]::NewLine
}

if ($PSCmdlet.ShouldProcess($profilePath, "Install project UTF-8 PowerShell profile loader")) {
    Set-Content -LiteralPath $profilePath -Value $updated -Encoding UTF8
    Write-Host "Installed master_mvp UTF-8 loader in $profilePath"
}
